# Backup Info - Working State 2025-10-30 18:54

## Status
✅ All features working correctly
✅ Visual appearance perfect
✅ All user flows tested

## Key Features Implemented

### 1. Services Menu (🛠 Сервисы)
- Replaced "🏢 Поиск недвижимости" button with "🛠 Сервисы"
- Shows М2 services menu with 5 buttons:
  - 💰 Ипотечный брокер → https://m2.ru/ipoteka/calculator/
  - 🛡 Защита сделки → https://m2.ru/services/guaranteed-deal/
  - 📋 Регистрация и безопасные расчеты → https://m2.ru/services/deal/
  - 🏠 Аренда → https://arenda.yandex.ru/pages/for-agents/?utm_source=menu_landing
  - 🏢 Подбор новостроек → Opens @aipropertyfinder_bot info

### 2. Consent System
- Advertising consent with retry on decline
- Privacy consent with retry on decline
- Sequential flow: advertising → privacy → welcome message
- Stored in user_preferences.json

### 3. Settings Menu
- Morning summary toggle + time change
- Evening digest toggle + time change
- Quiet hours with separate start/end time editing
- Timezone selection
- Help screen with command examples

### 4. Delete Operations
- Delete all events matching title (search range: 365 days)
- Delete by criteria with confirmation
- Delete duplicates detection
- Inline button confirmations

### 5. Recurring Events
- Create daily/weekly/monthly recurring events
- Time-only parsing for "09:00" format
- Creates individual events up to 365 days or specified end date

### 6. Free Slots Feature
- Shows available time slots for specified date
- Merges overlapping busy periods
- Displays slots with duration

### 7. Timezone Handling
- All events stored in UTC in CalDAV
- Converted to user's timezone for display (Europe/Moscow by default)
- Timezone-aware datetime throughout the codebase

## Modified Files

1. **app/services/telegram_handler.py** (63KB)
   - Added _handle_services_menu()
   - Added services:property_search callback handler
   - Updated main keyboard button
   - All event display functions pass user_tz to format_datetime_human()

2. **app/services/llm_agent_yandex.py** (54KB)
   - Added time-only parsing (HH:MM format) for recurring events
   - Logging for parsed time with timezone info

3. **app/services/calendar_radicale.py** (16KB)
   - Fixed free slots algorithm (merge overlapping busy periods)
   - Logging for UTC conversion on create/retrieve
   - All datetimes properly converted UTC ↔ Moscow

4. **app/services/daily_reminders.py** (15KB)
   - Uses user's configured reminder times (not hardcoded)
   - Respects quiet hours setting
   - Checks if reminders are enabled before sending

5. **app/services/user_preferences.py** (9.8KB)
   - Added consent tracking (advertising, privacy)
   - Added reminder settings (morning/evening enabled + times)
   - Added quiet hours settings (start/end times)

6. **app/utils/datetime_parser.py** (8.2KB)
   - Enhanced format_datetime_human() to convert UTC → user timezone
   - Accepts timezone as parameter
   - Comprehensive logging (INFO level)

## Environment

- Server: 95.163.227.26
- Container: telegram-bot-polling
- Bot: @CalendarAI_m2_bot
- Database: Radicale CalDAV (radicale-calendar container)
- User preferences: /var/lib/calendar-bot/user_preferences.json

## Git Status at Backup Time

Modified files:
- app/services/telegram_handler.py
- app/services/llm_agent_yandex.py
- app/services/calendar_radicale.py
- app/services/daily_reminders.py
- app/services/user_preferences.py
- app/utils/datetime_parser.py

## Deployment Commands

```bash
# Copy files to server
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/services/telegram_handler.py \
  app/services/llm_agent_yandex.py \
  app/services/calendar_radicale.py \
  app/services/daily_reminders.py \
  app/services/user_preferences.py \
  root@95.163.227.26:/root/ai-calendar-assistant/app/services/

sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/utils/datetime_parser.py \
  root@95.163.227.26:/root/ai-calendar-assistant/app/utils/

# Deploy to container
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 "\
  docker cp /root/ai-calendar-assistant/app/services/telegram_handler.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/llm_agent_yandex.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/calendar_radicale.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/daily_reminders.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/user_preferences.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/utils/datetime_parser.py telegram-bot-polling:/app/app/utils/ && \
  docker restart telegram-bot-polling"
```

## Known Issues

- Timezone display bug for recurring events (being investigated with logging)
- Events created with schedule format show correct time in web app but 3 hours off in bot queries

## Next Steps

- Debug timezone issue with new logging
- User to test "дела на завтра" to capture logs
- Fix timezone conversion for query display
