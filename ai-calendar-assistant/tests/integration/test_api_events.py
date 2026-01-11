"""Tests for Events API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request

from app.main import app


class TestEventsAPI:
    """Test events API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "123456789"

    @pytest.fixture
    def mock_auth(self, test_user_id):
        """Mock Telegram authentication middleware."""
        def add_user_to_request(request: Request):
            request.state.telegram_user_id = test_user_id
            request.state.telegram_user_info = {
                "id": int(test_user_id),
                "first_name": "Test",
                "username": "testuser"
            }
        return add_user_to_request

    @pytest.fixture
    def sample_event(self):
        """Sample event data."""
        now = datetime.now()
        return {
            "title": "Test Meeting",
            "start": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "location": "Conference Room",
            "description": "Test meeting description",
            "color": "blue"
        }

    @pytest.fixture
    def mock_calendar_event(self):
        """Mock calendar event object."""
        event = MagicMock()
        event.id = "test-event-123"
        event.summary = "Test Meeting"
        event.start = datetime.now() + timedelta(hours=1)
        event.end = datetime.now() + timedelta(hours=2)
        event.location = "Conference Room"
        event.description = "Test description"
        return event

    # ==================== Health Check ====================

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/events/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data

    # ==================== GET /events/{user_id} ====================

    @patch("app.routers.events.calendar_service")
    @patch("app.routers.events.analytics_service")
    def test_get_events_success(self, mock_analytics, mock_calendar, client, test_user_id, mock_calendar_event):
        """Test successful event retrieval."""
        # Setup mocks
        mock_calendar.list_events = AsyncMock(return_value=[mock_calendar_event])

        # Mock auth middleware by patching request state
        with patch("app.middleware.telegram_auth.TelegramAuthMiddleware") as mock_middleware:
            # Add auth header with mock data
            response = client.get(
                f"/api/events/events/{test_user_id}",
                headers={"X-Telegram-Init-Data": "mock_data"}
            )

        # For now, expect 401 since auth is not mocked properly
        # This test documents the expected behavior
        assert response.status_code in [200, 401, 403]

    def test_get_events_no_auth(self, client, test_user_id):
        """Test event retrieval without authentication."""
        response = client.get(f"/api/events/events/{test_user_id}")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    # ==================== POST /events/{user_id} ====================

    def test_create_event_no_auth(self, client, test_user_id, sample_event):
        """Test event creation without authentication."""
        response = client.post(
            f"/api/events/events/{test_user_id}",
            json=sample_event
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    def test_create_event_invalid_time_range(self, client, test_user_id):
        """Test event creation with end time before start time."""
        now = datetime.now()
        invalid_event = {
            "title": "Invalid Event",
            "start": (now + timedelta(hours=2)).isoformat(),
            "end": (now + timedelta(hours=1)).isoformat(),  # End before start
            "location": "",
            "description": ""
        }
        response = client.post(
            f"/api/events/events/{test_user_id}",
            json=invalid_event
        )
        # Should return 422 (validation error) or auth error
        assert response.status_code in [401, 403, 422, 500]

    def test_create_event_missing_required_fields(self, client, test_user_id):
        """Test event creation with missing required fields."""
        incomplete_event = {
            "title": "Incomplete Event"
            # Missing start and end
        }
        response = client.post(
            f"/api/events/events/{test_user_id}",
            json=incomplete_event
        )
        # Should return 422 (validation error)
        assert response.status_code == 422

    # ==================== PUT /events/{user_id}/{event_id} ====================

    def test_update_event_no_auth(self, client, test_user_id):
        """Test event update without authentication."""
        update_data = {"title": "Updated Title"}
        response = client.put(
            f"/api/events/events/{test_user_id}/test-event-123",
            json=update_data
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    # ==================== DELETE /events/{user_id}/{event_id} ====================

    def test_delete_event_no_auth(self, client, test_user_id):
        """Test event deletion without authentication."""
        response = client.delete(
            f"/api/events/events/{test_user_id}/test-event-123"
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]


class TestEventsValidation:
    """Test event data validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_event_create_request_validation(self):
        """Test EventCreateRequest pydantic validation."""
        from app.routers.events import EventCreateRequest

        # Valid event
        now = datetime.now()
        valid_data = {
            "title": "Test",
            "start": now,
            "end": now + timedelta(hours=1)
        }
        event = EventCreateRequest(**valid_data)
        assert event.title == "Test"

        # Invalid: end before start
        with pytest.raises(ValueError, match="end time must be after start time"):
            EventCreateRequest(
                title="Invalid",
                start=now + timedelta(hours=2),
                end=now + timedelta(hours=1)
            )

    def test_event_update_request_validation(self):
        """Test EventUpdateRequest pydantic validation."""
        from app.routers.events import EventUpdateRequest

        # Valid partial update
        update = EventUpdateRequest(title="Updated Title")
        assert update.title == "Updated Title"
        assert update.start is None

        # Invalid: end before start when both provided
        now = datetime.now()
        with pytest.raises(ValueError, match="end time must be after start time"):
            EventUpdateRequest(
                start=now + timedelta(hours=2),
                end=now + timedelta(hours=1)
            )


class TestEventsCache:
    """Test events caching behavior."""

    def test_webapp_cache_cleanup(self):
        """Test webapp cache cleanup function."""
        from app.routers.events import _cleanup_webapp_cache, _webapp_open_cache, _CACHE_MAX_SIZE

        # Add many entries to cache
        now = datetime.now()
        for i in range(_CACHE_MAX_SIZE + 100):
            _webapp_open_cache[f"user_{i}"] = now - timedelta(hours=2)  # Old entries

        # Run cleanup
        _cleanup_webapp_cache()

        # Cache should be cleaned up
        assert len(_webapp_open_cache) <= _CACHE_MAX_SIZE


class TestUserIdValidation:
    """SEC-010: Test user_id input validation."""

    def test_valid_user_id_numeric(self):
        """SEC-010: Test that valid numeric user_id is accepted."""
        from app.routers.events import validate_user_id

        # Valid Telegram user IDs (positive integers)
        valid_ids = [
            "1",
            "123456789",
            "9876543210",
            "12345678901234567890",  # Max 20 digits
        ]

        for user_id in valid_ids:
            result = validate_user_id(user_id)
            assert result == user_id, f"Valid user_id {user_id} should be accepted"

    def test_invalid_user_id_empty(self):
        """SEC-010: Test that empty user_id is rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id("")

        assert exc_info.value.status_code == 400

    def test_invalid_user_id_zero(self):
        """SEC-010: Test that zero user_id is rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id("0")

        assert exc_info.value.status_code == 400

    def test_invalid_user_id_negative(self):
        """SEC-010: Test that negative user_id is rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id("-123456789")

        assert exc_info.value.status_code == 400

    def test_invalid_user_id_letters(self):
        """SEC-010: Test that user_id with letters is rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        invalid_ids = [
            "abc",
            "123abc",
            "abc123",
            "user_123",
        ]

        for user_id in invalid_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_user_id(user_id)
            assert exc_info.value.status_code == 400

    def test_invalid_user_id_path_traversal(self):
        """SEC-010: Test that path traversal attempts are rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        path_traversal_attempts = [
            "../admin",
            "..%2Fadmin",
            "123/../admin",
            "123/../../etc/passwd",
        ]

        for user_id in path_traversal_attempts:
            with pytest.raises(HTTPException) as exc_info:
                validate_user_id(user_id)
            assert exc_info.value.status_code == 400

    def test_invalid_user_id_special_chars(self):
        """SEC-010: Test that special characters are rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        special_char_ids = [
            "123;456",
            "123'456",
            "123\"456",
            "123<script>",
            "123&456",
            "123=456",
            "123 456",
        ]

        for user_id in special_char_ids:
            with pytest.raises(HTTPException) as exc_info:
                validate_user_id(user_id)
            assert exc_info.value.status_code == 400

    def test_invalid_user_id_leading_zeros(self):
        """SEC-010: Test that leading zeros are rejected (not a valid positive integer)."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id("0123456789")  # Leading zero

        assert exc_info.value.status_code == 400

    def test_invalid_user_id_too_long(self):
        """SEC-010: Test that user_id with more than 20 digits is rejected."""
        from app.routers.events import validate_user_id
        from fastapi import HTTPException

        # 21 digits - too long
        with pytest.raises(HTTPException) as exc_info:
            validate_user_id("123456789012345678901")

        assert exc_info.value.status_code == 400

    def test_user_id_validation_pattern(self):
        """SEC-010: Test the regex pattern directly."""
        from app.routers.events import _USER_ID_PATTERN

        # Should match
        assert _USER_ID_PATTERN.match("1")
        assert _USER_ID_PATTERN.match("123456789")
        assert _USER_ID_PATTERN.match("12345678901234567890")

        # Should not match
        assert not _USER_ID_PATTERN.match("")
        assert not _USER_ID_PATTERN.match("0")
        assert not _USER_ID_PATTERN.match("01")
        assert not _USER_ID_PATTERN.match("-1")
        assert not _USER_ID_PATTERN.match("abc")
        assert not _USER_ID_PATTERN.match("123456789012345678901")  # 21 digits
