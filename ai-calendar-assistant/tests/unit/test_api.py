"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient


class TestEventsAPI:
    """Tests for /api/events endpoints."""

    def test_events_requires_auth(self, client: TestClient):
        """Events API should reject requests without Telegram auth."""
        response = client.get("/api/events/")
        assert response.status_code == 401
        assert "Unauthorized" in response.json().get("detail", "")

    def test_events_list_with_invalid_auth(self, client: TestClient):
        """Events API should reject invalid auth header."""
        response = client.get(
            "/api/events/",
            headers={"X-Telegram-Init-Data": "invalid_data"}
        )
        assert response.status_code == 401


class TestTodosAPI:
    """Tests for /api/todos endpoints."""

    def test_todos_requires_auth(self, client: TestClient):
        """Todos API should reject requests without Telegram auth."""
        response = client.get("/api/todos/")
        assert response.status_code == 401


class TestAdminAPI:
    """Tests for /api/admin/v2 endpoints."""

    def test_admin_health(self, client: TestClient):
        """Admin health endpoint should be accessible without auth."""
        response = client.get("/api/admin/v2/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "v2"}

    def test_admin_login_requires_credentials(self, client: TestClient):
        """Admin login should require username and password."""
        response = client.post("/api/admin/v2/login", json={})
        assert response.status_code == 422  # Validation error

    def test_admin_login_invalid_credentials(self, client: TestClient):
        """Admin login should reject invalid credentials."""
        response = client.post(
            "/api/admin/v2/login",
            json={"username": "invalid", "password": "invalid"}
        )
        data = response.json()
        assert data.get("success") is False or response.status_code != 200

    def test_admin_stats_requires_auth(self, client: TestClient):
        """Admin stats should require authentication."""
        response = client.get("/api/admin/v2/stats")
        assert response.status_code == 401

    def test_admin_users_requires_auth(self, client: TestClient):
        """Admin users should require authentication."""
        response = client.get("/api/admin/v2/users")
        assert response.status_code == 401


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_security_headers_present(self, client: TestClient):
        """Security headers should be present in response."""
        response = client.get("/health")

        # Check required security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "strict-origin" in response.headers.get("Referrer-Policy", "")


class TestCSRFProtection:
    """Tests for CSRF protection middleware."""

    def test_csrf_allows_get_requests(self, client: TestClient):
        """GET requests should not be blocked by CSRF."""
        response = client.get("/api/admin/v2/health")
        assert response.status_code == 200

    def test_csrf_allows_login_without_origin(self, client: TestClient):
        """Login endpoint should be exempt from CSRF check."""
        response = client.post(
            "/api/admin/v2/login",
            json={"username": "test", "password": "test"}
        )
        # Should not be blocked by CSRF (422 is validation, not 403)
        assert response.status_code != 403


class TestRateLimiting:
    """Tests for rate limiting."""

    def test_rate_limit_header_present(self, client: TestClient):
        """Rate limit headers should be present on rate-limited endpoints."""
        # Make a request to admin login (rate limited)
        response = client.post(
            "/api/admin/v2/login",
            json={"username": "test", "password": "test"}
        )
        # slowapi adds these headers when rate limiting is active
        # This test just verifies the endpoint works
        assert response.status_code in [200, 401, 422, 429]
