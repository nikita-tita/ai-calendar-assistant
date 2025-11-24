"""Admin authentication service with two-factor password protection."""

import bcrypt
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict
import structlog

logger = structlog.get_logger()


class AdminAuthService:
    """
    Two-factor password authentication for admin panel.

    Requires two separate passwords for access:
    - Primary password: Main admin password
    - Secondary password: Additional verification password
    """

    def __init__(self):
        """Initialize admin auth service."""
        # Get passwords from environment variables
        primary_password = os.getenv("ADMIN_PRIMARY_PASSWORD")
        secondary_password = os.getenv("ADMIN_SECONDARY_PASSWORD")

        if not primary_password or not secondary_password:
            logger.error("admin_passwords_not_set",
                        message="ADMIN_PRIMARY_PASSWORD and ADMIN_SECONDARY_PASSWORD must be set in environment")
            raise ValueError("Admin passwords not configured. Set ADMIN_PRIMARY_PASSWORD and ADMIN_SECONDARY_PASSWORD in .env file")

        # Primary password hash (bcrypt with salt)
        self.primary_hash = self._hash_password(primary_password)

        # Secondary password hash (bcrypt with salt)
        self.secondary_hash = self._hash_password(secondary_password)

        # Session storage (user_id -> session data)
        self._sessions: Dict[str, dict] = {}

        # Session timeout (1 hour)
        self.session_timeout = timedelta(hours=1)

        logger.info("admin_auth_initialized")

    def _hash_password(self, password: str) -> bytes:
        """
        Hash password using bcrypt with automatic salt generation.

        bcrypt is more secure than SHA-256 because:
        - Includes automatic salt generation
        - Computationally expensive (resistant to brute-force)
        - Industry standard for password hashing
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

    def _verify_password(self, password: str, hashed: bytes) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)

    def authenticate(self, primary_password: str, secondary_password: str) -> Optional[str]:
        """
        Authenticate admin with two passwords.

        Args:
            primary_password: First password
            secondary_password: Second password

        Returns:
            Session token if authenticated, None otherwise
        """
        # Use bcrypt's built-in timing-safe comparison
        primary_valid = self._verify_password(primary_password, self.primary_hash)
        secondary_valid = self._verify_password(secondary_password, self.secondary_hash)

        if primary_valid and secondary_valid:
            # Generate session token
            session_token = secrets.token_urlsafe(32)

            # Store session
            self._sessions[session_token] = {
                'created_at': datetime.now(),
                'last_activity': datetime.now()
            }

            logger.info("admin_authenticated", session_token=session_token[:8] + "...")
            return session_token
        else:
            logger.warning("admin_auth_failed")
            return None

    def verify_session(self, session_token: str) -> bool:
        """
        Verify if session token is valid.

        Args:
            session_token: Session token to verify

        Returns:
            True if session is valid, False otherwise
        """
        if session_token not in self._sessions:
            return False

        session = self._sessions[session_token]
        now = datetime.now()

        # Check if session expired
        if now - session['last_activity'] > self.session_timeout:
            del self._sessions[session_token]
            logger.info("admin_session_expired", session_token=session_token[:8] + "...")
            return False

        # Update last activity
        session['last_activity'] = now
        return True

    def logout(self, session_token: str):
        """Logout and invalidate session."""
        if session_token in self._sessions:
            del self._sessions[session_token]
            logger.info("admin_logged_out", session_token=session_token[:8] + "...")

    def get_active_sessions_count(self) -> int:
        """Get number of active admin sessions."""
        return len(self._sessions)

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired_tokens = [
            token for token, session in self._sessions.items()
            if now - session['last_activity'] > self.session_timeout
        ]

        for token in expired_tokens:
            del self._sessions[token]

        if expired_tokens:
            logger.info("admin_sessions_cleaned", count=len(expired_tokens))


# Global instance
admin_auth_service = AdminAuthService()
