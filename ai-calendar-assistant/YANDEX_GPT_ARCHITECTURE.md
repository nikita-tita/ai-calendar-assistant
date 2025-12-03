# 🤖 Архитектура взаимодействия с Яндекс GPT

**Дата:** 24 ноября 2025
**Проект:** AI Calendar Assistant
**Модель:** YandexGPT (yandexgpt / yandexgpt-lite)

---

## 📋 Оглавление

1. [Общая архитектура](#общая-архитектура)
2. [Конфигурация](#конфигурация)
3. [Промпты системы](#промпты-системы)
4. [Схема обработки запросов](#схема-обработки-запросов)
5. [Типы интентов](#типы-интентов)
6. [Function Calling](#function-calling)
7. [Примеры промптов](#примеры-промптов)
8. [Обработка ошибок](#обработка-ошибок)

---

## 🏗 Общая архитектура

### Схема взаимодействия

```
Пользователь (Telegram)
    ↓
Telegram Bot (webhook)
    ↓
TelegramHandler
    ↓
LLMAgentYandex.extract_event()
    ↓
Yandex GPT API (completion endpoint)
    ↓
Response Parser (_parse_yandex_response)
    ↓
EventDTO с extracted данными
    ↓
Calendar Service / Todos Service
    ↓
Response to User
```

### Компоненты системы

1. **TelegramHandler** (`app/services/telegram_handler.py`)
   - Обрабатывает входящие сообщения от пользователей
   - Управляет conversation history
   - Маршрутизирует запросы к LLM Agent

2. **LLMAgentYandex** (`app/services/llm_agent_yandex.py`)
   - Основной класс для взаимодействия с Yandex GPT
   - Формирует промпты с контекстом
   - Парсит ответы от API
   - Возвращает структурированные EventDTO

3. **Calendar Service** (`app/services/calendar_radicale.py`)
   - Управляет событиями через CalDAV (Radicale)
   - Выполняет CRUD операции

4. **Todos Service** (`app/services/todos_service.py`)
   - Управляет задачами (TODO)
   - Не привязаны к конкретному времени

---

## ⚙️ Конфигурация

### Переменные окружения (.env)

```bash
# Yandex GPT API (Primary LLM)
YANDEX_GPT_API_KEY=your_yandex_gpt_api_key_here
YANDEX_GPT_FOLDER_ID=your_yandex_folder_id_here
```

### Настройки в коде (config.py)

```python
class Settings(BaseSettings):
    # Yandex GPT (для регионов где Claude/OpenAI заблокированы)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None

    # Default timezone
    default_timezone: str = "Europe/Moscow"
```

### API Endpoint

```python
api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
model = "yandexgpt"  # или "yandexgpt-lite" для быстрого/дешевого
```

---

## 📝 Промпты системы

### Базовый системный промпт (base_system_prompt)

Это основной промпт, который формирует поведение ассистента. Он содержит:

#### 1. Роль и задача

```
You are an intelligent calendar assistant.
Your task is to understand user commands in natural language
(Russian, English, Spanish, or Arabic) and convert them into
structured calendar actions.
```

#### 2. Типы действий (intents)

```
Possible actions (intent):
- create: create a single new event WITH specific time
- create_recurring: create recurring events (daily, weekly, monthly patterns)
- update: modify an existing event
- delete: delete an event
- query: query information about events
- find_free_slots: find free time
- batch_confirm: confirm multiple specific events
- delete_by_criteria: delete events matching criteria
- delete_duplicates: delete duplicate events
- todo: create a task WITHOUT specific time slot
- clarify: ask for clarification if information is insufficient
```

#### 3. Различие между событиями и задачами

```
DISTINGUISHING EVENTS vs TASKS (TODO):

Use intent="todo" when:
- Action verbs WITHOUT specific time: написать, позвонить, купить, изучить
- User says "завтра", "в понедельник" but NO specific time mentioned
- Request is about completing something, not scheduling
- Keywords: "надо", "нужно", "не забыть", "сделать"
- CRITICAL: If no time specified → ALWAYS use intent="todo"

Use intent="create" (calendar event) when:
- Specific time mentioned: "в 15:00", "завтра в 10 утра"
- Meeting/appointment words WITH time
- Events that occupy a specific time slot
```

**Примеры:**
- ❌ `"Написать отчет завтра"` → `intent="todo"` (нет времени)
- ✅ `"Встреча завтра в 15:00"` → `intent="create"` (есть время)
- ❌ `"Позвонить Ивану"` → `intent="todo"` (нет времени)
- ✅ `"Звонок с Иваном в 10:00"` → `intent="create"` (есть время)

#### 4. Правила обработки дат

```
Rules:
1. Always return time in ISO 8601 format with user's timezone
2. For EVENTS: If information missing (date, time, title) - use intent=clarify
3. For TODO: Only title required. If "завтра" mentioned, set due_date
4. IMPORTANT: For relative dates calculate exact date relative to CURRENT DATE
5. IMPORTANT: Use context from previous messages for clarification answers
6. Default duration is 60 minutes if not specified
7. Extract attendees from text
```

#### 5. Повторяющиеся события (Recurring Events)

```
RECURRING EVENTS (Creating Multiple Events with Patterns):

8. For requests like "every day", "daily", use intent="create_recurring"
9. Include fields:
   - recurrence_type: "daily" | "weekly" | "monthly"
   - recurrence_end_date: ISO 8601 date when recurrence should stop
   - recurrence_days: (for weekly) ["mon", "wed", "fri"]

10. CRITICAL RULES for duration (TODAY is {today_str}):
   - "every day" WITHOUT period → recurrence_end_date = end of year
   - "for 3 days" → recurrence_end_date = today + 3 days
   - "until Friday" → recurrence_end_date = next Friday

11. RECURRING PATTERNS - Examples:
   - "бег по утрам в 9 часов" → create_recurring, daily, 9:00
   - "каждый вторник в 14 совещание" → create_recurring, weekly, ["tue"], 14:00
```

#### 6. Операции удаления

```
DELETION OPERATIONS:

16. For "delete all X" requests:
    - Use intent="delete_by_criteria" with delete_criteria_title_contains
    - Example: "удали все утренние ритуалы" →
      {"intent": "delete_by_criteria", "delete_criteria_title_contains": "утренн"}

17. For "delete X" (single event) - use intent="delete" with event_id

18. NEVER return large batch_actions arrays for deletion (token limit!)
```

#### 7. Пакетное создание (Batch Operations)

```
BATCH SCHEDULE CREATION:

21. CRITICAL: If user provides schedule with MULTIPLE time ranges,
    create batch_actions array

22. Schedule format patterns:
    - Multiple lines with time ranges (HH:MM-HH:MM)
    - Each line has event title after time
    - All for same date context

23. For schedule format:
    - Return intent="batch_confirm"
    - Create batch_actions array with one action per line

24. Example input:
    "тайминг на 23 октября:
     12:45-13:00 Приезд, заселение
     13:00-13:30 Кофе-брейк
     13:30-15:00 Дискуссия по ИИ"
```

#### 8. Множественные действия в одной команде

```
MULTIPLE EVENTS IN ONE COMMAND:

26. When user mentions MULTIPLE events/tasks with connectors,
    create batch_actions array

27. Connectors: "потом", "затем", "а потом", "после этого", "then", "also"

28. Mixed events and tasks detection:
   - Parse each part separately
   - Events (with time) → intent="create"
   - Tasks (no time) → intent="todo"
   - Return batch_actions array with ALL actions

29. EXAMPLES:
   - "В 17 встреча, в 19 ужин и еще позвонить маме" →
     batch_actions: [{create at 17}, {create at 19}, {todo: call}]
```

---

### Динамические инструкции по языку

Для каждого поддерживаемого языка генерируется отдельная инструкция:

#### Русский язык (ru)

```
КРИТИЧЕСКИ ВАЖНО: ЯЗЫК ОБЩЕНИЯ - РУССКИЙ!
ВСЕ ответы (clarify_question, заголовки событий, описания) на русском.

ВАЖНО: ТЕКУЩАЯ ДАТА И ВРЕМЯ: {current_datetime_str}
({timezone}, UTC{tz_offset_formatted}), {current_weekday_ru}

КРИТИЧЕСКИ ВАЖНО: Примеры относительных дат:
- "завтра" = {tomorrow_date} ({tomorrow_iso})
- "послезавтра" = {day_after_tomorrow} ({iso})
- "через неделю" = {next_week} ({iso})

КРИТИЧЕСКИ ВАЖНО: Ближайшие дни недели:
- "в понедельник" = {next_monday} ({iso})
- "во вторник" = {next_tuesday} ({iso})
- "в среду" = {next_wednesday} ({iso})
...

ВНИМАНИЕ: Используй ТОЧНО эти даты! Не пересчитывай сам!
```

#### Английский язык (en)

```
CRITICAL: USER LANGUAGE IS ENGLISH!
ALL responses must be in English.

IMPORTANT: CURRENT DATE AND TIME: {current_datetime_str}

CRITICAL: Examples of relative dates:
- "tomorrow" = {tomorrow_date} ({iso})
- "day after tomorrow" = {date} ({iso})
- "next week" = {date} ({iso})

CRITICAL: Next weekdays:
- "on Monday" = {next_monday} ({iso})
...

IMPORTANT: Use EXACTLY these dates! Do not recalculate!
```

---

### Форматирование финального промпта

Финальный промпт, отправляемый в Yandex GPT, формируется так:

```python
full_prompt = f"""{system_prompt}

{events_prefix + user_text}

{json_instructions}"""
```

Где:
- `system_prompt` = базовый промпт + языковые инструкции
- `events_prefix` = список существующих событий (если есть)
- `user_text` = запрос пользователя
- `json_instructions` = инструкция вернуть JSON

---

## 🔄 Схема обработки запросов

### Пошаговый процесс

```
1. Получение сообщения пользователя
   ├─> Telegram webhook → TelegramHandler.handle_update()
   └─> Определение типа сообщения (текст/голос/кнопка)

2. Предобработка
   ├─> Проверка conversation_history
   ├─> Получение timezone пользователя
   ├─> Загрузка existing_events из календаря (последние 7-60 дней)
   └─> Проверка на schedule format (batch operations)

3. Вызов LLM Agent
   ├─> LLMAgentYandex.extract_event()
   ├─> Формирование system_prompt с датами
   ├─> Добавление events_prefix (если есть события)
   ├─> Формирование function_schema
   └─> Вызов Yandex GPT API

4. Yandex GPT API Request
   ├─> POST to completion endpoint
   ├─> Headers: {"Authorization": f"Api-Key {api_key}"}
   ├─> Body: {
   │     "modelUri": f"gpt://{folder_id}/{model}/latest",
   │     "completionOptions": {
   │       "stream": False,
   │       "temperature": 0.2,
   │       "maxTokens": 2000
   │     },
   │     "messages": [{"role": "system", "text": full_prompt}]
   │   }
   └─> Timeout: 30 секунд

5. Парсинг ответа
   ├─> Извлечение JSON из response
   ├─> Удаление markdown code blocks (```)
   ├─> Парсинг intent, параметров
   ├─> Создание EventDTO / TodoDTO
   └─> Валидация данных

6. Выполнение действия
   ├─> IntentType.CREATE → _handle_create()
   ├─> IntentType.TODO → _handle_todo()
   ├─> IntentType.QUERY → _handle_query()
   ├─> IntentType.DELETE → _handle_delete()
   ├─> IntentType.BATCH_CONFIRM → _handle_batch_confirm()
   └─> IntentType.CLARIFY → запрос уточнения

7. Ответ пользователю
   └─> Форматированное сообщение в Telegram
```

---

## 🎯 Типы интентов

### CREATE - Создание события

**Когда используется:**
- Пользователь указал конкретное время
- Есть название события
- Присутствуют слова: "встреча", "показ", "звонок" + время

**Обязательные поля:**
- `title` - название события
- `start_time` - время начала (ISO 8601)
- `end_time` - время окончания (опционально, по умолчанию +60 минут)

**Пример запроса:**
```
Пользователь: "Встреча с клиентом завтра в 15:00"
```

**Пример ответа LLM:**
```json
{
  "intent": "create",
  "title": "Встреча с клиентом",
  "start_time": "2025-11-25T15:00:00+03:00",
  "end_time": "2025-11-25T16:00:00+03:00",
  "duration_minutes": 60,
  "confidence": 0.95
}
```

---

### TODO - Создание задачи

**Когда используется:**
- НЕТ конкретного времени
- Глаголы действия: "написать", "позвонить", "купить", "обновить"
- Ключевые слова: "надо", "нужно", "не забыть"

**Обязательные поля:**
- `title` - название задачи
- `due_date` - дата выполнения (опционально)

**Пример запроса:**
```
Пользователь: "Обновить персональные данные"
```

**Пример ответа LLM:**
```json
{
  "intent": "todo",
  "title": "Обновить персональные данные",
  "confidence": 0.9
}
```

---

### QUERY - Запрос событий

**Когда используется:**
- "Что у меня...", "Какие планы...", "Покажи события..."
- Запрос информации о будущих/прошлых событиях

**Обязательные поля:**
- `query_date_start` - начало периода
- `query_date_end` - конец периода (опционально)

**Пример запроса:**
```
Пользователь: "Что у меня на этой неделе?"
```

**Пример ответа LLM:**
```json
{
  "intent": "query",
  "query_date_start": "2025-11-24T00:00:00+03:00",
  "query_date_end": "2025-12-01T23:59:59+03:00",
  "confidence": 0.9
}
```

**CRITICAL для "на этой неделе":**
```
query_date_start = today
query_date_end = today + 7 days
```
Это включает все события от сегодня до +7 дней.

---

### CREATE_RECURRING - Повторяющиеся события

**Когда используется:**
- "Каждый день", "every day", "daily"
- "Каждый понедельник", "по вторникам"
- Паттерны повторения

**Обязательные поля:**
- `recurrence_type`: "daily" | "weekly" | "monthly"
- `recurrence_end_date` - дата окончания повторений
- `start_time` - время начала
- `title` - название
- `recurrence_days` - (для weekly) дни недели

**Пример запроса:**
```
Пользователь: "Бег по утрам в 9 часов"
```

**Пример ответа LLM:**
```json
{
  "intent": "create_recurring",
  "title": "Бег",
  "start_time": "09:00",
  "recurrence_type": "daily",
  "recurrence_end_date": "2025-12-31",
  "duration_minutes": 60,
  "confidence": 0.85
}
```

---

### BATCH_CONFIRM - Пакетные операции

**Когда используется:**
- Множественные события в одной команде
- Разделители: "потом", "затем", "а потом"
- Schedule формат (тайминг с временными интервалами)

**Обязательные поля:**
- `batch_actions` - массив действий
- `batch_summary` - краткое описание

**Пример запроса:**
```
Пользователь: "В 17 встреча, потом в 19 ужин и позвонить маме"
```

**Пример ответа LLM:**
```json
{
  "intent": "batch_confirm",
  "batch_actions": [
    {
      "intent": "create",
      "title": "Встреча",
      "start_time": "2025-11-24T17:00:00+03:00",
      "end_time": "2025-11-24T18:00:00+03:00"
    },
    {
      "intent": "create",
      "title": "Ужин",
      "start_time": "2025-11-24T19:00:00+03:00",
      "end_time": "2025-11-24T20:00:00+03:00"
    },
    {
      "intent": "todo",
      "title": "Позвонить маме"
    }
  ],
  "batch_summary": "📅 Создать 2 события и 1 задачу",
  "confidence": 0.9
}
```

---

### DELETE_BY_CRITERIA - Удаление по критериям

**Когда используется:**
- "Удали все...", "delete all..."
- Массовое удаление по названию/дате

**Обязательные поля:**
- `delete_criteria_title_contains` - фрагмент названия

**Пример запроса:**
```
Пользователь: "Удали все утренние ритуалы"
```

**Пример ответа LLM:**
```json
{
  "intent": "delete_by_criteria",
  "delete_criteria_title_contains": "утренн",
  "confidence": 0.85
}
```

---

### DELETE_DUPLICATES - Удаление дубликатов

**Когда используется:**
- "Удали дубликаты", "удали повторяющиеся"
- "Удали одинаковые события"

**Пример запроса:**
```
Пользователь: "Удали дубликаты"
```

**Пример ответа LLM:**
```json
{
  "intent": "delete_duplicates",
  "confidence": 0.9
}
```

---

### UPDATE - Обновление события

**Когда используется:**
- "Перенеси...", "измени...", "reschedule..."
- Изменение существующего события

**Обязательные поля:**
- `event_id` - ID события (из existing_events)
- Новые значения (start_time/title/location)

**Пример запроса:**
```
Пользователь: "Перенеси встречу с Катей на 16:00"
```

**Пример ответа LLM:**
```json
{
  "intent": "update",
  "event_id": "abc-123-def",
  "start_time": "2025-11-24T16:00:00+03:00",
  "confidence": 0.85
}
```

**Важно:** Система автоматически загружает `existing_events` и передает их в промпт.

---

### DELETE - Удаление события

**Когда используется:**
- "Удали...", "отмени...", "delete..."
- Удаление конкретного события

**Обязательные поля:**
- `event_id` - ID события

---

### FIND_FREE_SLOTS - Поиск свободного времени

**Когда используется:**
- "Когда я свободен...", "свободное время..."
- "When am I free..."

**Обязательные поля:**
- `query_date_start` - дата поиска
- `query_time_start` - (опционально) время начала поиска

**Пример запроса:**
```
Пользователь: "Когда я свободен завтра после 16?"
```

**Пример ответа LLM:**
```json
{
  "intent": "find_free_slots",
  "query_date_start": "2025-11-25T00:00:00+03:00",
  "query_time_start": "2025-11-25T16:00:00+03:00",
  "confidence": 0.9
}
```

---

### CLARIFY - Запрос уточнения

**Когда используется:**
- Недостаточно информации для выполнения действия
- Двусмысленность в запросе
- Нужно больше деталей

**Обязательные поля:**
- `clarify_question` - вопрос на языке пользователя

**Пример запроса:**
```
Пользователь: "Перенеси встречу"
```

**Пример ответа LLM:**
```json
{
  "intent": "clarify",
  "clarify_question": "Какую именно встречу перенести? Уточните дату или название.",
  "confidence": 0.5
}
```

---

## 🔧 Function Calling

### Схема функции set_calendar_action

Yandex GPT получает следующую схему функции в промпте:

```json
{
  "name": "set_calendar_action",
  "description": "Установить действие с календарем",
  "parameters": {
    "type": "object",
    "properties": {
      "intent": {
        "type": "string",
        "enum": [
          "create", "create_recurring", "update", "delete",
          "query", "find_free_slots", "clarify", "batch_confirm",
          "delete_by_criteria", "delete_duplicates", "todo"
        ]
      },
      "title": {"type": "string"},
      "start_time": {"type": "string", "description": "ISO 8601"},
      "end_time": {"type": "string"},
      "duration_minutes": {"type": "integer"},
      "location": {"type": "string"},
      "attendees": {"type": "array", "items": {"type": "string"}},
      "event_id": {
        "type": "string",
        "enum": ["none", "event-1", "event-2", ...],
        "description": "ID события из списка existing_events"
      },
      "clarify_question": {"type": "string"},
      "query_date_start": {"type": "string"},
      "query_date_end": {"type": "string"},
      "confidence": {"type": "number"},
      "recurrence_type": {
        "type": "string",
        "enum": ["daily", "weekly", "monthly"]
      },
      "recurrence_end_date": {"type": "string"},
      "recurrence_days": {
        "type": "array",
        "items": {"enum": ["mon","tue","wed","thu","fri","sat","sun"]}
      },
      "batch_actions": {
        "type": "array",
        "items": {"type": "object"}
      },
      "delete_criteria_title_contains": {"type": "string"}
    },
    "required": ["intent"]
  }
}
```

### Динамическое формирование event_id enum

Для операций UPDATE/DELETE система автоматически формирует список ID из existing_events:

```python
event_id_enum = ["none"]  # default
if existing_events:
    for event in existing_events:
        if event.id:
            event_id_enum.append(str(event.id))
```

Это позволяет LLM выбрать правильный ID события из контекста.

---

## 💬 Примеры промптов

### Пример 1: Создание простого события

**User input:**
```
Встреча с клиентом завтра в 15:00
```

**System prompt (фрагмент):**
```
КРИТИЧЕСКИ ВАЖНО: ТЕКУЩАЯ ДАТА: 24.11.2025, воскресенье

Примеры относительных дат:
- "завтра" = 25.11.2025 (2025-11-25)

User request:
Встреча с клиентом завтра в 15:00

Верни ТОЛЬКО JSON:
```

**LLM Response:**
```json
{
  "intent": "create",
  "title": "Встреча с клиентом",
  "start_time": "2025-11-25T15:00:00+03:00",
  "end_time": "2025-11-25T16:00:00+03:00",
  "duration_minutes": 60,
  "confidence": 0.95
}
```

**Result:**
```
✅ Записал
25 ноября, понедельник 15:00 • Встреча с клиентом
```

---

### Пример 2: Создание задачи (TODO)

**User input:**
```
Обновить персональные данные
```

**System prompt (фрагмент):**
```
Use intent="todo" when:
- Action verbs WITHOUT specific time: обновить
- No time mentioned
- CRITICAL: If no time specified → ALWAYS use intent="todo"

User request:
Обновить персональные данные

Верни ТОЛЬКО JSON:
```

**LLM Response:**
```json
{
  "intent": "todo",
  "title": "Обновить персональные данные",
  "confidence": 0.9
}
```

**Result:**
```
✅ Записал задачу
📝 Обновить персональные данные
```

---

### Пример 3: Множественные события с "потом"

**User input:**
```
В 17 встреча, потом в 19 ужин и позвонить маме
```

**System prompt (фрагмент):**
```
MULTIPLE EVENTS IN ONE COMMAND:
When user mentions MULTIPLE events/tasks with connectors ("потом"),
create batch_actions array.

Example:
"В 17 встреча, в 19 ужин и позвонить маме" →
  batch_actions: [{create at 17}, {create at 19}, {todo}]

User request:
В 17 встреча, потом в 19 ужин и позвонить маме
```

**LLM Response:**
```json
{
  "intent": "batch_confirm",
  "batch_actions": [
    {
      "intent": "create",
      "title": "Встреча",
      "start_time": "2025-11-24T17:00:00+03:00",
      "end_time": "2025-11-24T18:00:00+03:00"
    },
    {
      "intent": "create",
      "title": "Ужин",
      "start_time": "2025-11-24T19:00:00+03:00",
      "end_time": "2025-11-24T20:00:00+03:00"
    },
    {
      "intent": "todo",
      "title": "Позвонить маме"
    }
  ],
  "batch_summary": "📅 Создать 2 события и 1 задачу:\n• 17:00 - Встреча\n• 19:00 - Ужин\n• Задача: Позвонить маме"
}
```

**Result:**
```
📅 Создать 2 события и 1 задачу:
• 17:00 - Встреча
• 19:00 - Ужин
• Задача: Позвонить маме

Подтвердите создание?
[Создать] [Отмена]
```

---

### Пример 4: Запрос расписания на неделю

**User input:**
```
Что у меня на этой неделе?
```

**System prompt (фрагмент):**
```
Querying schedule:
- "Какие планы на эту неделю?" → query,
  query_date_start=today, query_date_end=today+7 days

КРИТИЧЕСКИ ВАЖНО: Для "этой неделе" используй:
query_date_start = 24.11.2025 (сегодня)
query_date_end = 01.12.2025 (через 7 дней)

User request:
Что у меня на этой неделе?
```

**LLM Response:**
```json
{
  "intent": "query",
  "query_date_start": "2025-11-24T00:00:00+03:00",
  "query_date_end": "2025-12-01T23:59:59+03:00",
  "confidence": 0.95
}
```

**Result:**
```
📅 Ваши планы на эту неделю:

Понедельник, 25 ноября:
• 15:00-16:00 Встреча с клиентом

Вторник, 26 ноября:
• 10:00-11:00 Звонок с партнером

Среда, 27 ноября:
• Нет событий

...
```

---

### Пример 5: Повторяющиеся события

**User input:**
```
Бег по утрам в 9 часов
```

**System prompt (фрагмент):**
```
RECURRING EVENTS:
For "бег по утрам в 9 часов" → create_recurring,
  recurrence_type="daily", start_time=9:00

"every day" WITHOUT period → recurrence_end_date = 2025-12-31

User request:
Бег по утрам в 9 часов
```

**LLM Response:**
```json
{
  "intent": "create_recurring",
  "title": "Бег",
  "start_time": "09:00",
  "recurrence_type": "daily",
  "recurrence_end_date": "2025-12-31",
  "duration_minutes": 60,
  "confidence": 0.85
}
```

**Result:**
```
📅 Создать 38 событий: 'Бег'
📍 С 25 ноября по 31 декабря
⏰ Каждый день в 09:00

Подтвердите создание?
[Создать] [Отмена]
```

---

### Пример 6: Schedule format (тайминг)

**User input:**
```
тайминг на 25 ноября:
12:45-13:00 Приезд, заселение
13:00-13:30 Кофе-брейк
13:30-15:00 Дискуссия по ИИ
```

**Preprocessing:**
Система обнаруживает schedule format ДО вызова LLM через `_detect_schedule_format()`.

**Result (без вызова LLM):**
```json
{
  "intent": "batch_confirm",
  "batch_actions": [
    {
      "intent": "create",
      "title": "Приезд, заселение",
      "start_time": "2025-11-25T12:45:00+03:00",
      "end_time": "2025-11-25T13:00:00+03:00",
      "duration_minutes": 15
    },
    {
      "intent": "create",
      "title": "Кофе-брейк",
      "start_time": "2025-11-25T13:00:00+03:00",
      "end_time": "2025-11-25T13:30:00+03:00",
      "duration_minutes": 30
    },
    {
      "intent": "create",
      "title": "Дискуссия по ИИ",
      "start_time": "2025-11-25T13:30:00+03:00",
      "end_time": "2025-11-25T15:00:00+03:00",
      "duration_minutes": 90
    }
  ],
  "batch_summary": "📅 Создать 3 события\n📍 25 ноября\n🔄 С 12:45 до 15:00"
}
```

---

### Пример 7: Удаление по критериям

**User input:**
```
Удали все утренние ритуалы
```

**System prompt (фрагмент):**
```
DELETION OPERATIONS:
For "удали все X" → use intent="delete_by_criteria"
  with delete_criteria_title_contains

Example: "удали все утренние ритуалы" →
  delete_criteria_title_contains: "утренн"

User request:
Удали все утренние ритуалы
```

**LLM Response:**
```json
{
  "intent": "delete_by_criteria",
  "delete_criteria_title_contains": "утренн",
  "confidence": 0.85
}
```

**System actions:**
1. Ищет все события с "утренн" в названии
2. Находит 5 событий
3. Просит подтверждение

**Result:**
```
🗑 Найдено 5 событий с "утренн":
• Утренний ритуал (25.11)
• Утренний ритуал (26.11)
• Утренний ритуал (27.11)
• Утренний ритуал (28.11)
• Утренняя пробежка (29.11)

Удалить все? [Удалить] [Отмена]
```

---

### Пример 8: Обновление события с existing_events

**User input:**
```
Перенеси встречу с Леной на 16:00
```

**System prompt (с existing_events):**
```
<existing_calendar_events>
Event: Встреча с Леной
Time: 24.11.2025 15:00
ID: abc-123-def

Event: Показ квартиры
Time: 25.11.2025 10:00
ID: xyz-456-ghi
</existing_calendar_events>

CRITICAL: For update/delete operations:
- Find event in list by matching title
- COPY the exact ID value - NEVER use "unknown"
- Example: "перенеси встречу с Леной" → find "Встреча с Леной" → copy ID

User request:
Перенеси встречу с Леной на 16:00
```

**LLM Response:**
```json
{
  "intent": "update",
  "event_id": "abc-123-def",
  "start_time": "2025-11-24T16:00:00+03:00",
  "confidence": 0.9
}
```

**Result:**
```
✅ Перенесено
Встреча с Леной: 15:00 → 16:00
```

---

## 🚨 Обработка ошибок

### Ошибки API

```python
if response.status_code != 200:
    logger.error("yandex_gpt_api_error",
                 status_code=response.status_code,
                 response=response.text)
    raise Exception(f"Yandex GPT API error: {response.status_code}")
```

### Ошибки парсинга JSON

```python
try:
    json_str = extract_json_from_text(result_text)
    data = json.loads(json_str)
except (json.JSONDecodeError, ValueError) as e:
    logger.warning("json_parse_error", error=str(e))
    return EventDTO(
        intent=IntentType.CLARIFY,
        confidence=0.2,
        clarify_question="Не разобрал. Перефразируйте, пожалуйста."
    )
```

### Таймауты

```python
response = requests.post(
    api_url,
    headers=headers,
    json=payload,
    timeout=30  # 30 секунд
)
```

### Fallback на clarify

При любой ошибке система возвращает CLARIFY intent:

```python
except Exception as e:
    logger.error("llm_extract_error", error=str(e))
    return EventDTO(
        intent=IntentType.CLARIFY,
        confidence=0.0,
        clarify_question="Что-то пошло не так. Попробуйте еще раз."
    )
```

---

## 📊 Метрики и логирование

### Structured Logging

Все взаимодействия логируются через `structlog`:

```python
logger.info("llm_extract_start_yandex",
            user_text=user_text,
            user_id=user_id,
            language=language)

logger.info("yandex_gpt_raw_response",
            result_text=result_text)

logger.info("llm_extract_success_yandex",
            intent=event_dto.intent,
            confidence=event_dto.confidence)
```

### Ключевые метрики

- `llm_extract_start_yandex` - начало обработки запроса
- `yandex_gpt_api_call` - вызов API
- `yandex_gpt_raw_response` - сырой ответ от API
- `yandex_gpt_parsed_json` - распарсенный JSON
- `llm_extract_success_yandex` - успешная обработка
- `llm_extract_error_yandex` - ошибка обработки

### Analytics

Опционально подключен `analytics_service` для отслеживания:
- `user_start` - регистрация пользователя
- `text_message` - текстовое сообщение
- `voice_message` - голосовое сообщение
- `event_created` - создано событие
- `todo_created` - создана задача

---

## 🔄 Conversation History

### Управление контекстом

Система хранит историю последних сообщений для обработки clarify-диалогов:

```python
# TelegramHandler
self.conversation_history = {}  # user_id -> list of messages

# Добавление в историю при CLARIFY
if event_dto.intent == IntentType.CLARIFY:
    self.conversation_history[user_id] = [
        {"role": "user", "content": text},
        {"role": "assistant", "content": event_dto.clarify_question}
    ]
else:
    # Очистка после успешного действия
    self.conversation_history[user_id] = []
```

### Передача в LLM

История передается только для ответов на clarify-вопросы:

```python
limited_history = []
if len(self.conversation_history[user_id]) >= 2:
    last_assistant = self.conversation_history[user_id][-1]
    prev_user = self.conversation_history[user_id][-2]

    if (last_assistant.get("role") == "assistant" and
        prev_user.get("role") == "user"):
        limited_history = [prev_user, last_assistant]

event_dto = await llm_agent.extract_event(
    text,
    user_id,
    conversation_history=limited_history,  # Only for clarify context
    timezone=user_tz,
    existing_events=existing_events
)
```

---

## 🌍 Поддержка нескольких языков

Система поддерживает 4 языка:
- 🇷🇺 Русский (ru) - по умолчанию
- 🇬🇧 Английский (en)
- 🇪🇸 Испанский (es)
- 🇸🇦 Арабский (ar)

### Языковые инструкции в промпте

Для каждого языка генерируется:
1. Системное сообщение на языке пользователя
2. Примеры относительных дат на языке
3. Названия дней недели
4. Инструкция отвечать на языке пользователя

### Определение языка

```python
language = user_preferences.get_language(user_id)  # default: 'ru'

event_dto = await llm_agent.extract_event(
    text,
    user_id,
    language=language  # 'ru' | 'en' | 'es' | 'ar'
)
```

---

## 🎯 Оптимизации

### 1. Предобработка Schedule Format

```python
# Детектируется ДО вызова LLM
schedule_dto = self._detect_schedule_format(user_text, timezone)
if schedule_dto:
    return schedule_dto  # Не тратим токены на LLM
```

Экономия: ~1500-2000 токенов на запрос с расписанием.

### 2. Ограничение токенов

```python
"completionOptions": {
    "maxTokens": 2000  # Ограничение ответа
}
```

### 3. Temperature для точности

```python
"temperature": 0.2  # Низкая температура для точных ответов
```

### 4. Кэширование timezone

```python
self.user_timezones = {}  # Локальный кеш на уровне handler
```

---

## 📈 Примеры использования

### Простые команды

| Запрос | Intent | Результат |
|--------|--------|-----------|
| "Встреча завтра в 15:00" | CREATE | Событие 25.11 15:00 |
| "Позвонить Ивану" | TODO | Задача без времени |
| "Что у меня сегодня?" | QUERY | Список событий |
| "Бег каждое утро в 9" | CREATE_RECURRING | Ежедневные события |
| "Удали встречу с Леной" | DELETE | Удаление события |

### Сложные команды

| Запрос | Intent | Описание |
|--------|--------|----------|
| "В 17 встреча, потом в 19 ужин" | BATCH_CONFIRM | 2 события |
| "Удали все показы" | DELETE_BY_CRITERIA | Массовое удаление |
| "Перенеси встречу на 16:00" | UPDATE | Обновление времени |
| "Когда я свободен завтра?" | FIND_FREE_SLOTS | Поиск окон |
| "Удали дубликаты" | DELETE_DUPLICATES | Умное удаление |

---

## 🔮 Будущие улучшения

### Планируется

1. **Streaming responses** - потоковый вывод для длинных ответов
2. **Контекстная память** - долгосрочное хранение предпочтений
3. **Умное переспрашивание** - меньше clarify, больше уточнений
4. **Категории событий** - автоматическая классификация
5. **Интеграция с внешними календарями** - Google Calendar, iCloud

### Эксперименты

- Использование **yandexgpt-lite** для простых запросов (экономия)
- **Embeddings** для семантического поиска событий
- **Few-shot examples** в промпте для улучшения точности

---

## 📞 Контакты и поддержка

**Проект:** AI Calendar Assistant
**Модель:** YandexGPT
**Версия документа:** 1.0
**Дата:** 24 ноября 2025

---

## 📚 Ссылки

- [Yandex GPT API Documentation](https://cloud.yandex.ru/docs/foundation-models/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [CalDAV Protocol](https://tools.ietf.org/html/rfc4791)
- [ISO 8601 DateTime Format](https://en.wikipedia.org/wiki/ISO_8601)

---

**Документ создан:** Claude Code
**Дата:** 24.11.2025
