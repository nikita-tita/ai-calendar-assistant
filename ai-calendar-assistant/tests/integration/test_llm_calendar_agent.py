"""Integration tests for Calendar LLM Agent."""

import pytest
from datetime import datetime
from app.services.llm_agent_yandex import LLMAgentYandex
from app.schemas.events import IntentType


@pytest.fixture
def llm_agent():
    """Create LLM agent instance."""
    return LLMAgentYandex()


@pytest.mark.asyncio
class TestCalendarLLMIntentDetection:
    """Test intent detection from user messages."""

    async def test_create_intent_detection(self, llm_agent):
        """Test detecting CREATE intent."""
        # Russian
        result = await llm_agent.extract_event("Запланируй встречу с командой завтра в 10:00")
        assert result.intent == IntentType.CREATE
        assert result.title is not None
        assert "встреч" in result.title.lower() or "команд" in result.title.lower()
        
        # English
        result = await llm_agent.extract_event("Create meeting with team tomorrow at 10am")
        assert result.intent == IntentType.CREATE

    async def test_query_intent_detection(self, llm_agent):
        """Test detecting QUERY intent."""
        # Russian
        result = await llm_agent.extract_event("Что у меня на завтра?")
        assert result.intent == IntentType.QUERY
        
        # English
        result = await llm_agent.extract_event("What do I have tomorrow?")
        assert result.intent == IntentType.QUERY

    async def test_find_free_slots_intent(self, llm_agent):
        """Test detecting FIND_FREE_SLOTS intent."""
        # Russian
        result = await llm_agent.extract_event("Какие свободные слоты в пятницу?")
        assert result.intent == IntentType.FIND_FREE_SLOTS
        
        # English
        result = await llm_agent.extract_event("Free time on Friday")
        assert result.intent == IntentType.FIND_FREE_SLOTS

    async def test_clarify_intent_detection(self, llm_agent):
        """Test detecting CLARIFY intent when info is missing."""
        # No date
        result = await llm_agent.extract_event("Создай встречу")
        assert result.intent == IntentType.CLARIFY
        assert result.clarify_question is not None
        
        # No time
        result = await llm_agent.extract_event("Встреча завтра")
        # Should ask for time
        assert result.intent == IntentType.CLARIFY or result.intent == IntentType.CREATE


@pytest.mark.asyncio
class TestCalendarLLMDateParsing:
    """Test date and time parsing from natural language."""

    async def test_relative_date_parsing(self, llm_agent):
        """Test parsing relative dates."""
        # Tomorrow
        result = await llm_agent.extract_event("Встреча завтра в 15:00")
        assert result.intent == IntentType.CREATE
        assert result.start_time is not None
        assert result.start_time.date() > datetime.now().date()
        
        # Friday
        result = await llm_agent.extract_event("Meeting on Friday at 2pm")
        assert result.intent == IntentType.CREATE
        assert result.start_time is not None

    async def test_time_parsing(self, llm_agent):
        """Test time parsing from various formats."""
        # 24-hour format
        result = await llm_agent.extract_event("Встреча в 14:00")
        assert result.intent == IntentType.CREATE
        assert result.start_time is not None
        assert result.start_time.hour == 14
        
        # 12-hour format
        result = await llm_agent.extract_event("Meeting at 3 PM")
        assert result.intent == IntentType.CREATE
        assert result.start_time is not None
        assert result.start_time.hour == 15  # 3 PM = 15:00

    async def test_absolute_date_parsing(self, llm_agent):
        """Test parsing absolute dates."""
        result = await llm_agent.extract_event("Встреча 25 января в 10:00")
        assert result.intent == IntentType.CREATE
        assert result.start_time is not None


@pytest.mark.asyncio
class TestCalendarLLMMultilingual:
    """Test multilingual support."""

    async def test_russian_language(self, llm_agent):
        """Test Russian language support."""
        result = await llm_agent.extract_event("Создай встречу с Иваном на завтра в 15:00")
        assert result.intent == IntentType.CREATE
        assert result.title is not None
        assert "встреч" in result.title.lower()

    async def test_english_language(self, llm_agent):
        """Test English language support."""
        result = await llm_agent.extract_event("Create meeting with John tomorrow at 3pm")
        assert result.intent == IntentType.CREATE
        assert result.title is not None
        assert "meeting" in result.title.lower()


@pytest.mark.asyncio
class TestCalendarLLMEdgeCases:
    """Test edge cases and complex scenarios."""

    async def test_recurring_events(self, llm_agent):
        """Test recurring events detection."""
        result = await llm_agent.extract_event("Каждый день в 9 утра")
        # Should detect recurring pattern
        assert result.intent in [IntentType.CREATE_RECURRING, IntentType.CLARIFY]

    async def test_update_with_existing_events(self, llm_agent):
        """Test update intent with existing events context."""
        existing_events = [
            {"title": "Встреча с Катей", "uid": "event1", "start_time": "2025-01-28T10:00:00"}
        ]
        
        result = await llm_agent.extract_event(
            "Перенеси встречу с Катей на 14:00",
            existing_events=existing_events
        )
        
        assert result.intent == IntentType.UPDATE
        assert result.event_id is not None or result.title is not None

    async def test_delete_with_existing_events(self, llm_agent):
        """Test delete intent with existing events context."""
        existing_events = [
            {"title": "Утренние ритуалы", "uid": "event1", "start_time": "2025-01-28T09:00:00"}
        ]
        
        result = await llm_agent.extract_event(
            "Удали утренние ритуалы",
            existing_events=existing_events
        )
        
        assert result.intent in [IntentType.DELETE, IntentType.DELETE_BY_CRITERIA]

    async def test_schedule_format_detection(self, llm_agent):
        """Test schedule format detection (multiple events)."""
        schedule_text = """Тайминг на завтра:
12:00-12:30 Приветствие
12:30-13:00 Выступление
13:00-13:30 Обсуждение"""
        
        result = await llm_agent.extract_event(schedule_text)
        
        # Should detect batch format
        assert result.intent == IntentType.BATCH_CONFIRM or result.batch_actions is not None


@pytest.mark.skip(reason="Requires Yandex GPT API key")
class TestCalendarLLMIntegration:
    """Full integration tests with actual Yandex GPT API."""

    async def test_full_conversation_flow(self, llm_agent):
        """Test full conversation with context."""
        # First message - incomplete
        result1 = await llm_agent.extract_event("Встреча")
        assert result1.intent == IntentType.CLARIFY
        
        # Second message - with clarification
        conversation_history = [
            {"role": "user", "content": "Встреча"},
            {"role": "assistant", "content": result1.clarify_question or "Уточните"}
        ]
        
        result2 = await llm_agent.extract_event(
            "Завтра в 10:00 с командой",
            conversation_history=conversation_history
        )
        
        assert result2.intent == IntentType.CREATE
        assert result2.start_time is not None
        assert "команд" in result2.title.lower()

    async def test_complex_event_creation(self, llm_agent):
        """Test creating complex event with all fields."""
        result = await llm_agent.extract_event(
            "Запланируй встречу с Иваном Ивановым (ivan@example.com) "
            "завтра в 15:00 на 2 часа в офисе на Тверской, 1"
        )
        
        assert result.intent == IntentType.CREATE
        assert result.title is not None
        assert result.start_time is not None
        assert result.duration_minutes == 120
        # Should extract location and attendees
        # assert result.location is not None
        # assert len(result.attendees) > 0
