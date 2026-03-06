"""Local regex-based intent parser for common calendar queries.

Handles 60-70% of typical requests without LLM call:
- Queries: "что на сегодня", "какие планы на завтра", "мои дела"
- Todos: "позвонить клиенту", "подготовить документы" (no time)
- Creates: keywords + explicit time like "встреча в 15:00"
- Free slots: "свободное время", "когда я свободен"

Fallback to LLM for complex/ambiguous requests.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger()

# Confidence threshold — below this, fall through to LLM
CONFIDENCE_THRESHOLD = 0.85


def parse_intent(
    text: str,
    timezone: str = "Europe/Moscow"
) -> Optional[Tuple[str, dict, float]]:
    """
    Try to parse user intent from text using regex patterns.

    Args:
        text: User's message text
        timezone: User timezone string

    Returns:
        Tuple of (intent_type, params_dict, confidence) or None if can't parse.
        intent_type: "query", "todo", "create", "find_free_slots"
        params_dict: extracted parameters (dates, title, time, etc.)
        confidence: float 0.0-1.0
    """
    text_lower = text.lower().strip()

    # Skip very short or very long texts
    if len(text_lower) < 2 or len(text_lower) > 500:
        return None

    # Try each parser in priority order
    result = _try_query(text_lower, timezone)
    if result:
        return result

    result = _try_free_slots(text_lower, timezone)
    if result:
        return result

    result = _try_create_with_time(text_lower, text, timezone)
    if result:
        return result

    result = _try_todo(text_lower, text)
    if result:
        return result

    return None


# ==================== Query patterns ====================

_QUERY_PATTERNS = [
    # "что на сегодня/завтра/неделю"
    (r"(?:что|чё|шо)\s+(?:у меня\s+)?на\s+(сегодня|завтра|послезавтра|(?:эту\s+)?недел[юе])", 0.95),
    # "какие планы на сегодня"
    (r"как(?:ие|ой)\s+(?:план[ыа]?|дел[аов]?|событи[яей]?|встреч[иа]?)\s+(?:на\s+)?(сегодня|завтра|послезавтра|(?:эту\s+)?недел[юе])", 0.95),
    # "дела на сегодня"
    (r"^(?:мои\s+)?(?:план[ыа]?|дел[аов]?|событи[яей]?|расписани[ее])\s+(?:на\s+)?(сегодня|завтра|послезавтра|(?:эту\s+)?недел[юе])", 0.93),
    # "покажи расписание"
    (r"покаж[иь]\s+(?:мо[иёе]\s+)?(?:расписани[ее]|план[ыа]?|дел[аов]?|событи[яей]?)", 0.90),
    # "что запланировано"
    (r"что\s+(?:у меня\s+)?запланирован[оа]", 0.90),
    # Simple exact matches
    (r"^(?:мои\s+)?дела$", 0.90),
    (r"^(?:мои\s+)?планы$", 0.90),
    (r"^расписание$", 0.90),
    (r"^(?:что\s+)?на\s+сегодня\??$", 0.95),
    (r"^(?:что\s+)?на\s+завтра\??$", 0.95),
]

_DAY_MAP = {
    "сегодня": 0,
    "завтра": 1,
    "послезавтра": 2,
}


def _try_query(text_lower: str, timezone: str) -> Optional[Tuple[str, dict, float]]:
    """Try to match query intent."""
    for pattern, confidence in _QUERY_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            # Extract day reference
            day_ref = m.group(1) if m.lastindex and m.lastindex >= 1 else "сегодня"
            day_ref = day_ref.strip().lower()

            now = datetime.now()

            if "недел" in day_ref:
                # This week: from today to +7 days
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=7)
            elif day_ref in _DAY_MAP:
                offset = _DAY_MAP[day_ref]
                start = (now + timedelta(days=offset)).replace(hour=0, minute=0, second=0, microsecond=0)
                end = start.replace(hour=23, minute=59, second=59)
            else:
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start.replace(hour=23, minute=59, second=59)

            return ("query", {
                "query_date_start": start,
                "query_date_end": end,
            }, confidence)

    return None


# ==================== Free slots patterns ====================

_FREE_SLOTS_PATTERNS = [
    (r"свободн(?:ое|ые|ого)\s+(?:врем[яени]+|слот[ыа]?|окн[аоу])", 0.93),
    (r"когда\s+(?:я\s+)?свобод(?:ен|на|ны)", 0.93),
    (r"(?:есть|будет)\s+(?:ли\s+)?свободн(?:ое|ые)\s+(?:врем[яени]+|окн[аоу])", 0.90),
    (r"найд[иь]\s+(?:свободн(?:ое|ые)\s+)?(?:врем[яени]+|слот[ыа]?)", 0.90),
]


def _try_free_slots(text_lower: str, timezone: str) -> Optional[Tuple[str, dict, float]]:
    """Try to match free slots intent."""
    for pattern, confidence in _FREE_SLOTS_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            # Check for day reference in the rest of text
            now = datetime.now()
            if "завтра" in text_lower:
                date = now + timedelta(days=1)
            elif "послезавтра" in text_lower:
                date = now + timedelta(days=2)
            else:
                date = now

            return ("find_free_slots", {
                "query_date_start": date.replace(hour=0, minute=0, second=0, microsecond=0),
            }, confidence)

    return None


# ==================== Create patterns (with explicit time) ====================

_TIME_PATTERN = r'(?:в\s+)?(\d{1,2})[:.ч](\d{2})?'

_CREATE_KEYWORDS = [
    "встреча", "показ", "просмотр", "совещание", "созвон",
    "звонок", "собрание", "презентация", "консультация",
    "обед", "ужин", "завтрак", "тренировка", "вебинар",
    "митинг", "конференция", "собеседование", "интервью",
]

_DAY_KEYWORDS = {
    "сегодня": 0,
    "завтра": 1,
    "послезавтра": 2,
    "понедельник": None,  # Will calculate from current weekday
    "вторник": None,
    "среда": None,
    "среду": None,
    "четверг": None,
    "пятница": None,
    "пятницу": None,
    "суббота": None,
    "субботу": None,
    "воскресенье": None,
    "воскресени": None,
}

_WEEKDAY_MAP = {
    "понедельник": 0, "вторник": 1, "среда": 2, "среду": 2,
    "четверг": 3, "пятница": 4, "пятницу": 4,
    "суббота": 5, "субботу": 5, "воскресенье": 6, "воскресени": 6,
}

# Event type detection keywords
_EVENT_TYPE_KEYWORDS = {
    "showing": ["показ", "просмотр", "осмотр", "смотрин"],
    "client_call": ["позвонить", "звонок", "созвон", "перезвонить", "дозвонить"],
    "doc_signing": ["подписание", "подписать", "сделка", "договор", "документы на подпис"],
    "dev_meeting": ["застройщик", "девелопер", "строител", "жк ", "новостройк"],
}


def _detect_event_type(text_lower: str) -> str:
    """Detect domain event type from text keywords."""
    for event_type, keywords in _EVENT_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return event_type
    return "generic"


def _get_now(timezone: str) -> datetime:
    """Get current time in user's timezone as naive datetime."""
    try:
        import pytz
        tz = pytz.timezone(timezone)
        return datetime.now(tz).replace(tzinfo=None)
    except Exception:
        return datetime.now()


def _try_create_with_time(text_lower: str, text_orig: str, timezone: str) -> Optional[Tuple[str, dict, float]]:
    """Try to match create intent — requires explicit time."""
    # Must have explicit time to be confident
    time_match = re.search(_TIME_PATTERN, text_lower)
    if not time_match:
        return None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2)) if time_match.group(2) else 0

    # Validate time
    if hour > 23 or minute > 59:
        return None

    # Use timezone-aware "now" for correct past-time detection
    now = _get_now(timezone)
    target_date = now  # Default to today

    for day_kw, offset in _DAY_KEYWORDS.items():
        if day_kw in text_lower:
            if offset is not None:
                target_date = now + timedelta(days=offset)
            else:
                # Weekday — find next occurrence
                weekday = _WEEKDAY_MAP.get(day_kw)
                if weekday is not None:
                    days_ahead = weekday - now.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)
            break

    start_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If time already passed today and no day specified, assume tomorrow
    if start_time < now and "сегодня" not in text_lower:
        found_day = any(day_kw in text_lower for day_kw in _DAY_KEYWORDS)
        if not found_day:
            start_time += timedelta(days=1)

    # Extract title: remove time pattern and day keywords, use the rest
    title = text_orig.strip()
    # Remove time references
    title = re.sub(r'(?:в\s+)?\d{1,2}[:.ч]\d{0,2}', '', title).strip()
    # Remove day references
    for day_kw in _DAY_KEYWORDS:
        title = re.sub(rf'\b{day_kw}\b', '', title, flags=re.IGNORECASE).strip()
    # Remove prepositions left hanging
    title = re.sub(r'\s+на\s*$', '', title).strip()
    title = re.sub(r'\s+в\s*$', '', title).strip()
    title = re.sub(r'^\s*на\s+', '', title).strip()
    # Clean up extra spaces
    title = re.sub(r'\s+', ' ', title).strip()

    if not title or len(title) < 2:
        return None  # Can't determine title — fall to LLM

    # Check confidence: higher if text contains known event keywords
    confidence = 0.80  # base
    for kw in _CREATE_KEYWORDS:
        if kw in text_lower:
            confidence = 0.92
            break

    if confidence < CONFIDENCE_THRESHOLD:
        return None  # Not confident enough

    # Detect domain event type
    event_type = _detect_event_type(text_lower)

    return ("create", {
        "title": title,
        "start_time": start_time,
        "end_time": start_time + timedelta(hours=1),  # Default 1h duration
        "event_type": event_type,
    }, confidence)


# ==================== Todo patterns (no time) ====================

_TODO_KEYWORDS = [
    r"позвони(?:ть)?", r"написа(?:ть)?", r"напиши",
    r"согласова(?:ть)?", r"подготови(?:ть)?",
    r"куп(?:ить|и)", r"оплати(?:ть)?", r"отправ(?:ить|ь)",
    r"проверь", r"проверить", r"узна(?:ть|й)",
    r"заказа(?:ть)?", r"забра(?:ть)?", r"забери",
    r"сдела(?:ть|й)", r"зарегистрирова(?:ть)?",
    r"обнови(?:ть)?", r"найти", r"найди",
    r"(?:нужно|надо|необходимо)\s+\w+",
]

_TODO_PREFIX_PATTERN = re.compile(
    r'^(?:' + '|'.join(_TODO_KEYWORDS) + r')\s+',
    re.IGNORECASE
)

# Explicit todo markers
_EXPLICIT_TODO_PATTERNS = [
    (r"^(?:задач[аиу]|todo|напоминани[ее]|напомни)[\s:]+(.+)", 0.95),
    (r"^(?:добав(?:ь|ить)\s+(?:в\s+)?(?:задач[иу]|todo))[\s:]+(.+)", 0.95),
]


def _try_todo(text_lower: str, text_orig: str) -> Optional[Tuple[str, dict, float]]:
    """Try to match todo intent — task without specific time."""
    # If text contains explicit time, it's probably an event, not todo
    if re.search(r'\d{1,2}[:.]\d{2}', text_lower):
        return None

    # Check explicit todo markers first
    for pattern, confidence in _EXPLICIT_TODO_PATTERNS:
        m = re.search(pattern, text_lower)
        if m:
            title = m.group(1).strip() if m.lastindex >= 1 else text_orig.strip()
            if title and len(title) >= 2:
                return ("todo", {"title": title}, confidence)

    # Check keyword-based todo detection
    if _TODO_PREFIX_PATTERN.search(text_lower):
        # Has todo keyword at start — high confidence
        title = text_orig.strip()
        if title and len(title) >= 3:
            return ("todo", {"title": title}, 0.88)

    return None
