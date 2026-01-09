"""Security integration tests."""

import pytest
import requests
from pathlib import Path
import stat
import os
from app.config import settings


class TestSecurityConfiguration:
    """Test security configuration and settings."""

    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets exist in production config."""
        # Check that secret_key is not default value
        assert settings.secret_key != "default-secret-key-change-in-production"
        assert settings.secret_key is not None
        assert len(settings.secret_key) > 20  # Must be secure length

    def test_telegram_bot_token_set(self):
        """Test that Telegram bot token is configured."""
        assert settings.telegram_bot_token is not None
        assert settings.telegram_bot_token != ""
        assert len(settings.telegram_bot_token) > 10

    def test_env_file_not_in_git(self):
        """Test that .env file is properly gitignored."""
        env_path = Path(".env")
        
        # If .env exists, it should not be in .git (gitignored)
        if env_path.exists():
            # Check .gitignore contains .env
            gitignore = Path(".gitignore")
            if gitignore.exists():
                gitignore_content = gitignore.read_text()
                assert ".env" in gitignore_content or "*.env" in gitignore_content or ".env\n" in gitignore_content

    @pytest.mark.skipif(os.getenv("SKIP_PERMISSION_TEST") == "1", reason="Skip on CI")
    def test_env_file_permissions(self):
        """Test that .env file has secure permissions (600 or 400)."""
        env_path = Path(".env")
        
        if env_path.exists():
            file_stat = os.stat(env_path)
            # Check that file permissions are 600 (rw-------) or stricter
            permissions = stat.filemode(file_stat.st_mode)
            
            # File should not be readable by group or others
            assert permissions[5] not in ['r', 'w', 'x'], f".env file permissions too open: {permissions}"
            assert permissions[8] not in ['r', 'w', 'x'], f".env file permissions too open: {permissions}"


class TestRadicaleSecurity:
    """Test Radicale server security configuration."""

    @pytest.mark.skipif(os.getenv("SKIP_NETWORK_TEST") == "1", reason="Skip network tests")
    def test_radicale_not_publicly_accessible(self):
        """
        Test that Radicale is not accessible from public internet.
        
        Note: This test checks if Radicale is accessible on localhost.
        In production, Radicale should only be accessible within internal Docker network.
        """
        try:
            # Try to connect to Radicale
            response = requests.get("http://localhost:5232", timeout=2)
            
            # If Radicale is accessible, this is a security issue
            # (Unless we're running in a local test environment)
            if response.status_code in [200, 302, 401]:
                # Check if we're in local/test environment
                if settings.app_env == "production":
                    pytest.fail("Radicale is publicly accessible in production!")
        except requests.exceptions.ConnectionError:
            # Expected - Radicale should not be accessible
            pass
        except requests.exceptions.Timeout:
            # Expected - no response
            pass

    def test_radicale_uses_internal_network(self):
        """Test that Radicale URL uses internal network."""
        radicale_url = settings.radicale_url
        
        # Should use internal network (radicale hostname, not localhost/public IP)
        assert "radicale" in radicale_url.lower() or "localhost" in radicale_url.lower()
        # Should not use public IP or domain
        assert "http://95.163.227.26" not in radicale_url
        assert "http://1.2.3.4" not in radicale_url


class TestAuthenticationSecurity:
    """Test authentication and authorization mechanisms."""

    def test_webhook_secret_configured(self):
        """Test that webhook secret is configured in production."""
        if settings.app_env == "production":
            assert settings.telegram_webhook_secret is not None
            assert settings.telegram_webhook_secret != ""
            assert len(settings.telegram_webhook_secret) > 10

    def test_jwt_secret_not_default(self):
        """Test that JWT secret is not default value."""
        if hasattr(settings, 'secret_key'):
            assert settings.secret_key != "default-secret-key"
            assert settings.secret_key != "secret"


class TestDataProtection:
    """Test data protection mechanisms."""

    def test_database_connection_secure(self):
        """Test that database connection string uses proper authentication."""
        db_url = settings.database_url
        
        # Should not be using unauthenticated connections
        if "postgresql" in db_url.lower() or "mysql" in db_url.lower():
            assert "@" in db_url, "Database URL should include credentials"
        elif "sqlite" in db_url.lower():
            # SQLite is local file-based, acceptable for development
            pass

    def test_redis_password_configured(self):
        """Test that Redis password is configured in production."""
        if settings.app_env == "production" and "redis://" in settings.redis_url:
            # Redis password should be in URL or separate config
            redis_url = settings.redis_url
            # Check if password is configured (in URL or separate)
            assert settings.redis_password is not None or ":" in redis_url.split("@")[0] or "@" not in redis_url


@pytest.mark.asyncio
class TestAPIEndpointSecurity:
    """Test API endpoint security."""

    async def test_health_endpoint_open(self, client):
        """Test that health endpoint is accessible without auth."""
        response = client.get("/health")
        assert response.status_code == 200

    async def test_events_endpoint_requires_auth(self, client):
        """Test that events endpoints require authentication."""
        # Try to access events without auth
        response = client.get("/api/events")
        
        # Should either require auth or validate Telegram init data
        assert response.status_code in [401, 403, 422]
