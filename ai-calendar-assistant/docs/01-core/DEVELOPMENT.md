# Руководство для разработчиков

## 🛠️ Структура проекта

```
ai-calendar-assistant/
├── app/                          # Основной код приложения
│   ├── main.py                   # Точка входа FastAPI
│   ├── config.py                 # Настройки приложения
│   ├── routers/                  # HTTP роутеры
│   │   ├── telegram.py           # Telegram webhook
│   │   └── oauth.py              # Google OAuth2
│   ├── services/                 # Бизнес-логика
│   │   ├── llm_agent.py          # Claude LLM интеграция
│   │   ├── calendar_google.py    # Google Calendar API
│   │   ├── stt.py                # Speech-to-Text (Whisper)
│   │   └── telegram_handler.py   # Обработка Telegram сообщений
│   ├── schemas/                  # Pydantic модели
│   │   └── events.py             # EventDTO, IntentType, etc.
│   └── utils/                    # Утилиты
│       ├── logger.py             # Логирование
│       └── datetime_parser.py    # Парсинг дат/времени
├── tests/                        # Тесты
│   ├── unit/                     # Юнит-тесты
│   ├── integration/              # Интеграционные тесты
│   └── conftest.py               # Pytest фикстуры
├── scripts/                      # Вспомогательные скрипты
│   └── set_webhook.py            # Управление Telegram webhook
├── .github/workflows/            # GitHub Actions CI/CD
│   └── ci.yml                    # Pipeline определение
├── requirements.txt              # Python зависимости
├── Dockerfile                    # Docker образ
├── docker-compose.yml            # Docker Compose конфигурация
├── pytest.ini                    # Pytest настройки
├── pyproject.toml               # Poetry/Black/MyPy настройки
└── .env.example                  # Пример переменных окружения
```

## 🔄 Workflow разработки

### 1. Создание новой ветки

```bash
git checkout -b feature/your-feature-name
```

### 2. Внесение изменений

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Запустите приложение в режиме разработки
uvicorn app.main:app --reload
```

### 3. Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=app --cov-report=html

# Запуск конкретного теста
pytest tests/unit/test_datetime_parser.py

# Запуск с детальным выводом
pytest -v -s
```

### 4. Форматирование и линтинг

```bash
# Форматирование кода с Black
black app tests

# Проверка с flake8
flake8 app tests

# Сортировка импортов
isort app tests

# Проверка типов с MyPy
mypy app
```

### 5. Коммит изменений

```bash
git add .
git commit -m "feat: add new feature description"

# Используйте conventional commits:
# feat: новая функциональность
# fix: исправление бага
# docs: документация
# style: форматирование
# refactor: рефакторинг
# test: добавление тестов
# chore: вспомогательные изменения
```

### 6. Создание Pull Request

```bash
git push origin feature/your-feature-name
```

Затем создайте PR в GitHub.

## 📝 Добавление новой функциональности

### Пример: Добавление удаления событий

#### 1. Обновите EventDTO (app/schemas/events.py)

```python
# Уже есть поле event_id для идентификации события
```

#### 2. Добавьте метод в CalendarService (app/services/calendar_google.py)

```python
async def delete_event(self, user_id: str, event_id: str) -> bool:
    """Delete calendar event."""
    credentials = self._load_credentials(user_id)
    if not credentials:
        return False

    try:
        service = build('calendar', 'v3', credentials=credentials)
        service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()

        logger.info("event_deleted", user_id=user_id, event_id=event_id)
        return True

    except HttpError as e:
        logger.error("delete_error", user_id=user_id, error=str(e))
        return False
```

#### 3. Обновите LLM промпт для поддержки DELETE intent

```python
# В llm_agent.py system_prompt уже есть delete intent
```

#### 4. Добавьте обработчик в TelegramHandler (app/services/telegram_handler.py)

```python
async def _handle_delete(self, update: Update, user_id: str, event_dto) -> None:
    """Handle event deletion."""
    if not event_dto.event_id and event_dto.title:
        # Нужно найти событие по названию
        # Получить события и найти совпадение
        pass

    if event_dto.event_id:
        success = await calendar_service.delete_event(user_id, event_dto.event_id)
        if success:
            await update.message.reply_text("✅ Событие удалено")
        else:
            await update.message.reply_text("❌ Не удалось удалить событие")
```

#### 5. Добавьте в роутинг (app/services/telegram_handler.py)

```python
if event_dto.intent == IntentType.DELETE:
    await self._handle_delete(update, user_id, event_dto)
    return
```

#### 6. Напишите тесты (tests/unit/test_calendar.py)

```python
@pytest.mark.asyncio
async def test_delete_event(mock_calendar_service):
    result = await mock_calendar_service.delete_event("user123", "event456")
    assert result is True
```

#### 7. Обновите документацию (README.md)

```markdown
### Удаление событий
- "Удали встречу с доктором"
- "Отмени тренировку в субботу"
```

## 🧪 Тестирование

### Unit Tests

Тестируют отдельные функции/методы в изоляции:

```python
# tests/unit/test_datetime_parser.py
def test_extract_duration():
    assert extract_duration("на час") == 60
    assert extract_duration("на 2 часа") == 120
```

### Integration Tests

Тестируют взаимодействие компонентов:

```python
# tests/integration/test_telegram_flow.py
@pytest.mark.asyncio
async def test_create_event_flow(client, mock_llm, mock_calendar):
    # Эмулировать полный флоу от webhook до создания события
    pass
```

### Моки для внешних API

```python
# tests/conftest.py
@pytest.fixture
def mock_anthropic():
    with patch('app.services.llm_agent.anthropic.Anthropic') as mock:
        mock.return_value.messages.create.return_value = ...
        yield mock
```

## 🔍 Debugging

### Локальное тестирование Telegram webhook

Используйте ngrok для локального тестирования:

```bash
# Установите ngrok
brew install ngrok  # или скачайте с ngrok.com

# Запустите туннель
ngrok http 8000

# Обновите .env
TELEGRAM_WEBHOOK_URL=https://your-ngrok-url.ngrok.io/telegram/webhook

# Установите webhook
python scripts/set_webhook.py set
```

### Просмотр логов

```python
# Логи структурированные (structlog)
logger.info("event_created", user_id=user_id, event_id=event_id)

# В development выводятся красиво
# В production - JSON формат для парсинга
```

### Отладка LLM ответов

```python
# В llm_agent.py включите debug логирование
logger.debug("llm_response", response=response.model_dump())
```

## 🚀 Deployment

### Локальный запуск с Docker

```bash
docker-compose up --build
```

### Deploy на Heroku

```bash
# Установите Heroku CLI
brew install heroku/brew/heroku

# Логин
heroku login

# Создайте приложение
heroku create your-app-name

# Добавьте переменные окружения
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set ANTHROPIC_API_KEY=your_key
# ... и т.д.

# Deploy
git push heroku main

# Установите webhook
TELEGRAM_WEBHOOK_URL=https://your-app-name.herokuapp.com/telegram/webhook \
python scripts/set_webhook.py set
```

### Deploy на Railway

1. Подключите GitHub репозиторий
2. Добавьте переменные окружения в UI
3. Railway автоматически задеплоит

### Deploy на VPS

```bash
# SSH на сервер
ssh user@your-server

# Клонируйте репозиторий
git clone your-repo-url
cd ai-calendar-assistant

# Установите Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Создайте .env файл
cp .env.example .env
nano .env  # Заполните переменные

# Запустите с docker-compose
docker-compose up -d

# Настройте Nginx reverse proxy (опционально)
```

## 📊 Мониторинг

### Логирование

```python
# Используйте structlog для структурированных логов
import structlog
logger = structlog.get_logger()

logger.info("event_created",
    user_id=user_id,
    event_id=event_id,
    duration=duration_ms
)
```

### Метрики (будущее)

Планируется добавить:
- Prometheus для метрик
- Grafana для визуализации
- Sentry для отслеживания ошибок

## 🔐 Безопасность

### Секреты

- Никогда не коммитьте `.env`
- Используйте environment variables в production
- Ротируйте API ключи регулярно

### OAuth токены

```python
# Токены хранятся в credentials/
# В production используйте зашифрованное хранилище
```

### Rate Limiting

```python
# TODO: Добавить rate limiting
# Например, с помощью slowapi или redis
```

## 📚 Полезные ресурсы

### Документация API

- [Anthropic Claude](https://docs.anthropic.com/)
- [Google Calendar API](https://developers.google.com/calendar/api)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI](https://fastapi.tiangolo.com/)

### Библиотеки

- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [Pydantic](https://docs.pydantic.dev/)
- [structlog](https://www.structlog.org/)

## 🤔 FAQ

### Q: Как добавить поддержку другого языка?

A: Обновите system_prompt в `llm_agent.py` и добавьте языковой код в `stt.py`.

### Q: Как добавить поддержку другого календаря (Outlook)?

A: Создайте новый сервис `calendar_outlook.py` по аналогии с `calendar_google.py`.

### Q: Как масштабировать на большое количество пользователей?

A:
- Используйте PostgreSQL вместо file storage
- Добавьте Redis для кэширования
- Используйте Celery для фоновых задач
- Разверните несколько инстансов с load balancer

### Q: Как добавить Text-to-Speech?

A: Создайте сервис `tts.py` используя Google TTS или ElevenLabs API.

## 🐛 Known Issues

1. **Парсинг сложных дат** - dateparser иногда неправильно интерпретирует относительные даты
   - Решение: Улучшить логику в `datetime_parser.py`

2. **OAuth токены истекают** - нужна автоматическая рефреш
   - TODO: Добавить автоматический refresh в `calendar_google.py`

3. **Голосовые сообщения на шумном фоне** - Whisper может ошибаться
   - Решение: Добавить confidence score и переспрашивать при низком качестве

## 📞 Контакты

Для вопросов по разработке:
- GitHub Issues: [repository-url]/issues
- Email: dev@example.com
