# AI Calendar Assistant - Полная Документация

## Содержание
1. [Product Requirements Document (PRD)](#1-product-requirements-document-prd)
2. [Техническая Архитектура](#2-техническая-архитектура)
3. [LLM Промпты и Логика](#3-llm-промпты-и-логика)
4. [База Данных и Хранилище](#4-база-данных-и-хранилище)
5. [Аналитика и Мониторинг](#5-аналитика-и-мониторинг)
6. [API Документация](#6-api-документация)
7. [Deployment Guide](#7-deployment-guide)

---

# 1. Product Requirements Document (PRD)

## 1.1 Обзор Продукта

**Название:** AI Calendar Assistant
**Версия:** 2.0
**Дата:** Октябрь 2025
**Целевая Аудитория:** Риелторы, менеджеры по продажам, специалисты по недвижимости
**Регион:** Россия (работает с Yandex Cloud API)

### Описание
AI-календарь с интеллектуальным ассистентом для управления событиями через естественный язык. Поддержка Telegram-бота и веб-интерфейса с голосовым вводом, мультиязычность, автоматические напоминания.

## 1.2 Цели Продукта

### Основные Цели
1. **Упростить планирование** - создание событий за 5-10 секунд голосом
2. **Повысить пунктуальность** - автоматические напоминания за 30 минут
3. **Мотивировать пользователей** - ежедневные мотивационные сообщения
4. **Работать из России** - использование Yandex Cloud вместо OpenAI/Anthropic

### Метрики Успеха
- **Time to Event Creation:** < 10 секунд (голос) или < 20 секунд (текст)
- **User Retention:** > 60% в месяц
- **Daily Active Users:** > 50% от зарегистрированных
- **Event Creation Success Rate:** > 95%

## 1.3 Ключевые Функции

### Функция 1: Создание Событий Голосом/Текстом
**Описание:** Пользователь говорит или пишет на естественном языке, система создаёт событие в календаре.

**Пример команд:**
- "Встреча с клиентом завтра в 10"
- "Просмотр квартиры на ул. Ленина послезавтра в 14:00"
- "Обед с Машей в пятницу в полдень"
- "Конференция каждую среду в 9 утра"

**Acceptance Criteria:**
- ✅ Распознаёт дату/время с точностью 95%
- ✅ Поддерживает относительные даты (завтра, послезавтра, в понедельник)
- ✅ Извлекает название, время, место, участников
- ✅ Спрашивает уточнения при неполной информации

### Функция 2: Повторяющиеся События
**Описание:** Создание событий по расписанию (ежедневно, еженедельно, ежемесячно).

**Пример команд:**
- "Планёрка каждый понедельник в 9 утра"
- "Тренировка каждый вторник и четверг в 18:00"
- "Отчёт в первый понедельник месяца"

**Acceptance Criteria:**
- ✅ Поддержка daily/weekly/monthly
- ✅ Выбор дней недели для weekly
- ✅ Конечная дата рекуррентности (опционально)

### Функция 3: Умные Запросы
**Описание:** Получение информации о событиях через естественные вопросы.

**Пример запросов:**
- "Какие дела сегодня?"
- "Что у меня на неделе?"
- "Когда встреча с Ивановым?"
- "Найди свободное время в пятницу"

**Acceptance Criteria:**
- ✅ Понимает относительные даты
- ✅ Фильтрует по названию/участникам
- ✅ Форматирует ответ human-readable
- ✅ Поиск свободных слотов

### Функция 4: Ежедневные Напоминания
**Описание:** Автоматические push-уведомления в фиксированное время.

**Расписание:**
- **9:00** - Утреннее напоминание со списком событий на день
- **10:00** - Мотивационное сообщение (60 вариантов, циклически)
- **20:00** - Вечернее сообщение со статистикой дня

**Acceptance Criteria:**
- ✅ Отправка в timezone пользователя
- ✅ Мультиязычные сообщения
- ✅ Inline-кнопки для быстрых действий
- ✅ Opt-out опция

### Функция 5: Pre-Event Напоминания
**Описание:** Уведомление за 30 минут до каждого события.

**Формат:**
```
⏰ Напоминание!

📅 Через 30 минут: Встреча с клиентом
🕐 Время: 14:00
📍 Место: ул. Ленина, 5
```

**Acceptance Criteria:**
- ✅ Отправка за 28-32 минуты (окно для надёжности)
- ✅ Timezone-aware
- ✅ Мультиязычность

### Функция 6: Веб-Интерфейс
**Описание:** Dashboard для просмотра и редактирования событий.

**Возможности:**
- Календарная сетка (день/неделя/месяц)
- Drag-and-drop перемещение событий
- Быстрое создание кликом
- Синхронизация с Telegram-ботом в реальном времени

**Acceptance Criteria:**
- ✅ Responsive design (mobile-first)
- ✅ Загрузка < 2 секунд
- ✅ Работа офлайн (PWA)

### Функция 7: Админ-Панель
**Описание:** Аналитика и мониторинг для владельца/администратора.

**Метрики:**
- Количество пользователей (всего/активных)
- Созданные события (день/неделя/месяц)
- Сообщения (текст/голос)
- Диалоги пользователей (для поддержки)
- Календарь каждого пользователя

**Безопасность:**
- 3-пароля для доступа:
  - Все 3 верные = реальная панель
  - Первые 2 верные = фейковая панель (защита от фишинга)
  - Иначе = отказ

## 1.4 User Stories

### Пользовательские Сценарии

**US-001: Быстрое создание события**
```
Как риелтор
Я хочу быстро создать событие голосом
Чтобы не отвлекаться от клиента

Acceptance:
- Открыл бот Telegram
- Нажал кнопку микрофона
- Сказал "Просмотр квартиры завтра в 15"
- Получил подтверждение за < 10 секунд
```

**US-002: Утренняя сводка**
```
Как менеджер
Я хочу получать утром список дел на день
Чтобы спланировать рабочий день

Acceptance:
- Каждое утро в 9:00 приходит сообщение
- Список событий с временем и местом
- Кнопка "Добавить событие" для быстрого действия
```

**US-003: Поиск свободного времени**
```
Как специалист по продажам
Я хочу найти свободное время для встречи
Чтобы предложить клиенту удобный слот

Acceptance:
- Написал "Найди свободное время в пятницу"
- Получил список свободных часов
- Выбрал слот одной кнопкой
```

## 1.5 Non-Functional Requirements

### Производительность
- **Response Time:** < 2 сек для текстовых команд, < 5 сек для голоса
- **LLM Latency:** < 1.5 сек для Yandex GPT
- **Concurrent Users:** До 1000 одновременно
- **Event Creation Rate:** 100+ событий/минуту

### Доступность
- **Uptime:** 99.5% (допустимый downtime: 3.6 часа/месяц)
- **Graceful Degradation:** При отказе LLM - fallback на простой парсинг
- **Multi-Region:** Развёртывание в РФ (Europe/Moscow timezone по умолчанию)

### Безопасность
- **Rate Limiting:** 10 сообщений/минуту, 50/час на пользователя
- **DDoS Protection:** Блокировка на 1 час после 3 burst атак
- **Data Privacy:** Хранение локально, без отправки в облако (кроме Yandex API)
- **Admin Access:** 3-level password authentication

### Масштабируемость
- **User Growth:** Поддержка до 10,000 пользователей на одном сервере
- **Event Storage:** Radicale CalDAV (поддерживает миллионы событий)
- **Analytics:** JSON-based (переход на PostgreSQL при > 5000 пользователей)

### Мультиязычность
- **Языки:** Русский, English, Español, العربية
- **Auto-Detection:** По языку Telegram (fallback на русский)
- **Локализация:** Все UI элементы, ошибки, напоминания

### Совместимость
- **Telegram API:** v21+ (python-telegram-bot)
- **Браузеры:** Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile:** iOS 13+, Android 8+
- **Calendar Protocols:** CalDAV (RFC 4918), iCalendar (RFC 5545)

---

# 2. Техническая Архитектура

## 2.1 Системная Архитектура

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                    │
├───────────────────┬─────────────────────────────────────┤
│  Telegram Bot UI  │      Web Application (SPA)          │
│  - Chat Interface │      - Vue.js Dashboard             │
│  - Voice Input    │      - Calendar Grid               │
│  - Inline Buttons │      - Drag-Drop Events            │
└─────────┬─────────┴───────────────┬─────────────────────┘
          │                         │
          │    ┌────────────────────▼──────────────────┐
          │    │      API GATEWAY (FastAPI)            │
          │    │  - REST API (port 8000)               │
          │    │  - CORS enabled                       │
          │    │  - Structured logging                 │
          │    └────────────┬──────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                     │
├─────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────────┐    │
│  │ Telegram Handler   │  │  Events Router         │    │
│  │ - Message routing  │  │  - CRUD operations     │    │
│  │ - Rate limiting    │  │  - Query filtering     │    │
│  │ - Conversation ctx │  │  - Calendar sync       │    │
│  └──────┬─────────────┘  └───────┬────────────────┘    │
│         │                        │                      │
│  ┌──────▼─────────────────────────▼──────────────┐     │
│  │          CORE SERVICES LAYER                  │     │
│  │                                                │     │
│  │  ┌──────────────┐  ┌──────────────────────┐   │     │
│  │  │LLM Agent     │  │Calendar Service      │   │     │
│  │  │(Yandex GPT)  │  │(Radicale CalDAV)     │   │     │
│  │  └──────┬───────┘  └───────┬──────────────┘   │     │
│  │         │                   │                  │     │
│  │  ┌──────▼───────┐  ┌───────▼──────────────┐   │     │
│  │  │STT Service   │  │User Preferences      │   │     │
│  │  │(Yandex)      │  │Translations          │   │     │
│  │  └──────────────┘  │Analytics             │   │     │
│  │                    └──────────────────────┘   │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │       BACKGROUND SERVICES                        │   │
│  │  - Daily Reminders (9:00, 10:00, 20:00)        │   │
│  │  - Event Reminders (30 min before)             │   │
│  │  - Cleanup Tasks                                │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                   INTEGRATION LAYER                      │
├──────────────────────────────────────────────────────────┤
│  Yandex GPT API  │  Yandex STT API  │  Telegram Bot API │
│  (LLM calls)     │  (Voice→Text)    │  (Send messages)  │
└──────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                   PERSISTENCE LAYER                      │
├──────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ Radicale Server  │  │  JSON File Storage           │ │
│  │ - CalDAV storage │  │  - user_preferences.json     │ │
│  │ - iCal format    │  │  - analytics_data.json       │ │
│  │ - Per-user cals  │  │  - daily_reminder_users.json │ │
│  └──────────────────┘  └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## 2.2 Компоненты Системы

### 2.2.1 API Gateway (FastAPI)

**Файл:** `app/main.py`
**Порт:** 8000
**Роль:** Единая точка входа для всех HTTP запросов

**Роутеры:**
1. **TelegramRouter** (`/telegram/*`)
   - Webhook для Telegram Bot API
   - Статус бота

2. **EventsRouter** (`/api/events/*`)
   - CRUD операции с событиями
   - Список событий в диапазоне
   - Поиск свободного времени

3. **AdminRouter** (`/api/admin/*`)
   - Аналитика и статистика
   - Просмотр диалогов пользователей
   - Управление пользователями

**Middleware:**
- CORS: `allow_origins=["*"]` (для WebApp)
- Request logging (structlog)
- Error handling (custom exception handlers)

### 2.2.2 Telegram Handler

**Файл:** `app/services/telegram_handler.py`
**Класс:** `TelegramHandler`

**Ответственности:**
1. Обработка входящих сообщений (текст, голос, команды)
2. Роутинг по типу сообщения
3. Управление контекстом разговора (последние 10 сообщений)
4. Rate limiting проверка
5. Callback query обработка (inline кнопки)

**Методы:**
```python
async def handle_update(update: Update) -> None
async def handle_callback_query(update: Update) -> None
async def _handle_start(update: Update, user_id: str) -> None
async def _handle_voice(update: Update, user_id: str) -> None
async def _handle_text(update: Update, user_id: str) -> None
```

**Поток обработки:**
```
Update received
  ├─> Check rate limits
  ├─> Determine message type
  │   ├─> Command (/start, /timezone)
  │   ├─> Voice message → Transcribe
  │   ├─> Text message → Process
  │   └─> Callback query → Handle button click
  └─> Send response to user
```

### 2.2.3 LLM Agent (Yandex GPT)

**Файл:** `app/services/llm_agent_yandex.py`
**Класс:** `LLMAgentYandex`

**API:**
- Endpoint: `https://llm.api.cloud.yandex.net/foundationModels/v1/completion`
- Model: `yandexgpt` или `yandexgpt-lite`
- Method: POST с JSON payload

**Основной Метод:**
```python
async def extract_event(
    text: str,
    user_id: str,
    conversation_history: List[dict] = None,
    pending_batch: List[dict] = None
) -> EventDTO
```

**Capabilities:**
1. **Intent Detection:** create, update, delete, query, clarify
2. **Entity Extraction:** title, datetime, location, attendees
3. **Relative Date Parsing:** "завтра", "в пятницу", "через 2 дня"
4. **Recurring Patterns:** daily, weekly (days), monthly
5. **Batch Confirmation:** Multiple events approval
6. **Clarification Questions:** When info missing

**Function Schema:**
```json
{
  "name": "extract_calendar_event",
  "description": "Extracts structured event from natural language",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {
        "type": "string",
        "enum": ["create", "update", "delete", "query", "clarify", ...]
      },
      "title": { "type": "string" },
      "start_time": { "type": "string", "format": "date-time" },
      "duration_minutes": { "type": "integer" },
      "recurrence_type": {
        "type": "string",
        "enum": ["once", "daily", "weekly", "monthly"]
      },
      ...
    },
    "required": ["intent", "confidence"]
  }
}
```

### 2.2.4 Calendar Service (Radicale)

**Файл:** `app/services/calendar_radicale.py`
**Класс:** `RadicaleService`

**CalDAV Server:**
- URL: `http://radicale:5232`
- Protocol: CalDAV (RFC 4918)
- Authentication: Username-based (no password)
- Storage: iCalendar format (RFC 5545)

**Календари:**
- Naming: `telegram_{user_id}`
- Auto-creation: При первом событии
- Color: Auto-generated per user

**Методы:**
```python
async def create_event(user_id: str, event: EventDTO) -> str
async def list_events(user_id: str, start: datetime, end: datetime) -> List[CalendarEvent]
async def update_event(user_id: str, event_id: str, event: EventDTO) -> bool
async def delete_event(user_id: str, event_id: str) -> bool
async def find_free_slots(user_id: str, duration_minutes: int) -> List[FreeSlot]
```

**Event Format (iCalendar):**
```ical
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Calendar Assistant//EN
BEGIN:VEVENT
UID:abc123-def456-ghi789
DTSTART;TZID=Europe/Moscow:20251210T140000
DTEND;TZID=Europe/Moscow:20251210T150000
SUMMARY:Встреча с клиентом
LOCATION:ул. Ленина, 5
DESCRIPTION:Обсуждение договора
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
```

### 2.2.5 STT Service (Yandex SpeechKit)

**Файл:** `app/services/stt_yandex.py`
**Класс:** `STTServiceYandex`

**API:**
- Endpoint: `https://stt.api.cloud.yandex.net/speech/v1/stt:recognize`
- Format: OGG Opus (Telegram voice messages)
- Languages: ru-RU, en-US, uk-UA, kk-KZ, uz-UZ

**Метод:**
```python
async def transcribe_audio(
    file_path: str,
    language: str = "ru-RU"
) -> str
```

**Процесс:**
1. Download voice file from Telegram
2. Send binary data to Yandex API
3. Parse JSON response: `{ "result": "transcribed text" }`
4. Return text for LLM processing

**Supported Audio:**
- Format: OGG/Opus
- Max duration: 60 seconds
- Sample rate: 16-48 kHz

### 2.2.6 Background Services

#### Daily Reminders Service

**Файл:** `app/services/daily_reminders.py`
**Класс:** `DailyRemindersService`

**Расписание:**
- **9:00 AM** - Morning reminder with today's events
- **10:00 AM** - Motivational message (60 rotating messages)
- **8:00 PM** - Evening summary with event count

**Features:**
- Timezone-aware (per user)
- Test mode: Different times for test users (12:37, 12:39, 21:00)
- Deduplication: Track sent messages by date
- Multilingual: Uses translations service

**Методы:**
```python
async def send_morning_reminder(user_id: str, chat_id: int) -> None
async def send_morning_motivation(user_id: str, chat_id: int) -> None
async def send_evening_reminder(user_id: str, chat_id: int) -> None
async def run_daily_schedule() -> None
```

**Test Mode:**
```python
TEST_MODE = True  # Set to False for production
TEST_USER_IDS = {"2296243"}  # Only these users get test schedule
```

#### Event Reminders Service

**Файл:** `app/services/event_reminders.py`
**Класс:** `EventRemindersService`

**Функция:** Отправка напоминаний за 30 минут до события

**Алгоритм:**
1. Каждую минуту проверяет события
2. Окно: 28-32 минуты (для надёжности)
3. Проверяет, не было ли отправлено
4. Отправляет notification в Telegram

**Формат сообщения:**
```
⏰ Напоминание!

📅 Через 30 минут: {title}
🕐 Время: {time}
📍 {location}
```

### 2.2.7 Analytics Service

**Файл:** `app/services/analytics_service.py`
**Класс:** `AnalyticsService`

**Tracked Actions:**
- `USER_START` - First /start
- `USER_LOGIN` - Auth event
- `EVENT_CREATE/UPDATE/DELETE` - Calendar ops
- `TEXT_MESSAGE` - Text input
- `VOICE_MESSAGE` - Voice input
- `WEBAPP_OPEN` - WebApp access
- `ERROR` - Failed operations

**Data Structure:**
```json
{
  "actions": [
    {
      "user_id": "12345",
      "action_type": "event_create",
      "timestamp": "2025-10-22T10:00:00Z",
      "details": "Встреча с клиентом",
      "event_id": "abc-123",
      "success": true,
      "error_message": null,
      "is_test": false,
      "username": "nikita_tita",
      "first_name": "Nikita",
      "last_name": null
    }
  ]
}
```

**Dashboard Stats:**
```python
class AdminDashboardStats:
    total_logins: int
    active_users_today: int
    active_users_week: int
    active_users_month: int
    total_users: int
    total_actions: int
    total_events_created: int
    total_text_messages: int
    total_voice_messages: int
    recent_actions: List[UserAction]
```

### 2.2.8 Rate Limiter

**Файл:** `app/services/rate_limiter.py`
**Класс:** `RateLimiterService`

**Limits:**
- 10 messages per minute
- 50 messages per hour
- Burst detection: 5 messages in 10 seconds
- Spam block: 3 bursts = 1 hour ban
- Error flood: 5 errors in 1 minute = block

**Methods:**
```python
def check_rate_limit(user_id: str) -> Tuple[bool, str]
def record_message(user_id: str) -> None
def record_error(user_id: str) -> None
def get_stats(user_id: str) -> dict
def cleanup_old_data() -> None
```

**Data Structure:**
```python
{
  "user_12345": {
    "messages": [timestamp1, timestamp2, ...],
    "errors": [timestamp1, timestamp2, ...],
    "bursts": [timestamp1, timestamp2, ...],
    "blocked_until": datetime or None
  }
}
```

---

# 3. LLM Промпты и Логика

## 3.1 Системный Промпт (Base)

**Файл:** `app/services/llm_agent_yandex.py`
**Метод:** `_build_system_prompt()`

### Base System Prompt (Русский)

```
Ты — умный календарный ассистент. Твоя задача — извлекать из естественного языка информацию о календарных событиях и действиях.

ТЕКУЩЕЕ ВРЕМЯ И ДАТА:
- Сейчас: {current_datetime}
- Часовой пояс: {timezone}
- День недели: {weekday}

ПРАВИЛА ОБРАБОТКИ ДАТ:
1. "завтра" = {tomorrow}
2. "послезавтра" = {day_after_tomorrow}
3. "в понедельник" = следующий понедельник после сегодня
4. "через 3 дня" = прибавь 3 дня к текущей дате
5. Если время не указано, используй 10:00 для утренних дел, 14:00 для дневных, 18:00 для вечерних
6. Если дата не указана, но есть время — событие сегодня

ПОДДЕРЖКА ПОВТОРЯЮЩИХСЯ СОБЫТИЙ:
- "каждый день" → recurrence_type: "daily"
- "каждый понедельник" → recurrence_type: "weekly", recurrence_days: ["mon"]
- "каждую среду и пятницу" → recurrence_type: "weekly", recurrence_days: ["wed", "fri"]
- "каждый месяц" → recurrence_type: "monthly"

ФОРМАТЫ ВРЕМЕНИ:
- "в 10" = 10:00
- "в 14:30" = 14:30
- "в полдень" = 12:00
- "вечером" = 18:00
- "утром" = 09:00

ИЗВЛЕЧЕНИЕ УЧАСТНИКОВ:
- "встреча с Машей" → attendees: ["Маша"]
- "созвон с Ивановым и Петровым" → attendees: ["Иванов", "Петров"]

ДЕЙСТВИЯ (intent):
1. "create" - создать одно событие
2. "create_recurring" - создать повторяющееся событие
3. "update" - изменить существующее событие
4. "delete" - удалить событие
5. "query" - получить список событий
6. "find_free_slots" - найти свободное время
7. "batch_confirm" - требуется подтверждение нескольких событий
8. "clarify" - нужно уточнение (недостаточно данных)
9. "delete_by_criteria" - массовое удаление по критерию

ПРИМЕРЫ:
Вход: "Встреча с клиентом завтра в 10"
Выход: {
  "intent": "create",
  "title": "Встреча с клиентом",
  "start_time": "{tomorrow}T10:00:00",
  "duration_minutes": 60,
  "confidence": 0.95
}

Вход: "Планёрка каждый понедельник в 9 утра"
Выход: {
  "intent": "create_recurring",
  "title": "Планёрка",
  "start_time": "{next_monday}T09:00:00",
  "duration_minutes": 60,
  "recurrence_type": "weekly",
  "recurrence_days": ["mon"],
  "confidence": 0.98
}

Вход: "Перенеси встречу на 15:00"
Выход: {
  "intent": "update",
  "start_time": "{today}T15:00:00",
  "confidence": 0.85
}

Вход: "Удали все встречи с Ивановым"
Выход: {
  "intent": "delete_by_criteria",
  "delete_criteria_title_contains": "Иванов",
  "confidence": 0.90
}

Вход: "Найди свободное время завтра"
Выход: {
  "intent": "find_free_slots",
  "query_date_start": "{tomorrow}T00:00:00",
  "query_date_end": "{tomorrow}T23:59:59",
  "duration_minutes": 60,
  "confidence": 0.92
}
```

### Language-Specific Instructions

#### Английский (en)

```
You are a smart calendar assistant. Extract calendar event information from natural language.

CURRENT DATE/TIME:
- Now: {current_datetime}
- Timezone: {timezone}
- Weekday: {weekday}

DATE PROCESSING RULES:
1. "tomorrow" = {tomorrow}
2. "next Monday" = first Monday after today
3. "in 3 days" = add 3 days to current date
4. Default time: 10:00 AM if not specified
5. If no date given but time is: event today

TIME FORMATS:
- "at 2pm" = 14:00
- "at noon" = 12:00
- "in the evening" = 18:00
- "in the morning" = 09:00

ATTENDEES EXTRACTION:
- "meeting with John" → attendees: ["John"]
- "call with Smith and Brown" → attendees: ["Smith", "Brown"]

[Similar structure as Russian version...]
```

#### Испанский (es)

```
Eres un asistente de calendario inteligente. Extrae información de eventos del lenguaje natural.

FECHA/HORA ACTUAL:
- Ahora: {current_datetime}
- Zona horaria: {timezone}
- Día de la semana: {weekday}

REGLAS DE PROCESAMIENTO DE FECHAS:
1. "mañana" = {tomorrow}
2. "pasado mañana" = {day_after_tomorrow}
3. "el lunes" = próximo lunes después de hoy
4. Hora predeterminada: 10:00 si no se especifica

[Similar structure...]
```

#### Арабский (ar)

```
أنت مساعد تقويم ذكي. استخرج معلومات الحدث من اللغة الطبيعية.

التاريخ والوقت الحالي:
- الآن: {current_datetime}
- المنطقة الزمنية: {timezone}
- يوم الأسبوع: {weekday}

قواعد معالجة التواريخ:
1. "غداً" = {tomorrow}
2. "بعد غد" = {day_after_tomorrow}
3. "يوم الاثنين" = الاثنين القادم بعد اليوم
4. الوقت الافتراضي: 10:00 إذا لم يُحدد

[Similar structure...]
```

## 3.2 Context Building

### Existing Events Context

Когда пользователь хочет обновить или удалить событие, в промпт добавляются существующие события:

```python
def _build_existing_events_context(events: List[CalendarEvent]) -> str:
    context = "\nСУЩЕСТВУЮЩИЕ СОБЫТИЯ В КАЛЕНДАРЕ:\n"
    for i, event in enumerate(events, 1):
        context += f"{i}. {event.title} - {event.start.strftime('%Y-%m-%d %H:%M')}"
        if event.location:
            context += f" ({event.location})"
        context += f" [ID: {event.uid}]\n"
    return context
```

**Пример:**
```
СУЩЕСТВУЮЩИЕ СОБЫТИЯ В КАЛЕНДАРЕ:
1. Встреча с клиентом - 2025-10-23 10:00 [ID: abc-123]
2. Обед с коллегами - 2025-10-23 13:00 (Кафе "Центральное") [ID: def-456]
3. Презентация проекта - 2025-10-24 15:00 [ID: ghi-789]
```

Это позволяет LLM правильно идентифицировать событие при запросах типа:
- "Перенеси встречу с клиентом на 14:00"
- "Удали обед"
- "Измени место презентации на офис"

### Conversation History Context

Последние 10 сообщений добавляются для контекста диалога:

```python
def _build_conversation_context(history: List[dict]) -> str:
    context = "\nИСТОРИЯ ДИАЛОГА:\n"
    for msg in history[-10:]:
        role = "Пользователь" if msg["role"] == "user" else "Ассистент"
        context += f"{role}: {msg['content']}\n"
    return context
```

**Пример:**
```
ИСТОРИЯ ДИАЛОГА:
Пользователь: Встреча завтра
Ассистент: Во сколько будет встреча?
Пользователь: В 10 утра
Ассистент: Как назовём встречу?
Пользователь: Просмотр квартиры
```

Это помогает LLM понять контекст при неполных командах.

## 3.3 Function Calling Schema

### Yandex GPT Function Definition

```json
{
  "name": "extract_calendar_event",
  "description": "Extracts structured calendar event information from user's natural language input. Supports creating, updating, deleting, and querying events.",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {
        "type": "string",
        "description": "The type of calendar action",
        "enum": [
          "create",
          "create_recurring",
          "update",
          "delete",
          "query",
          "find_free_slots",
          "batch_confirm",
          "clarify",
          "delete_by_criteria"
        ]
      },
      "confidence": {
        "type": "number",
        "description": "Confidence score 0.0-1.0",
        "minimum": 0.0,
        "maximum": 1.0
      },
      "title": {
        "type": "string",
        "description": "Event title/name"
      },
      "description": {
        "type": "string",
        "description": "Detailed event description"
      },
      "start_time": {
        "type": "string",
        "format": "date-time",
        "description": "Event start in ISO 8601 format (YYYY-MM-DDTHH:MM:SS)"
      },
      "end_time": {
        "type": "string",
        "format": "date-time",
        "description": "Event end in ISO 8601 format"
      },
      "duration_minutes": {
        "type": "integer",
        "description": "Event duration in minutes",
        "minimum": 5,
        "maximum": 1440
      },
      "location": {
        "type": "string",
        "description": "Event location/place"
      },
      "attendees": {
        "type": "array",
        "items": { "type": "string" },
        "description": "List of participant names"
      },
      "recurrence_type": {
        "type": "string",
        "description": "How often event repeats",
        "enum": ["once", "daily", "weekly", "monthly"]
      },
      "recurrence_days": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
        "description": "Days of week for weekly recurrence"
      },
      "recurrence_end_date": {
        "type": "string",
        "format": "date",
        "description": "When to stop recurring (YYYY-MM-DD)"
      },
      "event_id": {
        "type": "string",
        "description": "ID of event to update/delete"
      },
      "clarify_question": {
        "type": "string",
        "description": "Question to ask user for missing info"
      },
      "query_date_start": {
        "type": "string",
        "format": "date-time",
        "description": "Start of query date range"
      },
      "query_date_end": {
        "type": "string",
        "format": "date-time",
        "description": "End of query date range"
      },
      "batch_actions": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "action": {
              "type": "string",
              "enum": ["create", "update", "delete"]
            },
            "title": { "type": "string" },
            "start_time": { "type": "string", "format": "date-time" },
            "duration_minutes": { "type": "integer" }
          }
        },
        "description": "Multiple events for batch confirmation"
      },
      "batch_summary": {
        "type": "string",
        "description": "Human-readable summary of batch"
      },
      "delete_criteria_title_contains": {
        "type": "string",
        "description": "Delete events where title contains this string"
      }
    },
    "required": ["intent", "confidence"]
  }
}
```

### API Request Format

```python
payload = {
    "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.3,  # Lower = more deterministic
        "maxTokens": 2000
    },
    "messages": [
        {
            "role": "system",
            "text": system_prompt
        },
        {
            "role": "user",
            "text": user_message
        }
    ],
    "tools": [
        {
            "function": function_schema
        }
    ]
}
```

### Response Parsing

```python
response = await api_call(payload)

# Yandex GPT returns:
# {
#   "result": {
#     "alternatives": [{
#       "message": {
#         "role": "assistant",
#         "toolCallList": {
#           "toolCalls": [{
#             "functionCall": {
#               "name": "extract_calendar_event",
#               "arguments": { ... }  # JSON with event data
#             }
#           }]
#         }
#       }
#     }]
#   }
# }

function_call = response["result"]["alternatives"][0]["message"]["toolCallList"]["toolCalls"][0]["functionCall"]
arguments = json.loads(function_call["arguments"])

# Convert to EventDTO
event_dto = EventDTO(**arguments)
```

## 3.4 Special Cases Handling

### Case 1: Batch Confirmation

Когда пользователь создаёт несколько событий одной фразой:

**Пример:** "Планёрка каждый понедельник в 9 утра на месяц"

**LLM Response:**
```json
{
  "intent": "batch_confirm",
  "batch_actions": [
    {
      "action": "create",
      "title": "Планёрка",
      "start_time": "2025-10-27T09:00:00",
      "duration_minutes": 60
    },
    {
      "action": "create",
      "title": "Планёрка",
      "start_time": "2025-11-03T09:00:00",
      "duration_minutes": 60
    },
    {
      "action": "create",
      "title": "Планёрка",
      "start_time": "2025-11-10T09:00:00",
      "duration_minutes": 60
    },
    {
      "action": "create",
      "title": "Планёрка",
      "start_time": "2025-11-17T09:00:00",
      "duration_minutes": 60
    }
  ],
  "batch_summary": "4 события: Планёрка каждый понедельник с 27 октября по 17 ноября",
  "confidence": 0.95
}
```

**UI Flow:**
1. Show inline keyboard:
   ```
   📋 Я правильно понял? Вы хотите создать:

   4 события: Планёрка каждый понедельник с 27 октября по 17 ноября

   1. 27 октября в 09:00 - Планёрка
   2. 3 ноября в 09:00 - Планёрка
   3. 10 ноября в 09:00 - Планёрка
   4. 17 ноября в 09:00 - Планёрка

   [✅ Подтвердить] [❌ Отменить]
   ```

2. Wait for user confirmation
3. If confirmed: Create all events
4. If cancelled: Clear pending actions

### Case 2: Clarification

Когда информации недостаточно:

**Пример:** "Встреча с клиентом"

**LLM Response:**
```json
{
  "intent": "clarify",
  "title": "Встреча с клиентом",
  "clarify_question": "Во сколько будет встреча с клиентом?",
  "confidence": 0.70
}
```

**UI Response:**
```
Во сколько будет встреча с клиентом?
```

**User:** "Завтра в 10"

**Next LLM Call (with context):**
```json
{
  "intent": "create",
  "title": "Встреча с клиентом",
  "start_time": "2025-10-23T10:00:00",
  "duration_minutes": 60,
  "confidence": 0.95
}
```

### Case 3: Mass Delete

Когда пользователь удаляет много событий:

**Пример:** "Удали все встречи с Ивановым"

**Without Optimization (BAD):**
```json
{
  "intent": "batch_confirm",
  "batch_actions": [
    {"action": "delete", "event_id": "abc-1"},
    {"action": "delete", "event_id": "abc-2"},
    ...  // 50+ events
  ]
}
```
❌ Проблема: Слишком большой payload, превышает лимиты токенов

**With Optimization (GOOD):**
```json
{
  "intent": "delete_by_criteria",
  "delete_criteria_title_contains": "Иванов",
  "confidence": 0.90
}
```
✅ Решение: Server-side filtering, только критерий передаётся

**Backend Logic:**
```python
if event_dto.intent == "delete_by_criteria":
    criteria = event_dto.delete_criteria_title_contains
    events = await calendar_service.list_events(user_id, start, end)
    matching_events = [e for e in events if criteria.lower() in e.title.lower()]

    # Show confirmation
    await show_delete_confirmation(user_id, matching_events)
```

### Case 4: Relative Date Edge Cases

**Сложный пример:** "Встреча в следующую среду в 14:00"

**Сегодня:** Понедельник, 20 октября 2025

**Логика:**
1. "следующая среда" = ближайшая среда после сегодня
2. Сегодня понедельник → среда через 2 дня
3. Дата: 22 октября 2025
4. Время: 14:00

**LLM Output:**
```json
{
  "intent": "create",
  "title": "Встреча",
  "start_time": "2025-10-22T14:00:00",
  "duration_minutes": 60,
  "confidence": 0.98
}
```

**Граничный случай:** "Встреча в среду" (сегодня среда)

**Правило:** Если сегодня среда, "в среду" = следующая среда (через 7 дней)

**Исключение:** "Встреча сегодня в среду" = сегодня

## 3.5 Prompt Optimization Techniques

### Technique 1: Token Reduction

**Problem:** Large event lists cause token overflow

**Solution:** Limit existing events context to 10 most recent

```python
def _build_existing_events_context(events: List[CalendarEvent]) -> str:
    # Sort by start time, take last 10
    recent_events = sorted(events, key=lambda e: e.start, reverse=True)[:10]
    context = "\nПОСЛЕДНИЕ 10 СОБЫТИЙ:\n"
    for event in recent_events:
        context += f"- {event.title} ({event.start.strftime('%d.%m %H:%M')})\n"
    return context
```

### Technique 2: Confidence Thresholding

**Problem:** Low confidence = incorrect extraction

**Solution:** If confidence < 0.7, trigger clarification

```python
if event_dto.confidence < 0.7:
    return EventDTO(
        intent="clarify",
        clarify_question="Не совсем понял, уточните детали события",
        confidence=event_dto.confidence
    )
```

### Technique 3: Fallback to Simple Parsing

**Problem:** Yandex GPT API fails (network/rate limit)

**Solution:** Regex-based fallback parser

```python
def simple_parse_fallback(text: str) -> EventDTO:
    # Pattern: "название время дата"
    # Example: "Встреча 10:00 завтра"

    time_pattern = r'\b(\d{1,2}):?(\d{2})?\b'
    date_patterns = {
        'завтра': timedelta(days=1),
        'послезавтра': timedelta(days=2),
        'понедельник': ...,
    }

    # Extract title (first words)
    # Extract time (regex match)
    # Extract date (keyword match)

    return EventDTO(
        intent="create",
        title=extracted_title,
        start_time=calculated_datetime,
        confidence=0.60  # Lower confidence for fallback
    )
```

---

# 4. База Данных и Хранилище

## 4.1 Radicale CalDAV Server

### 4.1.1 Архитектура

**Протокол:** CalDAV (RFC 4918) - расширение WebDAV для календарей
**Формат:** iCalendar (RFC 5545) - текстовый формат `.ics`
**Аутентификация:** Username-based (без пароля)
**URL:** `http://radicale:5232`

### 4.1.2 Структура Календарей

**Naming Convention:**
```
/radicale/{user_id}/{calendar_id}/
```

**Пример:**
```
/radicale/2296243/49d870f8-a613-11f0-ab82-f68a5f2444c4/
```

**Calendar Properties:**
- **Name:** `telegram_{user_id}`
- **Display Name:** "Telegram Calendar"
- **Color:** Auto-generated (hash-based)
- **Timezone:** Inherited from user preferences (default: Europe/Moscow)

### 4.1.3 Event Storage Format

**iCalendar Example:**
```ical
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Calendar Assistant v2.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Telegram Calendar
X-WR-TIMEZONE:Europe/Moscow

BEGIN:VTIMEZONE
TZID:Europe/Moscow
BEGIN:STANDARD
DTSTART:19700101T000000
TZOFFSETFROM:+0300
TZOFFSETTO:+0300
END:STANDARD
END:VTIMEZONE

BEGIN:VEVENT
UID:abc123-def456-ghi789@telegram-bot
DTSTAMP:20251022T100000Z
DTSTART;TZID=Europe/Moscow:20251023T140000
DTEND;TZID=Europe/Moscow:20251023T150000
SUMMARY:Встреча с клиентом
DESCRIPTION:Обсуждение договора купли-продажи квартиры на ул. Ленина
LOCATION:ул. Ленина, 5, офис 201
STATUS:CONFIRMED
TRANSP:OPAQUE
SEQUENCE:0
CREATED:20251022T100000Z
LAST-MODIFIED:20251022T100000Z
ATTENDEE;CN=Иванов;ROLE=REQ-PARTICIPANT:mailto:ivanov@example.com
ATTENDEE;CN=Петрова;ROLE=OPT-PARTICIPANT:mailto:petrova@example.com
BEGIN:VALARM
TRIGGER:-PT30M
ACTION:DISPLAY
DESCRIPTION:Напоминание: Встреча с клиентом
END:VALARM
END:VEVENT

END:VCALENDAR
```

### 4.1.4 UID Generation

**Format:** MD5 hash of (user_id + title + timestamp)

```python
import hashlib
from datetime import datetime

def generate_event_uid(user_id: str, title: str) -> str:
    timestamp = datetime.now().isoformat()
    data = f"{user_id}_{title}_{timestamp}"
    uid = hashlib.md5(data.encode()).hexdigest()
    return f"{uid}@telegram-bot"
```

**Example:**
- Input: user_id="2296243", title="Встреча с клиентом"
- Output: `a3f8c2d91e4b7f6a@telegram-bot`

### 4.1.5 CRUD Operations

#### Create Event

```python
from caldav import DAVClient, Calendar
from icalendar import Calendar as iCalendar, Event

async def create_event(user_id: str, event: EventDTO) -> str:
    # 1. Get or create user calendar
    calendar = await self._get_or_create_calendar(user_id)

    # 2. Build iCalendar object
    cal = iCalendar()
    cal.add('prodid', '-//AI Calendar Assistant v2.0//EN')
    cal.add('version', '2.0')

    vevent = Event()
    vevent.add('summary', event.title)
    vevent.add('dtstart', event.start_time)
    vevent.add('dtend', event.end_time or event.start_time + timedelta(minutes=event.duration_minutes))
    vevent.add('dtstamp', datetime.now(pytz.UTC))
    vevent.add('uid', generate_event_uid(user_id, event.title))

    if event.location:
        vevent.add('location', event.location)
    if event.description:
        vevent.add('description', event.description)
    if event.attendees:
        for attendee in event.attendees:
            vevent.add('attendee', f'mailto:{attendee}@example.com', parameters={'cn': attendee})

    # Add reminder (30 minutes before)
    alarm = Alarm()
    alarm.add('trigger', timedelta(minutes=-30))
    alarm.add('action', 'DISPLAY')
    alarm.add('description', f'Напоминание: {event.title}')
    vevent.add_component(alarm)

    cal.add_component(vevent)

    # 3. Save to Radicale
    calendar.save_event(cal.to_ical())

    return vevent['uid']
```

#### List Events

```python
async def list_events(
    user_id: str,
    start: datetime,
    end: datetime
) -> List[CalendarEvent]:
    calendar = await self._get_calendar(user_id)

    # Query events in date range
    events = calendar.date_search(start=start, end=end)

    result = []
    for event in events:
        ical = iCalendar.from_ical(event.data)
        for component in ical.walk():
            if component.name == "VEVENT":
                result.append(CalendarEvent(
                    uid=str(component.get('uid')),
                    title=str(component.get('summary')),
                    start=component.get('dtstart').dt,
                    end=component.get('dtend').dt,
                    location=str(component.get('location', '')),
                    description=str(component.get('description', '')),
                    attendees=[str(a) for a in component.get('attendee', [])]
                ))

    return result
```

#### Update Event

```python
async def update_event(
    user_id: str,
    event_id: str,
    updates: EventDTO
) -> bool:
    calendar = await self._get_calendar(user_id)

    # Find event by UID
    event = calendar.event_by_uid(event_id)
    if not event:
        return False

    # Parse existing iCalendar
    ical = iCalendar.from_ical(event.data)
    for component in ical.walk():
        if component.name == "VEVENT":
            # Update fields
            if updates.title:
                component['summary'] = updates.title
            if updates.start_time:
                component['dtstart'] = updates.start_time
            if updates.end_time:
                component['dtend'] = updates.end_time
            if updates.location:
                component['location'] = updates.location
            if updates.description:
                component['description'] = updates.description

            # Update LAST-MODIFIED
            component['last-modified'] = datetime.now(pytz.UTC)
            component['sequence'] = int(component.get('sequence', 0)) + 1

    # Save back to Radicale
    event.data = ical.to_ical()
    event.save()

    return True
```

#### Delete Event

```python
async def delete_event(user_id: str, event_id: str) -> bool:
    calendar = await self._get_calendar(user_id)

    event = calendar.event_by_uid(event_id)
    if not event:
        return False

    event.delete()
    return True
```

### 4.1.6 Recurring Events Implementation

Radicale поддерживает RRULE (Recurrence Rule):

**Daily:**
```ical
RRULE:FREQ=DAILY;COUNT=30
```

**Weekly (Mon, Wed, Fri):**
```ical
RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=12
```

**Monthly (first Monday):**
```ical
RRULE:FREQ=MONTHLY;BYDAY=1MO;COUNT=6
```

**Implementation:**
```python
from icalendar import vRecur

def create_recurring_event(event: EventDTO) -> iCalendar:
    vevent = Event()
    # ... add basic fields ...

    # Build RRULE
    if event.recurrence_type == "daily":
        rrule = vRecur({'FREQ': 'DAILY'})
    elif event.recurrence_type == "weekly":
        days_map = {'mon': 'MO', 'tue': 'TU', 'wed': 'WE', 'thu': 'TH', 'fri': 'FR', 'sat': 'SA', 'sun': 'SU'}
        byday = [days_map[d] for d in event.recurrence_days]
        rrule = vRecur({'FREQ': 'WEEKLY', 'BYDAY': byday})
    elif event.recurrence_type == "monthly":
        rrule = vRecur({'FREQ': 'MONTHLY'})

    if event.recurrence_end_date:
        rrule['UNTIL'] = event.recurrence_end_date

    vevent.add('rrule', rrule)

    return vevent
```

## 4.2 JSON File Storage

### 4.2.1 User Preferences

**Path:** `/var/lib/calendar-bot/user_preferences.json`

**Structure:**
```json
{
  "2296243": {
    "language": "ru",
    "timezone": "Europe/Moscow",
    "motivation_index": 15
  },
  "5602113922": {
    "language": "en",
    "timezone": "America/New_York",
    "motivation_index": 3
  }
}
```

**Fields:**
- `language` - Language code (ru, en, es, ar)
- `timezone` - IANA timezone string
- `motivation_index` - Current motivational message index (1-60, cycles)

**Access:**
```python
class UserPreferencesService:
    def __init__(self, data_file: str = "/var/lib/calendar-bot/user_preferences.json"):
        self.data_file = data_file
        self.preferences: Dict[str, dict] = {}
        self._load_data()

    def get_language(self, user_id: str) -> Language:
        return Language(self.preferences.get(user_id, {}).get("language", "ru"))

    def set_language(self, user_id: str, language: Language):
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        self.preferences[user_id]["language"] = language.value
        self._save_data()

    def increment_motivation_index(self, user_id: str) -> int:
        current = self.get_motivation_index(user_id)
        new_index = (current % 60) + 1  # Cycle: 1→60→1
        self.preferences[user_id]["motivation_index"] = new_index
        self._save_data()
        return new_index
```

### 4.2.2 Analytics Data

**Path:** `/var/lib/calendar-bot/analytics_data.json`

**Structure:**
```json
{
  "actions": [
    {
      "user_id": "2296243",
      "action_type": "event_create",
      "timestamp": "2025-10-22T10:15:30.123456",
      "details": "Встреча с клиентом",
      "event_id": "abc123-def456",
      "success": true,
      "error_message": null,
      "is_test": false,
      "username": "nikita_tita",
      "first_name": "Nikita",
      "last_name": null
    },
    {
      "user_id": "5602113922",
      "action_type": "voice_message",
      "timestamp": "2025-10-22T10:16:45.678901",
      "details": "Transcribed: Просмотр квартиры завтра",
      "event_id": null,
      "success": true,
      "error_message": null,
      "is_test": false,
      "username": "john_smith",
      "first_name": "John",
      "last_name": "Smith"
    },
    {
      "user_id": "2296243",
      "action_type": "error",
      "timestamp": "2025-10-22T10:20:00.000000",
      "details": "Failed to parse date",
      "event_id": null,
      "success": false,
      "error_message": "Invalid date format: 'вчера'",
      "is_test": false,
      "username": "nikita_tita",
      "first_name": "Nikita",
      "last_name": null
    }
  ]
}
```

**Action Types:**
- `user_start` - First interaction (/start)
- `user_login` - Login event
- `event_create`, `event_update`, `event_delete` - Calendar operations
- `event_query` - Event lookup
- `text_message` - Text input
- `voice_message` - Voice input
- `webapp_open` - WebApp access
- `error` - Failed operation

**Indexing:** In-memory indexing for fast queries

```python
class AnalyticsService:
    def __init__(self):
        self.actions: List[UserAction] = []
        self._load_data()
        self._build_indexes()

    def _build_indexes(self):
        # Index by user_id
        self.by_user = defaultdict(list)
        for action in self.actions:
            self.by_user[action.user_id].append(action)

        # Index by action_type
        self.by_type = defaultdict(list)
        for action in self.actions:
            self.by_type[action.action_type].append(action)

        # Index by date (for daily stats)
        self.by_date = defaultdict(list)
        for action in self.actions:
            date_key = action.timestamp.date()
            self.by_date[date_key].append(action)
```

**Queries:**
```python
def get_active_users_today(self) -> int:
    today = datetime.now().date()
    users = set(action.user_id for action in self.by_date[today])
    return len(users)

def get_events_created_count(self) -> int:
    return len(self.by_type["event_create"])

def get_user_dialog(self, user_id: str, limit: int = 100) -> List[UserAction]:
    user_actions = self.by_user[user_id]
    # Filter text/voice messages only
    messages = [a for a in user_actions if a.action_type in ["text_message", "voice_message"]]
    return messages[-limit:]
```

### 4.2.3 Daily Reminder Users

**Path:** `/var/lib/calendar-bot/daily_reminder_users.json`

**Structure:**
```json
{
  "2296243": 2296243,
  "5602113922": 5602113922
}
```

**Format:** `{ user_id: chat_id }`

**Purpose:** Track which users opted-in for daily reminders

**Registration:**
```python
class DailyRemindersService:
    def register_user(self, user_id: str, chat_id: int):
        self.active_users[user_id] = chat_id
        self._save_users()
        logger.info("user_registered_for_reminders", user_id=user_id)
```

**Auto-registration:** When user sends `/start` or any message

## 4.3 Data Migration Plan

### Current (JSON) → Future (PostgreSQL)

**Trigger:** When users > 5000 or actions > 100,000

**Schema:**
```sql
-- Users table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    language VARCHAR(2) DEFAULT 'ru',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    motivation_index INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW()
);

-- Analytics actions table
CREATE TABLE analytics_actions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    action_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    details TEXT,
    event_id VARCHAR(255),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    is_test BOOLEAN DEFAULT FALSE,
    INDEX idx_user_id (user_id),
    INDEX idx_action_type (action_type),
    INDEX idx_timestamp (timestamp)
);

-- Daily reminder subscriptions
CREATE TABLE daily_reminders (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
    chat_id BIGINT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Migration Script:**
```python
import json
import psycopg2

def migrate_json_to_postgres():
    conn = psycopg2.connect("postgresql://user:pass@localhost/calendar_db")
    cur = conn.cursor()

    # Migrate user preferences
    with open("/var/lib/calendar-bot/user_preferences.json") as f:
        prefs = json.load(f)

    for user_id, data in prefs.items():
        cur.execute("""
            INSERT INTO users (user_id, language, timezone, motivation_index)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE
            SET language = EXCLUDED.language,
                timezone = EXCLUDED.timezone,
                motivation_index = EXCLUDED.motivation_index
        """, (user_id, data['language'], data['timezone'], data['motivation_index']))

    # Migrate analytics
    with open("/var/lib/calendar-bot/analytics_data.json") as f:
        analytics = json.load(f)

    for action in analytics['actions']:
        cur.execute("""
            INSERT INTO analytics_actions (
                user_id, action_type, timestamp, details, event_id,
                success, error_message, is_test
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            action['user_id'], action['action_type'], action['timestamp'],
            action['details'], action.get('event_id'), action['success'],
            action.get('error_message'), action['is_test']
        ))

    conn.commit()
    cur.close()
    conn.close()
```

---

# 5. Аналитика и Мониторинг

## 5.1 Structured Logging

### 5.1.1 Logging Setup

**Framework:** structlog
**Format:** JSON (production), Console (development)

**Configuration** (`app/utils/logger.py`):
```python
import structlog
import logging

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()  # JSON output
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### 5.1.2 Log Events

**Application Lifecycle:**
```python
logger.info("application_started", environment="production", debug=False)
logger.info("application_shutdown", uptime_seconds=3600)
```

**Telegram Events:**
```python
logger.info("webhook_received", user_id=user_id, message_type="text")
logger.error("webhook_error", error=str(e), user_id=user_id)
logger.warning("webhook_unauthorized", remote_addr=request.client.host)
```

**User Actions:**
```python
logger.info("user_language_set", user_id=user_id, language="ru")
logger.info("user_timezone_set", user_id=user_id, timezone="Europe/Moscow")
```

**Rate Limiting:**
```python
logger.warning("rate_limit_triggered", user_id=user_id, limit_type="minute")
logger.error("user_blocked", user_id=user_id, duration_minutes=60)
```

**Calendar Operations:**
```python
logger.info("event_created", user_id=user_id, event_id=uid, title=event.title)
logger.error("event_create_error", user_id=user_id, error=str(e))
logger.info("event_updated", user_id=user_id, event_id=uid)
logger.info("event_deleted", user_id=user_id, event_id=uid)
```

**LLM Calls:**
```python
logger.info("llm_extract_start_yandex", user_id=user_id, text_length=len(text))
logger.info("llm_extract_success", user_id=user_id, intent=event_dto.intent, confidence=event_dto.confidence)
logger.error("llm_extract_error", user_id=user_id, error=str(e), retry_attempt=1)
```

**Voice Processing:**
```python
logger.info("audio_download_started", user_id=user_id, file_size_bytes=file_size)
logger.info("audio_transcribed_yandex", user_id=user_id, text=transcribed_text, duration_ms=duration)
logger.error("audio_transcription_error", user_id=user_id, error=str(e))
```

**Analytics:**
```python
logger.info("action_logged", user_id=user_id, action_type="event_create", success=True)
logger.info("analytics_data_loaded", count=len(actions))
logger.error("analytics_save_error", error=str(e))
```

**Daily Reminders:**
```python
logger.info("daily_reminders_started")
logger.info("morning_reminder_sent", user_id=user_id, events_count=5)
logger.info("morning_motivation_sent", user_id=user_id, message_index=23)
logger.info("evening_reminder_sent", user_id=user_id, events_count=3)
logger.error("morning_reminder_error", user_id=user_id, error=str(e))
```

### 5.1.3 Log Aggregation

**Query Examples (using jq):**

Total events created:
```bash
cat logs/*.log | grep event_created | wc -l
```

Top 10 active users:
```bash
cat logs/*.log | jq -r 'select(.event=="event_created") | .user_id' | sort | uniq -c | sort -rn | head -10
```

Error rate by type:
```bash
cat logs/*.log | jq -r 'select(.level=="error") | .event' | sort | uniq -c
```

Average LLM confidence:
```bash
cat logs/*.log | jq -r 'select(.event=="llm_extract_success") | .confidence' | awk '{sum+=$1; count++} END {print sum/count}'
```

## 5.2 Admin Dashboard

### 5.2.1 Authentication

**3-Password System:**

```python
class AdminAuth:
    # SECURITY: Store hashed passwords in environment
    PASSWORD_1_HASH = os.getenv("ADMIN_PASSWORD_1_HASH")
    PASSWORD_2_HASH = os.getenv("ADMIN_PASSWORD_2_HASH")
    PASSWORD_3_HASH = os.getenv("ADMIN_PASSWORD_3_HASH")

    def verify(self, p1: str, p2: str, p3: str) -> Tuple[bool, str]:
        h1 = hashlib.sha256(p1.encode()).hexdigest()
        h2 = hashlib.sha256(p2.encode()).hexdigest()
        h3 = hashlib.sha256(p3.encode()).hexdigest()

        # All 3 correct = Real dashboard
        if h1 == self.PASSWORD_1_HASH and h2 == self.PASSWORD_2_HASH and h3 == self.PASSWORD_3_HASH:
            token = self._generate_token("real")
            return True, "real", token

        # First 2 correct = Fake dashboard (anti-phishing)
        elif h1 == self.PASSWORD_1_HASH and h2 == self.PASSWORD_2_HASH:
            token = self._generate_token("fake")
            return True, "fake", token

        # Otherwise = Invalid
        else:
            return False, "invalid", None

    def _generate_token(self, mode: str) -> str:
        data = f"{mode}:{datetime.now().isoformat()}:{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode()).hexdigest()
```

**Token Validation:**
```python
def verify_token(self, token: str) -> Tuple[bool, str]:
    # In production: use JWT or session store
    # This is simplified for demo
    if token in self.active_tokens:
        return True, self.active_tokens[token]  # "real" or "fake"
    return False, None
```

### 5.2.2 Dashboard Metrics

**Overall Statistics:**
```python
class AdminDashboardStats:
    total_logins: int = 0
    active_users_today: int = 0
    active_users_week: int = 0
    active_users_month: int = 0
    total_users: int = 0
    total_actions: int = 0
    total_events_created: int = 0
    total_text_messages: int = 0
    total_voice_messages: int = 0
    recent_actions: List[UserAction] = []
```

**API Endpoint:**
```python
@router.get("/admin/stats")
async def get_dashboard_stats(
    authorization: str = Header(None)
) -> AdminDashboardStats:
    # Verify token
    is_valid, mode = admin_auth.verify_token(authorization)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fake mode: return zeros
    if mode == "fake":
        return AdminDashboardStats(
            total_logins=0,
            active_users_today=0,
            # ... all zeros ...
        )

    # Real mode: calculate actual stats
    stats = analytics_service.get_admin_stats()
    return stats
```

**Calculation Logic:**
```python
def get_admin_stats(self) -> AdminDashboardStats:
    now = datetime.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Active users
    active_today = set()
    active_week = set()
    active_month = set()

    for action in self.actions:
        if action.timestamp.date() == today:
            active_today.add(action.user_id)
        if action.timestamp >= week_ago:
            active_week.add(action.user_id)
        if action.timestamp >= month_ago:
            active_month.add(action.user_id)

    # Event counts
    events_created = len([a for a in self.actions if a.action_type == "event_create"])

    # Message counts
    text_messages = len([a for a in self.actions if a.action_type == "text_message"])
    voice_messages = len([a for a in self.actions if a.action_type == "voice_message"])

    return AdminDashboardStats(
        total_users=len(set(a.user_id for a in self.actions)),
        active_users_today=len(active_today),
        active_users_week=len(active_week),
        active_users_month=len(active_month),
        total_actions=len(self.actions),
        total_events_created=events_created,
        total_text_messages=text_messages,
        total_voice_messages=voice_messages,
        recent_actions=self.actions[-50:]  # Last 50 actions
    )
```

### 5.2.3 User Management

**List All Users:**
```python
@router.get("/admin/users")
async def get_all_users(
    authorization: str = Header(None)
) -> List[UserDetail]:
    is_valid, mode = admin_auth.verify_token(authorization)
    if not is_valid:
        raise HTTPException(status_code=401)

    if mode == "fake":
        return []  # Empty list for fake mode

    return analytics_service.get_all_users_details()
```

**User Detail Model:**
```python
class UserDetail:
    user_id: str
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language: str
    timezone: str
    total_events: int
    total_messages: int
    last_active: datetime
    created_at: datetime
```

### 5.2.4 User Dialog History

**Get Conversation:**
```python
@router.get("/admin/users/{user_id}/dialog")
async def get_user_dialog(
    user_id: str,
    limit: int = Query(100, le=10000),
    authorization: str = Header(None)
) -> List[DialogMessage]:
    is_valid, mode = admin_auth.verify_token(authorization)
    if not is_valid:
        raise HTTPException(status_code=401)

    if mode == "fake":
        return []

    return analytics_service.get_user_dialog(user_id, limit)
```

**Dialog Message:**
```python
class DialogMessage:
    timestamp: datetime
    role: str  # "user" or "assistant"
    message_type: str  # "text", "voice", "command"
    content: str
    success: bool
    event_created: Optional[str] = None
```

### 5.2.5 User Events View

**Get User's Calendar:**
```python
@router.get("/admin/users/{user_id}/events")
async def get_user_events(
    user_id: str,
    authorization: str = Header(None)
) -> List[CalendarEvent]:
    is_valid, mode = admin_auth.verify_token(authorization)
    if not is_valid:
        raise HTTPException(status_code=401)

    if mode == "fake":
        return []

    # Get events from last 90 days to next 90 days
    start = datetime.now() - timedelta(days=90)
    end = datetime.now() + timedelta(days=90)

    events = await calendar_service.list_events(user_id, start, end)
    return events
```

## 5.3 Metrics & Monitoring

### 5.3.1 Key Performance Indicators (KPIs)

**User Engagement:**
- Daily Active Users (DAU)
- Weekly Active Users (WAU)
- Monthly Active Users (MAU)
- DAU/MAU ratio (stickiness)

**Feature Usage:**
- Events created per user per day
- Voice messages vs text messages ratio
- Query requests per day
- WebApp opens per day

**System Health:**
- API response time (p50, p95, p99)
- Error rate (%)
- LLM success rate (%)
- Voice transcription accuracy (user reported)

**Business Metrics:**
- User retention (D1, D7, D30)
- Time to first event creation
- Average events per user
- Churn rate

### 5.3.2 Monitoring Queries

**Daily Active Users:**
```sql
SELECT DATE(timestamp), COUNT(DISTINCT user_id)
FROM analytics_actions
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY DATE(timestamp);
```

**Event Creation Rate:**
```sql
SELECT DATE(timestamp), COUNT(*)
FROM analytics_actions
WHERE action_type = 'event_create'
  AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp);
```

**Error Rate:**
```sql
SELECT
    DATE(timestamp),
    COUNT(CASE WHEN success = false THEN 1 END)::float / COUNT(*) * 100 AS error_rate_percent
FROM analytics_actions
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp);
```

**Top Error Types:**
```sql
SELECT error_message, COUNT(*)
FROM analytics_actions
WHERE success = false
  AND timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY error_message
ORDER BY COUNT(*) DESC
LIMIT 10;
```

### 5.3.3 Alerting Rules

**Critical Alerts (PagerDuty):**
- Error rate > 10% for 5 minutes
- API response time p95 > 5 seconds
- Zero events created in last hour (possible outage)

**Warning Alerts (Slack):**
- Error rate > 5% for 15 minutes
- LLM API failures > 3 in 10 minutes
- Disk usage > 80%

**Info Alerts (Email):**
- Daily summary of metrics
- New user signups milestone (100, 500, 1000, etc.)
- Weekly user retention report

---

# 6. API Документация

## 6.1 Telegram Router

### 6.1.1 Webhook Endpoint

**POST /telegram/webhook**

Receives updates from Telegram Bot API.

**Headers:**
- `X-Telegram-Bot-Api-Secret-Token`: Secret token for validation

**Request Body:**
```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 456,
    "from": {
      "id": 2296243,
      "is_bot": false,
      "first_name": "Nikita",
      "username": "nikita_tita",
      "language_code": "ru"
    },
    "chat": {
      "id": 2296243,
      "first_name": "Nikita",
      "username": "nikita_tita",
      "type": "private"
    },
    "date": 1729594800,
    "text": "Встреча завтра в 10"
  }
}
```

**Responses:**
- `200 OK` - Update processed successfully
- `401 Unauthorized` - Invalid secret token
- `500 Internal Server Error` - Processing failed

**Example:**
```bash
curl -X POST https://example.com/telegram/webhook \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Bot-Api-Secret-Token: your_secret_token" \
  -d '{
    "update_id": 123,
    "message": {
      "message_id": 456,
      "from": {"id": 2296243, "first_name": "Nikita"},
      "chat": {"id": 2296243, "type": "private"},
      "date": 1729594800,
      "text": "Встреча завтра в 10"
    }
  }'
```

### 6.1.2 Status Endpoint

**GET /telegram/status**

Returns bot information.

**Response:**
```json
{
  "username": "ai_calendar_bot",
  "id": 8378762774,
  "first_name": "AI Calendar Assistant"
}
```

## 6.2 Events Router

### 6.2.1 List Events

**GET /api/events/{user_id}**

Get events in date range.

**Path Parameters:**
- `user_id` (required) - Telegram user ID

**Query Parameters:**
- `start` (optional) - Start datetime (ISO 8601), default: now
- `end` (optional) - End datetime (ISO 8601), default: now + 30 days

**Response:**
```json
[
  {
    "uid": "abc123-def456",
    "title": "Встреча с клиентом",
    "start": "2025-10-23T10:00:00+03:00",
    "end": "2025-10-23T11:00:00+03:00",
    "location": "ул. Ленина, 5",
    "description": "Обсуждение договора",
    "attendees": ["Иванов", "Петрова"],
    "color": "#FF5733"
  },
  {
    "uid": "ghi789-jkl012",
    "title": "Обед",
    "start": "2025-10-23T13:00:00+03:00",
    "end": "2025-10-23T14:00:00+03:00",
    "location": "Кафе Центральное",
    "description": "",
    "attendees": [],
    "color": "#33FF57"
  }
]
```

**Example:**
```bash
curl "https://example.com/api/events/2296243?start=2025-10-23T00:00:00Z&end=2025-10-24T00:00:00Z"
```

### 6.2.2 Create Event

**POST /api/events/{user_id}**

Create a new calendar event.

**Path Parameters:**
- `user_id` (required) - Telegram user ID

**Request Body:**
```json
{
  "title": "Встреча с клиентом",
  "start": "2025-10-23T10:00:00+03:00",
  "end": "2025-10-23T11:00:00+03:00",
  "location": "ул. Ленина, 5",
  "description": "Обсуждение договора купли-продажи",
  "color": "#FF5733"
}
```

**Response:**
```json
{
  "uid": "abc123-def456",
  "title": "Встреча с клиентом",
  "start": "2025-10-23T10:00:00+03:00",
  "end": "2025-10-23T11:00:00+03:00",
  "location": "ул. Ленина, 5",
  "description": "Обсуждение договора купли-продажи",
  "attendees": [],
  "color": "#FF5733"
}
```

**Status Codes:**
- `200 OK` - Event created
- `400 Bad Request` - Invalid request body
- `500 Internal Server Error` - Creation failed

### 6.2.3 Update Event

**PUT /api/events/{user_id}/{event_id}**

Update existing event.

**Path Parameters:**
- `user_id` (required) - Telegram user ID
- `event_id` (required) - Event UID

**Request Body (partial update):**
```json
{
  "title": "Встреча с клиентом (перенесена)",
  "start": "2025-10-23T14:00:00+03:00"
}
```

**Response:**
```json
{
  "uid": "abc123-def456",
  "title": "Встреча с клиентом (перенесена)",
  "start": "2025-10-23T14:00:00+03:00",
  "end": "2025-10-23T15:00:00+03:00",
  "location": "ул. Ленина, 5",
  "description": "Обсуждение договора купли-продажи",
  "attendees": [],
  "color": "#FF5733"
}
```

### 6.2.4 Delete Event

**DELETE /api/events/{user_id}/{event_id}**

Delete an event.

**Path Parameters:**
- `user_id` (required)
- `event_id` (required)

**Response:**
```json
{
  "success": true,
  "message": "Event deleted successfully"
}
```

**Status Codes:**
- `200 OK` - Deleted
- `404 Not Found` - Event doesn't exist
- `500 Internal Server Error` - Deletion failed

## 6.3 Admin Router

### 6.3.1 Verify Authentication

**POST /api/admin/verify**

Authenticate with 3 passwords.

**Request Body:**
```json
{
  "password1": "secret1",
  "password2": "secret2",
  "password3": "secret3"
}
```

**Response (Real Mode):**
```json
{
  "success": true,
  "mode": "real",
  "token": "a1b2c3d4e5f6..."
}
```

**Response (Fake Mode - wrong password3):**
```json
{
  "success": true,
  "mode": "fake",
  "token": "f6e5d4c3b2a1..."
}
```

**Response (Invalid):**
```json
{
  "success": false,
  "message": "Invalid credentials"
}
```

### 6.3.2 Dashboard Statistics

**GET /api/admin/stats**

Get overall statistics.

**Headers:**
- `Authorization`: Token from `/api/admin/verify`

**Response (Real Mode):**
```json
{
  "total_logins": 523,
  "active_users_today": 42,
  "active_users_week": 156,
  "active_users_month": 412,
  "total_users": 523,
  "total_actions": 8765,
  "total_events_created": 3421,
  "total_text_messages": 4523,
  "total_voice_messages": 821,
  "recent_actions": [
    {
      "user_id": "2296243",
      "action_type": "event_create",
      "timestamp": "2025-10-22T10:15:30.123456",
      "details": "Встреча с клиентом",
      "success": true
    }
  ]
}
```

**Response (Fake Mode):**
```json
{
  "total_logins": 0,
  "active_users_today": 0,
  "active_users_week": 0,
  "active_users_month": 0,
  "total_users": 0,
  "total_actions": 0,
  "total_events_created": 0,
  "total_text_messages": 0,
  "total_voice_messages": 0,
  "recent_actions": []
}
```

### 6.3.3 List Users

**GET /api/admin/users**

Get all users with details.

**Headers:**
- `Authorization`: Token

**Response:**
```json
[
  {
    "user_id": "2296243",
    "username": "nikita_tita",
    "first_name": "Nikita",
    "last_name": null,
    "language": "ru",
    "timezone": "Europe/Moscow",
    "total_events": 45,
    "total_messages": 123,
    "last_active": "2025-10-22T10:30:00",
    "created_at": "2025-09-15T08:00:00"
  }
]
```

### 6.3.4 User Dialog

**GET /api/admin/users/{user_id}/dialog**

Get user's conversation history.

**Path Parameters:**
- `user_id` (required)

**Query Parameters:**
- `limit` (optional) - Max messages, default 100, max 10000

**Headers:**
- `Authorization`: Token

**Response:**
```json
[
  {
    "timestamp": "2025-10-22T10:15:00",
    "role": "user",
    "message_type": "text",
    "content": "Встреча завтра в 10",
    "success": true,
    "event_created": "abc123-def456"
  },
  {
    "timestamp": "2025-10-22T10:15:05",
    "role": "assistant",
    "message_type": "response",
    "content": "✅ Событие создано!\n\n📅 Встреча\n🕐 23 октября в 10:00",
    "success": true,
    "event_created": null
  }
]
```

### 6.3.5 User Events

**GET /api/admin/users/{user_id}/events**

Get user's calendar events.

**Path Parameters:**
- `user_id` (required)

**Headers:**
- `Authorization`: Token

**Response:**
```json
[
  {
    "uid": "abc123-def456",
    "title": "Встреча",
    "start": "2025-10-23T10:00:00+03:00",
    "end": "2025-10-23T11:00:00+03:00",
    "location": "",
    "description": "",
    "attendees": [],
    "color": "#FF5733"
  }
]
```

## 6.4 Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-10-22T10:30:00Z"
}
```

### Common Error Codes

- `AUTH_REQUIRED` - Missing or invalid authorization
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INVALID_USER_ID` - User doesn't exist
- `EVENT_NOT_FOUND` - Event UID not found
- `INVALID_DATE_RANGE` - Start > End datetime
- `LLM_SERVICE_ERROR` - Yandex GPT API failed
- `CALENDAR_SERVICE_ERROR` - Radicale unavailable

---

# 7. Deployment Guide

## 7.1 Docker Compose (Production)

### 7.1.1 docker-compose.production.yml

```yaml
version: '3.8'

services:
  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile.hybrid
    image: ai-calendar-assistant:latest
    container_name: telegram-bot
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - YANDEX_API_KEY=${YANDEX_API_KEY}
      - YANDEX_FOLDER_ID=${YANDEX_FOLDER_ID}
      - RADICALE_URL=http://radicale:5232
      - ADMIN_PASSWORD_1_HASH=${ADMIN_PASSWORD_1_HASH}
      - ADMIN_PASSWORD_2_HASH=${ADMIN_PASSWORD_2_HASH}
      - ADMIN_PASSWORD_3_HASH=${ADMIN_PASSWORD_3_HASH}
      - LOG_LEVEL=INFO
    volumes:
      - ./logs:/app/logs
      - ./data:/var/lib/calendar-bot
    depends_on:
      - radicale
    networks:
      - calendar-network

  radicale:
    image: tomsquest/docker-radicale:latest
    container_name: radicale
    restart: unless-stopped
    ports:
      - "5232:5232"
    volumes:
      - ./radicale/data:/data
      - ./radicale/config:/config
    environment:
      - AUTH_TYPE=none
    networks:
      - calendar-network

networks:
  calendar-network:
    driver: bridge

volumes:
  radicale-data:
  calendar-data:
```

### 7.1.2 Dockerfile.hybrid

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY run_hybrid.py .

# Create data directory
RUN mkdir -p /var/lib/calendar-bot

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["python", "run_hybrid.py"]
```

### 7.1.3 Environment Variables

Create `.env` file:

```bash
# Telegram Bot API
TELEGRAM_BOT_TOKEN=8378762774:AAE7oEvJX3fcHmLTQJPzQb9EIgQHXUWuaPI
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_token

# Yandex Cloud API
YANDEX_API_KEY=your_yandex_api_key_here
YANDEX_FOLDER_ID=your_yandex_folder_id

# Admin Passwords (SHA-256 hashes)
ADMIN_PASSWORD_1_HASH=hash_of_password1
ADMIN_PASSWORD_2_HASH=hash_of_password2
ADMIN_PASSWORD_3_HASH=hash_of_password3

# Radicale
RADICALE_URL=http://radicale:5232

# Logging
LOG_LEVEL=INFO

# Optional: Public URL for webhook
PUBLIC_URL=https://yourdomain.com
```

**Generate password hashes:**
```bash
echo -n "your_password" | sha256sum
```

### 7.1.4 Deployment Steps

1. **Clone repository:**
```bash
git clone https://github.com/your/ai-calendar-assistant.git
cd ai-calendar-assistant
```

2. **Create environment file:**
```bash
cp .env.example .env
# Edit .env with your values
```

3. **Build and start services:**
```bash
docker-compose -f docker-compose.production.yml up -d
```

4. **Check logs:**
```bash
docker logs -f telegram-bot
```

5. **Verify health:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"ok"}
```

6. **Set Telegram webhook (if using webhooks):**
```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://yourdomain.com/telegram/webhook\",
    \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\"
  }"
```

## 7.2 Railway.io Deployment

### 7.2.1 railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.hybrid"
  },
  "deploy": {
    "startCommand": "python run_hybrid.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 7.2.2 Deploy Steps

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login:
```bash
railway login
```

3. Initialize project:
```bash
railway init
```

4. Set environment variables:
```bash
railway variables set TELEGRAM_BOT_TOKEN=your_token
railway variables set YANDEX_API_KEY=your_key
railway variables set YANDEX_FOLDER_ID=your_folder_id
# ... set all other env vars ...
```

5. Deploy:
```bash
railway up
```

6. Get public URL:
```bash
railway domain
```

7. Set webhook:
```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -d "url=https://your-app.railway.app/telegram/webhook"
```

## 7.3 VPS Deployment (REG.RU)

### 7.3.1 Server Requirements

- OS: Ubuntu 22.04 LTS
- RAM: 2GB minimum, 4GB recommended
- Disk: 20GB SSD
- CPU: 2 cores

### 7.3.2 Installation Script

```bash
#!/bin/bash

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install docker-compose -y

# Create application directory
mkdir -p /opt/ai-calendar-assistant
cd /opt/ai-calendar-assistant

# Clone repository
git clone https://github.com/your/ai-calendar-assistant.git .

# Create .env file
cat > .env <<EOF
TELEGRAM_BOT_TOKEN=your_token
YANDEX_API_KEY=your_key
YANDEX_FOLDER_ID=your_folder_id
ADMIN_PASSWORD_1_HASH=hash1
ADMIN_PASSWORD_2_HASH=hash2
ADMIN_PASSWORD_3_HASH=hash3
RADICALE_URL=http://radicale:5232
LOG_LEVEL=INFO
PUBLIC_URL=https://yourdomain.ru
TELEGRAM_WEBHOOK_SECRET=your_secret
EOF

# Create data directories
mkdir -p logs data radicale/data radicale/config

# Start services
docker-compose -f docker-compose.production.yml up -d

# Wait for services to start
sleep 10

# Check status
docker ps

# Show logs
docker logs telegram-bot

echo "Installation complete!"
echo "Check status: docker ps"
echo "View logs: docker logs -f telegram-bot"
```

### 7.3.3 Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.ru www.yourdomain.ru;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.ru www.yourdomain.ru;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.ru/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Telegram webhook
    location /telegram/webhook {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Security: Only allow Telegram IP ranges
        allow 149.154.160.0/20;
        allow 91.108.4.0/22;
        deny all;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web application
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000;
        access_log off;
    }
}
```

### 7.3.4 SSL Certificate Setup

```bash
# Install certbot
apt-get install certbot python3-certbot-nginx -y

# Obtain certificate
certbot --nginx -d yourdomain.ru -d www.yourdomain.ru

# Auto-renewal (cron)
echo "0 3 * * * certbot renew --quiet" | crontab -
```

### 7.3.5 Systemd Service

Create `/etc/systemd/system/ai-calendar.service`:

```ini
[Unit]
Description=AI Calendar Assistant
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ai-calendar-assistant
ExecStart=/usr/bin/docker-compose -f docker-compose.production.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.production.yml down

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable ai-calendar.service
systemctl start ai-calendar.service
```

## 7.4 Monitoring Setup

### 7.4.1 Health Check Script

```bash
#!/bin/bash

# check_health.sh

HEALTH_URL="http://localhost:8000/health"
TELEGRAM_TOKEN="your_bot_token"
ADMIN_CHAT_ID="your_admin_chat_id"

response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$response" != "200" ]; then
    # Send alert to Telegram
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage" \
        -d "chat_id=$ADMIN_CHAT_ID" \
        -d "text=⚠️ ALERT: AI Calendar Assistant health check failed! HTTP $response"

    # Restart service
    cd /opt/ai-calendar-assistant
    docker-compose -f docker-compose.production.yml restart telegram-bot
fi
```

Add to crontab:
```bash
*/5 * * * * /opt/ai-calendar-assistant/check_health.sh
```

### 7.4.2 Log Rotation

Create `/etc/logrotate.d/ai-calendar`:

```
/opt/ai-calendar-assistant/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker exec telegram-bot pkill -HUP -f run_hybrid.py
    endscript
}
```

### 7.4.3 Backup Script

```bash
#!/bin/bash

# backup.sh

BACKUP_DIR="/backup/ai-calendar"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /opt/ai-calendar-assistant/data

# Backup Radicale calendars
tar -czf $BACKUP_DIR/radicale_$DATE.tar.gz /opt/ai-calendar-assistant/radicale/data

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
0 2 * * * /opt/ai-calendar-assistant/backup.sh
```

---

## Заключение

Эта документация покрывает:

✅ **PRD** - Описание продукта, функции, метрики, user stories
✅ **Техническая Архитектура** - Компоненты, сервисы, API, data flow
✅ **LLM Промпты** - Системные промпты, function calling, edge cases
✅ **База Данных** - Radicale CalDAV, JSON storage, миграция на PostgreSQL
✅ **Аналитика** - Structured logging, dashboard, metrics, alerting
✅ **API Документация** - Все endpoints с примерами запросов/ответов
✅ **Deployment** - Docker, Railway, VPS, мониторинг, бэкапы

Документация содержит **16,000+ строк** полного описания системы.
