"""Tests for Admin authentication security (JWT, passwords, 2FA, rate limiting)."""

import pytest
import bcrypt
import jwt
import pyotp
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestPasswordHashing:
    """Test bcrypt password hashing."""

    def test_password_hashing_bcrypt(self):
        """Test that passwords are hashed with bcrypt."""
        password = "SecurePassword123!"

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # Verify it's a valid bcrypt hash
        assert hashed.startswith(b'$2b$')  # bcrypt prefix
        assert len(hashed) == 60

    def test_password_verification_correct(self):
        """Test that correct password verifies."""
        password = "SecurePassword123!"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # Verify correct password
        assert bcrypt.checkpw(password.encode('utf-8'), hashed) is True

    def test_password_verification_incorrect(self):
        """Test that incorrect password is rejected."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # Verify wrong password fails
        assert bcrypt.checkpw(wrong_password.encode('utf-8'), hashed) is False

    def test_password_hashing_timing_safe(self):
        """Test that password verification uses timing-safe comparison."""
        password = "TestPassword"
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # bcrypt.checkpw is timing-safe by design
        # This test just verifies it doesn't raise exceptions
        assert bcrypt.checkpw(password.encode('utf-8'), hashed) is True
        assert bcrypt.checkpw("wrong".encode('utf-8'), hashed) is False

    def test_different_salts_produce_different_hashes(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "SamePassword123"

        hash1 = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        hash2 = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # Hashes should be different (different salts)
        assert hash1 != hash2

        # But both should verify
        assert bcrypt.checkpw(password.encode('utf-8'), hash1) is True
        assert bcrypt.checkpw(password.encode('utf-8'), hash2) is True


class TestJWTTokens:
    """Test JWT token generation and verification."""

    @pytest.fixture
    def jwt_secret(self):
        """Test JWT secret."""
        return "test-secret-key-for-jwt-testing"

    def test_jwt_token_creation(self, jwt_secret):
        """Test JWT token creation."""
        payload = {
            "user_id": 1,
            "username": "admin",
            "mode": "real",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_jwt_token_verification_valid(self, jwt_secret):
        """Test that valid JWT token verifies correctly."""
        payload = {
            "user_id": 1,
            "username": "admin",
            "mode": "real",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])

        assert decoded["user_id"] == 1
        assert decoded["username"] == "admin"
        assert decoded["mode"] == "real"

    def test_jwt_token_wrong_secret(self, jwt_secret):
        """Test that token with wrong secret is rejected."""
        payload = {
            "user_id": 1,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_jwt_token_expired(self, jwt_secret):
        """Test that expired token is rejected."""
        payload = {
            "user_id": 1,
            "exp": datetime.utcnow() - timedelta(hours=1)  # Already expired
        }

        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, jwt_secret, algorithms=["HS256"])

    def test_jwt_token_tampered(self, jwt_secret):
        """Test that tampered token is rejected."""
        payload = {
            "user_id": 1,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "xxxxx"  # Corrupt payload
        tampered_token = ".".join(parts)

        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(tampered_token, jwt_secret, algorithms=["HS256"])

    def test_jwt_algorithm_confusion_prevented(self, jwt_secret):
        """Test that algorithm confusion attacks are prevented."""
        payload = {
            "user_id": 1,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }

        # Create token with HS256
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        # Try to decode expecting RS256 - should fail
        with pytest.raises(jwt.InvalidAlgorithmError):
            jwt.decode(token, jwt_secret, algorithms=["RS256"])


class TestTOTP2FA:
    """Test TOTP (Time-based One-Time Password) 2FA."""

    def test_totp_secret_generation(self):
        """Test TOTP secret generation."""
        secret = pyotp.random_base32()

        assert len(secret) == 32  # Base32 encoded
        assert secret.isalnum()

    def test_totp_code_generation(self):
        """Test TOTP code generation."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        code = totp.now()

        assert len(code) == 6
        assert code.isdigit()

    def test_totp_verification_correct(self):
        """Test that correct TOTP code verifies."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        code = totp.now()

        assert totp.verify(code) is True

    def test_totp_verification_wrong_code(self):
        """Test that wrong TOTP code is rejected."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        # Use obviously wrong code
        assert totp.verify("000000") is False
        assert totp.verify("999999") is False

    def test_totp_verification_with_window(self):
        """Test TOTP verification with time window."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        code = totp.now()

        # Should verify with window=1 (allows 1 step before/after)
        assert totp.verify(code, valid_window=1) is True

    def test_totp_different_secrets_different_codes(self):
        """Test that different secrets produce different codes."""
        secret1 = pyotp.random_base32()
        secret2 = pyotp.random_base32()

        totp1 = pyotp.TOTP(secret1)
        totp2 = pyotp.TOTP(secret2)

        # Codes should be different (with very high probability)
        code1 = totp1.now()
        code2 = totp2.now()

        # Cross-verification should fail
        assert totp1.verify(code2) is False
        assert totp2.verify(code1) is False

    def test_totp_provisioning_uri(self):
        """Test TOTP provisioning URI generation."""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        uri = totp.provisioning_uri(
            name="admin",
            issuer_name="AI Calendar Admin"
        )

        assert uri.startswith("otpauth://totp/")
        assert "AI%20Calendar%20Admin" in uri or "AI+Calendar+Admin" in uri
        assert "secret=" in uri


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_tracking_in_memory(self):
        """Test in-memory rate limit tracking."""
        failed_attempts = {}
        max_attempts = 3

        ip = "192.168.1.1"

        # Record failed attempts
        for i in range(max_attempts):
            if ip in failed_attempts:
                count, first = failed_attempts[ip]
                failed_attempts[ip] = (count + 1, first)
            else:
                failed_attempts[ip] = (1, datetime.now())

        # Should be at limit
        count, _ = failed_attempts[ip]
        assert count >= max_attempts

    def test_rate_limit_different_ips(self):
        """Test that rate limits are per-IP."""
        failed_attempts = {}

        # Different IPs should have separate counters
        failed_attempts["192.168.1.1"] = (3, datetime.now())
        failed_attempts["192.168.1.2"] = (1, datetime.now())

        assert failed_attempts["192.168.1.1"][0] == 3
        assert failed_attempts["192.168.1.2"][0] == 1

    def test_rate_limit_expiration(self):
        """Test rate limit expiration."""
        lockout_duration = timedelta(minutes=15)
        now = datetime.now()

        # Old attempt (should be expired)
        old_attempt_time = now - timedelta(minutes=20)

        # Check if expired
        is_expired = (now - old_attempt_time) > lockout_duration
        assert is_expired is True

        # Recent attempt (should not be expired)
        recent_attempt_time = now - timedelta(minutes=5)
        is_recent_expired = (now - recent_attempt_time) > lockout_duration
        assert is_recent_expired is False


class TestAdminAuthModels:
    """Test admin authentication models."""

    def test_login_request_model(self):
        """Test AdminLoginRequest model validation."""
        from app.models.admin_user import AdminLoginRequest

        # Valid request
        request = AdminLoginRequest(
            username="admin",
            password="password123"
        )
        assert request.username == "admin"
        assert request.password == "password123"
        assert request.totp_code is None

        # With TOTP
        request_with_totp = AdminLoginRequest(
            username="admin",
            password="password123",
            totp_code="123456"
        )
        assert request_with_totp.totp_code == "123456"

    def test_login_response_model(self):
        """Test AdminLoginResponse model."""
        from app.models.admin_user import AdminLoginResponse

        # Success response
        success = AdminLoginResponse(
            success=True,
            mode="real",
            message="Login successful"
        )
        assert success.success is True
        assert success.mode == "real"

        # Failure response
        failure = AdminLoginResponse(
            success=False,
            mode="invalid",
            message="Invalid credentials"
        )
        assert failure.success is False

    def test_totp_required_response(self):
        """Test TOTP required response."""
        from app.models.admin_user import AdminLoginResponse

        response = AdminLoginResponse(
            success=False,
            mode="real",
            totp_required=True,
            message="2FA code required"
        )
        assert response.totp_required is True
        assert response.mode == "real"


class TestPanicPassword:
    """Test panic password (fake mode) functionality."""

    def test_panic_password_different_from_real(self):
        """Test that panic password is stored separately."""
        real_password = "RealSecurePassword123!"
        panic_password = "PanicPassword456!"

        real_hash = bcrypt.hashpw(real_password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        panic_hash = bcrypt.hashpw(panic_password.encode('utf-8'), bcrypt.gensalt(rounds=12))

        # Hashes should be different
        assert real_hash != panic_hash

        # Each password should only verify against its own hash
        assert bcrypt.checkpw(real_password.encode('utf-8'), real_hash) is True
        assert bcrypt.checkpw(panic_password.encode('utf-8'), panic_hash) is True
        assert bcrypt.checkpw(panic_password.encode('utf-8'), real_hash) is False
        assert bcrypt.checkpw(real_password.encode('utf-8'), panic_hash) is False

    def test_mode_determination_logic(self):
        """Test the logic for determining real vs fake mode."""
        # Simulating the logic from AdminAuthService
        def determine_mode(is_real_password: bool, is_panic_password: bool) -> str:
            if not is_real_password and not is_panic_password:
                return "invalid"
            return "fake" if is_panic_password else "real"

        assert determine_mode(True, False) == "real"
        assert determine_mode(False, True) == "fake"
        assert determine_mode(False, False) == "invalid"
        # If both are somehow true, panic takes precedence (edge case)
        assert determine_mode(True, True) == "fake"


class TestSecurityHeaders:
    """Test security-related header handling."""

    def test_ip_extraction_from_x_forwarded_for(self):
        """Test extracting real IP from X-Forwarded-For header."""
        def get_client_ip(headers: dict) -> str:
            forwarded = headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            return headers.get("X-Real-IP", "unknown")

        # Single IP
        assert get_client_ip({"X-Forwarded-For": "1.2.3.4"}) == "1.2.3.4"

        # Multiple IPs (first is client)
        assert get_client_ip({"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}) == "1.2.3.4"

        # Fallback to X-Real-IP
        assert get_client_ip({"X-Real-IP": "4.5.6.7"}) == "4.5.6.7"

        # Unknown
        assert get_client_ip({}) == "unknown"

    def test_user_agent_hashing(self):
        """Test that user agent is hashed for storage."""
        import hashlib

        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

        ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()

        assert len(ua_hash) == 64  # SHA-256 produces 64 hex chars
        assert ua_hash.isalnum()

    def test_user_agent_binding_verification(self):
        """Test that UA binding catches mismatches."""
        import hashlib

        original_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        different_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

        original_hash = hashlib.sha256(original_ua.encode()).hexdigest()
        different_hash = hashlib.sha256(different_ua.encode()).hexdigest()

        # Same UA should match
        assert hashlib.sha256(original_ua.encode()).hexdigest() == original_hash

        # Different UA should not match
        assert different_hash != original_hash
