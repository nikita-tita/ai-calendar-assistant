# Batch Schedule Creation Feature

## Overview

The AI Calendar Assistant now supports automatic detection and parsing of schedule-formatted text with multiple time ranges. This allows users to paste an entire day's schedule and create all events at once.

## How It Works

### Pattern Detection

The system automatically detects schedule format when:
- **3+ time entries** are present in the message
- Time entries use format: `HH:MM-HH:MM Event Title` or `HH:MM Event Title`
- Optional keywords help detection: `тайминг`, `расписание`, `schedule`, `agenda`, `программа`

### Supported Formats

#### Time Range Format (Recommended)
```
12:45-13:00 Приезд, заселение
13:00-13:30 Кофе-брейк с сендвичами
13:30-15:00 Дискуссия по ИИ
15:00-16:00 Обед
```

#### Single Time Format
```
20:00 Ужин
21:00 Свободное время
22:00 Отбой
```
*Note: Single time entries default to 1-hour duration*

#### Mixed Format
```
12:45-13:00 Приезд
13:00-13:30 Кофе-брейк
20:00 Ужин
```

### Date Context

The system extracts the target date from the text:

**Relative dates:**
- `завтра` / `tomorrow` → next day
- `послезавтра` → day after tomorrow
- `сегодня` / `today` → current day

**Explicit dates:**
- `на 23 октября` → October 23 (of current year if not passed, otherwise asks for clarification)
- `на 15.11.2025` → November 15, 2025 (explicit year, no clarification needed)
- `на 5 января` → January 5

**Year Ambiguity Handling:**
- If a date like "23 октября" has already passed this year (more than 1 day ago), the bot will ask for clarification
- Example: "Уточните, пожалуйста: расписание на 23 октября 2025 года или 2026 года?"
- User can respond with:
  - Explicit year: "2026" or "2026 года"
  - Relative: "следующего года" / "next year" → next year
  - Relative: "этого года" / "this year" → current year

**Default:** If no date is specified, defaults to current day

## Usage Example

### User Input
```
тайминг на 23 октября (завтра):
12:45-13:00 Приезд, заселение (по готовности номеров)
13:00-13:30 Кофе-брейк с сендвичами
13:30-15:00 Дискуссия по ИИ
15:00-16:00 Обед
16:00-16:30 Заезд, свободное время
16:30-18:00 Игра "Го"
18:00-18:20 Кофе-брейк
18:20-20:00 Игра "Го"
20:00 Ужин
```

### Bot Response
```
📅 Создать 9 событий
📍 23 октября 2025, 12:45
🔄 С 12:45 до 20:00

[Подтвердить] [Отменить]
```

### After Confirmation
All 9 events are created automatically in the user's calendar with correct start/end times.

## Technical Implementation

### Location in Codebase

**File:** [app/services/llm_agent_yandex.py](app/services/llm_agent_yandex.py)

**Key Functions:**
- `_detect_schedule_format()` - Pattern detection and parsing (lines 134-313)
- `extract_event()` - Entry point with preprocessing (lines 295-299)

### Processing Flow

1. **Preprocessing** (before LLM call)
   - User text is analyzed for schedule patterns
   - Regex matches time ranges: `(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})\s+(.+?)(?:\n|$)`
   - Regex matches single times: `^(\d{1,2}:\d{2})\s+([^-–—\n]+)(?:\n|$)`

2. **Date Extraction**
   - Searches for date keywords/patterns in text
   - Parses Russian/English month names
   - Handles relative dates (tomorrow, today, etc.)
   - Defaults to current date if not found

3. **Batch Actions Generation**
   - Each matched line becomes one event
   - Start/end times are parsed and combined with target date
   - Titles are cleaned (trailing punctuation removed)
   - Duration calculated automatically

4. **Confirmation Flow**
   - Returns `EventDTO` with `intent=BATCH_CONFIRM`
   - User sees summary with confirm/cancel buttons
   - On confirmation, all events created via existing batch handler

### Regex Patterns

**Time Range Pattern:**
```regex
(\d{1,2}:\d{2})\s*[-–—]\s*(\d{1,2}:\d{2})\s+(.+?)(?:\n|$)
```
- Captures: start_time, end_time, title
- Supports various dash characters (-, –, —)
- Multiline matching

**Single Time Pattern:**
```regex
^(\d{1,2}:\d{2})\s+([^-–—\n]+)(?:\n|$)
```
- Captures: start_time, title
- Defaults to 1-hour duration

**Date Patterns:**
```regex
на\s+(\d{1,2})\s+(января|февраля|марта|...|декабря)  # Russian months
на\s+(завтра|послезавтра|сегодня)                     # Relative dates
(\d{1,2})\.(\d{1,2})\.(\d{2,4})                       # DD.MM.YYYY
```

## Benefits

1. **Time Saving** - Create entire day's schedule in one message
2. **No LLM Overhead** - Regex-based parsing is fast and reliable
3. **Flexible Format** - Supports various time formats and date expressions
4. **User-Friendly** - Natural format matching how people write schedules
5. **Preview & Confirm** - User sees summary before creation

## Limitations

1. **Minimum 3 Events** - Requires at least 3 time entries to activate
2. **Same-Day Events** - All events must be for the same date
3. **Simple Titles** - Complex multi-line titles may not parse correctly
4. **Date Parsing** - Non-standard date formats may default to today
5. **Past Dates** - Dates that have already passed require year clarification from user

## Future Enhancements

- Support for multi-day schedules
- Location extraction from event titles
- Recurring pattern detection within schedule
- Export/import from calendar apps
- Template saving for common schedules

## Testing

To test the feature:

1. Send a message with 3+ time ranges
2. Include date context (e.g., "на завтра")
3. Verify all events are detected correctly
4. Confirm and check calendar

**Example Test Message:**
```
расписание на завтра:
09:00-10:00 Встреча с командой
10:00-11:30 Обзор проекта
11:30-12:00 Кофе-брейк
12:00-13:00 Презентация
```

## Related Files

- [app/services/llm_agent_yandex.py](app/services/llm_agent_yandex.py#L134-L313) - Schedule detection
- [app/services/telegram_handler.py](app/services/telegram_handler.py#L1093-L1138) - Batch confirmation UI
- [app/schemas/events.py](app/schemas/events.py) - EventDTO and IntentType definitions

## Version History

- **2025-10-27** - Initial implementation
  - Regex-based pattern detection
  - Russian/English date parsing
  - Support for time ranges and single times
  - Integration with existing batch confirmation flow
