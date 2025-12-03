"""LLM Agent service using OpenAI GPT-4 as fallback for regions where Claude is blocked."""

from typing import Optional
import json
from datetime import datetime, timedelta
import openai
import structlog

from app.config import settings
from app.schemas.events import EventDTO, IntentType
from app.utils.datetime_parser import parse_datetime_range

logger = structlog.get_logger()


class LLMAgentOpenAI:
    """
    LLM Agent for understanding natural language calendar commands.

    Uses OpenAI GPT-4 with function calling to extract structured
    event information from user queries.

    This is a drop-in replacement for Anthropic Claude agent,
    preserving all logic for update/delete operations with existing_events.
    """

    def __init__(self):
        """Initialize LLM agent with OpenAI client."""
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # or "gpt-4o" for better quality

        # System prompt will be generated per request with current date
        self.base_system_prompt = """Ты - интеллектуальный календарный ассистент.
Твоя задача - понимать команды пользователя на естественном языке (русском или английском)
и преобразовывать их в структурированные действия с календарем.

Возможные действия (intent):
- create: создать новое событие
- update: изменить существующее событие
- delete: удалить событие
- query: запросить информацию о событиях
- find_free_slots: найти свободное время
- clarify: запросить уточнение, если данных недостаточно

Правила:
1. Всегда возвращай время в формате ISO 8601 с таймзоной указанной для пользователя
2. Если не хватает информации (даты, времени, названия) - используй intent=clarify
3. ВАЖНО: Для относительных дат (завтра, послезавтра, в пятницу) вычисляй конкретную дату относительно ТЕКУЩЕЙ ДАТЫ
4. ВАЖНО: Если дата НЕ указана явно и НЕ является относительной - используй intent=clarify
5. ВАЖНО: Используй контекст предыдущих сообщений - если пользователь отвечает на уточняющий вопрос, дополни информацию из истории
6. Длительность по умолчанию - 60 минут, если не указано иное
7. Извлекай участников из текста (имена, email)

Примеры распознавания времени:
- "встреча в 10" или "на 10" -> 10:00 (утро)
- "встреча в 14" или "на 14" -> 14:00 (день)
- "встреча в 18" или "на 18" -> 18:00 (вечер)
- "перенеси на 15" -> новое время 15:00 (НЕ дата!)
- "перенеси на 15-е" -> новая дата 15-е число

Примеры команд:
- "Встреча с командой завтра в 10" -> create, title="Встреча с командой", start=завтра 10:00
- "Что у меня на завтра?" -> query, query_date_start=завтра
- "Свободное время в пятницу" -> find_free_slots, query_date_start=пятница
- "Перенеси встречу с Катей на 14" -> update, найти "Встреча с Катей", new start_time=14:00 ТОГО ЖЕ ДНЯ
- "Перенеси на среду" -> update или clarify (нужно знать какую встречу)
"""

    async def extract_event(
        self,
        user_text: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        timezone: str = 'Europe/Moscow',
        existing_events: Optional[list] = None
    ) -> EventDTO:
        """
        Extract structured event information from natural language text.

        Args:
            user_text: User's natural language command
            user_id: User identifier for context
            conversation_history: Previous messages for context
            timezone: User's timezone
            existing_events: List of existing calendar events from DB (for update/delete)

        Returns:
            EventDTO with extracted information

        Examples:
            >>> await extract_event("Запланируй встречу с Иваном на пятницу 15:00")
            EventDTO(intent="create", title="Встреча с Иваном", ...)
        """
        logger.info("llm_extract_start_openai", user_text=user_text, user_id=user_id)

        try:
            # Get current date/time in user's timezone
            import pytz
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            current_date_str = now.strftime('%d.%m.%Y')  # Format: DD.MM.YYYY
            current_datetime_str = now.strftime('%d.%m.%Y %H:%M')
            current_weekday = now.strftime('%A')  # Day of week

            # Weekday translation
            weekdays_ru = {
                'Monday': 'понедельник',
                'Tuesday': 'вторник',
                'Wednesday': 'среда',
                'Thursday': 'четверг',
                'Friday': 'пятница',
                'Saturday': 'суббота',
                'Sunday': 'воскресенье'
            }
            current_weekday_ru = weekdays_ru.get(current_weekday, current_weekday)

            # Get timezone offset
            tz_offset = now.strftime('%z')
            tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}"  # Format: +03:00

            # Prepare events list to prepend to user message
            events_prefix = ""
            if existing_events and len(existing_events) > 0:
                events_prefix = "<existing_calendar_events>\n"
                for event in existing_events:
                    event_time = event.start.strftime('%d.%m.%Y %H:%M') if hasattr(event, 'start') else 'Unknown'
                    event_title = event.summary if hasattr(event, 'summary') else 'No title'
                    # CalendarEvent uses 'id' attribute, not 'uid'
                    event_id = event.id if hasattr(event, 'id') else 'unknown'
                    events_prefix += f"Event: {event_title}\nTime: {event_time}\nID: {event_id}\n\n"
                events_prefix += """</existing_calendar_events>

CRITICAL: For update/delete operations:
- Find the event in the list above by matching title/description
- COPY the exact ID value - NEVER use "unknown"
- Example: "перенеси встречу с Леной" → find "Встреча с Леной" → copy its ID

User request:
"""

            # Create dynamic system prompt with current date
            system_prompt = f"""{self.base_system_prompt}

ВАЖНО: ТЕКУЩАЯ ДАТА И ВРЕМЯ: {current_datetime_str} ({timezone}, UTC{tz_offset_formatted}), {current_weekday_ru}
Используй эту дату для расчета относительных дат (завтра, послезавтра, через неделю и т.д.)

Примеры относительных дат от ТЕКУЩЕЙ ДАТЫ ({current_date_str}):
- "завтра" = {(now + timedelta(days=1)).strftime('%d.%m.%Y')}
- "послезавтра" = {(now + timedelta(days=2)).strftime('%d.%m.%Y')}
- "через неделю" = {(now + timedelta(days=7)).strftime('%d.%m.%Y')}
"""

            # First, try to parse datetime with dateparser
            start_time, end_time, duration = parse_datetime_range(user_text)

            # Prepare messages with events prepended to user text
            messages = [{"role": "system", "content": system_prompt}]

            # Add conversation history if exists
            if conversation_history:
                messages.extend(conversation_history)

            # Add current user message with events prefix
            user_message_content = events_prefix + user_text
            messages.append({
                "role": "user",
                "content": user_message_content
            })

            # Build dynamic enum for event_id with real IDs from existing events
            event_id_enum = ["none"]  # default value for create/query
            if existing_events and len(existing_events) > 0:
                for event in existing_events:
                    # CalendarEvent uses 'id' attribute, not 'uid'
                    if hasattr(event, 'id') and event.id:
                        event_id_enum.append(str(event.id))

            # Define function for OpenAI with dynamic event_id enum
            functions = [{
                "name": "set_calendar_action",
                "description": "Установить действие с календарем на основе команды пользователя",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["create", "update", "delete", "query", "find_free_slots", "clarify"],
                            "description": "Тип действия"
                        },
                        "title": {
                            "type": "string",
                            "description": "Название события"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Время начала в ISO 8601 (Europe/Moscow)"
                        },
                        "end_time": {
                            "type": "string",
                            "description": "Время окончания в ISO 8601"
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Длительность в минутах"
                        },
                        "location": {
                            "type": "string",
                            "description": "Место встречи"
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Участники (email или имена)"
                        },
                        "event_id": {
                            "type": "string",
                            "enum": event_id_enum,
                            "description": "ID события для update/delete - ВЫБЕРИ из списка enum по названию/описанию события. Для create/query используй 'none'"
                        },
                        "clarify_question": {
                            "type": "string",
                            "description": "Вопрос для уточнения (если intent=clarify)"
                        },
                        "query_date_start": {
                            "type": "string",
                            "description": "Начальная дата для запросов (ISO 8601)"
                        },
                        "query_date_end": {
                            "type": "string",
                            "description": "Конечная дата для запросов (ISO 8601)"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Уверенность в разборе (0-1)"
                        }
                    },
                    "required": ["intent"]
                }
            }]

            # DEBUG: Log what we're sending to OpenAI
            logger.debug("openai_api_call",
                        event_id_enum=event_id_enum,
                        user_message_preview=user_message_content[:200] if len(user_message_content) > 200 else user_message_content)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=functions,
                function_call={"name": "set_calendar_action"},
                temperature=0.2
            )

            logger.debug("llm_response_openai", response=response.model_dump())

            # Extract function call from response
            event_dto = self._parse_openai_response(
                response,
                user_text,
                start_time,
                end_time,
                duration
            )

            logger.info(
                "llm_extract_success_openai",
                intent=event_dto.intent,
                confidence=event_dto.confidence
            )

            return event_dto

        except Exception as e:
            logger.error("llm_extract_error_openai", error=str(e), exc_info=True)

            # Return clarify intent on error
            return EventDTO(
                intent=IntentType.CLARIFY,
                confidence=0.0,
                clarify_question="Извините, я не совсем понял. Не могли бы вы переформулировать?",
                raw_text=user_text
            )

    def _parse_openai_response(
        self,
        response,
        user_text: str,
        parsed_start: Optional[datetime],
        parsed_end: Optional[datetime],
        parsed_duration: Optional[int]
    ) -> EventDTO:
        """Parse OpenAI API response into EventDTO."""

        # Find function call in response
        message = response.choices[0].message

        if not message.function_call:
            # No function call, return clarify
            return EventDTO(
                intent=IntentType.CLARIFY,
                confidence=0.3,
                clarify_question="Не могли бы вы уточнить детали?",
                raw_text=user_text
            )

        # Extract arguments from function call
        try:
            input_data = json.loads(message.function_call.arguments)
        except json.JSONDecodeError:
            return EventDTO(
                intent=IntentType.CLARIFY,
                confidence=0.2,
                clarify_question="Не могли бы вы переформулировать?",
                raw_text=user_text
            )

        # Build EventDTO
        intent = IntentType(input_data.get("intent", "clarify"))

        # Parse datetimes
        start_time = None
        end_time = None

        if "start_time" in input_data:
            try:
                start_time = datetime.fromisoformat(input_data["start_time"])
            except:
                start_time = parsed_start

        if "end_time" in input_data:
            try:
                end_time = datetime.fromisoformat(input_data["end_time"])
            except:
                end_time = parsed_end

        # Use parsed values as fallback
        if not start_time:
            start_time = parsed_start
        if not end_time:
            end_time = parsed_end

        duration_minutes = input_data.get("duration_minutes", parsed_duration)

        # Build DTO
        event_dto = EventDTO(
            intent=intent,
            confidence=input_data.get("confidence", 0.75),
            title=input_data.get("title"),
            description=None,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            location=input_data.get("location"),
            attendees=input_data.get("attendees", []),
            event_id=input_data.get("event_id"),  # For update/delete
            clarify_question=input_data.get("clarify_question"),
            query_date_start=self._parse_optional_datetime(input_data.get("query_date_start")),
            query_date_end=self._parse_optional_datetime(input_data.get("query_date_end")),
            raw_text=user_text
        )

        return event_dto

    def _parse_optional_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse optional datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return None


# Global instance
llm_agent_openai = LLMAgentOpenAI()
