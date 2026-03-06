"""LLM Agent service using Yandex GPT (YandexGPT Foundation Models)."""

from typing import Optional, List
import asyncio
import json
import time
from datetime import datetime, timedelta
import httpx
import structlog

from app.config import settings
from app.schemas.events import EventDTO, IntentType
from app.utils.datetime_parser import parse_datetime_range
from app.services.translations import get_translation, Language

logger = structlog.get_logger()


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass

# Analytics imports (optional - graceful fallback if not available)
try:
    from app.services.analytics_service import analytics_service
    from app.models.analytics import ActionType
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False
    analytics_service = None


class LLMAgentYandex:
    """
    LLM Agent for understanding natural language calendar commands.

    Uses Yandex GPT (YandexGPT) with function calling to extract structured
    event information from user queries.

    This is a drop-in replacement for Anthropic Claude agent,
    preserving all logic for update/delete operations with existing_events.
    Works from Russia without restrictions.
    """

    # Circuit breaker settings
    FAILURE_THRESHOLD = 5     # Open circuit after N consecutive failures
    RESET_TIMEOUT = 60        # Seconds before attempting to close circuit
    REQUEST_TIMEOUT = 15.0    # HTTP timeout in seconds

    # Retry settings for content moderation refusals
    MAX_REFUSAL_RETRIES = 2   # Retry attempts when LLM refuses request
    REFUSAL_RETRY_DELAY = 0.5 # Seconds between retries

    # Patterns that indicate Yandex GPT content moderation refusal
    REFUSAL_PATTERNS = [
        "не могу обсуждать",
        "не могу помочь с этим",
        "давайте поговорим о чём-нибудь",
        "давайте поговорим о чем-нибудь",
        "не могу ответить на этот",
        "не в моих возможностях",
    ]

    # Token limits (BIZ-002: prevent excessive API costs)
    # YandexGPT charges per token, limit input to prevent abuse
    MAX_INPUT_CHARS = 4000  # ~1000 tokens (1 token ≈ 4 chars in Russian)
    MAX_INPUT_TOKENS = 1500  # Hard limit for API request

    def __init__(self):
        """Initialize LLM agent with Yandex GPT client."""
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id
        self.model = "yandexgpt"  # Full model - Lite doesn't handle batch commands well
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        # Async HTTP client (reusable with connection pooling)
        self._http_client: Optional[httpx.AsyncClient] = None

        # Circuit breaker state
        self._circuit_open = False
        self._circuit_open_until: float = 0
        self._failure_count = 0

        # OPTIMIZED: Compact Russian-only system prompt (~60% smaller)
        self.base_system_prompt = """Ты - ИИ-ассистент для работы с календарём. Понимаешь русский язык.
Преобразуй команды пользователя в структурированные действия с календарём.

ДЕЙСТВИЯ (intent):
- create: создать событие С УКАЗАНИЕМ ВРЕМЕНИ
- create_recurring: повторяющиеся события (ежедневно/еженедельно/ежемесячно)
- update: изменить существующее событие
- delete: удалить событие
- query: запрос информации о событиях
- find_free_slots: поиск свободного времени
- batch_confirm: несколько событий одной командой
- delete_by_criteria: удаление по критерию (удали все X)
- delete_duplicates: удаление дубликатов
- todo: задача БЕЗ привязки ко времени
- clarify: запросить уточнение

РАЗЛИЧИЕ СОБЫТИЙ И ЗАДАЧ:
intent="todo" когда:
- Глаголы действия БЕЗ времени: написать, позвонить, купить, сделать, подготовить, обновить, проверить, согласовать, договориться
- "завтра", "в понедельник" без конкретного времени
- Слова: "надо", "нужно", "не забыть", "задача"
- ВАЖНО: "задача" ВСЕГДА = intent="todo"
- Сокращения: "пнд" = персональные данные
- КРИТИЧНО: Нет времени → ВСЕГДА intent="todo", НЕ clarify

intent="create" когда:
- Указано время: "в 15:00", "завтра в 10 утра"
- "встреча", "показ", "звонок" С временем

Примеры:
- "Написать отчет завтра" → todo
- "Встреча завтра в 15:00" → create
- "Позвонить Ивану" → todo
- "Показ квартиры в 14:00" → create
- "Обновить пнд" → todo, title="Обновить персональные данные"
- "Встреча завтра" → todo (нет времени)

ПРАВИЛА:
1. Время в ISO 8601 с таймзоной пользователя
2. Для событий без даты/времени/названия → clarify
3. Для TODO: обязателен только title
4. ИСПОЛЬЗУЙ КОНТЕКСТ из предыдущих сообщений
5. Длительность по умолчанию 60 минут
6. "эту неделю" → query_date_end = сегодня + 7 дней

ПОВТОРЯЮЩИЕСЯ СОБЫТИЯ (intent="create_recurring"):
- recurrence_type: "daily" | "weekly" | "monthly"
- recurrence_end_date: дата окончания (по умолчанию {end_of_year_date})
- recurrence_days: для weekly ["mon", "wed", "fri"]
- "каждый день" без периода → до конца года
- "на 3 дня" → +3 дня
- "на неделю" → +7 дней

ТИП СОБЫТИЯ (event_type):
- "showing": показ, просмотр, осмотр квартиры
- "client_call": звонок, созвон с клиентом
- "doc_signing": подписание, сделка, договор
- "dev_meeting": встреча с застройщиком, девелопером
- "generic": всё остальное (по умолчанию)
Примеры:
- "Показ на Пионерской в 14:00" → event_type="showing"
- "Позвонить Иванову в 10:00" → event_type="client_call"
- "Подписание договора завтра в 15:00" → event_type="doc_signing"

УДАЛЕНИЕ:
- "удали все X" → intent="delete_by_criteria", delete_criteria_title_contains="X"
- "удали дубликаты" → intent="delete_duplicates"

НЕСКОЛЬКО СОБЫТИЙ В ОДНОЙ КОМАНДЕ:
- Слова-связки: "потом", "затем", "а потом", "также", "еще"
- "В 17 встреча, в 19 ужин" → batch_actions: [create 17:00, create 19:00]
- "Встреча в 10, потом позвонить маме" → batch_actions: [create, todo]

РАСПИСАНИЕ (3+ строк с временем):
- Паттерн: ЧЧ:ММ-ЧЧ:ММ Название
- intent="batch_confirm" с batch_actions

ВАЖНО: Ответ ТОЛЬКО в JSON формате. Никакого текста до/после JSON."""

    def _is_llm_refusal(self, text: str) -> bool:
        """
        Detect if Yandex GPT refused to process request due to content moderation.

        Args:
            text: Raw LLM response text

        Returns:
            True if response appears to be a refusal
        """
        if not text:
            return False
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.REFUSAL_PATTERNS)

    def _create_todo_fallback(self, user_text: str, user_id: Optional[str] = None) -> EventDTO:
        """
        Create TODO fallback when LLM refuses to process request.

        This is used when Yandex GPT content moderation blocks a legitimate request.
        Instead of failing, we create a simple TODO task from user's text.

        Args:
            user_text: Original user request
            user_id: User ID for logging

        Returns:
            EventDTO with TODO intent
        """
        logger.warning("llm_refusal_fallback_to_todo",
                      user_id=user_id,
                      text=user_text[:100])

        # Log to analytics
        if ANALYTICS_ENABLED and analytics_service and user_id:
            analytics_service.log_action(
                user_id=user_id,
                action_type=ActionType.LLM_PARSE_ERROR,
                details=f"LLM refusal fallback: {user_text[:100]}",
                success=True,
                error_message="Yandex GPT refused, created TODO fallback"
            )

        # Clean up the text for title
        title = user_text.strip()
        if len(title) > 100:
            title = title[:97] + "..."

        return EventDTO(
            intent=IntentType.TODO,
            title=title,
            confidence=0.6,
            raw_text=user_text
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create reusable async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.REQUEST_TIMEOUT, connect=5.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10)
            )
        return self._http_client

    async def close(self):
        """Close HTTP client. Call on shutdown."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("llm_agent_http_client_closed")

    def _check_circuit(self) -> bool:
        """Check if circuit breaker allows requests. Returns True if allowed."""
        if not self._circuit_open:
            return True

        # Check if reset timeout passed
        if time.time() >= self._circuit_open_until:
            self._circuit_open = False
            self._failure_count = 0
            logger.info("circuit_breaker_reset", message="Attempting to close circuit")
            return True

        return False

    def _record_success(self):
        """Record successful request - reset failure count."""
        self._failure_count = 0

    def _record_failure(self):
        """Record failed request - potentially open circuit."""
        self._failure_count += 1

        if self._failure_count >= self.FAILURE_THRESHOLD:
            self._circuit_open = True
            self._circuit_open_until = time.time() + self.RESET_TIMEOUT
            logger.warning("circuit_breaker_opened",
                          failures=self._failure_count,
                          reset_in_seconds=self.RESET_TIMEOUT)

    def _prepare_datetime_context(self, timezone: str) -> dict:
        """
        Prepare datetime context for LLM prompt.

        Returns dict with:
            - now: current datetime in timezone
            - current_date_str: formatted date string
            - current_datetime_str: formatted datetime string
            - current_weekday_ru: weekday name in Russian
            - next_weekdays_ru: dict of next weekday dates
            - tz_offset_formatted: timezone offset string
            - days_until_eoy: days until end of year
            - end_of_year_date: end of year date string
        """
        import pytz
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        current_date_str = now.strftime('%d.%m.%Y')
        current_datetime_str = now.strftime('%d.%m.%Y %H:%M')
        current_weekday = now.strftime('%A')

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

        # Calculate next weekdays
        weekday_to_num = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
            'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        current_weekday_num = now.weekday()

        next_weekdays_ru = {}
        for weekday_name, weekday_num in weekday_to_num.items():
            if weekday_num > current_weekday_num:
                days_ahead = weekday_num - current_weekday_num
            else:
                days_ahead = 7 - (current_weekday_num - weekday_num)
            next_date = now + timedelta(days=days_ahead)
            next_weekdays_ru[weekdays_ru[weekday_name]] = next_date

        # Timezone offset
        tz_offset = now.strftime('%z')
        tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}"

        # Days until end of year
        end_of_year = datetime(now.year, 12, 31, tzinfo=tz)
        days_until_eoy = (end_of_year - now).days + 1
        end_of_year_date = end_of_year.strftime('%Y-%m-%d')

        return {
            'now': now,
            'timezone': timezone,
            'current_date_str': current_date_str,
            'current_datetime_str': current_datetime_str,
            'current_weekday_ru': current_weekday_ru,
            'next_weekdays_ru': next_weekdays_ru,
            'tz_offset_formatted': tz_offset_formatted,
            'days_until_eoy': days_until_eoy,
            'end_of_year_date': end_of_year_date
        }

    def _prepare_events_context(
        self,
        existing_events: Optional[list],
        recent_context: Optional[list],
        conversation_history: Optional[list]
    ) -> str:
        """
        Prepare events context string for LLM prompt.

        Includes:
            - Existing calendar events (for update/delete)
            - Recent context (for follow-up commands)
            - Dialog history
        """
        # Existing events prefix
        events_prefix = ""
        if existing_events and len(existing_events) > 0:
            max_events_in_context = 10
            limited_events = existing_events[:max_events_in_context]
            events_prefix = "<existing_calendar_events>\n"
            for event in limited_events:
                event_time = event.start.strftime('%d.%m.%Y %H:%M') if hasattr(event, 'start') else 'Unknown'
                event_title = event.summary if hasattr(event, 'summary') else 'No title'
                event_id = event.id if hasattr(event, 'id') else 'unknown'
                events_prefix += f"Event: {event_title}\nTime: {event_time}\nID: {event_id}\n\n"
            events_prefix += """</existing_calendar_events>

CRITICAL: For update/delete operations:
- Find the event in the list above by matching title/description
- COPY the exact ID value - NEVER use "unknown"
- Example: "перенеси встречу с Леной" → find "Встреча с Леной" → copy its ID

"""

        # Recent context prefix
        recent_context_prefix = ""
        if recent_context and len(recent_context) > 0:
            recent_context_prefix = "<recent_context>\n"
            recent_context_prefix += "Пользователь ТОЛЬКО ЧТО создал/изменил следующие события:\n"
            for event in recent_context:
                event_time = event.start.strftime('%d.%m.%Y %H:%M') if hasattr(event, 'start') else 'Unknown'
                event_title = event.summary if hasattr(event, 'summary') else 'No title'
                event_id = event.id if hasattr(event, 'id') else 'unknown'
                recent_context_prefix += f"- {event_title} ({event_time}) ID: {event_id}\n"
            recent_context_prefix += """
ВАЖНО: Если пользователь говорит "эти события", "их", "перепиши", "перенеси" БЕЗ указания конкретного названия — он имеет в виду события выше из recent_context.
Используй их ID для update/delete операций.
</recent_context>

"""
        events_prefix += recent_context_prefix + "User request:\n"

        # Dialog history context
        dialog_context = ""
        if conversation_history and len(conversation_history) > 0:
            dialog_context = "<dialog_history>\n"
            for msg in conversation_history[-10:]:
                role = msg.get('role', 'user')
                text = msg.get('text', msg.get('content', ''))[:300]
                if role == 'user':
                    dialog_context += f"Пользователь: {text}\n"
                else:
                    dialog_context += f"Бот: {text}\n"
            dialog_context += "</dialog_history>\n\n"
            dialog_context += "ВАЖНО: Используй контекст диалога для понимания намерений пользователя.\n\n"

        return events_prefix + dialog_context

    def _build_function_schema(self, existing_events: Optional[list]) -> dict:
        """
        Build function schema for LLM with dynamic event_id enum.
        """
        # Build dynamic enum for event_id
        event_id_enum = ["none"]
        if existing_events and len(existing_events) > 0:
            max_events_in_context = 10
            limited_events = existing_events[:max_events_in_context]
            for event in limited_events:
                if hasattr(event, 'id') and event.id:
                    event_id_enum.append(str(event.id))

        return {
            "name": "set_calendar_action",
            "description": "Установить действие с календарем на основе команды пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["create", "create_recurring", "update", "delete", "query", "find_free_slots", "clarify", "batch_confirm", "delete_by_criteria", "delete_duplicates", "todo"],
                        "description": "Тип действия"
                    },
                    "title": {"type": "string", "description": "Название события"},
                    "start_time": {"type": "string", "description": "Время начала в ISO 8601 (Europe/Moscow)"},
                    "end_time": {"type": "string", "description": "Время окончания в ISO 8601"},
                    "duration_minutes": {"type": "integer", "description": "Длительность в минутах"},
                    "location": {"type": "string", "description": "Место встречи"},
                    "attendees": {"type": "array", "items": {"type": "string"}, "description": "Участники (email или имена)"},
                    "event_id": {
                        "type": "string",
                        "enum": event_id_enum,
                        "description": "ID события для update/delete - ВЫБЕРИ из списка enum по названию/описанию события. Для create/query используй 'none'"
                    },
                    "clarify_question": {"type": "string", "description": "Вопрос для уточнения (если intent=clarify)"},
                    "query_date_start": {"type": "string", "description": "Начальная дата для запросов (ISO 8601)"},
                    "query_date_end": {"type": "string", "description": "Конечная дата для запросов (ISO 8601)"},
                    "confidence": {"type": "number", "description": "Уверенность в разборе (0-1)"},
                    "recurrence_type": {"type": "string", "enum": ["daily", "weekly", "monthly"], "description": "Тип повторения для intent=create_recurring"},
                    "recurrence_end_date": {"type": "string", "description": "Дата окончания повторений (ISO 8601) для intent=create_recurring"},
                    "recurrence_days": {
                        "type": "array",
                        "items": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
                        "description": "Дни недели для weekly recurrence (например: ['mon', 'wed', 'fri'])"
                    },
                    "batch_actions": {"type": "array", "items": {"type": "object"}, "description": "Массив действий для intent=batch_confirm (только для удаления или специфичных списков)"}
                },
                "required": ["intent"]
            }
        }, event_id_enum

    def _build_full_prompt(self, dt_context: dict, events_context: str, user_text: str) -> str:
        """
        Build full prompt for LLM API call.
        """
        # Date context block
        date_context = f"""ТЕКУЩАЯ ДАТА: {dt_context['current_datetime_str']} ({dt_context['timezone']}, UTC{dt_context['tz_offset_formatted']}), {dt_context['current_weekday_ru']}

Относительные даты:
- "завтра" = {(dt_context['now'] + timedelta(days=1)).strftime('%Y-%m-%d')}
- "послезавтра" = {(dt_context['now'] + timedelta(days=2)).strftime('%Y-%m-%d')}
- "через неделю" = {(dt_context['now'] + timedelta(days=7)).strftime('%Y-%m-%d')}

Ближайшие дни недели:
- понедельник = {dt_context['next_weekdays_ru']['понедельник'].strftime('%Y-%m-%d')}
- вторник = {dt_context['next_weekdays_ru']['вторник'].strftime('%Y-%m-%d')}
- среда = {dt_context['next_weekdays_ru']['среда'].strftime('%Y-%m-%d')}
- четверг = {dt_context['next_weekdays_ru']['четверг'].strftime('%Y-%m-%d')}
- пятница = {dt_context['next_weekdays_ru']['пятница'].strftime('%Y-%m-%d')}
- суббота = {dt_context['next_weekdays_ru']['суббота'].strftime('%Y-%m-%d')}
- воскресенье = {dt_context['next_weekdays_ru']['воскресенье'].strftime('%Y-%m-%d')}

Используй ТОЧНО эти даты!"""

        # Format base system prompt
        formatted_base_prompt = self.base_system_prompt.format(
            today_str=dt_context['current_date_str'],
            days_until_eoy=dt_context['days_until_eoy'],
            end_of_year_date=dt_context['end_of_year_date']
        )

        system_prompt = f"""{formatted_base_prompt}

{date_context}
"""

        # JSON instruction
        json_instruction = """ФОРМАТ ОТВЕТА: Верни ТОЛЬКО JSON объект с параметрами.

Пример для одного события:
{"intent": "create", "title": "Встреча", "start_time": "2025-01-15T15:00:00+03:00"}

Пример для нескольких событий:
{"intent": "batch_confirm", "batch_actions": [{"intent": "create", "title": "Дорога", "start_time": "2025-01-15T19:00:00+03:00"}, {"intent": "create", "title": "Ужин", "start_time": "2025-01-15T20:00:00+03:00"}]}

Пример для задачи:
{"intent": "todo", "title": "Позвонить маме"}

Пример для уточнения:
{"intent": "clarify", "clarify_question": "Уточните время события"}

ВАЖНО: Возвращай ТОЛЬКО значения параметров, НЕ структуру схемы!
JSON:"""

        # Full user message
        user_message_content = events_context + user_text

        return f"""{system_prompt}

{user_message_content}

{json_instruction}"""

    async def _call_llm_api(
        self,
        full_prompt: str,
        user_id: Optional[str],
        user_text: str,
        event_id_enum: list
    ) -> tuple:
        """
        Call Yandex GPT API with circuit breaker and error handling.

        Returns:
            tuple: (response_data, result_text) or raises exception
        """
        # DEBUG log
        logger.debug("yandex_gpt_api_call",
                    event_id_enum=event_id_enum,
                    user_message_preview=user_text[:200] if len(user_text) > 200 else user_text)

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.2,
                "maxTokens": 2000
            },
            "messages": [
                {
                    "role": "system",
                    "text": full_prompt
                }
            ]
        }

        # Circuit breaker check
        if not self._check_circuit():
            logger.warning("circuit_breaker_reject", message="Yandex GPT temporarily unavailable")
            if ANALYTICS_ENABLED and analytics_service and user_id:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.LLM_ERROR,
                    details=f"Circuit breaker open: {user_text[:100]}",
                    success=False,
                    error_message="Yandex GPT temporarily unavailable (circuit breaker)"
                )
            raise CircuitOpenError("Yandex GPT temporarily unavailable")

        try:
            _http_start = time.perf_counter()
            client = await self._get_http_client()
            response = await client.post(
                self.api_url,
                headers=headers,
                json=payload
            )
            _http_duration_ms = (time.perf_counter() - _http_start) * 1000
            logger.info("yandex_gpt_http_duration", duration_ms=round(_http_duration_ms, 1))

            self._record_success()

        except httpx.TimeoutException as e:
            self._record_failure()
            logger.error("yandex_gpt_timeout", error=str(e))
            if ANALYTICS_ENABLED and analytics_service and user_id:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.LLM_TIMEOUT,
                    details=f"Yandex GPT timeout: {user_text[:100]}",
                    success=False,
                    error_message=f"API request timed out after {self.REQUEST_TIMEOUT}s"
                )
            raise

        except httpx.HTTPError as e:
            self._record_failure()
            logger.error("yandex_gpt_http_error", error=str(e))
            raise

        if response.status_code != 200:
            self._record_failure()
            logger.error("yandex_gpt_api_error", status_code=response.status_code, response=response.text)
            if ANALYTICS_ENABLED and analytics_service and user_id:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.LLM_ERROR,
                    details=f"API error {response.status_code}: {user_text[:100]}",
                    success=False,
                    error_message=f"Status {response.status_code}: {response.text[:200]}"
                )
            raise Exception(f"Yandex GPT API error: {response.status_code} - {response.text}")

        response_data = response.json()
        result_text = response_data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")
        logger.info("yandex_gpt_raw_response", result_text=result_text)

        return response_data, result_text

    def _log_success_analytics(
        self,
        response_data: dict,
        event_dto: 'EventDTO',
        user_id: Optional[str]
    ) -> None:
        """Log successful LLM request to analytics for cost tracking."""
        usage = response_data.get("result", {}).get("usage", {})
        input_tokens = int(usage.get("inputTextTokens", 0))
        output_tokens = int(usage.get("completionTokens", 0))
        total_tokens = int(usage.get("totalTokens", 0))

        # Calculate cost (rubles per 1000 tokens)
        cost_per_1000 = 0.2 if self.model == "yandexgpt-lite" else 1.2
        cost_rub = round(total_tokens * cost_per_1000 / 1000, 4)

        logger.info(
            "llm_extract_success_yandex",
            intent=event_dto.intent,
            confidence=event_dto.confidence,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_rub=cost_rub
        )

        if ANALYTICS_ENABLED and analytics_service and user_id:
            analytics_service.log_action(
                user_id=user_id,
                action_type=ActionType.LLM_REQUEST,
                details=f"intent={event_dto.intent}",
                success=True,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_rub=cost_rub,
                llm_model=self.model
            )

    def _try_local_parser(self, user_text: str, timezone: str = 'Europe/Moscow') -> Optional[EventDTO]:
        """
        Phase 4: Try local regex parser before calling LLM.

        Handles ~60-70% of typical requests (query, todo, create, free_slots)
        without an LLM call, saving cost and latency.

        Returns:
            EventDTO if locally parsed, None to fall through to LLM.
        """
        try:
            from app.services.local_intent_parser import parse_intent
            result = parse_intent(user_text, timezone)
            if result is None:
                return None

            intent_str, params, confidence = result

            if intent_str == "query":
                dto = EventDTO(
                    intent=IntentType.QUERY,
                    confidence=confidence,
                    query_date_start=params.get("query_date_start"),
                    query_date_end=params.get("query_date_end"),
                )
            elif intent_str == "todo":
                dto = EventDTO(
                    intent=IntentType.TODO,
                    confidence=confidence,
                    title=params.get("title"),
                )
            elif intent_str == "create":
                dto = EventDTO(
                    intent=IntentType.CREATE,
                    confidence=confidence,
                    title=params.get("title"),
                    start_time=params.get("start_time"),
                    end_time=params.get("end_time"),
                    event_type=params.get("event_type", "generic"),
                )
            elif intent_str == "find_free_slots":
                dto = EventDTO(
                    intent=IntentType.FIND_FREE_SLOTS,
                    confidence=confidence,
                    query_date_start=params.get("query_date_start"),
                )
            else:
                return None

            logger.info("local_parser_matched",
                       intent=intent_str,
                       confidence=confidence,
                       text=user_text[:100])
            return dto

        except Exception as e:
            logger.warning("local_parser_error", error=str(e))
            return None

    def _detect_schedule_format(self, user_text: str, timezone: str = 'Europe/Moscow', conversation_history: Optional[list] = None) -> Optional[EventDTO]:
        """
        Detect and parse schedule format with multiple time ranges.

        Pattern: Multiple lines with HH:MM-HH:MM format followed by event title
        Example:
            12:45-13:00 Приезд, заселение
            13:00-13:30 Кофе-брейк
            13:30-15:00 Дискуссия

        Returns EventDTO with batch_actions if pattern detected, None otherwise.
        """
        import re
        from datetime import datetime, time
        import pytz

        # Check for schedule keywords
        schedule_keywords = ['тайминг', 'расписание', 'schedule', 'agenda', 'программа']
        has_schedule_keyword = any(keyword in user_text.lower() for keyword in schedule_keywords)

        # Find all time range patterns (HH:MM-HH:MM title)
        # Pattern: optional whitespace, time range, space, title text
        pattern = r'(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})\s+(.+?)(?:\n|$)'
        matches = re.findall(pattern, user_text, re.MULTILINE)

        # Also find single time entries (HH:MM title without end time)
        single_time_pattern = r'^(\d{1,2}:\d{2})\s+([^-–—\n]+)(?:\n|$)'
        single_matches = re.findall(single_time_pattern, user_text, re.MULTILINE)

        # Need at least 3 time entries (ranges or singles) to consider it a schedule
        total_matches = len(matches) + len(single_matches)
        if total_matches < 3:
            return None

        logger.info("schedule_format_detected",
                   matches_count=len(matches),
                   has_keyword=has_schedule_keyword)

        # Extract date context from text
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        target_date = now.date()  # Default to today

        # Check if this is a response to year clarification question
        # Look for year in user text (e.g., "2025", "2026", "этого года", "следующего года")
        year_override = None
        if conversation_history and len(conversation_history) > 0:
            last_message = conversation_history[-1]
            if last_message.get('role') == 'assistant':
                clarify_text = last_message.get('content', '').lower()
                # Check if last message was asking about year
                if ('года' in clarify_text or 'year' in clarify_text) and ('2025' in clarify_text or '2026' in clarify_text):
                    # User is responding to year question
                    text_lower = user_text.lower()
                    if '2025' in text_lower or '2026' in text_lower or '2027' in text_lower:
                        # Extract explicit year
                        year_match = re.search(r'(202\d)', user_text)
                        if year_match:
                            year_override = int(year_match.group(1))
                            logger.info("year_clarification_detected", year=year_override)
                    elif 'следующ' in text_lower or 'next' in text_lower:
                        year_override = now.year + 1
                        logger.info("year_clarification_next_year", year=year_override)
                    elif 'этого' in text_lower or 'this' in text_lower or 'текущ' in text_lower or 'current' in text_lower:
                        year_override = now.year
                        logger.info("year_clarification_current_year", year=year_override)

        # Month name mappings
        ru_months = {
            'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
            'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
            'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
        }

        en_months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }

        text_lower = user_text.lower()

        # Try relative date keywords first
        if 'завтра' in text_lower or 'tomorrow' in text_lower:
            from datetime import timedelta
            target_date = (now + timedelta(days=1)).date()
        elif 'послезавтра' in text_lower:
            from datetime import timedelta
            target_date = (now + timedelta(days=2)).date()
        elif 'сегодня' in text_lower or 'today' in text_lower:
            target_date = now.date()
        else:
            # Try Russian month pattern: "на 23 октября"
            ru_pattern = r'на\s+(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)'
            ru_match = re.search(ru_pattern, text_lower)
            if ru_match:
                day = int(ru_match.group(1))
                month = ru_months[ru_match.group(2)]
                month_name = ru_match.group(2)

                # Use year_override if provided by user in response to clarification
                if year_override:
                    year = year_override
                    target_date = datetime(year, month, day, tzinfo=tz).date()
                    logger.info("using_year_override", year=year, date=target_date)
                else:
                    # Check both current and next year
                    year = now.year
                    candidate_date = datetime(year, month, day, tzinfo=tz).date()

                    # If date is in the past (more than 1 day ago), it's ambiguous
                    from datetime import timedelta
                    if candidate_date < (now.date() - timedelta(days=1)):
                        # Date already passed - need clarification
                        # Return None to let LLM handle clarification
                        logger.info("schedule_date_ambiguous_past",
                                   date=f"{day} {month_name}",
                                   current_year=year,
                                   next_year=year+1)
                        return None  # Let LLM ask for year clarification

                    target_date = candidate_date
            else:
                # Try English month pattern
                en_pattern = r'на\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)'
                en_match = re.search(en_pattern, text_lower)
                if en_match:
                    day = int(en_match.group(1))
                    month = en_months[en_match.group(2)]
                    month_name = en_match.group(2)

                    # Use year_override if provided
                    if year_override:
                        year = year_override
                        target_date = datetime(year, month, day, tzinfo=tz).date()
                        logger.info("using_year_override_en", year=year, date=target_date)
                    else:
                        year = now.year
                        candidate_date = datetime(year, month, day, tzinfo=tz).date()

                        from datetime import timedelta
                        if candidate_date < (now.date() - timedelta(days=1)):
                            logger.info("schedule_date_ambiguous_past",
                                       date=f"{day} {month_name}",
                                       current_year=year,
                                       next_year=year+1)
                            return None  # Let LLM ask for year clarification

                        target_date = candidate_date
                else:
                    # Try DD.MM.YYYY pattern
                    date_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})'
                    date_match = re.search(date_pattern, text_lower)
                    if date_match:
                        day = int(date_match.group(1))
                        month = int(date_match.group(2))
                        year = int(date_match.group(3))
                        if year < 100:
                            year += 2000
                        target_date = datetime(year, month, day, tzinfo=tz).date()

        # Build batch_actions array
        batch_actions = []

        # Process time range entries (with start and end times)
        for start_time_str, end_time_str, title in matches:
            try:
                # Parse times
                start_hour, start_min = map(int, start_time_str.split(':'))
                end_hour, end_min = map(int, end_time_str.split(':'))

                # Create datetime objects with target date
                start_dt = datetime.combine(
                    target_date,
                    time(start_hour, start_min),
                    tzinfo=tz
                )
                end_dt = datetime.combine(
                    target_date,
                    time(end_hour, end_min),
                    tzinfo=tz
                )

                # Clean up title (remove extra whitespace, trailing punctuation)
                title = title.strip().rstrip(',;.')

                # Calculate duration in minutes
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

                batch_actions.append({
                    "intent": "create",
                    "title": title,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "duration_minutes": duration_minutes
                })

            except Exception as e:
                logger.warning("schedule_line_parse_error",
                             line=f"{start_time_str}-{end_time_str} {title}",
                             error=str(e))
                continue

        # Process single time entries (without end time - default to 1 hour)
        for start_time_str, title in single_matches:
            try:
                # Parse start time
                start_hour, start_min = map(int, start_time_str.split(':'))

                # Create datetime objects with target date
                start_dt = datetime.combine(
                    target_date,
                    time(start_hour, start_min),
                    tzinfo=tz
                )

                # Default to 1 hour duration
                from datetime import timedelta
                end_dt = start_dt + timedelta(hours=1)

                # Clean up title
                title = title.strip().rstrip(',;.')

                batch_actions.append({
                    "intent": "create",
                    "title": title,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "duration_minutes": 60
                })

            except Exception as e:
                logger.warning("schedule_single_time_parse_error",
                             line=f"{start_time_str} {title}",
                             error=str(e))
                continue

        # If we successfully parsed events, return batch confirmation DTO
        if batch_actions:
            from app.utils.datetime_parser import format_datetime_human

            # Build summary
            first_action = batch_actions[0]
            last_action = batch_actions[-1]

            first_dt = datetime.fromisoformat(first_action['start_time'])
            last_dt = datetime.fromisoformat(last_action['start_time'])

            summary = f"📅 Создать {len(batch_actions)} событий\n"
            summary += f"📍 {format_datetime_human(first_dt, locale='ru')}\n"
            summary += f"🔄 С {first_dt.strftime('%H:%M')} до {last_dt.strftime('%H:%M')}"

            logger.info("schedule_format_parsed_successfully",
                       events_count=len(batch_actions),
                       date=target_date.isoformat())

            return EventDTO(
                intent=IntentType.BATCH_CONFIRM,
                confidence=0.9,
                batch_actions=batch_actions,
                batch_summary=summary,
                raw_text=user_text
            )

        return None

    async def extract_event(
        self,
        user_text: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        timezone: str = 'Europe/Moscow',
        existing_events: Optional[list] = None,
        language: str = 'ru',
        recent_context: Optional[list] = None
    ) -> EventDTO:
        """
        Extract structured event information from natural language text.

        ARCH-001: Refactored from ~500 lines to ~80 lines using helper methods.

        Args:
            user_text: User's natural language command
            user_id: User identifier for context
            conversation_history: Previous messages for context
            timezone: User's timezone
            existing_events: List of existing calendar events from DB (for update/delete)
            language: User's preferred language (ru, en, es, ar)
            recent_context: Recently created/modified events for follow-up commands

        Returns:
            EventDTO with extracted information

        Examples:
            >>> await extract_event("Запланируй встречу с Иваном на пятницу 15:00")
            EventDTO(intent="create", title="Встреча с Иваном", ...)
        """
        logger.info("llm_extract_start_yandex", user_text=user_text, user_id=user_id, language=language)

        # 1. BIZ-002: Enforce input token limit to prevent excessive API costs
        if len(user_text) > self.MAX_INPUT_CHARS:
            logger.warning(
                "llm_input_truncated",
                original_length=len(user_text),
                truncated_to=self.MAX_INPUT_CHARS,
                user_id=user_id
            )
            user_text = user_text[:self.MAX_INPUT_CHARS]

        # 2. Quick path: Try to detect schedule format pattern before calling LLM
        schedule_dto = self._detect_schedule_format(user_text, timezone, conversation_history)
        if schedule_dto:
            logger.info("schedule_format_detected_preprocessing",
                       events_count=len(schedule_dto.batch_actions))
            return schedule_dto

        # 2.5 Phase 4: Local regex parser for common queries (saves LLM cost)
        local_dto = self._try_local_parser(user_text, timezone)
        if local_dto:
            return local_dto

        try:
            # 3. Prepare datetime context using helper
            dt_context = self._prepare_datetime_context(timezone)

            # 4. Prepare events context using helper
            events_context = self._prepare_events_context(
                existing_events, recent_context, conversation_history
            )

            # 5. Build function schema (only need event_id_enum for logging)
            _, event_id_enum = self._build_function_schema(existing_events)

            # 6. Build full prompt using helper
            full_prompt = self._build_full_prompt(dt_context, events_context, user_text)

            # 7. Parse datetime from user text for fallback values
            start_time, end_time, duration = parse_datetime_range(user_text)

            # 8. Call LLM API using helper
            response_data, result_text = await self._call_llm_api(
                full_prompt, user_id, user_text, event_id_enum
            )

            # 9. Check for content moderation refusal
            if self._is_llm_refusal(result_text):
                logger.warning("yandex_gpt_content_refusal",
                              user_id=user_id,
                              user_text=user_text[:100],
                              refusal_text=result_text[:200])

                if ANALYTICS_ENABLED and analytics_service and user_id:
                    analytics_service.log_action(
                        user_id=user_id,
                        action_type=ActionType.LLM_PARSE_ERROR,
                        details=f"Content refusal: {user_text[:100]}",
                        success=False,
                        error_message=f"Yandex GPT refused: {result_text[:100]}"
                    )

                # Fallback: create TODO from user text
                return self._create_todo_fallback(user_text, user_id)

            # 10. Parse JSON from LLM response
            event_dto = self._parse_yandex_response(
                result_text,
                user_text,
                start_time,
                end_time,
                duration,
                language,
                existing_events,
                user_id
            )

            # 11. Log analytics using helper
            self._log_success_analytics(response_data, event_dto, user_id)

            return event_dto

        except Exception as e:
            logger.error("llm_extract_error_yandex", error=str(e), exc_info=True)

            if ANALYTICS_ENABLED and analytics_service and user_id:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.LLM_ERROR,
                    details=f"LLM extract failed: {user_text[:100]}",
                    success=False,
                    error_message=str(e)[:200]
                )

            # Return clarify intent on error with translated message
            lang_enum = Language(language) if language in ['ru', 'en', 'es', 'ar'] else Language.ENGLISH
            clarify_msg = get_translation("clarify_more_details", lang_enum)

            return EventDTO(
                intent=IntentType.CLARIFY,
                confidence=0.0,
                clarify_question=clarify_msg,
                raw_text=user_text
            )

    def _parse_yandex_response(
        self,
        result_text: str,
        user_text: str,
        parsed_start: Optional[datetime],
        parsed_end: Optional[datetime],
        parsed_duration: Optional[int],
        language: str = 'ru',
        existing_events: Optional[list] = None,
        user_id: Optional[str] = None
    ) -> EventDTO:
        """Parse Yandex GPT API response into EventDTO."""

        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            text = result_text.strip()
            if text.startswith('```'):
                # Remove opening ```json or ``` and closing ```
                lines = text.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  # Remove first line with ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]  # Remove last line with ```
                text = '\n'.join(lines)

            # Find JSON in text (sometimes model adds text before/after)
            # Check if it's an array or object
            array_start = text.find('[')
            obj_start = text.find('{')

            # Determine if response is array or object
            is_array = array_start != -1 and (obj_start == -1 or array_start < obj_start)

            if is_array:
                # Handle array of actions - BATCH OPERATION
                start_idx = array_start
                end_idx = text.find(']', start_idx) + 1

                if start_idx == -1 or end_idx == 0:
                    raise ValueError("No JSON array found in response")

                json_str = text[start_idx:end_idx]
                data_array = json.loads(json_str)

                logger.info("yandex_gpt_returned_array",
                             array_length=len(data_array),
                             message="Model returned multiple actions - will request confirmation")

                # Validate array is not empty
                if not data_array or len(data_array) == 0:
                    raise ValueError("Empty array in response")

                # Return BATCH_CONFIRM intent with all actions
                return self._build_batch_confirmation(data_array, user_text, language, existing_events)
            else:
                # Handle single object
                start_idx = obj_start
                end_idx = text.rfind('}') + 1

                if start_idx == -1 or end_idx == 0:
                    raise ValueError("No JSON found in response")

                json_str = text[start_idx:end_idx]
                data = json.loads(json_str)
                logger.info("yandex_gpt_parsed_json", data=data)

            # Handle function call format: {"name": "...", "parameters": {...}}
            if "parameters" in data:
                input_data = data["parameters"]
                logger.info("yandex_gpt_extracted_parameters", input_data=input_data)
            else:
                input_data = data
                logger.info("yandex_gpt_using_data_directly", input_data=input_data)

            # DEFENSIVE: Handle if LLM returned full schema format with "properties" wrapper
            # This happens when LLM mirrors the function schema structure literally
            if "properties" in input_data and "type" in input_data:
                logger.warning("yandex_gpt_schema_format_detected",
                              message="LLM returned schema format - unwrapping properties")
                input_data = input_data["properties"]

            # Check if this is a batch operation with batch_actions array
            if "batch_actions" in input_data and isinstance(input_data["batch_actions"], list):
                batch_actions = input_data["batch_actions"]
                if len(batch_actions) > 0:
                    logger.info("yandex_gpt_batch_detected",
                               actions_count=len(batch_actions),
                               message="Batch actions detected, building confirmation")
                    return self._build_batch_confirmation(batch_actions, user_text, language, existing_events)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("yandex_gpt_json_parse_error", error=str(e), text=result_text)

            # Log parse error to analytics
            if ANALYTICS_ENABLED and analytics_service and user_id:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.LLM_PARSE_ERROR,
                    details=f"JSON parse failed: {user_text[:100]}",
                    success=False,
                    error_message=f"Parse error: {str(e)[:100]}. Response: {result_text[:100]}"
                )

            # Use translated clarify message
            lang_enum = Language(language) if language in ['ru', 'en', 'es', 'ar'] else Language.ENGLISH
            clarify_msg = get_translation("clarify_rephrase", lang_enum)

            return EventDTO(
                intent=IntentType.CLARIFY,
                confidence=0.2,
                clarify_question=clarify_msg,
                raw_text=user_text
            )

        # Build EventDTO
        raw_intent = input_data.get("intent", "clarify")
        logger.info("yandex_gpt_building_dto", raw_intent=raw_intent, input_data_keys=list(input_data.keys()))

        # FALLBACK: If LLM returns clarify asking for date/time, but text looks like a simple task
        # Convert to todo intent instead
        if raw_intent == "clarify":
            clarify_q = input_data.get("clarify_question", "").lower()
            text_lower = user_text.lower()
            
            # Check if clarify is asking for date/time
            date_time_keywords = ["дату", "время", "когда", "date", "time", "when"]
            asking_for_datetime = any(kw in clarify_q for kw in date_time_keywords)
            
            # Check if text has action verbs typical for tasks (without specific time)
            task_verbs = ["позвонить", "написать", "купить", "сделать", "проверить", 
                         "обновить", "согласовать", "подготовить", "отправить", "найти",
                         "изучить", "узнать", "договориться", "поменять", "заменить",
                         "задача", "напомнить", "записать"]
            has_task_verb = any(verb in text_lower for verb in task_verbs)
            
            # Check if there is NO specific time in user text
            import re
            time_pattern = r"\d{1,2}[:\.]?\d{0,2}\s*(утра|вечера|ночи|дня|am|pm)"
            has_time = bool(re.search(time_pattern, text_lower)) or bool(re.search(r"\d{1,2}:\d{2}", text_lower))
            
            if asking_for_datetime and has_task_verb and not has_time:
                logger.info("todo_fallback_activated", user_text=user_text, clarify_question=clarify_q)
                raw_intent = "todo"
                intent = IntentType.TODO
                input_data["title"] = user_text.strip()
                input_data["intent"] = "todo"


        intent = IntentType(raw_intent)
        # Parse datetimes
        start_time = None
        end_time = None

        if "start_time" in input_data:
            try:
                start_time = datetime.fromisoformat(input_data["start_time"])
            except (ValueError, TypeError):
                # Try parsing as time-only (HH:MM) for recurring events
                import re
                import pytz
                time_match = re.match(r'^(\d{1,2}):(\d{2})$', str(input_data["start_time"]))
                if time_match:
                    # Parse time and combine with today's date
                    from app.config import settings
                    tz = pytz.timezone(settings.default_timezone)
                    now = datetime.now(tz)
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    start_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    logger.info("parsed_time_only_start",
                               input=input_data["start_time"],
                               parsed_datetime=start_time.isoformat(),
                               timezone=str(start_time.tzinfo))
                else:
                    start_time = parsed_start

        if "end_time" in input_data:
            try:
                end_time = datetime.fromisoformat(input_data["end_time"])
            except (ValueError, TypeError):
                # Try parsing as time-only (HH:MM)
                import re
                time_match = re.match(r'^(\d{1,2}):(\d{2})$', str(input_data["end_time"]))
                if time_match and start_time:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    end_time = start_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    end_time = parsed_end

        # Use parsed values as fallback
        if not start_time:
            start_time = parsed_start
        if not end_time:
            end_time = parsed_end

        # FALLBACK: Set default start_time for CREATE intent if not specified
        # This prevents NoneType + timedelta crash in calendar_radicale.py
        if intent == IntentType.CREATE and not start_time:
            import pytz
            tz = pytz.timezone(settings.default_timezone)
            now = datetime.now(tz)

            # Check for relative date markers in user text
            text_lower = user_text.lower()
            if any(w in text_lower for w in ["завтра", "tomorrow", "mañana", "غداً"]):
                # Tomorrow at 09:00
                start_time = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            elif any(w in text_lower for w in ["послезавтра", "day after tomorrow", "pasado mañana"]):
                # Day after tomorrow at 09:00
                start_time = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                # Today: next round hour if before 18:00, otherwise tomorrow 09:00
                if now.hour < 18:
                    start_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
                else:
                    start_time = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

            logger.info("default_start_time_set",
                        start_time=start_time.isoformat(),
                        reason="no_time_specified",
                        user_text=user_text[:50])

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
            query_date_start=self._parse_optional_datetime(
                input_data.get("query_date_start") or input_data.get("delete_criteria_date")
            ),
            query_date_end=self._parse_optional_datetime(
                input_data.get("query_date_end") or input_data.get("delete_criteria_date")
            ),
            raw_text=user_text,
            # Recurring events fields
            recurrence_type=input_data.get("recurrence_type"),
            recurrence_end_date=self._parse_optional_datetime(input_data.get("recurrence_end_date")),
            recurrence_days=input_data.get("recurrence_days"),
            # Delete by criteria fields
            delete_criteria_title=input_data.get("delete_criteria_title"),
            delete_criteria_title_contains=input_data.get("delete_criteria_title_contains"),
            # Real estate domain fields
            event_type=input_data.get("event_type", "generic"),
            client_name=input_data.get("client_name"),
            client_phone=input_data.get("client_phone"),
            apartment_details=input_data.get("apartment_details"),
        )

        return event_dto

    def _build_batch_confirmation(self, data_array: List[dict], user_text: str, language: str, existing_events: List[dict] = None) -> EventDTO:
        """Build batch confirmation EventDTO from array of actions."""
        from app.services.translations import get_translation, Language
        from app.utils.datetime_parser import format_datetime_human

        lang_enum = Language(language) if language in ['ru', 'en', 'es', 'ar'] else Language.RUSSIAN

        # Build compact summary (not full list)
        action_count = len(data_array)

        # Get first and last event info
        first_action = data_array[0].get("parameters", data_array[0])
        last_action = data_array[-1].get("parameters", data_array[-1])

        intent = first_action.get("intent", "create")

        # For DELETE operations, get info from existing_events by event_id
        if intent == "delete" and existing_events:
            # Find events by event_id
            first_event_id = first_action.get("event_id", "")
            last_event_id = last_action.get("event_id", "")

            # Search in existing_events
            first_event_data = None
            last_event_data = None
            for ev in existing_events:
                if ev.get("uid") == first_event_id:
                    first_event_data = ev
                if ev.get("uid") == last_event_id:
                    last_event_data = ev

            # Extract info from found events
            title = first_event_data.get("title", "") if first_event_data else ""
            first_date_str = first_event_data.get("start") if first_event_data else None
            last_date_str = last_event_data.get("start") if last_event_data else None
        else:
            # For CREATE/UPDATE - get from action parameters
            title = first_action.get("title", "")
            first_date_str = first_action.get("start_time", "")
            last_date_str = last_action.get("start_time", "")

        # Format dates
        first_date = ""
        last_date = ""
        try:
            if first_date_str:
                dt = self._parse_optional_datetime(first_date_str)
                if dt:
                    first_date = format_datetime_human(dt, locale=language)
        except (ValueError, TypeError, AttributeError):
            pass

        try:
            if last_date_str:
                dt = self._parse_optional_datetime(last_date_str)
                if dt:
                    last_date = format_datetime_human(dt, locale=language)
        except (ValueError, TypeError, AttributeError):
            pass

        # Build compact summary based on action type
        # Get last event title too
        last_title = last_action.get("title", "")

        if intent == "delete":
            if language == 'ru':
                if action_count == 1:
                    summary = f"🗑 Удалить событие: '{title}'\n📍 {first_date}"
                else:
                    summary = f"🗑 Удалить {action_count} событий\n📍 С {first_date} по {last_date}"
            elif language == 'en':
                if action_count == 1:
                    summary = f"🗑 Delete event: '{title}'\n📍 {first_date}"
                else:
                    summary = f"🗑 Delete {action_count} events\n📍 From {first_date} to {last_date}"
            elif language == 'es':
                if action_count == 1:
                    summary = f"🗑 Eliminar evento: '{title}'\n📍 {first_date}"
                else:
                    summary = f"🗑 Eliminar {action_count} eventos\n📍 Desde {first_date} hasta {last_date}"
            else:  # ar
                if action_count == 1:
                    summary = f"🗑 حذف حدث: '{title}'\n📍 {first_date}"
                else:
                    summary = f"🗑 حذف {action_count} أحداث\n📍 من {first_date} إلى {last_date}"
        else:  # create
            if language == 'ru':
                if action_count == 1:
                    summary = f"📅 Создать событие: '{title}'\n📍 {first_date}"
                elif action_count == 2:
                    # Show both event names for 2 events
                    summary = f"📅 Создать 2 события:\n• {first_date} - {title}\n• {last_date} - {last_title}"
                else:
                    # For 3+ events: check if all have same title (recurring)
                    all_titles = [act.get("title", "") for act in data_array]
                    all_same = len(set(all_titles)) == 1

                    if all_same:
                        # Recurring events - show range
                        summary = f"📅 Создать {action_count} событий: '{title}'\n📍 С {first_date} по {last_date}"
                    else:
                        # Different events - show list (up to 10 events)
                        summary = f"📅 Создать {action_count} событий:\n\n"
                        for i, act in enumerate(data_array[:10]):  # Show max 10
                            act_params = act.get("parameters", act)
                            act_title = act_params.get("title", "")
                            act_start = act_params.get("start_time", "")
                            act_end = act_params.get("end_time", "")

                            try:
                                start_dt = self._parse_optional_datetime(act_start)
                                end_dt = self._parse_optional_datetime(act_end)
                                if start_dt and end_dt:
                                    date_str = start_dt.strftime("%d.%m")
                                    time_str = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                                    summary += f"• {act_title}\n  📅 {date_str} | 🕐 {time_str}\n"
                            except (ValueError, TypeError, AttributeError):
                                summary += f"• {act_title}\n"

                        if action_count > 10:
                            summary += f"\n... и ещё {action_count - 10}"
            elif language == 'en':
                if action_count == 1:
                    summary = f"📅 Create event: '{title}'\n📍 {first_date}"
                elif action_count == 2:
                    summary = f"📅 Create 2 events:\n• {first_date} - {title}\n• {last_date} - {last_title}"
                else:
                    # For 3+ events: check if all have same title (recurring)
                    all_titles = [act.get("title", "") for act in data_array]
                    all_same = len(set(all_titles)) == 1

                    if all_same:
                        # Recurring events - show range
                        summary = f"📅 Create {action_count} events: '{title}'\n📍 From {first_date} to {last_date}"
                    else:
                        # Different events - show list (up to 10 events)
                        summary = f"📅 Create {action_count} events:\n\n"
                        for i, act in enumerate(data_array[:10]):  # Show max 10
                            act_params = act.get("parameters", act)
                            act_title = act_params.get("title", "")
                            act_start = act_params.get("start_time", "")
                            act_end = act_params.get("end_time", "")

                            try:
                                start_dt = self._parse_optional_datetime(act_start)
                                end_dt = self._parse_optional_datetime(act_end)
                                if start_dt and end_dt:
                                    date_str = start_dt.strftime("%d.%m")
                                    time_str = f"{start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
                                    summary += f"• {act_title}\n  📅 {date_str} | 🕐 {time_str}\n"
                            except (ValueError, TypeError, AttributeError):
                                summary += f"• {act_title}\n"

                        if action_count > 10:
                            summary += f"\n... and {action_count - 10} more"
            elif language == 'es':
                if action_count == 1:
                    summary = f"📅 Crear evento: '{title}'\n📍 {first_date}"
                elif action_count == 2:
                    summary = f"📅 Crear 2 eventos:\n• {first_date} - {title}\n• {last_date} - {last_title}"
                else:
                    summary = f"📅 Crear {action_count} eventos\n📍 Desde {first_date} hasta {last_date}"
            else:  # ar
                if action_count == 1:
                    summary = f"📅 إنشاء حدث: '{title}'\n📍 {first_date}"
                elif action_count == 2:
                    summary = f"📅 إنشاء حدثين:\n• {first_date} - {title}\n• {last_date} - {last_title}"
                else:
                    summary = f"📅 إنشاء {action_count} أحداث\n📍 من {first_date} إلى {last_date}"

        logger.info("batch_confirmation_built",
                   actions_count=len(data_array),
                   summary=summary)

        return EventDTO(
            intent=IntentType.BATCH_CONFIRM,
            confidence=0.85,
            batch_actions=data_array,
            batch_summary=summary,
            raw_text=user_text
        )

    def _parse_optional_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse optional datetime string."""
        if not dt_str:
            return None
        try:
            dt = datetime.fromisoformat(dt_str)
            # If datetime is naive (no timezone), assume Moscow timezone
            if dt.tzinfo is None:
                import pytz
                tz = pytz.timezone(settings.default_timezone)
                dt = tz.localize(dt)
            return dt
        except (ValueError, TypeError):
            return None


# Global instance
llm_agent_yandex = LLMAgentYandex()
