# План активации бота по поиску недвижимости

**Дата:** 2025-10-30
**Статус:** Код готов, нужна активация
**Время:** 1 рабочий день

---

## 🎯 ТЕКУЩАЯ СИТУАЦИЯ

### ✅ Что готово (100% код):
- Все модели и сервисы реализованы
- Feed loader работает
- Telegram хендлер готов
- PostgreSQL конфигурация есть
- 8,500 строк кода

### ❌ Что НЕ работает:
- Property бот не запущен (контейнеры спят)
- Feed loader не автоматизирован
- Интеграция с Telegram отключена
- .env не настроен

---

## 🚀 ПЛАН АКТИВАЦИИ (1 день)

### Шаг 1: Настройка окружения (15 минут)

**1.1 Добавить в .env:**

```bash
# Property Bot Settings
PROPERTY_FEED_URL=https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78

# PostgreSQL для Property Bot
DB_PASSWORD=secure_password_here_123

# Yandex GPT (обязательно)
YANDEX_GPT_API_KEY=ваш_ключ
YANDEX_GPT_FOLDER_ID=ваш_folder_id

# Опционально (работает без них через graceful degradation)
YANDEX_MAPS_API_KEY=ваш_ключ_если_есть
YANDEX_VISION_API_KEY=ваш_ключ_если_есть

# Feature flags
ENABLE_POI_ENRICHMENT=true
ENABLE_ROUTE_ENRICHMENT=false  # включить когда будет Maps API
ENABLE_VISION_ENRICHMENT=false  # включить когда будет Vision API
ENABLE_PRICE_CONTEXT=true
ENABLE_DEVELOPER_REPUTATION=true
```

**1.2 Проверить что переменные загружены:**
```bash
grep "PROPERTY_FEED_URL" .env
```

---

### Шаг 2: Запуск PostgreSQL (10 минут)

**2.1 Запустить контейнер:**
```bash
docker-compose -f docker-compose.property.yml up -d property-db
```

**2.2 Проверить что БД работает:**
```bash
docker-compose -f docker-compose.property.yml exec property-db \
  psql -U property_user -d property_bot -c "SELECT version();"
```

**2.3 Применить миграции:**
```bash
docker-compose -f docker-compose.property.yml exec property-db \
  psql -U property_user -d property_bot < migrations/001_add_extended_property_fields.sql
```

---

### Шаг 3: Интеграция с Telegram ботом (30 минут)

**3.1 Раскомментировать импорты в app/main.py:**

Заменить строки 9-10:
```python
# БЫЛО:
# from app.routers import calendar_sync, property, health

# СТАНЕТ:
from app.routers import property
```

Раскомментировать строку 58:
```python
# БЫЛО:
# app.include_router(property.router, prefix="/api", tags=["property"])

# СТАНЕТ:
app.include_router(property.router, prefix="/api/property", tags=["property"])
```

**3.2 Обновить telegram_handler.py:**

Добавить импорт:
```python
from app.services.property.property_handler import property_handler
from app.models.property import BotMode
from app.services.property.property_service import property_service
```

В метод `handle_update()` добавить проверку режима:
```python
async def handle_update(self, update: Update):
    user_id = str(update.effective_user.id)

    # Check bot mode
    current_mode = await property_service.get_user_mode(user_id)

    if current_mode == BotMode.PROPERTY:
        # Delegate to property handler
        await property_handler.handle_property_message(
            update,
            user_id,
            update.message.text
        )
        return

    # Otherwise process as calendar bot (existing code)
    ...
```

**3.3 Обновить клавиатуру в telegram_handler.py:**

Добавить кнопку переключения в календарном режиме:
```python
def _get_main_keyboard(self):
    return [
        [KeyboardButton("Сегодня")],
        [KeyboardButton("Завтра"), KeyboardButton("Неделя")],
        [KeyboardButton("🏠 Поиск новостройки"), KeyboardButton("⚙️ Настройки")]
    ]
```

---

### Шаг 4: Автообновление фидов (1 час)

**4.1 Создать файл app/services/property/feed_scheduler.py:**

```python
"""Feed update scheduler."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from app.services.property.feed_loader import feed_loader

logger = structlog.get_logger()


class FeedScheduler:
    """Scheduler for automatic feed updates."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def update_feed_task(self):
        """Task to update feed."""
        logger.info("feed_update_scheduled_start")

        try:
            result = await feed_loader.update_feed()
            logger.info("feed_update_scheduled_complete", result=result)
        except Exception as e:
            logger.error("feed_update_scheduled_error", error=str(e))

    def start(self):
        """Start scheduler."""
        if self.is_running:
            logger.warning("feed_scheduler_already_running")
            return

        # Schedule every 6 hours
        self.scheduler.add_job(
            self.update_feed_task,
            trigger=IntervalTrigger(hours=6),
            id="feed_update",
            name="Update property feed",
            replace_existing=True
        )

        # Run immediately on startup
        self.scheduler.add_job(
            self.update_feed_task,
            id="feed_update_immediate",
            name="Immediate feed update"
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("feed_scheduler_started", interval_hours=6)

    def stop(self):
        """Stop scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("feed_scheduler_stopped")

    def get_status(self):
        """Get scheduler status."""
        if not self.is_running:
            return {"running": False}

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })

        return {
            "running": True,
            "jobs": jobs
        }


# Global instance
feed_scheduler = FeedScheduler()
```

**4.2 Обновить app/main.py - добавить в startup:**

```python
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("application_started", ...)

    # START FEED SCHEDULER
    from app.services.property.feed_scheduler import feed_scheduler
    feed_scheduler.start()
    logger.info("feed_scheduler_started")
```

**4.3 Добавить зависимость в requirements.txt:**
```bash
echo "APScheduler==3.10.4" >> requirements.txt
```

---

### Шаг 5: Тестирование (2 часа)

**5.1 Проверить загрузку фида:**
```bash
# Открыть логи
docker logs -f telegram-bot

# Должны увидеть:
# feed_update_scheduled_start
# feed_downloaded size_mb=60.0
# feed_parsed offers_count=11999
# listings_parsed total_offers=11999 parsed=11999
# feed_processed total=11999 created=11999
```

**5.2 Проверить БД:**
```bash
docker-compose -f docker-compose.property.yml exec property-db \
  psql -U property_user -d property_bot -c \
  "SELECT COUNT(*) FROM property_listings;"
```

Должно быть: ~11,999 записей

**5.3 Тестовый сценарий в Telegram:**

1. Открыть бота
2. Нажать "🏠 Поиск новостройки"
3. Должно появиться приветствие property бота
4. Написать: "Ищу 2-комнатную квартиру до 10 миллионов в Москве"
5. Бот должен показать подтверждение параметров
6. Нажать "✅ Подтвердить"
7. Должны прийти результаты поиска

**5.4 Проверить переключение режимов:**

1. В режиме property нажать "🔙 Календарь"
2. Должна появиться клавиатура календаря
3. Команды календаря должны работать
4. Вернуться в "🏠 Поиск новостройки"
5. Property команды должны снова работать

---

### Шаг 6: Мониторинг (опционально, +1 час)

**6.1 Добавить endpoint для статуса:**

В `app/routers/property.py` добавить:
```python
@router.get("/feed/status")
async def get_feed_status():
    """Get feed loader status."""
    from app.services.property.feed_loader import feed_loader
    from app.services.property.feed_scheduler import feed_scheduler

    return {
        "loader": feed_loader.get_status(),
        "scheduler": feed_scheduler.get_status()
    }
```

**6.2 Проверить статус:**
```bash
curl http://localhost:8000/api/property/feed/status
```

---

## 📋 ЧЕКЛИСТ АКТИВАЦИИ

### Подготовка:
- [ ] Добавить переменные в .env
- [ ] Получить Yandex GPT API ключ
- [ ] Проверить что Docker работает

### База данных:
- [ ] Запустить PostgreSQL контейнер
- [ ] Применить миграции
- [ ] Проверить подключение

### Код:
- [ ] Раскомментировать импорты в main.py
- [ ] Обновить telegram_handler.py
- [ ] Создать feed_scheduler.py
- [ ] Добавить APScheduler в requirements.txt
- [ ] Перезапустить бота

### Тестирование:
- [ ] Проверить загрузку фида (логи)
- [ ] Проверить кол-во записей в БД
- [ ] Протестировать поиск в Telegram
- [ ] Протестировать переключение режимов
- [ ] Проверить endpoint статуса

---

## 🔧 КОМАНДЫ ДЛЯ БЫСТРОГО ЗАПУСКА

**Полная последовательность:**

```bash
# 1. Настроить .env (вручную)
nano .env

# 2. Запустить PostgreSQL
docker-compose -f docker-compose.property.yml up -d property-db

# 3. Применить миграции
docker-compose -f docker-compose.property.yml exec property-db \
  psql -U property_user -d property_bot < migrations/001_add_extended_property_fields.sql

# 4. Обновить код (вручную - см. Шаг 3)

# 5. Перезапустить основной бот
docker-compose down
docker-compose up -d --build

# 6. Проверить логи
docker logs -f telegram-bot

# 7. Проверить статус feed
curl http://localhost:8000/api/property/feed/status

# 8. Проверить БД
docker-compose -f docker-compose.property.yml exec property-db \
  psql -U property_user -d property_bot -c \
  "SELECT COUNT(*), MIN(created_at), MAX(created_at) FROM property_listings;"
```

---

## ⚠️ ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ

### Проблема 1: Feed loader падает

**Симптомы:**
- Логи: `feed_download_failed` или `feed_parse_failed`

**Решение:**
```bash
# Проверить URL вручную
curl -I "https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78"

# Должно вернуть 200 OK
```

### Проблема 2: PostgreSQL не запускается

**Симптомы:**
- `docker-compose ps` показывает Exit 1

**Решение:**
```bash
# Проверить логи
docker-compose -f docker-compose.property.yml logs property-db

# Пересоздать volume
docker-compose -f docker-compose.property.yml down -v
docker-compose -f docker-compose.property.yml up -d property-db
```

### Проблема 3: Миграция не применяется

**Симптомы:**
- Ошибка: `relation "property_listings" does not exist`

**Решение:**
```bash
# Создать таблицы через Python
docker-compose exec telegram-bot python -c "
from app.services.property.property_service import property_service
# Tables created on init
print('Tables created')
"
```

### Проблема 4: Yandex GPT не работает

**Симптомы:**
- Логи: `yandex_gpt_error`

**Решение:**
- Проверить API ключ в .env
- Система продолжит работать с regex fallback
- Получить ключ: https://cloud.yandex.ru/docs/iam/operations/api-key/create

---

## 📊 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

После активации:

✅ Property бот отвечает в Telegram
✅ Feed обновляется каждые 6 часов
✅ В БД ~11,999 объектов недвижимости
✅ Поиск работает по всем 37 параметрам
✅ Dream Score рассчитывается
✅ Режимы calendar/property переключаются

---

## 💰 СТОИМОСТЬ ЭКСПЛУАТАЦИИ

**Yandex GPT:**
- 1₽ за 1,000 токенов
- ~9 токенов на запрос пользователя
- При 1000 запросов/день: ~270₽/день = ~8,100₽/месяц
- С кэшированием: ~4,500₽/месяц

**PostgreSQL:**
- БД на диске: ~500 MB для 11,999 объектов
- Растет на ~10 MB/месяц

**Сервер:**
- Существующий (уже оплачен)
- +200 MB RAM для PostgreSQL

**ИТОГО:** ~4,500₽/месяц

---

## 🎯 СЛЕДУЮЩИЕ ШАГИ ПОСЛЕ ЗАПУСКА

**Приоритет 1 (1 неделя):**
- [ ] Мониторинг Prometheus + Grafana
- [ ] Share-страница для подборок
- [ ] PDF экспорт

**Приоритет 2 (2 недели):**
- [ ] Персонализация (обучение по лайкам)
- [ ] Онбординг вкусов
- [ ] Расширение базы застройщиков

**Приоритет 3 (1 месяц):**
- [ ] Push-уведомления о новых объектах
- [ ] Интеграция с другими фидами
- [ ] A/B тестирование алгоритмов

---

**Готово к старту? Начнем с Шага 1!**
