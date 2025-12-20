"""Referral system service for invite tracking."""

import hashlib
import base64
from typing import Optional, Dict
import structlog

logger = structlog.get_logger()


class ReferralService:
    """Service for managing referral links and tracking."""

    # Bot username for generating links
    BOT_USERNAME = "aibroker_bot"

    def __init__(self):
        """Initialize referral service."""
        self._analytics_service = None

    @property
    def analytics(self):
        """Lazy load analytics service to avoid circular imports."""
        if self._analytics_service is None:
            from app.services.analytics_service import analytics_service
            self._analytics_service = analytics_service
        return self._analytics_service

    def _generate_code(self, user_id: str) -> str:
        """Generate deterministic referral code from user_id.

        Uses SHA256 hash for short, URL-safe codes.
        Example: user_id=123456789 -> ref_8M0kX2
        """
        hash_bytes = hashlib.sha256(user_id.encode()).digest()[:6]
        code = base64.urlsafe_b64encode(hash_bytes).decode().rstrip('=')
        return f"ref_{code}"

    def get_or_create_referral_code(self, user_id: str) -> str:
        """Get existing or create new referral code for user."""
        conn = self.analytics._get_connection()
        try:
            # Check if user already has a code
            cursor = conn.execute(
                'SELECT referral_code FROM users WHERE user_id = ?',
                (user_id,)
            )
            row = cursor.fetchone()

            if row and row['referral_code']:
                return row['referral_code']

            # Generate new code
            code = self._generate_code(user_id)

            # Save to database
            conn.execute(
                'UPDATE users SET referral_code = ? WHERE user_id = ?',
                (code, user_id)
            )
            conn.commit()

            logger.info("referral_code_created", user_id=user_id, code=code)
            return code

        except Exception as e:
            logger.error("referral_code_create_error", user_id=user_id, error=str(e))
            # Fallback: generate code without saving
            return self._generate_code(user_id)
        finally:
            conn.close()

    def get_referral_link(self, user_id: str) -> str:
        """Get full referral link for user."""
        code = self.get_or_create_referral_code(user_id)
        return f"https://t.me/{self.BOT_USERNAME}?start={code}"

    def find_referrer_by_code(self, code: str) -> Optional[str]:
        """Find referrer user_id by referral code.

        Args:
            code: Referral code (e.g., 'ref_8M0kX2')

        Returns:
            referrer_id if found, None otherwise
        """
        if not code or not code.startswith("ref_"):
            return None

        conn = self.analytics._get_connection()
        try:
            cursor = conn.execute(
                'SELECT user_id FROM users WHERE referral_code = ?',
                (code,)
            )
            row = cursor.fetchone()
            return row['user_id'] if row else None
        except Exception as e:
            logger.error("find_referrer_error", code=code, error=str(e))
            return None
        finally:
            conn.close()

    def process_referral(self, new_user_id: str, start_param: str) -> Optional[str]:
        """Process referral when new user joins with ref link.

        Args:
            new_user_id: New user's Telegram ID
            start_param: Parameter from /start command (e.g., 'ref_8M0kX2')

        Returns:
            referrer_id if valid referral was processed, None otherwise
        """
        if not start_param or not start_param.startswith("ref_"):
            return None

        # Find referrer by code
        referrer_id = self.find_referrer_by_code(start_param)
        if not referrer_id:
            logger.warning("referral_code_not_found", code=start_param)
            return None

        # Don't allow self-referral
        if referrer_id == new_user_id:
            logger.debug("referral_self_skipped", user_id=new_user_id)
            return None

        conn = self.analytics._get_connection()
        try:
            # Check if user was already referred
            cursor = conn.execute(
                'SELECT 1 FROM referrals WHERE referred_id = ?',
                (new_user_id,)
            )
            if cursor.fetchone():
                logger.debug("referral_already_exists", referred_id=new_user_id)
                return None

            # Save referral
            conn.execute('''
                INSERT INTO referrals (referrer_id, referred_id)
                VALUES (?, ?)
            ''', (referrer_id, new_user_id))

            # Update user's referred_by field
            conn.execute('''
                UPDATE users SET referred_by = ? WHERE user_id = ?
            ''', (referrer_id, new_user_id))

            conn.commit()

            logger.info("referral_processed",
                       referrer=referrer_id,
                       referred=new_user_id,
                       code=start_param)

            return referrer_id

        except Exception as e:
            logger.error("referral_process_error",
                        new_user_id=new_user_id,
                        start_param=start_param,
                        error=str(e))
            return None
        finally:
            conn.close()

    def get_referral_stats(self, user_id: str) -> Dict:
        """Get referral statistics for user.

        Returns:
            Dict with 'total_referred' count and 'referral_link'
        """
        conn = self.analytics._get_connection()
        try:
            cursor = conn.execute('''
                SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?
            ''', (user_id,))
            total = cursor.fetchone()['count']

            return {
                "total_referred": total,
                "referral_link": self.get_referral_link(user_id)
            }
        except Exception as e:
            logger.error("referral_stats_error", user_id=user_id, error=str(e))
            return {
                "total_referred": 0,
                "referral_link": self.get_referral_link(user_id)
            }
        finally:
            conn.close()

    def mark_notified(self, referred_id: str) -> bool:
        """Mark referral as notified (notification sent to referrer).

        Args:
            referred_id: The new user who was referred

        Returns:
            True if updated successfully
        """
        conn = self.analytics._get_connection()
        try:
            conn.execute('''
                UPDATE referrals SET notified = 1 WHERE referred_id = ?
            ''', (referred_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error("mark_notified_error", referred_id=referred_id, error=str(e))
            return False
        finally:
            conn.close()


# Global singleton instance
referral_service = ReferralService()
