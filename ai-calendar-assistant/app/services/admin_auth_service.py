"""Enhanced admin authentication service with login/password + 2FA."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import structlog
import bcrypt
import pyotp
import qrcode
import io
import base64
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import sqlite3

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from app.models.admin_user import (
    AdminUser, AdminLoginRequest, AdminLoginResponse,
    AdminTokenPayload, TOTPSetupResponse, AdminAuditLogEntry
)

logger = structlog.get_logger()

# SEC-006: Redis key prefix for rate limiting
RATE_LIMIT_KEY_PREFIX = "admin_rate_limit:"

# SEC-009: Default absolute paths for JWT keys (fallback when env vars not set)
_DEFAULT_KEYS_DIR = Path(__file__).parent.parent.parent / "data" / ".keys"
DEFAULT_JWT_PRIVATE_KEY_PATH = str(_DEFAULT_KEYS_DIR / "admin_jwt_private.pem")
DEFAULT_JWT_PUBLIC_KEY_PATH = str(_DEFAULT_KEYS_DIR / "admin_jwt_public.pem")


class AdminAuthService:
    """
    Admin authentication service with:
    - Login/Password authentication
    - 2FA (TOTP) with Google Authenticator
    - JWT tokens (RS256) with IP/UA binding
    - Refresh tokens (7 days)
    - Panic password for fake mode
    - Rate limiting
    - Audit logging
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize admin auth service."""
        if db_path is None:
            db_path = os.getenv("ADMIN_AUTH_DB_PATH", "/var/lib/calendar-bot/admin_auth.db")
            
        self.db_path = db_path
        
        # In development (locally), avoid permission errors if path is root-owned
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to local user data structure if we can't write to system paths
            logger.warning("admin_auth_db_permission_error", path=self.db_path, fallback="using local ./data directory")
            self.db_path = "./data/analytics.db" # Use analytics.db as default fallback
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_database()
        self._load_or_generate_keys()

        # Token expiration settings
        self.access_token_expiration = timedelta(hours=1)
        self.refresh_token_expiration = timedelta(days=7)

        # Rate limiting settings
        self.max_attempts = 3
        self.lockout_duration = timedelta(minutes=15)

        # SEC-006: Use Redis for distributed rate limiting if available
        self._redis_client = None
        self._failed_attempts = {}  # Fallback in-memory storage
        self._init_redis()

        logger.info("admin_auth_service_initialized", redis_enabled=self._redis_client is not None)

    def _init_redis(self):
        """Initialize Redis client for distributed rate limiting (SEC-006)."""
        if not REDIS_AVAILABLE:
            logger.warning("redis_not_available", message="Redis package not installed, using in-memory rate limiting")
            return

        try:
            from app.config import settings
            redis_url = getattr(settings, 'redis_url', None)

            if redis_url:
                self._redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self._redis_client.ping()
                logger.info("redis_rate_limiter_connected", url=redis_url.split('@')[-1])  # Log without password
            else:
                logger.warning("redis_url_not_configured", message="Using in-memory rate limiting")
        except Exception as e:
            logger.warning("redis_connection_failed", error=str(e), message="Falling back to in-memory rate limiting")
    
    def _init_database(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Admin users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    totp_secret TEXT,
                    totp_enabled INTEGER DEFAULT 0,
                    panic_password_hash TEXT,
                    role TEXT DEFAULT 'admin',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    last_login_ip TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Admin audit log table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS admin_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success INTEGER DEFAULT 1,
                    FOREIGN KEY (admin_user_id) REFERENCES admin_users(id)
                )
            ''')
            
            conn.commit()
            logger.info("admin_database_initialized")
        finally:
            conn.close()
    
    def _load_or_generate_keys(self):
        """Load RSA keys from files or generate new ones.

        SEC-009: Uses environment variables for key paths with absolute path fallback.
        """
        # SEC-009: Get paths from environment with absolute path fallback
        private_key_path = os.getenv("JWT_PRIVATE_KEY_PATH")
        public_key_path = os.getenv("JWT_PUBLIC_KEY_PATH")

        # Log whether using env or fallback paths
        if private_key_path:
            logger.info("jwt_key_path_from_env", key_type="private", path=private_key_path)
        else:
            private_key_path = DEFAULT_JWT_PRIVATE_KEY_PATH
            logger.info("jwt_key_path_fallback", key_type="private", path=private_key_path)

        if public_key_path:
            logger.info("jwt_key_path_from_env", key_type="public", path=public_key_path)
        else:
            public_key_path = DEFAULT_JWT_PUBLIC_KEY_PATH
            logger.info("jwt_key_path_fallback", key_type="public", path=public_key_path)

        # SEC-009: Validate and create key directory if needed
        self._validate_key_paths(private_key_path, public_key_path)

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

            logger.info("jwt_keys_loaded_from_files",
                       private_path=private_key_path,
                       public_path=public_key_path)

        except FileNotFoundError:
            # Generate new keys
            logger.info("jwt_keys_not_found_generating_new")
            self._generate_keys(private_key_path, public_key_path)

    def _validate_key_paths(self, private_path: str, public_path: str):
        """SEC-009: Validate that required key directories exist, create if needed."""
        for path_str, key_type in [(private_path, "private"), (public_path, "public")]:
            key_path = Path(path_str)
            parent_dir = key_path.parent

            if not parent_dir.exists():
                parent_dir.mkdir(parents=True, exist_ok=True)
                logger.info("jwt_key_directory_created",
                           key_type=key_type,
                           path=str(parent_dir))
    
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
        
        logger.info("jwt_keys_generated_and_saved", private_path=private_path)
    
    def _create_fingerprint(self, ip: str, user_agent: str) -> str:
        """
        SEC-007: Create a fingerprint hash from IP and User-Agent.

        Used for refresh token binding to prevent token theft.
        """
        data = f"{ip}:{user_agent}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _check_rate_limit(self, ip: str) -> bool:
        """
        Check if IP is rate limited (SEC-006: distributed via Redis).

        Returns True if allowed, False if rate limited.
        """
        # SEC-006: Try Redis first for distributed rate limiting
        if self._redis_client:
            try:
                key = f"{RATE_LIMIT_KEY_PREFIX}{ip}"
                count = self._redis_client.get(key)

                if count is None:
                    return True  # No failed attempts

                count = int(count)
                if count >= self.max_attempts:
                    logger.warning("rate_limit_exceeded", ip=ip, attempts=count, storage="redis")
                    return False
                return True
            except Exception as e:
                logger.warning("redis_rate_limit_check_failed", error=str(e), ip=ip)
                # Fall through to in-memory

        # Fallback: in-memory rate limiting
        now = datetime.now()

        if ip in self._failed_attempts:
            count, first_attempt = self._failed_attempts[ip]

            # Reset if lockout duration passed
            if now - first_attempt > self.lockout_duration:
                del self._failed_attempts[ip]
                return True

            # Check if locked out
            if count >= self.max_attempts:
                logger.warning("rate_limit_exceeded", ip=ip, attempts=count, storage="memory")
                return False

        return True

    def _record_failed_attempt(self, ip: str):
        """
        Record failed login attempt (SEC-006: distributed via Redis).
        """
        # SEC-006: Try Redis first for distributed rate limiting
        if self._redis_client:
            try:
                key = f"{RATE_LIMIT_KEY_PREFIX}{ip}"
                pipe = self._redis_client.pipeline()

                # Increment counter
                pipe.incr(key)
                # Set expiration (lockout duration)
                pipe.expire(key, int(self.lockout_duration.total_seconds()))

                results = pipe.execute()
                count = results[0]

                logger.info("failed_attempt_recorded", ip=ip, count=count, storage="redis")
                return
            except Exception as e:
                logger.warning("redis_record_attempt_failed", error=str(e), ip=ip)
                # Fall through to in-memory

        # Fallback: in-memory rate limiting
        now = datetime.now()

        if ip in self._failed_attempts:
            count, first_attempt = self._failed_attempts[ip]
            self._failed_attempts[ip] = (count + 1, first_attempt)
        else:
            self._failed_attempts[ip] = (1, now)

        logger.info("failed_attempt_recorded", ip=ip, count=self._failed_attempts[ip][0], storage="memory")

    def _clear_failed_attempts(self, ip: str):
        """
        Clear failed attempts for IP (SEC-006: distributed via Redis).
        """
        # SEC-006: Try Redis first
        if self._redis_client:
            try:
                key = f"{RATE_LIMIT_KEY_PREFIX}{ip}"
                self._redis_client.delete(key)
                logger.debug("failed_attempts_cleared", ip=ip, storage="redis")
                return
            except Exception as e:
                logger.warning("redis_clear_attempts_failed", error=str(e), ip=ip)
                # Fall through to in-memory

        # Fallback: in-memory
        if ip in self._failed_attempts:
            del self._failed_attempts[ip]
            logger.debug("failed_attempts_cleared", ip=ip, storage="memory")
    
    def create_admin_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        panic_password: Optional[str] = None,
        role: str = "admin"
    ) -> AdminUser:
        """Create a new admin user."""
        conn = sqlite3.connect(self.db_path)
        try:
            password_hash = self._hash_password(password)
            panic_hash = self._hash_password(panic_password) if panic_password else None
            
            cursor = conn.execute('''
                INSERT INTO admin_users
                (username, email, password_hash, panic_password_hash, role)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, email, password_hash, panic_hash, role))
            
            conn.commit()
            user_id = cursor.lastrowid
            
            logger.info("admin_user_created", username=username, role=role)
            
            return self.get_admin_user(user_id)
        finally:
            conn.close()
    
    def get_admin_user(self, user_id: int) -> Optional[AdminUser]:
        """Get admin user by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                'SELECT * FROM admin_users WHERE id = ?',
                (user_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return AdminUser(**dict(row))
            return None
        finally:
            conn.close()
    
    def get_admin_user_by_username(self, username: str) -> Optional[AdminUser]:
        """Get admin user by username."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                'SELECT * FROM admin_users WHERE username = ?',
                (username,)
            )
            row = cursor.fetchone()
            
            if row:
                return AdminUser(**dict(row))
            return None
        finally:
            conn.close()
    
    def setup_totp(self, user_id: int) -> TOTPSetupResponse:
        """Setup TOTP (2FA) for user."""
        user = self.get_admin_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.username,
            issuer_name="AI Calendar Admin"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Save secret to database
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                'UPDATE admin_users SET totp_secret = ?, totp_enabled = 1 WHERE id = ?',
                (secret, user_id)
            )
            conn.commit()
        finally:
            conn.close()
        
        logger.info("totp_setup_completed", user_id=user_id, username=user.username)
        
        return TOTPSetupResponse(
            secret=secret,
            qr_code=qr_code_base64,
            manual_entry_key=secret,
            issuer="AI Calendar Admin"
        )
    
    def verify_totp(self, user_id: int, code: str) -> bool:
        """Verify TOTP code."""
        user = self.get_admin_user(user_id)
        if not user or not user.totp_secret:
            return False
        
        totp = pyotp.TOTP(user.totp_secret)
        return totp.verify(code, valid_window=1)  # Allow 1 step before/after
    
    def authenticate(
        self,
        request: AdminLoginRequest,
        ip_address: str,
        user_agent: str
    ) -> Tuple[Optional[str], Optional[str], AdminLoginResponse]:
        """
        Authenticate admin user.
        
        Returns:
            (access_token, refresh_token, response)
        """
        # Check rate limit
        if not self._check_rate_limit(ip_address):
            return None, None, AdminLoginResponse(
                success=False,
                mode="invalid",
                message="Too many failed attempts. Please try again in 15 minutes."
            )
        
        # Get user
        user = self.get_admin_user_by_username(request.username)
        if not user or not user.is_active:
            self._record_failed_attempt(ip_address)
            self._log_audit(
                admin_user_id=0,
                username=request.username,
                action_type="login_failed",
                details=f"User not found or inactive",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
            return None, None, AdminLoginResponse(
                success=False,
                mode="invalid",
                message="Invalid username or password"
            )
        
        # Check password
        is_real_password = self._verify_password(request.password, user.password_hash)
        is_panic_password = (
            user.panic_password_hash and
            self._verify_password(request.password, user.panic_password_hash)
        )
        
        if not is_real_password and not is_panic_password:
            self._record_failed_attempt(ip_address)
            self._log_audit(
                admin_user_id=user.id,
                username=user.username,
                action_type="login_failed",
                details="Invalid password",
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
            return None, None, AdminLoginResponse(
                success=False,
                mode="invalid",
                message="Invalid username or password"
            )
        
        # Determine mode
        mode = "fake" if is_panic_password else "real"
        
        # Check 2FA if enabled (only for real mode)
        if mode == "real" and user.totp_enabled:
            if not request.totp_code:
                return None, None, AdminLoginResponse(
                    success=False,
                    mode="real",
                    totp_required=True,
                    message="2FA code required"
                )
            
            if not self.verify_totp(user.id, request.totp_code):
                self._record_failed_attempt(ip_address)
                self._log_audit(
                    admin_user_id=user.id,
                    username=user.username,
                    action_type="login_failed",
                    details="Invalid 2FA code",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False
                )
                return None, None, AdminLoginResponse(
                    success=False,
                    mode="invalid",
                    message="Invalid 2FA code"
                )
        
        # Authentication successful - clear failed attempts
        self._clear_failed_attempts(ip_address)
        
        # Update last login
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                'UPDATE admin_users SET last_login_at = ?, last_login_ip = ? WHERE id = ?',
                (datetime.now().isoformat(), ip_address, user.id)
            )
            conn.commit()
        finally:
            conn.close()
        
        # Generate tokens
        access_token = self._generate_token(
            user, mode, ip_address, user_agent, "access"
        )
        refresh_token = self._generate_token(
            user, mode, ip_address, user_agent, "refresh"
        )
        
        # Log successful login
        self._log_audit(
            admin_user_id=user.id,
            username=user.username,
            action_type="login_success",
            details=f"Mode: {mode}",
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
        
        logger.info(
            "admin_login_success",
            user_id=user.id,
            username=user.username,
            mode=mode,
            ip=ip_address
        )
        
        return access_token, refresh_token, AdminLoginResponse(
            success=True,
            mode=mode,
            message="Login successful"
        )
    
    def _generate_token(
        self,
        user: AdminUser,
        mode: str,
        ip_address: str,
        user_agent: str,
        token_type: str
    ) -> str:
        """Generate JWT token."""
        now = datetime.utcnow()
        expiration = (
            self.access_token_expiration if token_type == "access"
            else self.refresh_token_expiration
        )

        payload = {
            "type": token_type,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "mode": mode,
            "ip": ip_address,
            "ua_hash": hashlib.sha256(user_agent.encode()).hexdigest(),
            "exp": now + expiration,
            "iat": now
        }

        # SEC-007: Add fingerprint to refresh tokens for binding validation
        if token_type == "refresh":
            payload["fingerprint"] = self._create_fingerprint(ip_address, user_agent)
            logger.debug(
                "refresh_token_fingerprint_created",
                user_id=user.id,
                fingerprint=payload["fingerprint"]
            )

        return jwt.encode(payload, self.private_key, algorithm="RS256")
    
    def verify_token(
        self,
        token: str,
        ip_address: str,
        user_agent: str,
        token_type: str = "access"
    ) -> Optional[dict]:
        """
        Verify JWT token.

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"]
            )

            # Check token type
            if payload.get("type") != token_type:
                logger.warning("jwt_wrong_token_type", expected=token_type, got=payload.get("type"))
                return None

            # Check IP address binding
            if payload.get("ip") != ip_address:
                logger.warning("jwt_ip_mismatch", token_ip=payload.get("ip"), request_ip=ip_address)
                return None

            # Check User-Agent fingerprint
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()
            if payload.get("ua_hash") != ua_hash:
                logger.warning("jwt_ua_mismatch")
                return None

            # SEC-007: Check fingerprint for refresh tokens
            if token_type == "refresh":
                token_fingerprint = payload.get("fingerprint")
                # Backward compatibility: if old token without fingerprint - accept it
                if token_fingerprint:
                    current_fingerprint = self._create_fingerprint(ip_address, user_agent)
                    if token_fingerprint != current_fingerprint:
                        logger.warning(
                            "refresh_token_fingerprint_mismatch",
                            token_fingerprint=token_fingerprint,
                            current_fingerprint=current_fingerprint,
                            ip=ip_address
                        )
                        return None
                    logger.debug(
                        "refresh_token_fingerprint_valid",
                        fingerprint=token_fingerprint
                    )
                else:
                    logger.info(
                        "refresh_token_legacy_no_fingerprint",
                        user_id=payload.get("user_id"),
                        message="Accepting legacy token without fingerprint"
                    )

            return payload

        except jwt.ExpiredSignatureError:
            logger.info("jwt_token_expired")
            return None

        except jwt.InvalidTokenError as e:
            logger.warning("jwt_invalid_token", error=str(e))
            return None

        except Exception as e:
            logger.error("jwt_verification_error", error=str(e), exc_info=True)
            return None
    
    def _log_audit(
        self,
        admin_user_id: int,
        username: str,
        action_type: str,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ):
        """Log admin action to audit log."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('''
                INSERT INTO admin_audit_log
                (admin_user_id, username, action_type, details, ip_address, user_agent, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (admin_user_id, username, action_type, details, ip_address, user_agent, 1 if success else 0))
            conn.commit()
        finally:
            conn.close()
    
    def get_audit_logs(
        self,
        limit: int = 100,
        admin_user_id: Optional[int] = None,
        action_type: Optional[str] = None
    ) -> list[AdminAuditLogEntry]:
        """Get audit logs with optional filters."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            query = 'SELECT * FROM admin_audit_log WHERE 1=1'
            params = []
            
            if admin_user_id:
                query += ' AND admin_user_id = ?'
                params.append(admin_user_id)
            
            if action_type:
                query += ' AND action_type = ?'
                params.append(action_type)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [AdminAuditLogEntry(**dict(row)) for row in cursor.fetchall()]
        finally:
            conn.close()


# Global instance
admin_auth_service: Optional[AdminAuthService] = None


def init_admin_auth_service(db_path: str = "/var/lib/calendar-bot/admin_auth.db"):
    """Initialize global admin auth service instance.

    Uses persistent volume path by default to survive container rebuilds.
    """
    global admin_auth_service
    try:
        admin_auth_service = AdminAuthService(db_path)
        logger.info("admin_auth_service_global_initialized", db_path=db_path)
    except Exception as e:
        logger.error("admin_auth_service_init_failed", error=str(e))
        admin_auth_service = None


def get_admin_auth() -> AdminAuthService:
    """
    Get admin auth service instance.
    
    Returns:
        AdminAuthService instance
    
    Raises:
        RuntimeError: If not initialized
    """
    if admin_auth_service is None:
        raise RuntimeError("Admin auth service not initialized. Call init_admin_auth_service() first.")
    return admin_auth_service

