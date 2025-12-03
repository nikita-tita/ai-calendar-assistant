"""JWT-based admin authentication service with IP/User-Agent binding."""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = structlog.get_logger()


class AdminAuthJWT:
    """
    JWT-based two-factor password authentication for admin panel.

    Features:
    - RS256 signature (asymmetric keys)
    - IP address binding
    - User-Agent fingerprinting
    - Automatic token expiration (1 hour)
    - Token refresh capability
    """

    def __init__(self):
        """Initialize JWT admin auth service."""
        # Get passwords from environment
        primary_password = os.getenv("ADMIN_PRIMARY_PASSWORD")
        secondary_password = os.getenv("ADMIN_SECONDARY_PASSWORD")

        if not primary_password or not secondary_password:
            logger.error("admin_passwords_not_set")
            raise ValueError("ADMIN_PRIMARY_PASSWORD and ADMIN_SECONDARY_PASSWORD must be set")

        # Hash passwords
        self.primary_hash = self._hash_password(primary_password)
        self.secondary_hash = self._hash_password(secondary_password)

        # Load or generate RSA keys
        self._load_or_generate_keys()

        # Token expiration settings
        self.token_expiration = timedelta(hours=1)
        self.refresh_token_expiration = timedelta(days=7)

        logger.info("admin_auth_jwt_initialized")

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def _load_or_generate_keys(self):
        """Load RSA keys from files or generate new ones."""
        private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH", ".keys/admin_jwt_private.pem")
        public_key_path = os.getenv("JWT_PUBLIC_KEY_PATH", ".keys/admin_jwt_public.pem")

        try:
            # Try to load existing keys
            with open(private_key_path, "rb") as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            with open(public_key_path, "rb") as f:
                self.public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )

            logger.info("jwt_keys_loaded_from_files")

        except FileNotFoundError:
            # Generate new keys
            logger.info("jwt_keys_not_found_generating_new")
            self._generate_keys(private_key_path, public_key_path)

    def _generate_keys(self, private_path: str, public_path: str):
        """Generate new RSA key pair."""
        # Generate private key
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Generate public key
        self.public_key = self.private_key.public_key()

        # Save keys to files
        os.makedirs(os.path.dirname(private_path) or ".", exist_ok=True)

        # Save private key
        with open(private_path, "wb") as f:
            f.write(
                self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            )

        # Save public key
        with open(public_path, "wb") as f:
            f.write(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
            )

        # Set restrictive permissions
        os.chmod(private_path, 0o600)
        os.chmod(public_path, 0o644)

        logger.info("jwt_keys_generated_and_saved", private_path=private_path, public_path=public_path)

    def authenticate(
        self,
        primary_password: str,
        secondary_password: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[Tuple[str, str]]:
        """
        Authenticate admin with two passwords.

        Args:
            primary_password: First password
            secondary_password: Second password
            ip_address: Client IP address
            user_agent: Client User-Agent string

        Returns:
            Tuple of (access_token, refresh_token) if authenticated, None otherwise
        """
        primary_hash = self._hash_password(primary_password)
        secondary_hash = self._hash_password(secondary_password)

        if primary_hash == self.primary_hash and secondary_hash == self.secondary_hash:
            # Generate tokens
            access_token = self._generate_access_token(ip_address, user_agent)
            refresh_token = self._generate_refresh_token(ip_address, user_agent)

            logger.info("admin_authenticated",
                       ip=ip_address,
                       ua_hash=hashlib.sha256(user_agent.encode()).hexdigest()[:8])

            return access_token, refresh_token
        else:
            logger.warning("admin_auth_failed", ip=ip_address)
            return None

    def _generate_access_token(self, ip_address: str, user_agent: str) -> str:
        """Generate JWT access token."""
        now = datetime.utcnow()
        payload = {
            "type": "access",
            "iat": now,
            "exp": now + self.token_expiration,
            "ip": ip_address,
            "ua_hash": hashlib.sha256(user_agent.encode()).hexdigest(),
            "admin": True
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        return token

    def _generate_refresh_token(self, ip_address: str, user_agent: str) -> str:
        """Generate JWT refresh token."""
        now = datetime.utcnow()
        payload = {
            "type": "refresh",
            "iat": now,
            "exp": now + self.refresh_token_expiration,
            "ip": ip_address,
            "ua_hash": hashlib.sha256(user_agent.encode()).hexdigest(),
            "admin": True
        }

        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        return token

    def verify_token(
        self,
        token: str,
        ip_address: str,
        user_agent: str,
        token_type: str = "access"
    ) -> bool:
        """
        Verify JWT token.

        Args:
            token: JWT token to verify
            ip_address: Client IP address
            user_agent: Client User-Agent string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            True if token is valid, False otherwise
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"]
            )

            # Check token type
            if payload.get("type") != token_type:
                logger.warning("jwt_wrong_token_type",
                             expected=token_type,
                             got=payload.get("type"))
                return False

            # Check IP address binding
            if payload.get("ip") != ip_address:
                logger.warning("jwt_ip_mismatch",
                             token_ip=payload.get("ip"),
                             request_ip=ip_address)
                return False

            # Check User-Agent fingerprint
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()
            if payload.get("ua_hash") != ua_hash:
                logger.warning("jwt_ua_mismatch")
                return False

            # Check admin claim
            if not payload.get("admin"):
                logger.warning("jwt_not_admin_token")
                return False

            return True

        except jwt.ExpiredSignatureError:
            logger.info("jwt_token_expired")
            return False

        except jwt.InvalidTokenError as e:
            logger.warning("jwt_invalid_token", error=str(e))
            return False

        except Exception as e:
            logger.error("jwt_verification_error", error=str(e), exc_info=True)
            return False

    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: str,
        user_agent: str
    ) -> Optional[str]:
        """
        Generate new access token using refresh token.

        Args:
            refresh_token: Valid refresh token
            ip_address: Client IP address
            user_agent: Client User-Agent string

        Returns:
            New access token if refresh token is valid, None otherwise
        """
        if self.verify_token(refresh_token, ip_address, user_agent, token_type="refresh"):
            # Generate new access token
            access_token = self._generate_access_token(ip_address, user_agent)
            logger.info("access_token_refreshed", ip=ip_address)
            return access_token
        else:
            logger.warning("refresh_token_invalid", ip=ip_address)
            return None

    def decode_token(self, token: str) -> Optional[dict]:
        """
        Decode token without verification (for debugging).

        Args:
            token: JWT token

        Returns:
            Decoded payload or None
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"verify_exp": False}
            )
            return payload
        except Exception as e:
            logger.error("jwt_decode_error", error=str(e))
            return None


# Global instance
admin_auth_jwt: Optional[AdminAuthJWT] = None


def init_admin_auth_jwt():
    """Initialize global admin auth JWT instance."""
    global admin_auth_jwt
    try:
        admin_auth_jwt = AdminAuthJWT()
        logger.info("admin_auth_jwt_global_initialized")
    except Exception as e:
        logger.error("admin_auth_jwt_init_failed", error=str(e))
        admin_auth_jwt = None


def get_admin_auth() -> AdminAuthJWT:
    """
    Get admin auth instance.

    Returns:
        AdminAuthJWT instance

    Raises:
        RuntimeError: If not initialized
    """
    if admin_auth_jwt is None:
        raise RuntimeError("Admin auth JWT not initialized. Call init_admin_auth_jwt() first.")
    return admin_auth_jwt
