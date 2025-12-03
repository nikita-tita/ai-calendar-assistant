"""DateTime parsing utilities."""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import dateparser
import pytz
from app.config import settings
import structlog

logger = structlog.get_logger()


def parse_datetime_range(
    text: str,
    timezone: str = settings.default_timezone,
    reference_date: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[datetime], Optional[int]]:
    """
    Parse datetime range from natural language text.

    Args:
        text: Natural language text containing date/time information
        timezone: Timezone to use for parsing (default: Europe/Moscow)
        reference_date: Reference date for relative dates (default: now)

    Returns:
        Tuple of (start_time, end_time, duration_minutes)
        Any component can be None if not found in text

    Examples:
        >>> parse_datetime_range("завтра в 10:00 на час")
        (datetime(2025, 12, 11, 10, 0), datetime(2025, 12, 11, 11, 0), 60)

        >>> parse_datetime_range("в пятницу с 14:00 до 16:30")
        (datetime(2025, 12, 13, 14, 0), datetime(2025, 12, 13, 16, 30), 150)
    """
    tz = pytz.timezone(timezone)
    now = reference_date or datetime.now(tz)

    # Settings for dateparser
    settings_dict = {
        'TIMEZONE': timezone,
        'RETURN_AS_TIMEZONE_AWARE': True,
        'PREFER_DATES_FROM': 'future',  # Предпочитать будущие даты
        'RELATIVE_BASE': now,
    }

    start_time = None
    end_time = None
    duration_minutes = None

    try:
        # Attempt to parse the full text as a datetime
        parsed = dateparser.parse(text, settings=settings_dict, languages=['ru', 'en'])

        if parsed:
            start_time = parsed
            logger.debug("parsed_datetime", text=text, start=start_time.isoformat())

        # Try to extract duration
        duration_minutes = extract_duration(text)

        # Calculate end time if we have start + duration
        if start_time and duration_minutes:
            end_time = start_time + timedelta(minutes=duration_minutes)

        # Try to find explicit end time phrases
        end_phrases = extract_end_time(text, settings_dict)
        if end_phrases:
            end_time = end_phrases
            if start_time and end_time:
                duration_minutes = int((end_time - start_time).total_seconds() / 60)

    except Exception as e:
        logger.error("datetime_parse_error", text=text, error=str(e))

    return start_time, end_time, duration_minutes


def extract_duration(text: str) -> Optional[int]:
    """
    Extract duration in minutes from text.

    Args:
        text: Text to extract duration from

    Returns:
        Duration in minutes or None

    Examples:
        >>> extract_duration("на час")
        60
        >>> extract_duration("на 2 часа 30 минут")
        150
        >>> extract_duration("на полчаса")
        30
    """
    import re

    # Patterns for different duration formats
    patterns = [
        (r'на\s+(\d+)\s+час', lambda m: int(m.group(1)) * 60),
        (r'на\s+(\d+)\s+мин', lambda m: int(m.group(1))),
        (r'на\s+полчаса', lambda m: 30),
        (r'на\s+час', lambda m: 60),
        (r'(\d+)\s+hour', lambda m: int(m.group(1)) * 60),
        (r'(\d+)\s+min', lambda m: int(m.group(1))),
    ]

    for pattern, converter in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return converter(match)

    return None


def extract_end_time(text: str, settings_dict: dict) -> Optional[datetime]:
    """
    Extract explicit end time from text.

    Args:
        text: Text to extract end time from
        settings_dict: dateparser settings

    Returns:
        End datetime or None
    """
    import re

    # Look for "до" (until) patterns
    until_pattern = r'до\s+(\d{1,2}):?(\d{2})?'
    match = re.search(until_pattern, text)

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0

        # Use dateparser to get the date, then set the time
        base_date = dateparser.parse(text, settings=settings_dict, languages=['ru', 'en'])
        if base_date:
            return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return None


def format_datetime_human(dt: datetime, locale_or_timezone: str = 'ru') -> str:
    """
    Format datetime in human-readable format.

    Args:
        dt: Datetime to format
        locale_or_timezone: Locale (ru, en, es, ar) or timezone (for backwards compatibility)

    Returns:
        Human-readable datetime string

    Example:
        >>> format_datetime_human(datetime(2025, 12, 10, 15, 30), 'ru')
        "10 декабря в 15:30"
        >>> format_datetime_human(datetime(2025, 12, 10, 15, 30), 'en')
        "December 10 at 3:30 PM"
    """
    # Convert string datetime to datetime object if needed
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception as e:
            logger.error("format_datetime_human_parse_error", dt=dt, error=str(e))
            return str(dt)  # Fallback to string representation

    logger.info("format_datetime_human_input",
                dt_input=dt.isoformat() if dt else None,
                has_tzinfo=dt.tzinfo is not None if dt else None,
                tzinfo_str=str(dt.tzinfo) if dt and dt.tzinfo else None,
                locale_or_timezone=locale_or_timezone)

    # Handle timezone passed instead of locale (backwards compatibility)
    locale = locale_or_timezone
    target_timezone = None
    if '/' in locale_or_timezone:  # It's a timezone like "Europe/Moscow"
        target_timezone = locale_or_timezone
        locale = 'ru'  # Default to Russian for timezone format

    # Convert to target timezone if provided
    if target_timezone:
        try:
            tz = pytz.timezone(target_timezone)
            # If dt is naive, assume UTC
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            # Convert to target timezone
            dt_before = dt.isoformat()
            dt = dt.astimezone(tz)
            logger.info("format_datetime_human_converted",
                        dt_before=dt_before,
                        dt_after=dt.isoformat(),
                        target_timezone=target_timezone)
        except Exception as e:
            logger.error("timezone_conversion_error", timezone=target_timezone, error=str(e))

    if locale == 'ru':
        months = {
            1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
            5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
            9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
        }
        month_name = months[dt.month]
        return f"{dt.day} {month_name} в {dt.hour:02d}:{dt.minute:02d}"

    elif locale == 'en':
        # Format: "December 10 at 3:30 PM"
        hour_12 = dt.hour % 12 or 12
        am_pm = "AM" if dt.hour < 12 else "PM"
        month_name = dt.strftime("%B")
        return f"{month_name} {dt.day} at {hour_12}:{dt.minute:02d} {am_pm}"

    elif locale == 'es':
        months = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        month_name = months[dt.month]
        return f"{dt.day} de {month_name} a las {dt.hour:02d}:{dt.minute:02d}"

    elif locale == 'ar':
        months = {
            1: 'يناير', 2: 'فبراير', 3: 'مارس', 4: 'أبريل',
            5: 'مايو', 6: 'يونيو', 7: 'يوليو', 8: 'أغسطس',
            9: 'سبتمبر', 10: 'أكتوبر', 11: 'نوفمبر', 12: 'ديسمبر'
        }
        month_name = months[dt.month]
        # Arabic format: day month at HH:MM (reading right to left)
        return f"{dt.day} {month_name} في {dt.hour:02d}:{dt.minute:02d}"

    else:
        # Fallback to English
        hour_12 = dt.hour % 12 or 12
        am_pm = "AM" if dt.hour < 12 else "PM"
        month_name = dt.strftime("%B")
        return f"{month_name} {dt.day} at {hour_12}:{dt.minute:02d} {am_pm}"
