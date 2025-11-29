"""LLM Agent service using Yandex GPT (YandexGPT Foundation Models)."""

from typing import Optional, List
import json
from datetime import datetime, timedelta
import requests
import structlog

from app.config import settings
from app.schemas.events import EventDTO, IntentType
from app.utils.datetime_parser import parse_datetime_range
from app.services.translations import get_translation, Language

logger = structlog.get_logger()


class LLMAgentYandex:
    """
    LLM Agent for understanding natural language calendar commands.

    Uses Yandex GPT (YandexGPT) with function calling to extract structured
    event information from user queries.

    This is a drop-in replacement for Anthropic Claude agent,
    preserving all logic for update/delete operations with existing_events.
    Works from Russia without restrictions.
    """

    def __init__(self):
        """Initialize LLM agent with Yandex GPT client."""
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id
        self.model = "yandexgpt"  # or "yandexgpt-lite" for faster/cheaper
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        # System prompt will be generated per request with current date
        self.base_system_prompt = """You are an intelligent calendar assistant.
Your task is to understand user commands in natural language (Russian, English, Spanish, or Arabic)
and convert them into structured calendar actions.

Possible actions (intent):
- create: create a single new event
- create_recurring: create recurring events (daily, weekly, monthly patterns)
- update: modify an existing event
- delete: delete an event
- query: query information about events
- find_free_slots: find free time
- batch_confirm: confirm multiple specific events (for deletions or custom lists)
- delete_by_criteria: delete events matching criteria (title contains, date range)
- delete_duplicates: delete duplicate events (same title and time). Use when user says "удали дубликаты", "удали повторяющиеся", "удали одинаковые события"
- clarify: ask for clarification if information is insufficient

Rules:
1. Always return time in ISO 8601 format with the user's timezone
2. If information is missing (date, time, title) - use intent=clarify
3. IMPORTANT: For relative dates (tomorrow, next Friday) calculate the exact date relative to CURRENT DATE
4. IMPORTANT: If date is NOT explicitly stated and NOT relative - use intent=clarify
5. IMPORTANT: Use context from previous messages - if user is answering a clarification question, supplement with history
6. Default duration is 60 minutes if not specified
7. Extract attendees from text (names, emails)
7a. CRITICAL: For "this week" or "эту неделю" queries, set query_date_start=today and query_date_end=today+7 days to include all events from today through next 7 days

RECURRING EVENTS (Creating Multiple Events with Patterns):
8. For requests like "every day", "daily", "each day", use intent="create_recurring"
9. When intent="create_recurring", include these fields:
   - recurrence_type: "daily" | "weekly" | "monthly"
   - recurrence_end_date: ISO 8601 date when recurrence should stop
   - recurrence_days: (for weekly) list of weekdays like ["mon", "wed", "fri"]
   - start_time, end_time, title, duration_minutes: as usual
10. CRITICAL RULES for recurring events duration (TODAY is {today_str}):
   - "every day" or "каждый день" WITHOUT specific period → recurrence_end_date = {end_of_year_date}
   - "for 3 days" or "на 3 дня" → recurrence_end_date = today + 3 days
   - "for 2 years" or "на 2 года" → recurrence_end_date = today + 730 days
   - "until Friday" or "до пятницы" → recurrence_end_date = next Friday
   - "always" or "всегда" → recurrence_end_date = {end_of_year_date}
   - "for a week" or "на неделю" → recurrence_end_date = today + 7 days
11. EXAMPLES with current date {today_str}:
   - User: "Every day at 9am" → create_recurring with recurrence_type="daily", recurrence_end_date={end_of_year_date}
   - User: "каждый день в 9 утра" → create_recurring with recurrence_type="daily", recurrence_end_date={end_of_year_date}
   - User: "Daily for 5 days" → create_recurring with recurrence_type="daily", recurrence_end_date = today + 5 days
   - User: "Every Monday and Wednesday at 10am" → create_recurring with recurrence_type="weekly", recurrence_days=["mon", "wed"]
12. System will generate ALL events automatically from recurrence pattern
13. User will see summary and confirm before creation

DELETION OPERATIONS:
16. For "delete all X" or "удали все X" requests:
    - Use intent="delete_by_criteria" with delete_criteria_title_contains field
    - System will find ALL matching events and show confirmation
    - Example: "удали все утренние ритуалы" → {{"intent": "delete_by_criteria", "delete_criteria_title_contains": "утренн"}}
    - Example: "delete all meetings" → {{"intent": "delete_by_criteria", "delete_criteria_title_contains": "meeting"}}
17. For "delete X" (single specific event) - use intent="delete" with event_id of matching event
18. NEVER return large batch_actions arrays for deletion (token limit!) - always use delete_by_criteria for "all" requests

BATCH SCHEDULE CREATION (Multiple Events from Schedule Format):
21. CRITICAL: If user provides schedule with MULTIPLE time ranges (3+ lines), create batch_actions array
22. Schedule format detection patterns:
    - Multiple lines with time ranges (HH:MM-HH:MM format)
    - Each line has event title/description after time
    - All for same date context
    - Example input:
      "тайминг на 23 октября:
       12:45-13:00 Приезд, заселение
       13:00-13:30 Кофе-брейк
       13:30-15:00 Дискуссия по ИИ"
23. For schedule format:
    - Return intent="batch_confirm"
    - Create batch_actions array with one action per line
    - Parse time range from each line (start-end)
    - Extract title from text after time
    - Use date from context (today/tomorrow/specified date)
24. IMPORTANT: Detect keywords like "тайминг", "расписание", "schedule", "agenda" combined with multiple time ranges
25. DATE AMBIGUITY for schedule format:
    - If date like "23 октября" is in the PAST (already happened this year), ASK for clarification
    - Example clarify_question: "Уточните, пожалуйста: расписание на 23 октября 2025 года или 2026 года?"
    - Do NOT automatically assume next year - ALWAYS ask user to confirm
    - For dates with explicit year (23.10.2025) - no clarification needed

OTHER OPERATIONS:
26. For single updates - return ONE action without batch_actions
27. For complex commands ("delete X and create Y") - use clarify to ask for one at a time

Time recognition examples:
- "meeting at 10" or "at 10" -> 10:00 (morning)
- "meeting at 14" or "at 14" -> 14:00 (afternoon)
- "meeting at 6 PM" -> 18:00 (evening)
- "reschedule to 3" -> new time 15:00 (NOT a date!)
- "reschedule to the 15th" -> new date 15th of month

Example commands:
- "Team meeting tomorrow at 10" -> create, title="Team meeting", start=tomorrow 10:00
- "What do I have tomorrow?" -> query, query_date_start=tomorrow
- "What do I have today?" -> query, query_date_start=today
- "What do I have this week?" -> query, query_date_start=today, query_date_end=end_of_week (7 days from today)
- "Какие планы на эту неделю?" -> query, query_date_start=today, query_date_end=end_of_week (7 days from today)
- "Free time on Friday" -> find_free_slots, query_date_start=Friday
- "Reschedule meeting with Kate to 2 PM" -> update, find "meeting with Kate", new start_time=14:00 SAME DAY
- "Reschedule to Wednesday" -> clarify (need to know which meeting)
- "Meeting at 9am every day until Friday" -> batch_confirm with batch_actions array (5 events)
- "Cold calling at 8am until end of week" -> batch_confirm with batch_actions array

IMPORTANT: Your response must be ONLY in JSON format with fields from set_calendar_action function schema.
Do not add any text before or after JSON.
For batch_confirm intent, include "batch_actions" array field with all events to create."""

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
        language: str = 'ru'
    ) -> EventDTO:
        """
        Extract structured event information from natural language text.

        Args:
            user_text: User's natural language command
            user_id: User identifier for context
            conversation_history: Previous messages for context
            timezone: User's timezone
            existing_events: List of existing calendar events from DB (for update/delete)
            language: User's preferred language (ru, en, es, ar)

        Returns:
            EventDTO with extracted information

        Examples:
            >>> await extract_event("Запланируй встречу с Иваном на пятницу 15:00")
            EventDTO(intent="create", title="Встреча с Иваном", ...)
        """
        logger.info("llm_extract_start_yandex", user_text=user_text, user_id=user_id, language=language)

        # FIRST: Try to detect schedule format pattern before calling LLM
        schedule_dto = self._detect_schedule_format(user_text, timezone, conversation_history)
        if schedule_dto:
            logger.info("schedule_format_detected_preprocessing",
                       events_count=len(schedule_dto.batch_actions))
            return schedule_dto

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

            # Calculate next weekdays for prompt examples
            # Map weekday names to numbers (0=Monday, 6=Sunday)
            weekday_to_num = {
                'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                'Friday': 4, 'Saturday': 5, 'Sunday': 6
            }
            current_weekday_num = now.weekday()  # 0=Monday, 6=Sunday

            # Calculate next occurrence of each weekday
            next_weekdays = {}
            next_weekdays_ru = {}
            for weekday_name, weekday_num in weekday_to_num.items():
                # Calculate days until next occurrence
                if weekday_num > current_weekday_num:
                    # Later this week
                    days_ahead = weekday_num - current_weekday_num
                else:
                    # Next week
                    days_ahead = 7 - (current_weekday_num - weekday_num)

                next_date = now + timedelta(days=days_ahead)
                next_weekdays[weekday_name] = next_date
                next_weekdays_ru[weekdays_ru[weekday_name]] = next_date

            # Get timezone offset
            tz_offset = now.strftime('%z')
            tz_offset_formatted = f"{tz_offset[:3]}:{tz_offset[3:]}"  # Format: +03:00

            # Calculate days until end of year for batch operations
            end_of_year = datetime(now.year, 12, 31, tzinfo=tz)
            days_until_eoy = (end_of_year - now).days + 1  # +1 to include today
            today_str = current_date_str
            end_of_year_date = end_of_year.strftime('%Y-%m-%d')  # Format: 2025-12-31 or 2026-12-31

            # Prepare events list to prepend to user message
            # Limit to first 10 events to avoid content moderation triggers
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

User request:
"""

            # Language names
            language_names = {
                'ru': 'русском',
                'en': 'English',
                'es': 'español',
                'ar': 'العربية'
            }
            lang_name = language_names.get(language, 'русском')

            # Multilingual prompts for system instructions
            lang_instructions = {
                'ru': f"""КРИТИЧЕСКИ ВАЖНО: ЯЗЫК ОБЩЕНИЯ С ПОЛЬЗОВАТЕЛЕМ - РУССКИЙ!
ВСЕ твои ответы (clarify_question, заголовки событий, описания) должны быть на русском языке.
Пользователь общается на русском языке.

ВАЖНО: ТЕКУЩАЯ ДАТА И ВРЕМЯ: {current_datetime_str} ({timezone}, UTC{tz_offset_formatted}), {current_weekday_ru}
Используй эту дату для расчета относительных дат (завтра, послезавтра, через неделю и т.д.)

КРИТИЧЕСКИ ВАЖНО: Примеры относительных дат от ТЕКУЩЕЙ ДАТЫ ({current_date_str}):
- "завтра" = {(now + timedelta(days=1)).strftime('%d.%m.%Y')} ({(now + timedelta(days=1)).strftime('%Y-%m-%d')})
- "послезавтра" = {(now + timedelta(days=2)).strftime('%d.%m.%Y')} ({(now + timedelta(days=2)).strftime('%Y-%m-%d')})
- "через неделю" = {(now + timedelta(days=7)).strftime('%d.%m.%Y')} ({(now + timedelta(days=7)).strftime('%Y-%m-%d')})

КРИТИЧЕСКИ ВАЖНО: Ближайшие дни недели от ТЕКУЩЕЙ ДАТЫ ({current_date_str}, {current_weekday_ru}):
- "в понедельник" или "понедельник" = {next_weekdays_ru['понедельник'].strftime('%d.%m.%Y')} ({next_weekdays_ru['понедельник'].strftime('%Y-%m-%d')})
- "во вторник" или "вторник" = {next_weekdays_ru['вторник'].strftime('%d.%m.%Y')} ({next_weekdays_ru['вторник'].strftime('%Y-%m-%d')})
- "в среду" или "среда" = {next_weekdays_ru['среда'].strftime('%d.%m.%Y')} ({next_weekdays_ru['среда'].strftime('%Y-%m-%d')})
- "в четверг" или "четверг" = {next_weekdays_ru['четверг'].strftime('%d.%m.%Y')} ({next_weekdays_ru['четверг'].strftime('%Y-%m-%d')})
- "в пятницу" или "пятница" = {next_weekdays_ru['пятница'].strftime('%d.%m.%Y')} ({next_weekdays_ru['пятница'].strftime('%Y-%m-%d')})
- "в субботу" или "суббота" = {next_weekdays_ru['суббота'].strftime('%d.%m.%Y')} ({next_weekdays_ru['суббота'].strftime('%Y-%m-%d')})
- "в воскресенье" или "воскресенье" = {next_weekdays_ru['воскресенье'].strftime('%d.%m.%Y')} ({next_weekdays_ru['воскресенье'].strftime('%Y-%m-%d')})

ВНИМАНИЕ: Используй ТОЧНО эти даты для относительных запросов! Не пересчитывай их сам!""",
                'en': f"""CRITICAL: USER LANGUAGE IS ENGLISH!
ALL your responses (clarify_question, event titles, descriptions) MUST be in English.
The user communicates in English.

IMPORTANT: CURRENT DATE AND TIME: {current_datetime_str} ({timezone}, UTC{tz_offset_formatted}), {current_weekday}
Use this date to calculate relative dates (tomorrow, day after tomorrow, next week, etc.)

CRITICAL: Examples of relative dates from CURRENT DATE ({current_date_str}):
- "tomorrow" = {(now + timedelta(days=1)).strftime('%d.%m.%Y')} ({(now + timedelta(days=1)).strftime('%Y-%m-%d')})
- "day after tomorrow" = {(now + timedelta(days=2)).strftime('%d.%m.%Y')} ({(now + timedelta(days=2)).strftime('%Y-%m-%d')})
- "next week" = {(now + timedelta(days=7)).strftime('%d.%m.%Y')} ({(now + timedelta(days=7)).strftime('%Y-%m-%d')})

CRITICAL: Next weekdays from CURRENT DATE ({current_date_str}, {current_weekday}):
- "on Monday" or "Monday" = {next_weekdays['Monday'].strftime('%d.%m.%Y')} ({next_weekdays['Monday'].strftime('%Y-%m-%d')})
- "on Tuesday" or "Tuesday" = {next_weekdays['Tuesday'].strftime('%d.%m.%Y')} ({next_weekdays['Tuesday'].strftime('%Y-%m-%d')})
- "on Wednesday" or "Wednesday" = {next_weekdays['Wednesday'].strftime('%d.%m.%Y')} ({next_weekdays['Wednesday'].strftime('%Y-%m-%d')})
- "on Thursday" or "Thursday" = {next_weekdays['Thursday'].strftime('%d.%m.%Y')} ({next_weekdays['Thursday'].strftime('%Y-%m-%d')})
- "on Friday" or "Friday" = {next_weekdays['Friday'].strftime('%d.%m.%Y')} ({next_weekdays['Friday'].strftime('%Y-%m-%d')})
- "on Saturday" or "Saturday" = {next_weekdays['Saturday'].strftime('%d.%m.%Y')} ({next_weekdays['Saturday'].strftime('%Y-%m-%d')})
- "on Sunday" or "Sunday" = {next_weekdays['Sunday'].strftime('%d.%m.%Y')} ({next_weekdays['Sunday'].strftime('%Y-%m-%d')})

IMPORTANT: Use EXACTLY these dates for relative queries! Do not recalculate them yourself!""",
                'es': f"""CRÍTICO: EL IDIOMA DEL USUARIO ES ESPAÑOL!
TODAS tus respuestas (clarify_question, títulos de eventos, descripciones) DEBEN estar en español.
El usuario se comunica en español.

IMPORTANTE: FECHA Y HORA ACTUAL: {current_datetime_str} ({timezone}, UTC{tz_offset_formatted}), {current_weekday}
Usa esta fecha para calcular fechas relativas (mañana, pasado mañana, la próxima semana, etc.)

Ejemplos de fechas relativas desde la FECHA ACTUAL ({current_date_str}):
- "mañana" = {(now + timedelta(days=1)).strftime('%d.%m.%Y')}
- "pasado mañana" = {(now + timedelta(days=2)).strftime('%d.%m.%Y')}
- "la próxima semana" = {(now + timedelta(days=7)).strftime('%d.%m.%Y')}""",
                'ar': f"""حاسم: لغة المستخدم هي العربية!
جميع إجاباتك (clarify_question، عناوين الأحداث، الأوصاف) يجب أن تكون بالعربية.
المستخدم يتواصل بالعربية.

مهم: التاريخ والوقت الحالي: {current_datetime_str} ({timezone}, UTC{tz_offset_formatted}), {current_weekday}
استخدم هذا التاريخ لحساب التواريخ النسبية (غداً، بعد غد، الأسبوع القادم، إلخ)

أمثلة على التواريخ النسبية من التاريخ الحالي ({current_date_str}):
- "غداً" = {(now + timedelta(days=1)).strftime('%d.%m.%Y')}
- "بعد غد" = {(now + timedelta(days=2)).strftime('%d.%m.%Y')}
- "الأسبوع القادم" = {(now + timedelta(days=7)).strftime('%d.%m.%Y')}"""
            }

            # Create dynamic system prompt with current date and language
            # Format base prompt with calculated values
            formatted_base_prompt = self.base_system_prompt.format(
                today_str=today_str,
                days_until_eoy=days_until_eoy,
                end_of_year_date=end_of_year_date
            )

            system_prompt = f"""{formatted_base_prompt}

{lang_instructions.get(language, lang_instructions['en'])}
"""

            # First, try to parse datetime with dateparser
            start_time, end_time, duration = parse_datetime_range(user_text)

            # Build dynamic enum for event_id with real IDs from existing events
            # Limit to first 10 events to match events_prefix and avoid large prompts
            event_id_enum = ["none"]  # default value for create/query
            if existing_events and len(existing_events) > 0:
                max_events_in_context = 10
                limited_events = existing_events[:max_events_in_context]
                for event in limited_events:
                    if hasattr(event, 'id') and event.id:
                        event_id_enum.append(str(event.id))

            # Prepare the full user message with events context
            user_message_content = events_prefix + user_text

            # Build function schema
            function_schema = {
                "name": "set_calendar_action",
                "description": "Установить действие с календарем на основе команды пользователя",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "enum": ["create", "create_recurring", "update", "delete", "query", "find_free_slots", "clarify", "batch_confirm", "delete_by_criteria", "delete_duplicates"],
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
                        },
                        "recurrence_type": {
                            "type": "string",
                            "enum": ["daily", "weekly", "monthly"],
                            "description": "Тип повторения для intent=create_recurring"
                        },
                        "recurrence_end_date": {
                            "type": "string",
                            "description": "Дата окончания повторений (ISO 8601) для intent=create_recurring"
                        },
                        "recurrence_days": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
                            "description": "Дни недели для weekly recurrence (например: ['mon', 'wed', 'fri'])"
                        },
                        "batch_actions": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Массив действий для intent=batch_confirm (только для удаления или специфичных списков)"
                        }
                    },
                    "required": ["intent"]
                }
            }

            # Multilingual JSON instruction
            json_instructions = {
                'ru': f"""Верни ТОЛЬКО JSON с полями функции set_calendar_action. Схема функции:
{json.dumps(function_schema, ensure_ascii=False, indent=2)}

JSON ответ:""",
                'en': f"""Return ONLY JSON with fields from set_calendar_action function. Function schema:
{json.dumps(function_schema, ensure_ascii=False, indent=2)}

JSON response:""",
                'es': f"""Devuelve SOLO JSON con campos de la función set_calendar_action. Esquema de la función:
{json.dumps(function_schema, ensure_ascii=False, indent=2)}

Respuesta JSON:""",
                'ar': f"""أرجع JSON فقط بحقول دالة set_calendar_action. مخطط الدالة:
{json.dumps(function_schema, ensure_ascii=False, indent=2)}

استجابة JSON:"""
            }

            # Prepare the prompt for Yandex GPT
            full_prompt = f"""{system_prompt}

{user_message_content}

{json_instructions.get(language, json_instructions['en'])}"""

            # DEBUG: Log what we're sending to Yandex GPT
            logger.debug("yandex_gpt_api_call",
                        event_id_enum=event_id_enum,
                        user_message_preview=user_message_content[:200] if len(user_message_content) > 200 else user_message_content)

            # Call Yandex GPT API
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

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error("yandex_gpt_api_error", status_code=response.status_code, response=response.text)
                raise Exception(f"Yandex GPT API error: {response.status_code} - {response.text}")

            response_data = response.json()

            # Extract text from response
            result_text = response_data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")

            logger.info("yandex_gpt_raw_response", result_text=result_text)

            # Parse JSON from response
            event_dto = self._parse_yandex_response(
                result_text,
                user_text,
                start_time,
                end_time,
                duration,
                language,
                existing_events
            )

            logger.info(
                "llm_extract_success_yandex",
                intent=event_dto.intent,
                confidence=event_dto.confidence
            )

            return event_dto

        except Exception as e:
            logger.error("llm_extract_error_yandex", error=str(e), exc_info=True)

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
        existing_events: Optional[list] = None
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
        intent = IntentType(raw_intent)

        # Parse datetimes
        start_time = None
        end_time = None

        if "start_time" in input_data:
            try:
                start_time = datetime.fromisoformat(input_data["start_time"])
            except (ValueError, TypeError) as e:
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
                    logger.warning("start_time_parse_failed", input=input_data["start_time"], error=str(e))

        if "end_time" in input_data:
            try:
                end_time = datetime.fromisoformat(input_data["end_time"])
            except (ValueError, TypeError) as e:
                # Try parsing as time-only (HH:MM)
                import re
                time_match = re.match(r'^(\d{1,2}):(\d{2})$', str(input_data["end_time"]))
                if time_match and start_time:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2))
                    end_time = start_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    end_time = parsed_end
                    logger.warning("end_time_parse_failed", input=input_data["end_time"], error=str(e))

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
            raw_text=user_text,
            # Recurring events fields
            recurrence_type=input_data.get("recurrence_type"),
            recurrence_end_date=self._parse_optional_datetime(input_data.get("recurrence_end_date")),
            recurrence_days=input_data.get("recurrence_days"),
            # Delete by criteria fields
            delete_criteria_title=input_data.get("delete_criteria_title"),
            delete_criteria_title_contains=input_data.get("delete_criteria_title_contains")
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
        except Exception as e:
            logger.warning("first_date_format_error", date=first_date_str, error=str(e))

        try:
            if last_date_str:
                dt = self._parse_optional_datetime(last_date_str)
                if dt:
                    last_date = format_datetime_human(dt, locale=language)
        except Exception as e:
            logger.warning("last_date_format_error", date=last_date_str, error=str(e))

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
                            except Exception as e:
                                logger.debug("batch_summary_format_error", index=i, error=str(e))
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
                            except Exception as e:
                                logger.debug("batch_summary_format_error", index=i, error=str(e))
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
        except (ValueError, TypeError) as e:
            logger.debug("datetime_parse_failed", input=dt_str, error=str(e))
            return None


# Global instance
llm_agent_yandex = LLMAgentYandex()
