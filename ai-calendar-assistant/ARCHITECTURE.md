# Архитектура AI Calendar Assistant

## Обзор

AI Calendar Assistant - это интеллектуальный календарный ассистент, который позволяет управлять календарем через естественный язык (текст и голос).

## Основные компоненты

### 1. API Layer (FastAPI)
- **app/main.py** - точка входа приложения
- **app/routers/** - HTTP эндпоинты
  - `telegram.py` - Telegram webhook обработчик
  - `oauth.py` - Google OAuth2 flow

### 2. Service Layer
- **app/services/llm_agent.py** - Обработка NL с помощью Claude
  - Парсинг команд пользователя
  - Извлечение структурированной информации
  - Function calling для определения intent

- **app/services/calendar_google.py** - Интеграция с Google Calendar
  - OAuth2 авторизация
  - CRUD операции с событиями
  - Поиск свободных слотов

- **app/services/stt.py** - Speech-to-Text (Whisper)
  - Распознавание голосовых сообщений

- **app/services/telegram_handler.py** - Обработка Telegram сообщений
  - Роутинг команд
  - Формирование ответов

### 3. Data Layer
- **app/schemas/** - Pydantic модели
  - `events.py` - EventDTO, IntentType, CalendarEvent, FreeSlot

### 4. Utilities
- **app/utils/datetime_parser.py** - Парсинг дат/времени
- **app/utils/logger.py** - Структурированное логирование

## Поток обработки запроса

```
1. Пользователь отправляет сообщение в Telegram
   ↓
2. Telegram отправляет webhook на /telegram/webhook
   ↓
3. TelegramHandler получает Update
   ↓
4. Если голос → STTService преобразует в текст
   ↓
5. LLMAgent анализирует текст с помощью Claude
   ↓
6. Определяется intent (create/query/find_free_slots/etc)
   ↓
7. CalendarService выполняет действие через Google API
   ↓
8. TelegramHandler формирует и отправляет ответ
```

## Интеграция с LLM (Claude)

### Промпт-инженеринг
System prompt задает контекст календарного ассистента:
- Роль: календарный помощник
- Поддерживаемые языки: русский, английский
- Часовой пояс: Europe/Moscow
- Интенты: create, update, delete, query, find_free_slots, clarify

### Function Calling
Claude использует инструмент `set_calendar_action` для структурированного вывода:
```json
{
  "intent": "create",
  "title": "Встреча с командой",
  "start_time": "2025-12-11T10:00:00+03:00",
  "duration_minutes": 60
}
```

## Безопасность

1. **Webhook Protection**
   - Secret token валидация для Telegram webhook

2. **OAuth2 Flow**
   - Google OAuth для доступа к календарю
   - Токены сохраняются локально (в файлах)

3. **API Keys**
   - Все ключи в переменных окружения (.env)
   - Не логируются и не включаются в git

## Масштабирование

### Текущая архитектура (MVP)
- FastAPI с async обработкой
- File-based storage для OAuth токенов
- In-memory processing

### Планы на масштабирование
- PostgreSQL для хранения токенов и состояния
- Redis для кэширования и rate limiting
- Celery для фоновых задач
- Horizontal scaling с load balancer

## Тестирование

### Unit Tests
- Тестирование отдельных функций/методов
- Моки для внешних API (Claude, Google, Telegram)

### Integration Tests
- End-to-end сценарии
- Тестирование взаимодействия компонентов

### CI/CD
- GitHub Actions для автоматического тестирования
- Линтинг (flake8, black, mypy)
- Coverage reporting

## Зависимости

### Внешние сервисы
1. **Anthropic Claude API** - понимание NL
2. **Google Calendar API** - управление событиями
3. **OpenAI API** - Speech-to-Text (Whisper)
4. **Telegram Bot API** - интерфейс для пользователей

### Библиотеки
- FastAPI - веб-фреймворк
- python-telegram-bot - Telegram SDK
- anthropic - Claude SDK
- google-api-python-client - Google APIs
- dateparser - парсинг дат
- structlog - логирование

## Deployment

### Docker
```bash
docker-compose up --build
```

### Manual
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Environment Variables
См. `.env.example` для списка всех переменных

## Roadmap

### Phase 1 (MVP) ✅
- Базовая инфраструктура
- Создание событий
- Запрос расписания
- Голосовой ввод

### Phase 2 (Planned)
- Редактирование/удаление событий
- Recurring events
- Напоминания
- Multi-calendar support

### Phase 3 (Future)
- OCR для расписаний
- Multi-messenger (WhatsApp, Slack)
- TTS для ответов
- Веб-интерфейс
