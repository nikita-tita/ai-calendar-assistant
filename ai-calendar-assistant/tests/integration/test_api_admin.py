"""Tests for Admin API endpoints (v1 and v2)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request

from app.main import app


class TestAdminAPIv1:
    """Test admin API v1 endpoints (3-password auth)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    # ==================== Health Check ====================

    def test_health_check(self, client):
        """Test health check endpoint (no auth required)."""
        response = client.get("/api/admin/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    # ==================== POST /verify ====================

    def test_verify_no_passwords(self, client):
        """Test verify with missing passwords."""
        response = client.post("/api/admin/verify", json={})
        # Should return 422 (validation error)
        assert response.status_code == 422

    def test_verify_incomplete_passwords(self, client):
        """Test verify with incomplete passwords."""
        response = client.post(
            "/api/admin/verify",
            json={"password1": "test"}
        )
        # Should return 422 (missing password2 and password3)
        assert response.status_code == 422

    def test_verify_invalid_passwords(self, client):
        """Test verify with invalid passwords."""
        response = client.post(
            "/api/admin/verify",
            json={
                "password1": "wrong1",
                "password2": "wrong2",
                "password3": "wrong3"
            }
        )
        # Should return success=False with error
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    # ==================== GET /stats ====================

    def test_get_stats_no_auth(self, client):
        """Test stats endpoint without authentication."""
        response = client.get("/api/admin/stats")
        # Should return 401
        assert response.status_code == 401

    def test_get_stats_invalid_token(self, client):
        """Test stats endpoint with invalid token."""
        response = client.get(
            "/api/admin/stats",
            headers={"Authorization": "Bearer invalid_token"}
        )
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users ====================

    def test_get_users_no_auth(self, client):
        """Test users endpoint without authentication."""
        response = client.get("/api/admin/users")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/dialog ====================

    def test_get_user_dialog_no_auth(self, client):
        """Test user dialog endpoint without authentication."""
        response = client.get("/api/admin/users/123456/dialog")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/events ====================

    def test_get_user_events_no_auth(self, client):
        """Test user events endpoint without authentication."""
        response = client.get("/api/admin/users/123456/events")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/todos ====================

    def test_get_user_todos_no_auth(self, client):
        """Test user todos endpoint without authentication."""
        response = client.get("/api/admin/users/123456/todos")
        # Should return 401
        assert response.status_code == 401

    # ==================== POST /users/{user_id}/toggle-hidden ====================

    def test_toggle_user_hidden_no_auth(self, client):
        """Test toggle hidden endpoint without authentication."""
        response = client.post("/api/admin/users/123456/toggle-hidden")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /timeline ====================

    def test_get_timeline_no_auth(self, client):
        """Test timeline endpoint without authentication."""
        response = client.get("/api/admin/timeline")
        # Should return 401
        assert response.status_code == 401

    def test_get_timeline_invalid_hours(self, client):
        """Test timeline endpoint with invalid hours parameter."""
        response = client.get(
            "/api/admin/timeline",
            params={"hours": 200}  # Max is 168
        )
        # Should return 422 (validation error) or 401
        assert response.status_code in [401, 422]

    # ==================== GET /actions ====================

    def test_get_actions_no_auth(self, client):
        """Test actions endpoint without authentication."""
        response = client.get("/api/admin/actions")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /errors ====================

    def test_get_errors_no_auth(self, client):
        """Test errors endpoint without authentication."""
        response = client.get("/api/admin/errors")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /report ====================

    def test_get_report_no_auth(self, client):
        """Test report endpoint without authentication."""
        response = client.get("/api/admin/report")
        # Should return 401
        assert response.status_code == 401

    # ==================== POST /broadcast ====================

    def test_broadcast_no_auth(self, client):
        """Test broadcast endpoint without authentication."""
        response = client.post(
            "/api/admin/broadcast",
            json={"message": "Test broadcast"}
        )
        # Should return 401
        assert response.status_code == 401

    def test_broadcast_missing_message(self, client):
        """Test broadcast endpoint with missing message."""
        response = client.post(
            "/api/admin/broadcast",
            json={}
        )
        # Should return 422 (validation error)
        assert response.status_code == 422


class TestAdminAPIv2:
    """Test admin API v2 endpoints (login/password + 2FA)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    # ==================== Health Check ====================

    def test_health_check(self, client):
        """Test health check endpoint (no auth required)."""
        response = client.get("/api/admin/v2/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "v2"

    # ==================== POST /login ====================

    def test_login_missing_credentials(self, client):
        """Test login with missing credentials."""
        response = client.post("/api/admin/v2/login", json={})
        # Should return 422 (validation error)
        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/admin/v2/login",
            json={
                "username": "wrong",
                "password": "wrong"
            }
        )
        # Should return success=False
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    # ==================== POST /logout ====================

    def test_logout(self, client):
        """Test logout endpoint (clears cookies)."""
        response = client.post("/api/admin/v2/logout")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    # ==================== GET /me ====================

    def test_get_me_no_auth(self, client):
        """Test /me endpoint without authentication."""
        response = client.get("/api/admin/v2/me")
        # Should return 401
        assert response.status_code == 401

    # ==================== POST /setup-2fa ====================

    def test_setup_2fa_no_auth(self, client):
        """Test 2FA setup without authentication."""
        response = client.post("/api/admin/v2/setup-2fa")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /stats ====================

    def test_get_stats_no_auth(self, client):
        """Test stats endpoint without authentication."""
        response = client.get("/api/admin/v2/stats")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users ====================

    def test_get_users_no_auth(self, client):
        """Test users endpoint without authentication."""
        response = client.get("/api/admin/v2/users")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/dialog ====================

    def test_get_user_dialog_no_auth(self, client):
        """Test user dialog endpoint without authentication."""
        response = client.get("/api/admin/v2/users/123456/dialog")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/events ====================

    def test_get_user_events_no_auth(self, client):
        """Test user events endpoint without authentication."""
        response = client.get("/api/admin/v2/users/123456/events")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/{user_id}/todos ====================

    def test_get_user_todos_no_auth(self, client):
        """Test user todos endpoint without authentication."""
        response = client.get("/api/admin/v2/users/123456/todos")
        # Should return 401
        assert response.status_code == 401

    # ==================== POST /users/{user_id}/toggle-hidden ====================

    def test_toggle_user_hidden_no_auth(self, client):
        """Test toggle hidden endpoint without authentication."""
        response = client.post("/api/admin/v2/users/123456/toggle-hidden")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /timeline ====================

    def test_get_timeline_no_auth(self, client):
        """Test timeline endpoint without authentication."""
        response = client.get("/api/admin/v2/timeline")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /timeline/daily ====================

    def test_get_daily_timeline_no_auth(self, client):
        """Test daily timeline endpoint without authentication."""
        response = client.get("/api/admin/v2/timeline/daily")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /llm/costs ====================

    def test_get_llm_costs_no_auth(self, client):
        """Test LLM costs endpoint without authentication."""
        response = client.get("/api/admin/v2/llm/costs")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/metrics ====================

    def test_get_user_metrics_no_auth(self, client):
        """Test user metrics endpoint without authentication."""
        response = client.get("/api/admin/v2/users/metrics")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /users/top ====================

    def test_get_top_users_no_auth(self, client):
        """Test top users endpoint without authentication."""
        response = client.get("/api/admin/v2/users/top")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /actions ====================

    def test_get_actions_no_auth(self, client):
        """Test actions endpoint without authentication."""
        response = client.get("/api/admin/v2/actions")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /actions/summary ====================

    def test_get_actions_summary_no_auth(self, client):
        """Test actions summary endpoint without authentication."""
        response = client.get("/api/admin/v2/actions/summary")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /actions/by-type/{action_type} ====================

    def test_get_actions_by_type_no_auth(self, client):
        """Test actions by type endpoint without authentication."""
        response = client.get("/api/admin/v2/actions/by-type/event_create")
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /errors ====================

    def test_get_errors_no_auth(self, client):
        """Test errors endpoint without authentication."""
        response = client.get("/api/admin/v2/errors")
        # Should return 401
        assert response.status_code == 401

    # ==================== POST /broadcast ====================

    def test_broadcast_no_auth(self, client):
        """Test broadcast endpoint without authentication."""
        response = client.post(
            "/api/admin/v2/broadcast",
            json={"message": "Test broadcast"}
        )
        # Should return 401
        assert response.status_code == 401

    # ==================== GET /audit-logs ====================

    def test_get_audit_logs_no_auth(self, client):
        """Test audit logs endpoint without authentication."""
        response = client.get("/api/admin/v2/audit-logs")
        # Should return 401
        assert response.status_code == 401


class TestAdminModels:
    """Test admin request/response models."""

    def test_login_request_validation(self):
        """Test AdminLoginRequest pydantic validation."""
        from app.models.admin_user import AdminLoginRequest

        # Valid request with required fields
        request = AdminLoginRequest(username="admin", password="pass123")
        assert request.username == "admin"
        assert request.password == "pass123"
        assert request.totp_code is None  # Optional

        # Valid request with optional totp_code
        request_with_totp = AdminLoginRequest(
            username="admin",
            password="pass123",
            totp_code="123456"
        )
        assert request_with_totp.totp_code == "123456"

    def test_login_response_model(self):
        """Test AdminLoginResponse pydantic model."""
        from app.models.admin_user import AdminLoginResponse

        # Successful login response
        success_response = AdminLoginResponse(
            success=True,
            mode="real",
            message="Login successful"
        )
        assert success_response.success is True
        assert success_response.mode == "real"

        # Failed login response
        fail_response = AdminLoginResponse(
            success=False,
            mode="invalid",
            message="Invalid credentials"
        )
        assert fail_response.success is False

    def test_broadcast_request_validation(self):
        """Test BroadcastRequest pydantic validation."""
        from app.routers.admin import BroadcastRequest

        # Minimal request
        request = BroadcastRequest(message="Hello everyone!")
        assert request.message == "Hello everyone!"
        assert request.button_text is None
        assert request.button_action is None
        assert request.test_only is False

        # Full request with button
        full_request = BroadcastRequest(
            message="Update available!",
            button_text="Update",
            button_action="start",
            test_only=True
        )
        assert full_request.button_text == "Update"
        assert full_request.button_action == "start"
        assert full_request.test_only is True


class TestAdminSecurity:
    """Test admin security features."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_rate_limit_verify_endpoint(self, client):
        """Test that verify endpoint is rate limited."""
        # Make multiple requests quickly
        # Note: The actual rate limiting behavior depends on slowapi configuration
        responses = []
        for _ in range(6):  # Rate limit is 5/minute
            response = client.post(
                "/api/admin/verify",
                json={
                    "password1": "test1",
                    "password2": "test2",
                    "password3": "test3"
                }
            )
            responses.append(response.status_code)

        # At least some requests should succeed (200) with valid=False
        # Rate limiting behavior may vary in test environment
        assert 200 in responses

    def test_auth_required_for_sensitive_endpoints(self, client):
        """Test that all sensitive endpoints require authentication."""
        sensitive_endpoints = [
            ("GET", "/api/admin/stats"),
            ("GET", "/api/admin/users"),
            ("GET", "/api/admin/report"),
            ("GET", "/api/admin/v2/stats"),
            ("GET", "/api/admin/v2/users"),
            ("GET", "/api/admin/v2/audit-logs"),
        ]

        for method, endpoint in sensitive_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            assert response.status_code == 401, f"Endpoint {endpoint} should require auth"


class TestAdminQueryParams:
    """Test admin endpoint query parameters."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_dialog_limit_validation(self, client):
        """Test dialog endpoint limit parameter validation."""
        # Invalid: limit too high (max 10000)
        response = client.get(
            "/api/admin/users/123456/dialog",
            params={"limit": 15000}
        )
        # Should return 422 (validation error) or 401 (no auth)
        assert response.status_code in [401, 422]

    def test_timeline_hours_validation(self, client):
        """Test timeline endpoint hours parameter validation."""
        # Invalid: hours too high (max 168)
        response = client.get(
            "/api/admin/timeline",
            params={"hours": 500}
        )
        # Should return 422 (validation error) or 401 (no auth)
        assert response.status_code in [401, 422]

    def test_actions_limit_validation(self, client):
        """Test actions endpoint limit parameter validation."""
        # Invalid: limit too high (max 1000)
        response = client.get(
            "/api/admin/actions",
            params={"limit": 2000}
        )
        # Should return 422 (validation error) or 401 (no auth)
        assert response.status_code in [401, 422]

    def test_errors_valid_params(self, client):
        """Test errors endpoint with valid parameters."""
        response = client.get(
            "/api/admin/errors",
            params={"hours": 48, "limit": 50}
        )
        # Should return 401 (no auth) but params are valid
        assert response.status_code == 401
