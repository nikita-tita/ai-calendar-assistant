"""Rate limiting and spam detection service."""

from datetime import datetime, timedelta
from typing import Dict, List
import structlog

logger = structlog.get_logger()


class RateLimiter:
    """
    Rate limiting and spam detection for bot users.

    Protection rules:
    1. Max 10 messages per minute per user
    2. Max 50 messages per hour per user
    3. Auto-block after 3 rapid bursts (5+ messages in 10 seconds)
    4. Temporary ban: 1 hour
    5. Error flood detection: 5+ errors in 1 minute = block
    """

    def __init__(self):
        """Initialize rate limiter."""
        # User message history: user_id -> list of timestamps
        self._message_history: Dict[str, List[datetime]] = {}

        # User error history: user_id -> list of error timestamps
        self._error_history: Dict[str, List[datetime]] = {}

        # Blocked users: user_id -> block_until timestamp
        self._blocked_users: Dict[str, datetime] = {}

        # Burst detection: user_id -> burst_count
        self._burst_count: Dict[str, int] = {}

        # Rate limits
        self.MAX_MESSAGES_PER_MINUTE = 10
        self.MAX_MESSAGES_PER_HOUR = 50
        self.MAX_ERRORS_PER_MINUTE = 5
        self.RAPID_BURST_THRESHOLD = 5  # messages
        self.RAPID_BURST_WINDOW = 10  # seconds
        self.MAX_BURSTS_BEFORE_BLOCK = 3
        self.BLOCK_DURATION = timedelta(hours=1)

        logger.info("rate_limiter_initialized",
                   max_per_minute=self.MAX_MESSAGES_PER_MINUTE,
                   max_per_hour=self.MAX_MESSAGES_PER_HOUR)

    def is_blocked(self, user_id: str) -> bool:
        """
        Check if user is currently blocked.

        Args:
            user_id: User ID to check

        Returns:
            True if user is blocked, False otherwise
        """
        if user_id not in self._blocked_users:
            return False

        block_until = self._blocked_users[user_id]
        now = datetime.now()

        if now >= block_until:
            # Block expired, remove it
            del self._blocked_users[user_id]
            if user_id in self._burst_count:
                del self._burst_count[user_id]
            logger.info("user_unblocked", user_id=user_id)
            return False

        return True

    def check_rate_limit(self, user_id: str) -> tuple[bool, str]:
        """
        Check if user has exceeded rate limits.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (is_allowed, reason)
            - is_allowed: True if request is allowed, False if blocked
            - reason: Reason for blocking (empty if allowed)
        """
        # Check if user is blocked
        if self.is_blocked(user_id):
            block_until = self._blocked_users[user_id]
            minutes_left = int((block_until - datetime.now()).total_seconds() / 60)
            return False, f"blocked_until_{minutes_left}_min"

        now = datetime.now()

        # Initialize user history if not exists
        if user_id not in self._message_history:
            self._message_history[user_id] = []

        # Clean old messages (older than 1 hour)
        self._message_history[user_id] = [
            ts for ts in self._message_history[user_id]
            if now - ts < timedelta(hours=1)
        ]

        # Check rate limits
        messages_last_minute = sum(
            1 for ts in self._message_history[user_id]
            if now - ts < timedelta(minutes=1)
        )

        messages_last_hour = len(self._message_history[user_id])

        # Check per-minute limit
        if messages_last_minute >= self.MAX_MESSAGES_PER_MINUTE:
            logger.warning("rate_limit_exceeded_minute",
                          user_id=user_id,
                          count=messages_last_minute)
            return False, "too_many_requests_per_minute"

        # Check per-hour limit
        if messages_last_hour >= self.MAX_MESSAGES_PER_HOUR:
            logger.warning("rate_limit_exceeded_hour",
                          user_id=user_id,
                          count=messages_last_hour)
            return False, "too_many_requests_per_hour"

        # Check for rapid bursts (spam detection)
        messages_last_10sec = sum(
            1 for ts in self._message_history[user_id]
            if now - ts < timedelta(seconds=self.RAPID_BURST_WINDOW)
        )

        if messages_last_10sec >= self.RAPID_BURST_THRESHOLD:
            # Rapid burst detected
            if user_id not in self._burst_count:
                self._burst_count[user_id] = 0

            self._burst_count[user_id] += 1

            logger.warning("rapid_burst_detected",
                          user_id=user_id,
                          burst_count=self._burst_count[user_id],
                          messages_in_10sec=messages_last_10sec)

            if self._burst_count[user_id] >= self.MAX_BURSTS_BEFORE_BLOCK:
                # Block user for spamming
                self._block_user(user_id, "repeated_rapid_bursts")
                return False, "blocked_for_spamming"

            return False, "slow_down_please"

        # All checks passed
        return True, ""

    def record_message(self, user_id: str):
        """
        Record a message from user.

        Args:
            user_id: User ID
        """
        now = datetime.now()

        if user_id not in self._message_history:
            self._message_history[user_id] = []

        self._message_history[user_id].append(now)

    def record_error(self, user_id: str):
        """
        Record an error from user request.

        Args:
            user_id: User ID
        """
        now = datetime.now()

        if user_id not in self._error_history:
            self._error_history[user_id] = []

        # Clean old errors
        self._error_history[user_id] = [
            ts for ts in self._error_history[user_id]
            if now - ts < timedelta(minutes=1)
        ]

        self._error_history[user_id].append(now)

        # Check for error flood
        if len(self._error_history[user_id]) >= self.MAX_ERRORS_PER_MINUTE:
            logger.warning("error_flood_detected",
                          user_id=user_id,
                          error_count=len(self._error_history[user_id]))
            self._block_user(user_id, "error_flood")

    def _block_user(self, user_id: str, reason: str):
        """
        Block user for spam/abuse.

        Args:
            user_id: User ID to block
            reason: Reason for blocking
        """
        block_until = datetime.now() + self.BLOCK_DURATION
        self._blocked_users[user_id] = block_until

        logger.warning("user_blocked",
                      user_id=user_id,
                      reason=reason,
                      block_duration_hours=self.BLOCK_DURATION.total_seconds() / 3600)

    def get_stats(self, user_id: str) -> dict:
        """
        Get rate limiting stats for user.

        Args:
            user_id: User ID

        Returns:
            Dict with user stats
        """
        now = datetime.now()

        if user_id not in self._message_history:
            return {
                "messages_last_minute": 0,
                "messages_last_hour": 0,
                "is_blocked": False,
                "burst_count": 0
            }

        messages_last_minute = sum(
            1 for ts in self._message_history[user_id]
            if now - ts < timedelta(minutes=1)
        )

        messages_last_hour = sum(
            1 for ts in self._message_history[user_id]
            if now - ts < timedelta(hours=1)
        )

        return {
            "messages_last_minute": messages_last_minute,
            "messages_last_hour": messages_last_hour,
            "is_blocked": self.is_blocked(user_id),
            "burst_count": self._burst_count.get(user_id, 0)
        }

    def cleanup_old_data(self):
        """Clean up old tracking data (run periodically)."""
        now = datetime.now()

        # Clean message history
        for user_id in list(self._message_history.keys()):
            self._message_history[user_id] = [
                ts for ts in self._message_history[user_id]
                if now - ts < timedelta(hours=1)
            ]

            if not self._message_history[user_id]:
                del self._message_history[user_id]

        # Clean error history
        for user_id in list(self._error_history.keys()):
            self._error_history[user_id] = [
                ts for ts in self._error_history[user_id]
                if now - ts < timedelta(minutes=1)
            ]

            if not self._error_history[user_id]:
                del self._error_history[user_id]

        # Clean expired blocks
        for user_id in list(self._blocked_users.keys()):
            if now >= self._blocked_users[user_id]:
                del self._blocked_users[user_id]
                if user_id in self._burst_count:
                    del self._burst_count[user_id]

        logger.info("rate_limiter_cleanup_completed")


# Global instance
rate_limiter = RateLimiter()
