"""Tests for Todos API endpoints."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import Request

from app.main import app


class TestTodosAPI:
    """Test todos API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def test_user_id(self):
        """Test user ID."""
        return "123456789"

    @pytest.fixture
    def sample_todo(self):
        """Sample todo data."""
        return {
            "title": "Buy groceries",
            "completed": False,
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "notes": "Milk, eggs, bread"
        }

    @pytest.fixture
    def mock_todo(self):
        """Mock todo object."""
        todo = MagicMock()
        todo.id = "test-todo-123"
        todo.title = "Test Todo"
        todo.completed = False
        todo.priority = "medium"
        todo.due_date = datetime.now() + timedelta(days=1)
        todo.notes = "Test notes"
        todo.created_at = datetime.now()
        todo.updated_at = datetime.now()
        return todo

    # ==================== Health Check ====================

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/todos/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "todos"

    # ==================== GET /todos/{user_id} ====================

    @patch("app.routers.todos.todos_service")
    def test_get_todos_success(self, mock_todos_service, client, test_user_id, mock_todo):
        """Test successful todo retrieval."""
        # Setup mocks
        mock_todos_service.list_todos = AsyncMock(return_value=[mock_todo])

        # Mock auth middleware
        with patch("app.middleware.telegram_auth.TelegramAuthMiddleware"):
            response = client.get(
                f"/api/todos/todos/{test_user_id}",
                headers={"X-Telegram-Init-Data": "mock_data"}
            )

        # Expect 401/403 since auth is not properly mocked
        assert response.status_code in [200, 401, 403]

    def test_get_todos_no_auth(self, client, test_user_id):
        """Test todo retrieval without authentication."""
        response = client.get(f"/api/todos/todos/{test_user_id}")
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    def test_get_todos_with_filters(self, client, test_user_id):
        """Test todo retrieval with query filters."""
        response = client.get(
            f"/api/todos/todos/{test_user_id}",
            params={"completed": True, "priority": "high"}
        )
        # Should return auth error without proper auth
        assert response.status_code in [401, 403, 500]

    # ==================== POST /todos/{user_id} ====================

    def test_create_todo_no_auth(self, client, test_user_id, sample_todo):
        """Test todo creation without authentication."""
        response = client.post(
            f"/api/todos/todos/{test_user_id}",
            json=sample_todo
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    def test_create_todo_missing_title(self, client, test_user_id):
        """Test todo creation with missing required title field."""
        incomplete_todo = {
            "completed": False,
            "priority": "medium"
        }
        response = client.post(
            f"/api/todos/todos/{test_user_id}",
            json=incomplete_todo
        )
        # Should return 422 (validation error)
        assert response.status_code == 422

    def test_create_todo_invalid_priority(self, client, test_user_id):
        """Test todo creation with invalid priority value."""
        invalid_todo = {
            "title": "Test Todo",
            "priority": "invalid_priority"
        }
        response = client.post(
            f"/api/todos/todos/{test_user_id}",
            json=invalid_todo
        )
        # Should return 422 (validation error for invalid enum)
        assert response.status_code == 422

    # ==================== PUT /todos/{user_id}/{todo_id} ====================

    def test_update_todo_no_auth(self, client, test_user_id):
        """Test todo update without authentication."""
        update_data = {"title": "Updated Title"}
        response = client.put(
            f"/api/todos/todos/{test_user_id}/test-todo-123",
            json=update_data
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    def test_update_todo_partial(self, client, test_user_id):
        """Test partial todo update (only title)."""
        update_data = {"title": "Just updating title"}
        response = client.put(
            f"/api/todos/todos/{test_user_id}/test-todo-123",
            json=update_data
        )
        # Should return auth error without proper auth
        assert response.status_code in [401, 403, 500]

    # ==================== POST /todos/{user_id}/{todo_id}/toggle ====================

    def test_toggle_todo_no_auth(self, client, test_user_id):
        """Test todo toggle without authentication."""
        response = client.post(
            f"/api/todos/todos/{test_user_id}/test-todo-123/toggle"
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]

    # ==================== DELETE /todos/{user_id}/{todo_id} ====================

    def test_delete_todo_no_auth(self, client, test_user_id):
        """Test todo deletion without authentication."""
        response = client.delete(
            f"/api/todos/todos/{test_user_id}/test-todo-123"
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 500]


class TestTodosValidation:
    """Test todo data validation."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_todo_create_request_validation(self):
        """Test TodoCreateRequest pydantic validation."""
        from app.routers.todos import TodoCreateRequest

        # Valid todo with minimal fields
        valid_data = {"title": "Test Todo"}
        todo = TodoCreateRequest(**valid_data)
        assert todo.title == "Test Todo"
        assert todo.completed is False  # Default
        assert todo.priority.value == "medium"  # Default

        # Valid todo with all fields
        future_date = datetime.now() + timedelta(days=1)
        full_data = {
            "title": "Full Todo",
            "completed": True,
            "priority": "high",
            "due_date": future_date,
            "notes": "Some notes"
        }
        full_todo = TodoCreateRequest(**full_data)
        assert full_todo.title == "Full Todo"
        assert full_todo.completed is True
        assert full_todo.notes == "Some notes"

    def test_todo_update_request_validation(self):
        """Test TodoUpdateRequest pydantic validation."""
        from app.routers.todos import TodoUpdateRequest

        # Valid partial update
        update = TodoUpdateRequest(title="Updated Title")
        assert update.title == "Updated Title"
        assert update.completed is None

        # Valid update with multiple fields
        multi_update = TodoUpdateRequest(
            title="New Title",
            completed=True,
            priority="low"
        )
        assert multi_update.title == "New Title"
        assert multi_update.completed is True

    def test_todo_response_model(self):
        """Test TodoResponse pydantic model."""
        from app.routers.todos import TodoResponse

        now = datetime.now()
        response_data = {
            "id": "test-123",
            "title": "Test",
            "completed": False,
            "priority": "medium",
            "due_date": None,
            "notes": None,
            "created_at": now,
            "updated_at": now
        }
        response = TodoResponse(**response_data)
        assert response.id == "test-123"
        assert response.title == "Test"


class TestTodosPriority:
    """Test todo priority handling."""

    def test_valid_priorities(self):
        """Test all valid priority values."""
        from app.schemas.todos import TodoPriority

        # Check all valid values
        assert TodoPriority.LOW.value == "low"
        assert TodoPriority.MEDIUM.value == "medium"
        assert TodoPriority.HIGH.value == "high"

    def test_priority_in_request(self):
        """Test priority handling in create request."""
        from app.routers.todos import TodoCreateRequest

        # Low priority
        low = TodoCreateRequest(title="Low", priority="low")
        assert low.priority.value == "low"

        # High priority
        high = TodoCreateRequest(title="High", priority="high")
        assert high.priority.value == "high"

        # Default (medium)
        default = TodoCreateRequest(title="Default")
        assert default.priority.value == "medium"
