"""Unit tests for TelegramHandler.

Tests cover:
- Rate limiting integration
- Message handling
- Command handling
- Dialog history management
- Event context management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Mark tests to skip heavy dependencies
pytestmark = pytest.mark.unit


class MockUpdate:
    """Mock Telegram Update object."""

    def __init__(self, user_id: str = "123456789", text: str = "Привет"):
        self.effective_user = MagicMock()
        self.effective_user.id = int(user_id)
        self.effective_user.username = "test_user"
        self.effective_user.first_name = "Test"
        self.effective_user.last_name = "User"

        self.message = MagicMock()
        self.message.text = text
        self.message.reply_text = AsyncMock()
        self.message.chat_id = int(user_id)
        self.message.voice = None
        self.message.photo = None


class MockApplication:
    """Mock Telegram Application."""

    def __init__(self):
        self.bot = MagicMock()
        self.bot.send_message = AsyncMock()


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that allows all requests."""
    limiter = MagicMock()
    limiter.check_rate_limit.return_value = (True, "")
    limiter.record_message = MagicMock()
    return limiter


@pytest.fixture
def mock_rate_limiter_blocked():
    """Mock rate limiter that blocks requests."""
    limiter = MagicMock()
    limiter.check_rate_limit.return_value = (False, "too_many_requests_per_minute")
    return limiter


@pytest.fixture
def mock_analytics():
    """Mock analytics service."""
    analytics = MagicMock()
    analytics.log_action = MagicMock()
    analytics.record_user = MagicMock()
    return analytics


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_request(self, mock_rate_limiter, mock_analytics):
        """Test that requests within rate limit are allowed."""
        with patch("app.services.telegram_handler.get_rate_limiter", return_value=mock_rate_limiter), \
             patch("app.services.telegram_handler.analytics_service", mock_analytics), \
             patch("app.services.telegram_handler.llm_agent_yandex") as mock_llm:

            mock_llm.process_message = AsyncMock(return_value={
                "response": "Test response",
                "intent": "message"
            })

            from app.services.telegram_handler import TelegramHandler

            app = MockApplication()
            handler = TelegramHandler(app)

            update = MockUpdate()
            await handler.handle_update(update)

            # Rate limiter should be checked
            mock_rate_limiter.check_rate_limit.assert_called_once_with("123456789")

            # Message should be processed (not rate limited)
            # Check that reply_text was called (response sent)
            assert update.message.reply_text.called

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_request(self, mock_rate_limiter_blocked):
        """Test that requests exceeding rate limit are blocked."""
        with patch("app.services.telegram_handler.get_rate_limiter", return_value=mock_rate_limiter_blocked):

            from app.services.telegram_handler import TelegramHandler

            app = MockApplication()
            handler = TelegramHandler(app)

            update = MockUpdate()
            await handler.handle_update(update)

            # Rate limiter should be checked
            mock_rate_limiter_blocked.check_rate_limit.assert_called_once()

            # Should send rate limit message
            update.message.reply_text.assert_called()
            call_args = update.message.reply_text.call_args[0][0]
            assert "подождите" in call_args.lower() or "запросов" in call_args.lower()


class TestDialogHistory:
    """Tests for dialog history management."""

    def test_dialog_history_initialization(self):
        """Test that dialog history is initialized correctly."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Dialog history should be empty initially
        assert len(handler.dialog_history) == 0

    def test_dialog_history_lru_eviction(self):
        """Test that dialog history respects LRU eviction."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Add dialog history for many users
        for i in range(1100):
            handler.dialog_history[str(i)] = [{"role": "user", "text": f"test {i}"}]

        # Should be limited to max_size (1000)
        assert len(handler.dialog_history) <= 1000


class TestEventContext:
    """Tests for event context management."""

    def test_event_context_initialization(self):
        """Test that event context is initialized correctly."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Event context should be empty initially
        assert len(handler.event_context) == 0

    def test_event_context_structure(self):
        """Test event context data structure."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Simulate adding event context
        handler.event_context["123456789"] = {
            "event_ids": ["uuid-1", "uuid-2"],
            "messages_age": 0
        }

        ctx = handler.event_context["123456789"]
        assert "event_ids" in ctx
        assert "messages_age" in ctx
        assert len(ctx["event_ids"]) == 2


class TestMessageHandling:
    """Tests for message handling."""

    @pytest.mark.asyncio
    async def test_empty_message_ignored(self, mock_rate_limiter):
        """Test that empty updates are ignored."""
        with patch("app.services.telegram_handler.get_rate_limiter", return_value=mock_rate_limiter):

            from app.services.telegram_handler import TelegramHandler

            app = MockApplication()
            handler = TelegramHandler(app)

            # Update without message
            update = MagicMock()
            update.message = None

            await handler.handle_update(update)

            # Rate limiter should not be called for empty messages
            mock_rate_limiter.check_rate_limit.assert_not_called()


class TestConversationHistory:
    """Tests for conversation history management."""

    def test_conversation_history_lru_limit(self):
        """Test conversation history respects LRU limit."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Add history for many users
        for i in range(1100):
            handler.conversation_history[str(i)] = ["test"]

        # Should be limited to max_size
        assert len(handler.conversation_history) <= 1000


class TestUserTimezones:
    """Tests for user timezone management."""

    def test_timezone_storage(self):
        """Test timezone storage."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Store timezone
        handler.user_timezones["123456789"] = "Europe/Moscow"

        assert handler.user_timezones["123456789"] == "Europe/Moscow"

    def test_timezone_lru_limit(self):
        """Test timezone storage respects LRU limit."""
        from app.services.telegram_handler import TelegramHandler

        app = MockApplication()
        handler = TelegramHandler(app)

        # Add timezones for many users
        for i in range(1100):
            handler.user_timezones[str(i)] = "UTC"

        # Should be limited to max_size
        assert len(handler.user_timezones) <= 1000
