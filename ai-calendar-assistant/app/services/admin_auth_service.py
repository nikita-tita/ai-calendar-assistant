"""Enhanced admin authentication service with login/password + 2FA."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
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

from app.models.admin_user import (
    AdminUser, AdminLoginRequest, AdminLoginResponse, 
    AdminTokenPayload, TOTPSetupResponse, AdminAuditLogEntry
)

logger = structlog.get_logger()


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
    
    def __init__(self, db_path: str = "analytics.db"):
        """Initialize admin auth service."""
        self.db_path = db_path
        self._init_database()
        self._load_or_generate_keys()
        
        # Token expiration settings
        self.access_token_expiration = timedelta(hours=1)
        self.refresh_token_expiration = timedelta(days=7)
        
        # Rate limiting (in-memory for now, should use Redis in production)
        self._failed_attempts = {}  # ip -> (count, first_attempt_time)
        self.max_attempts = 3
        self.lockout_duration = timedelta(minutes=15)
        
        logger.info("admin_auth_service_initialized")
    
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
        
        logger.info("jwt_keys_generated_and_saved", private_path=private_path)
    
    def _hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _check_rate_limit(self, ip: str) -> bool:
        """Check if IP is rate limited."""
        now = datetime.now()
        
        if ip in self._failed_attempts:
            count, first_attempt = self._failed_attempts[ip]
            
            # Reset if lockout duration passed
            if now - first_attempt > self.lockout_duration:
                del self._failed_attempts[ip]
                return True
            
            # Check if locked out
            if count >= self.max_attempts:
                logger.warning("rate_limit_exceeded", ip=ip, attempts=count)
                return False
        
        return True
    
    def _record_failed_attempt(self, ip: str):
        """Record failed login attempt."""
        now = datetime.now()
        
        if ip in self._failed_attempts:
            count, first_attempt = self._failed_attempts[ip]
            self._failed_attempts[ip] = (count + 1, first_attempt)
        else:
            self._failed_attempts[ip] = (1, now)
    
    def _clear_failed_attempts(self, ip: str):
        """Clear failed attempts for IP."""
        if ip in self._failed_attempts:
            del self._failed_attempts[ip]
    
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


def init_admin_auth_service(db_path: str = "analytics.db"):
    """Initialize global admin auth service instance."""
    global admin_auth_service
    try:
        admin_auth_service = AdminAuthService(db_path)
        logger.info("admin_auth_service_global_initialized")
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

