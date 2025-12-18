"""Pytest configuration and fixtures."""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

# Mark that we're running in pytest environment
# This allows test detection in analytics_service
os.environ['PYTEST_RUNNING'] = '1'


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "123456789"


@pytest.fixture
def sample_event_text():
    """Sample event text for testing."""
    return "Запланируй встречу с командой завтра в 10:00 на час"
