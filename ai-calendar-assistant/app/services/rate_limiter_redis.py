"""Redis-based distributed rate limiting and spam detection service."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog
import redis
from redis.exceptions import RedisError

from app.config import settings

logger = structlog.get_logger()


class RedisRateLimiter:
    """
    Distributed rate limiting using Redis.

    Protection rules:
    1. Max 10 messages per minute per user
    2. Max 50 messages per hour per user
    3. Auto-block after 3 rapid bursts (5+ messages in 10 seconds)
    4. Temporary ban: 1 hour
    5. Error flood detection: 5+ errors in 1 minute = block

    Benefits:
    - Works across multiple application instances
    - Persistent across restarts
    - TTL-based automatic cleanup
    """

    def __init__(self):
        """Initialize Redis rate limiter."""
        # Connect to Redis
        try:
            # Build connection kwargs - only include password if set
            redis_kwargs = {
                "decode_responses": True,
                "socket_timeout": 5,
                "socket_connect_timeout": 5
            }
            if settings.redis_password:
                redis_kwargs["password"] = settings.redis_password

            self.redis = redis.from_url(settings.redis_url, **redis_kwargs)
            # Test connection
            self.redis.ping()
            logger.info("redis_rate_limiter_initialized", url=settings.redis_url)
        except RedisError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

        # Rate limits
        self.MAX_MESSAGES_PER_MINUTE = 10
        self.MAX_MESSAGES_PER_HOUR = 50
        self.MAX_ERRORS_PER_MINUTE = 5
        self.RAPID_BURST_THRESHOLD = 5  # messages
        self.RAPID_BURST_WINDOW = 10  # seconds
        self.MAX_BURSTS_BEFORE_BLOCK = 3
        self.BLOCK_DURATION_SECONDS = 3600  # 1 hour

    def _get_key(self, user_id: str, key_type: str) -> str:
        """Generate Redis key for user data."""
        return f"rate_limit:{user_id}:{key_type}"

    def is_blocked(self, user_id: str) -> bool:
        """
        Check if user is currently blocked.

        Args:
            user_id: User ID to check

        Returns:
            True if user is blocked, False otherwise
        """
        try:
            block_key = self._get_key(user_id, "blocked")
            return self.redis.exists(block_key) > 0
        except RedisError as e:
            logger.error("redis_is_blocked_error", user_id=user_id, error=str(e))
            # Fail open (allow request) on Redis errors
            return False

    def check_rate_limit(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user has exceeded rate limits.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (is_allowed, reason)
        """
        try:
            # Check if blocked
            if self.is_blocked(user_id):
                block_key = self._get_key(user_id, "blocked")
                ttl = self.redis.ttl(block_key)
                minutes_left = max(1, ttl // 60)
                return False, f"blocked_until_{minutes_left}_min"

            now = int(datetime.now().timestamp())

            # Per-minute rate limit (sliding window)
            minute_key = self._get_key(user_id, f"minute:{now // 60}")
            minute_count = self.redis.incr(minute_key)
            if minute_count == 1:
                self.redis.expire(minute_key, 60)  # TTL 60 seconds

            if minute_count > self.MAX_MESSAGES_PER_MINUTE:
                logger.warning("rate_limit_exceeded_minute",
                             user_id=user_id,
                             count=minute_count)
                return False, "too_many_requests_per_minute"

            # Per-hour rate limit (sliding window)
            hour_key = self._get_key(user_id, f"hour:{now // 3600}")
            hour_count = self.redis.incr(hour_key)
            if hour_count == 1:
                self.redis.expire(hour_key, 3600)  # TTL 1 hour

            if hour_count > self.MAX_MESSAGES_PER_HOUR:
                logger.warning("rate_limit_exceeded_hour",
                             user_id=user_id,
                             count=hour_count)
                return False, "too_many_requests_per_hour"

            # Rapid burst detection (10-second window)
            burst_key = self._get_key(user_id, f"burst:{now // self.RAPID_BURST_WINDOW}")
            burst_count = self.redis.incr(burst_key)
            if burst_count == 1:
                self.redis.expire(burst_key, self.RAPID_BURST_WINDOW)

            if burst_count >= self.RAPID_BURST_THRESHOLD:
                # Rapid burst detected - increment burst counter
                burst_counter_key = self._get_key(user_id, "burst_counter")
                total_bursts = self.redis.incr(burst_counter_key)
                self.redis.expire(burst_counter_key, 3600)  # Reset after 1 hour

                logger.warning("rapid_burst_detected",
                             user_id=user_id,
                             burst_count=total_bursts,
                             messages_in_window=burst_count)

                if total_bursts >= self.MAX_BURSTS_BEFORE_BLOCK:
                    # Block user for spamming
                    self._block_user(user_id, "repeated_rapid_bursts")
                    return False, "blocked_for_spamming"

                return False, "slow_down_please"

            # All checks passed
            return True, ""

        except RedisError as e:
            logger.error("redis_check_rate_limit_error", user_id=user_id, error=str(e))
            # Fail open on Redis errors
            return True, ""

    def record_message(self, user_id: str):
        """
        Record a message from user.

        Note: Recording is done automatically in check_rate_limit via incr.
        This method is kept for API compatibility.
        """
        pass  # Already recorded in check_rate_limit

    def record_error(self, user_id: str):
        """
        Record an error from user request.

        Blocks user if too many errors in short time.

        Args:
            user_id: User ID
        """
        try:
            now = int(datetime.now().timestamp())
            error_key = self._get_key(user_id, f"errors:{now // 60}")

            error_count = self.redis.incr(error_key)
            if error_count == 1:
                self.redis.expire(error_key, 60)

            if error_count >= self.MAX_ERRORS_PER_MINUTE:
                logger.warning("error_flood_detected",
                             user_id=user_id,
                             error_count=error_count)
                self._block_user(user_id, "error_flood")

        except RedisError as e:
            logger.error("redis_record_error_failed", user_id=user_id, error=str(e))

    def _block_user(self, user_id: str, reason: str):
        """
        Block user for spam/abuse.

        Args:
            user_id: User ID to block
            reason: Reason for blocking
        """
        try:
            block_key = self._get_key(user_id, "blocked")
            self.redis.setex(
                block_key,
                self.BLOCK_DURATION_SECONDS,
                reason
            )

            logger.warning("user_blocked",
                         user_id=user_id,
                         reason=reason,
                         duration_hours=self.BLOCK_DURATION_SECONDS / 3600)

        except RedisError as e:
            logger.error("redis_block_user_failed", user_id=user_id, error=str(e))

    def unblock_user(self, user_id: str):
        """
        Manually unblock a user.

        Args:
            user_id: User ID to unblock
        """
        try:
            block_key = self._get_key(user_id, "blocked")
            self.redis.delete(block_key)

            # Reset burst counter
            burst_counter_key = self._get_key(user_id, "burst_counter")
            self.redis.delete(burst_counter_key)

            logger.info("user_unblocked", user_id=user_id)

        except RedisError as e:
            logger.error("redis_unblock_user_failed", user_id=user_id, error=str(e))

    def get_stats(self, user_id: str) -> dict:
        """
        Get rate limiting stats for user.

        Args:
            user_id: User ID

        Returns:
            Dict with user stats
        """
        try:
            now = int(datetime.now().timestamp())

            # Get current minute/hour counts
            minute_key = self._get_key(user_id, f"minute:{now // 60}")
            hour_key = self._get_key(user_id, f"hour:{now // 3600}")
            burst_counter_key = self._get_key(user_id, "burst_counter")

            minute_count = int(self.redis.get(minute_key) or 0)
            hour_count = int(self.redis.get(hour_key) or 0)
            burst_count = int(self.redis.get(burst_counter_key) or 0)

            return {
                "messages_last_minute": minute_count,
                "messages_last_hour": hour_count,
                "is_blocked": self.is_blocked(user_id),
                "burst_count": burst_count,
                "max_per_minute": self.MAX_MESSAGES_PER_MINUTE,
                "max_per_hour": self.MAX_MESSAGES_PER_HOUR
            }

        except RedisError as e:
            logger.error("redis_get_stats_error", user_id=user_id, error=str(e))
            return {
                "messages_last_minute": 0,
                "messages_last_hour": 0,
                "is_blocked": False,
                "burst_count": 0,
                "error": str(e)
            }

    def cleanup_old_data(self):
        """
        Clean up old tracking data.

        Note: With Redis TTL, cleanup happens automatically.
        This method is kept for API compatibility.
        """
        logger.info("redis_rate_limiter_cleanup_skipped",
                   reason="TTL handles cleanup automatically")

    def get_connection_status(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if connected, False otherwise
        """
        try:
            self.redis.ping()
            return True
        except RedisError:
            return False


# Global instance - will be initialized by application
rate_limiter_redis: Optional[RedisRateLimiter] = None


def init_redis_rate_limiter():
    """Initialize global Redis rate limiter instance."""
    global rate_limiter_redis
    try:
        rate_limiter_redis = RedisRateLimiter()
        logger.info("redis_rate_limiter_global_initialized")
    except Exception as e:
        logger.error("redis_rate_limiter_init_failed", error=str(e))
        rate_limiter_redis = None


def get_rate_limiter():
    """
    Get the best available rate limiter.

    Priority:
    1. Redis rate limiter (persistent, distributed)
    2. In-memory rate limiter (fallback)

    Returns:
        Rate limiter instance (Redis or in-memory)
    """
    if rate_limiter_redis is not None:
        return rate_limiter_redis

    # Fallback to in-memory rate limiter
    from app.services.rate_limiter import rate_limiter
    logger.warning(
        "using_memory_rate_limiter",
        message="Redis rate limiter unavailable, using in-memory fallback. "
                "Rate limits will reset on application restart."
    )
    return rate_limiter


def is_redis_available() -> bool:
    """Check if Redis rate limiter is available and healthy."""
    if rate_limiter_redis is None:
        return False
    return rate_limiter_redis.get_connection_status()
