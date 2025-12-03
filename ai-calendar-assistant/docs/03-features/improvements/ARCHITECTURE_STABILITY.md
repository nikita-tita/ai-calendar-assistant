# Архитектура стабильности: Предотвращение регрессий

## Проблема

При добавлении Property Bot возникают регрессии в Calendar Bot:
- Ломается редактирование событий в веб-приложении
- Появляются старые баги
- Календарь отваливается после обновлений

## Решение: Модульная изоляция

### 1. Принцип разделения модулей

```
┌─────────────────────────────────────────┐
│         Main Application (FastAPI)       │
└─────────────────────────────────────────┘
           │              │
           ▼              ▼
    ┌──────────┐    ┌──────────┐
    │ Calendar │    │ Property │
    │  Module  │    │  Module  │
    └──────────┘    └──────────┘
         │               │
         ▼               ▼
    ┌──────────┐    ┌──────────┐
    │ Radicale │    │  SQLite  │
    │  CalDAV  │    │  + APIs  │
    └──────────┘    └──────────┘
```

**Правила:**
- ✅ Модули НЕ зависят друг от друга
- ✅ Каждый модуль имеет свою БД/хранилище
- ✅ Общая логика только в `main.py`
- ✅ Telegram handler роутит по режиму

### 2. Структура файлов

```
app/
├── main.py                      # ТОЛЬКО роутинг, никакой логики
│
├── routers/
│   ├── telegram.py              # Общий webhook
│   ├── events.py                # ✅ Calendar API (НЕ ТРОГАТЬ!)
│   └── property.py              # ➕ Property API (новое)
│
├── services/
│   ├── calendar/                # ✅ Calendar module
│   │   ├── __init__.py
│   │   ├── calendar_radicale.py # ✅ НЕ ТРОГАТЬ!
│   │   ├── llm_agent_yandex.py  # ✅ НЕ ТРОГАТЬ!
│   │   └── event_reminders.py   # ✅ НЕ ТРОГАТЬ!
│   │
│   ├── property/                # ➕ Property module (новое)
│   │   ├── __init__.py
│   │   ├── property_service.py
│   │   ├── property_scoring.py
│   │   ├── property_handler.py
│   │   └── llm_agent_property.py
│   │
│   └── telegram_handler.py      # 🔧 Роутер между модулями
│
├── models/
│   ├── analytics.py             # ✅ Calendar models
│   └── property.py              # ➕ Property models
│
└── schemas/
    ├── events.py                # ✅ Calendar schemas
    └── property.py              # ➕ Property schemas
```

### 3. Telegram Handler - ТОЛЬКО роутинг

**Файл:** `app/services/telegram_handler.py`

```python
class TelegramHandler:
    """ТОЛЬКО роутинг, никакой бизнес-логики!"""

    async def handle_update(self, update: Update):
        user_id = str(update.effective_user.id)
        message = update.message

        # Проверка режима
        current_mode = await property_service.get_user_mode(user_id)

        if current_mode == BotMode.PROPERTY:
            # Делегировать Property модулю
            await property_handler.handle_property_message(update, user_id, message.text)
        else:
            # Делегировать Calendar модулю (по умолчанию)
            await self._handle_calendar_message(update, user_id, message.text)
```

**Правила:**
- ❌ НЕ добавлять логику в `telegram_handler.py`
- ✅ Только проверка режима и делегирование
- ✅ Вся логика в модулях

### 4. API роутеры - НЕ ТРОГАТЬ существующие

**Calendar API:** `app/routers/events.py`
```python
# ✅ ЭТИ ЭНДПОИНТЫ НЕ ТРОГАТЬ!
GET    /api/events/{user_id}
POST   /api/events/{user_id}
PUT    /api/events/{user_id}/{event_id}
DELETE /api/events/{user_id}/{event_id}
```

**Property API:** `app/routers/property.py`
```python
# ➕ НОВЫЕ ЭНДПОИНТЫ
GET    /api/property/clients
POST   /api/property/listings
GET    /api/property/selections
```

### 5. Docker изоляция

**docker-compose.yml:**
```yaml
services:
  # ✅ Calendar infrastructure (НЕ ТРОГАТЬ)
  radicale:
    image: tomsquest/docker-radicale:latest
    volumes:
      - radicale_data:/data
    restart: unless-stopped

  # Telegram Bot (общий)
  telegram-bot:
    depends_on:
      - radicale
    environment:
      - RADICALE_URL=http://radicale:5232
    restart: unless-stopped

volumes:
  radicale_data:
    # ⚠️ ВАЖНО: НЕ удалять этот volume!
```

### 6. Health Checks для стабильности

**Файл:** `app/health.py`

```python
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/calendar")
async def calendar_health():
    """Проверка здоровья Calendar модуля."""
    from app.services.calendar.calendar_radicale import calendar_service

    radicale_ok = calendar_service.is_connected()

    return {
        "status": "ok" if radicale_ok else "error",
        "radicale": "connected" if radicale_ok else "disconnected"
    }

@router.get("/property")
async def property_health():
    """Проверка здоровья Property модуля."""
    from app.services.property.property_service import property_service

    try:
        # Проверка подключения к БД
        await property_service.get_client("test")
        return {"status": "ok", "database": "connected"}
    except:
        return {"status": "error", "database": "error"}
```

### 7. Автоматические тесты

**Файл:** `tests/test_calendar_stability.py`

```python
import pytest
from app.services.calendar.calendar_radicale import calendar_service

@pytest.mark.asyncio
async def test_calendar_connection():
    """Тест: календарь должен быть доступен."""
    assert calendar_service.is_connected()

@pytest.mark.asyncio
async def test_create_event():
    """Тест: создание события."""
    from app.schemas.events import EventDTO, IntentType
    from datetime import datetime

    event = EventDTO(
        intent=IntentType.CREATE,
        title="Test Event",
        start_time=datetime.now(),
        confidence=1.0,
        raw_text=""
    )

    uid = await calendar_service.create_event("test_user", event)
    assert uid is not None

@pytest.mark.asyncio
async def test_list_events():
    """Тест: получение событий."""
    from datetime import datetime, timedelta

    events = await calendar_service.list_events(
        "test_user",
        datetime.now(),
        datetime.now() + timedelta(days=1)
    )
    assert isinstance(events, list)
```

**Запуск тестов:**
```bash
# Локально
pytest tests/test_calendar_stability.py -v

# На сервере
docker exec telegram-bot pytest tests/test_calendar_stability.py -v
```

### 8. Deployment Guard (защита от ломания)

**Файл:** `deploy-safe.sh`

```bash
#!/bin/bash
set -e

echo "🛡️ Safe Deployment с проверками..."

# 1. Проверка что Calendar API работает
echo "1. Проверка Calendar API..."
curl -f http://localhost:8000/health/calendar || {
    echo "❌ Calendar API не работает! Отмена деплоя."
    exit 1
}

# 2. Запуск тестов
echo "2. Запуск тестов..."
pytest tests/test_calendar_stability.py || {
    echo "❌ Тесты не прошли! Отмена деплоя."
    exit 1
}

# 3. Деплой только Property файлов
echo "3. Деплой Property модуля..."
FILES_TO_DEPLOY=(
    "app/models/property.py"
    "app/schemas/property.py"
    "app/services/property/*.py"
    "app/routers/property.py"
)

for file in "${FILES_TO_DEPLOY[@]}"; do
    scp "$file" "root@server:/path/$file"
done

# 4. Перезапуск только если нужно
echo "4. Проверка нужен ли перезапуск..."
# Только если изменился main.py или telegram_handler.py

echo "✅ Деплой завершён безопасно!"
```

### 9. Monitoring и Alerts

**Файл:** `monitor-calendar.sh`

```bash
#!/bin/bash

# Проверка каждую минуту
while true; do
    STATUS=$(curl -s http://localhost:8000/health/calendar | jq -r '.status')

    if [ "$STATUS" != "ok" ]; then
        echo "⚠️ ALERT: Calendar не работает!"
        # Отправить уведомление
        # ...
    fi

    sleep 60
done
```

### 10. Rollback Plan

**Если что-то сломалось:**

```bash
# 1. Быстрый откат к последней рабочей версии
cd /root/ai-calendar-assistant
git log --oneline -5
git checkout <last-working-commit>
docker restart telegram-bot

# 2. Восстановление данных из бэкапа
cd /root/backups/radicale-data
ls -lth | head -5
tar -xzf radicale-YYYYMMDD_HHMMSS.tar.gz
docker cp data radicale-calendar:/
docker restart radicale-calendar

# 3. Проверка работоспособности
curl http://localhost:8000/health/calendar
```

### 11. Checklist перед каждым деплоем

```
☐ Локальные тесты пройдены
☐ Calendar API НЕ изменён
☐ Health checks добавлены для новых функций
☐ Docker volumes сохранены
☐ Бэкап данных создан
☐ Rollback plan готов
☐ Изменения в отдельном модуле (не в calendar/)
```

### 12. Monitoring Dashboard

**Файл:** `status.html` (доступен на `/status`)

```html
<!DOCTYPE html>
<html>
<head>
    <title>System Status</title>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>Calendar Bot Status</h1>

    <div id="calendar-status">
        <h2>📅 Calendar Module</h2>
        <div class="status"></div>
    </div>

    <div id="property-status">
        <h2>🏠 Property Module</h2>
        <div class="status"></div>
    </div>

    <script>
        async function checkStatus() {
            // Check Calendar
            const calResp = await fetch('/health/calendar');
            const calData = await calResp.json();
            document.querySelector('#calendar-status .status').innerHTML =
                calData.status === 'ok' ? '✅ Working' : '❌ Error';

            // Check Property
            const propResp = await fetch('/health/property');
            const propData = await propResp.json();
            document.querySelector('#property-status .status').innerHTML =
                propData.status === 'ok' ? '✅ Working' : '❌ Error';
        }

        checkStatus();
        setInterval(checkStatus, 30000);
    </script>
</body>
</html>
```

---

## Применение на практике

### Текущая ситуация

**Проблемы:**
1. ❌ Веб-приложение не может редактировать события
2. ❌ Файлы перемешаны (calendar + property в одной папке)
3. ❌ Нет изоляции между модулями
4. ❌ Нет тестов и health checks

### План исправления

1. **Реорганизовать структуру файлов**
   ```bash
   mkdir -p app/services/calendar
   mkdir -p app/services/property

   # Переместить Calendar файлы
   mv app/services/calendar_radicale.py app/services/calendar/
   mv app/services/llm_agent_yandex.py app/services/calendar/
   mv app/services/event_reminders.py app/services/calendar/

   # Переместить Property файлы
   mv app/services/property_*.py app/services/property/
   mv app/services/llm_agent_property.py app/services/property/
   ```

2. **Добавить Health Checks**
   - Создать `/health/calendar`
   - Создать `/health/property`
   - Мониторинг каждую минуту

3. **Создать тесты**
   - `test_calendar_stability.py`
   - Запускать перед каждым деплоем

4. **Исправить веб-приложение**
   - Проверить что API работает
   - Задеплоить правильный файл

5. **Настроить безопасный деплой**
   - `deploy-safe.sh` с проверками
   - Rollback plan

---

## Резюме

### Принципы стабильности:

1. **Изоляция модулей** - Calendar и Property не пересекаются
2. **Не трогать работающее** - Calendar API не изменяется
3. **Health checks** - Постоянный мониторинг
4. **Автоматические тесты** - Перед каждым деплоем
5. **Rollback plan** - Быстрый откат если что-то сломалось
6. **Бэкапы** - Каждые 6 часов автоматически

### Что делать при добавлении новых функций:

✅ **DO:**
- Создавать новые файлы в отдельной папке
- Добавлять health checks
- Писать тесты
- Использовать `deploy-safe.sh`

❌ **DON'T:**
- Не изменять существующие API
- Не трогать `calendar_radicale.py`
- Не изменять `events.py` router
- Не удалять Docker volumes

---

Теперь Calendar Bot будет стабильным и не будет ломаться при добавлении новых функций! 🛡️
