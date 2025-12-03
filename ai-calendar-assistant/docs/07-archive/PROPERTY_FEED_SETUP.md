# Property Feed Setup - Настройка фида недвижимости

**Инструкция по подключению и автообновлению фида**

---

## ✅ Статус фида

**URL фида доступен и работает!**

```
https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78
```

**Проверено:** 2025-10-29

**Результаты проверки:**
- ✅ Фид доступен
- ✅ Формат: Yandex.Realty XML
- ✅ Количество объектов: 11,999 (все квартиры)
- ✅ Размер: ~60 MB
- ✅ Парсер feed_mapper.py совместим

---

## 📊 Данные фида

### Статистика
- **Всего объектов:** 11,999
- **Категория:** 100% квартиры (фильтр по regionGroupId=78)
- **Формат:** XML (Yandex.Realty schema)
- **Регион:** Санкт-Петербург (regionGroupId=78)
- **Обновление:** автоматическое на стороне провайдера

### Пример объекта
```xml
<offer internal-id="1458634">
  <type>продажа</type>
  <property-type>жилая</property-type>
  <category>квартира</category>
  <rooms>2</rooms>
  <area><value>66.30</value><unit>кв.м</unit></area>
  <price><value>20336957</value><currency>RUR</currency></price>
  <renovation>Отделка "под ключ"</renovation>
  <mortgage>true</mortgage>
  <haggle>false</haggle>
  ...
</offer>
```

---

## 🔧 Настройка в проекте

### Шаг 1: Добавить в .env

```bash
# Добавить в файл .env
PROPERTY_FEED_URL="https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78"
PROPERTY_FEED_UPDATE_INTERVAL=21600  # 6 часов в секундах
```

### Шаг 2: Создать сервис загрузки фида

Создать файл `app/services/property/feed_loader.py`:

```python
"""Feed loader service - downloads and processes property feed."""

import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional
import structlog

from app.services.property.feed_mapper import FeedMapper
from app.services.property.property_service import property_service
from app.config import settings

logger = structlog.get_logger()


class FeedLoader:
    """Loads and processes property feed."""

    def __init__(self, feed_url: str):
        self.feed_url = feed_url
        self.last_update: Optional[datetime] = None
        self.last_count: int = 0

    async def download_feed(self) -> bytes:
        """Download feed XML."""
        logger.info("downloading_feed", url=self.feed_url)

        async with aiohttp.ClientSession() as session:
            async with session.get(self.feed_url, timeout=aiohttp.ClientTimeout(total=120)) as response:
                response.raise_for_status()
                content = await response.read()

        logger.info("feed_downloaded", size_mb=len(content) / 1024 / 1024)
        return content

    async def process_feed(self, content: bytes) -> int:
        """Process feed and update database."""
        logger.info("processing_feed")

        # Parse XML
        listings = FeedMapper.parse_feed_xml(content)

        if not listings:
            logger.warning("feed_empty")
            return 0

        logger.info("feed_parsed", listings_count=len(listings))

        # Upsert to database
        created = 0
        updated = 0
        errors = 0

        for listing in listings:
            try:
                # Check if exists
                existing = await property_service.get_listing_by_external_id(listing.external_id)

                if existing:
                    # Update
                    await property_service.update_listing(existing.id, listing)
                    updated += 1
                else:
                    # Create
                    await property_service.create_listing(listing)
                    created += 1

            except Exception as e:
                logger.error("listing_upsert_failed",
                           external_id=listing.external_id,
                           error=str(e))
                errors += 1

        logger.info("feed_processed",
                   total=len(listings),
                   created=created,
                   updated=updated,
                   errors=errors)

        self.last_update = datetime.now()
        self.last_count = len(listings)

        return len(listings)

    async def update_feed(self) -> dict:
        """Download and process feed."""
        start_time = datetime.now()

        try:
            # Download
            content = await self.download_feed()

            # Process
            count = await self.process_feed(content)

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "status": "success",
                "count": count,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }

            logger.info("feed_update_success", **result)
            return result

        except Exception as e:
            logger.error("feed_update_failed", error=str(e))

            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# Global instance
feed_loader = FeedLoader(feed_url=settings.PROPERTY_FEED_URL)
```

### Шаг 3: Добавить endpoint для ручного обновления

В `app/routers/property.py`:

```python
from app.services.property.feed_loader import feed_loader

@router.post("/admin/update-feed")
async def update_feed():
    """Manually trigger feed update (admin only)."""
    result = await feed_loader.update_feed()
    return result

@router.get("/admin/feed-status")
async def feed_status():
    """Get feed status."""
    return {
        "feed_url": feed_loader.feed_url,
        "last_update": feed_loader.last_update.isoformat() if feed_loader.last_update else None,
        "last_count": feed_loader.last_count
    }
```

### Шаг 4: Создать cron задачу

**Вариант A: Через crontab (Linux/Mac)**

```bash
# Редактировать crontab
crontab -e

# Добавить строку (обновление каждые 6 часов)
0 */6 * * * curl -X POST http://localhost:8000/property/admin/update-feed
```

**Вариант B: Через APScheduler (Python)**

Добавить в `app/main.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.property.feed_loader import feed_loader

# Create scheduler
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    """Start background tasks."""

    # Update feed every 6 hours
    scheduler.add_job(
        feed_loader.update_feed,
        'interval',
        hours=6,
        id='property_feed_update',
        replace_existing=True
    )

    scheduler.start()
    logger.info("scheduler_started")

    # Initial update
    await feed_loader.update_feed()

@app.on_event("shutdown")
async def stop_scheduler():
    """Stop background tasks."""
    scheduler.shutdown()
    logger.info("scheduler_stopped")
```

**Установить зависимости:**

```bash
pip install apscheduler
```

**Вариант C: Через Docker + cron**

Создать `cron/property-feed-update`:

```bash
#!/bin/bash
# Update property feed

echo "$(date): Starting feed update..."
curl -X POST http://property-bot:8000/property/admin/update-feed
echo "$(date): Feed update completed"
```

Добавить в `docker-compose.yml`:

```yaml
services:
  property-cron:
    image: property-bot:latest
    command: crond -f -l 2
    volumes:
      - ./cron/property-feed-update:/etc/periodic/6hour/property-feed-update:ro
    depends_on:
      - property-bot
```

---

## 🧪 Тестирование

### Тест 1: Проверка доступности фида

```bash
# Скачать и посмотреть первые 50 строк
curl -s "https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78" | head -50
```

**Ожидаемый результат:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<realty-feed xmlns="http://webmaster.yandex.ru/schemas/feed/realty/2010-06">
  <generation-date>2025-10-29T08:40:43+00:00</generation-date>
  <offer internal-id="1458634">
    ...
```

### Тест 2: Подсчет объектов

```bash
# Подсчитать количество объектов
curl -s "https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78" | grep -c '<offer internal-id='
```

**Ожидаемый результат:** ~12,000

### Тест 3: Парсинг через feed_mapper

```bash
# Запустить тест парсера
python test_feed_download.py
```

**Ожидаемый результат:**
```
✅ Feed is ACCESSIBLE and PARSEABLE
✅ Contains 11,999 total offers
✅ Contains 11,999 apartments
```

### Тест 4: Ручное обновление через API

```bash
# Запустить ручное обновление
curl -X POST http://localhost:8000/property/admin/update-feed
```

**Ожидаемый результат:**
```json
{
  "status": "success",
  "count": 11999,
  "duration_seconds": 45.2,
  "timestamp": "2025-10-29T10:45:00"
}
```

---

## 📊 Мониторинг

### Метрики для отслеживания

1. **Успешность обновления**
   - Процент успешных обновлений за последние 7 дней
   - Целевое значение: >95%

2. **Время обновления**
   - Среднее время загрузки и обработки фида
   - Целевое значение: <60 секунд

3. **Количество объектов**
   - Изменение количества объектов между обновлениями
   - Алерт если изменение >20%

4. **Ошибки парсинга**
   - Количество объектов, которые не удалось распарсить
   - Целевое значение: <5%

### Dashboard metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
feed_updates_total = Counter('property_feed_updates_total', 'Total feed updates', ['status'])
feed_duration = Histogram('property_feed_duration_seconds', 'Feed update duration')
feed_objects_count = Gauge('property_feed_objects_count', 'Number of objects in feed')
feed_errors_total = Counter('property_feed_errors_total', 'Total feed errors')
```

### Алерты (Prometheus AlertManager)

```yaml
groups:
  - name: property_feed
    rules:
      - alert: FeedUpdateFailed
        expr: rate(property_feed_updates_total{status="error"}[1h]) > 0.5
        annotations:
          summary: "Property feed updates failing"

      - alert: FeedObjectsDropped
        expr: delta(property_feed_objects_count[6h]) < -2000
        annotations:
          summary: "Property feed lost >2000 objects"

      - alert: FeedUpdateSlow
        expr: property_feed_duration_seconds > 120
        annotations:
          summary: "Property feed update taking >2 minutes"
```

---

## ⚠️ Troubleshooting

### Проблема: Фид не загружается

**Симптомы:**
```
Error: Connection timeout
```

**Решения:**
1. Проверить интернет-соединение
2. Увеличить timeout в коде (с 60 до 120 секунд)
3. Проверить, не заблокирован ли IP

### Проблема: Ошибки парсинга

**Симптомы:**
```
Error: Invalid XML
```

**Решения:**
1. Проверить кодировку (должна быть UTF-8)
2. Проверить namespace в XML
3. Обновить feed_mapper.py для новых полей

### Проблема: Дубликаты в БД

**Симптомы:**
```
Error: Duplicate key value violates unique constraint
```

**Решения:**
1. Добавить unique constraint на external_id
2. Использовать upsert вместо insert
3. Проверить логику в feed_loader.py

### Проблема: Медленное обновление

**Симптомы:**
```
Feed update takes >5 minutes
```

**Решения:**
1. Использовать bulk insert вместо по одному
2. Добавить индексы на external_id
3. Использовать параллельную обработку (asyncio.gather)

---

## 📋 Checklist развертывания

**Перед запуском в Production:**

- [ ] Добавить PROPERTY_FEED_URL в .env
- [ ] Создать feed_loader.py
- [ ] Добавить endpoints для ручного обновления
- [ ] Настроить cron или APScheduler
- [ ] Запустить первое обновление вручную
- [ ] Проверить логи (errors = 0)
- [ ] Настроить мониторинг (Prometheus)
- [ ] Настроить алерты (AlertManager)
- [ ] Добавить backup БД перед каждым обновлением
- [ ] Протестировать rollback на случай ошибок

**После запуска:**

- [ ] Мониторить первые 3 обновления (каждые 6 часов)
- [ ] Проверить количество объектов (стабильно ~12k)
- [ ] Проверить время обновления (<60 секунд)
- [ ] Проверить ошибки парсинга (<5%)
- [ ] Настроить дополнительные алерты по необходимости

---

## 🎯 Рекомендации

### Оптимизация производительности

1. **Bulk operations**
   ```python
   # Вместо
   for listing in listings:
       await property_service.create_listing(listing)

   # Использовать
   await property_service.bulk_create_listings(listings)
   ```

2. **Параллельная обработка**
   ```python
   # Обрабатывать батчами по 100
   batch_size = 100
   for i in range(0, len(listings), batch_size):
       batch = listings[i:i+batch_size]
       await asyncio.gather(*[process_listing(l) for l in batch])
   ```

3. **Кэширование unchanged objects**
   ```python
   # Проверять hash перед update
   new_hash = hash_listing(listing)
   if existing.hash == new_hash:
       continue  # Skip unchanged
   ```

### Безопасность

1. **Защита endpoint**
   ```python
   @router.post("/admin/update-feed")
   async def update_feed(api_key: str = Header(...)):
       if api_key != settings.ADMIN_API_KEY:
           raise HTTPException(401, "Unauthorized")
       ...
   ```

2. **Rate limiting**
   ```python
   @router.post("/admin/update-feed")
   @limiter.limit("1/hour")  # Максимум 1 обновление в час
   async def update_feed():
       ...
   ```

3. **Credentials в .env**
   ```bash
   # НЕ хранить логин/пароль в коде!
   PROPERTY_FEED_LOGIN=titworking_mail_ru
   PROPERTY_FEED_PASSWORD=q3uCvV5Y6GB
   PROPERTY_FEED_REGION=78
   ```

---

## 📞 Поддержка

### Контакты провайдера фида

- **Сервис:** ecatalog-service.nmarket.pro
- **Формат:** База.Про (Yandex.Realty XML)
- **Доступ:** логин/пароль в URL

### Документация

- **Feed Mapper:** [app/services/property/feed_mapper.py](app/services/property/feed_mapper.py)
- **Тесты:** [tests/test_feed_mapper.py](tests/test_feed_mapper.py)
- **Схема:** [app/schemas/property.py](app/schemas/property.py)

---

**Статус:** ✅ Готово к внедрению
**Дата:** 2025-10-29
**Версия:** 1.0
