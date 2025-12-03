# 🔄 Инструкция по восстановлению из бэкапа

## 📦 Последний рабочий бэкап

**Дата создания:** 2025-11-01 17:09:43
**Имя бэкапа:** `working_backup_20251101_170943`
**Расположение:** `/root/backups/full/`

**Что включено:**
- ✅ Весь код проекта (773 KB)
- ✅ Данные Radicale (календари пользователей)
- ✅ База данных PostgreSQL (property_db_data)
- ✅ Конфигурация Docker Compose
- ✅ Переменные окружения (.env)

**Рабочие функции в этом бэкапе:**
- ✅ Telegram бот (polling mode)
- ✅ FastAPI сервер на порту 8000
- ✅ Radicale CalDAV сервер
- ✅ PostgreSQL база данных
- ✅ Event Reminders (30 минут до события)
- ✅ Daily Reminders (9:00 утра, 20:00 вечера)
- ✅ Веб-интерфейс (WebApp)

---

## 🚨 Быстрое восстановление (если что-то сломалось)

### Вариант 1: Полное восстановление

```bash
ssh root@91.229.8.221
# Пароль: upvzrr3LH4pxsaqs

# Остановить все контейнеры
cd /root/ai-calendar-assistant
docker-compose down
docker-compose -f docker-compose.production.yml down

# Сохранить текущую версию (на всякий случай)
cd /root
mv ai-calendar-assistant ai-calendar-assistant.broken_$(date +%Y%m%d_%H%M%S)

# Восстановить из бэкапа
cd /root/backups/full
tar -xzf working_backup_20251101_170943.tar.gz -C /root/

# Восстановить данные Radicale
docker run --rm \
  -v radicale_data:/data \
  -v /root/backups/full:/backup \
  alpine tar -xzf /backup/working_backup_20251101_170943_radicale_data.tar.gz -C /

# Восстановить данные PostgreSQL
docker run --rm \
  -v property_db_data:/data \
  -v /root/backups/full:/backup \
  alpine tar -xzf /backup/working_backup_20251101_170943_property_db_data.tar.gz -C /

# Запустить всё заново
cd /root/ai-calendar-assistant
docker-compose up -d radicale property-bot-db
docker-compose -f docker-compose.production.yml up -d --build

# Подключить telegram-bot к internal network
docker network connect ai-calendar-assistant_internal telegram-bot

# Проверить статус
docker ps
docker logs telegram-bot --tail 30
```

### Вариант 2: Восстановить только код (данные остаются)

```bash
ssh root@91.229.8.221

# Остановить контейнеры
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down

# Бэкап текущей версии
cd /root
tar -czf ai-calendar-assistant.backup_$(date +%Y%m%d_%H%M%S).tar.gz ai-calendar-assistant/

# Восстановить код из бэкапа (данные НЕ трогаем)
cd /root/backups/full
tar -xzf working_backup_20251101_170943.tar.gz -C /root/

# Запустить
cd /root/ai-calendar-assistant
docker-compose up -d radicale property-bot-db
docker-compose -f docker-compose.production.yml up -d --build
docker network connect ai-calendar-assistant_internal telegram-bot
```

### Вариант 3: Восстановить только один файл

Если нужно восстановить конкретный файл (например, `run_polling.py`):

```bash
ssh root@91.229.8.221

cd /root/backups/full
tar -xzf working_backup_20251101_170943.tar.gz \
  ai-calendar-assistant/run_polling.py

# Копируем восстановленный файл
cp /root/ai-calendar-assistant/run_polling.py /root/ai-calendar-assistant/run_polling.py

# Перезапускаем контейнер
docker restart telegram-bot
```

---

## 📋 Проверка после восстановления

```bash
# 1. Проверить что все контейнеры работают
docker ps

# Должны быть:
# - telegram-bot (Up, healthy)
# - radicale-calendar (Up, healthy)
# - property-bot-db (Up, healthy)

# 2. Проверить API
curl http://localhost:8000/health
# Ожидаемый ответ: {"status":"ok","version":"0.1.0"}

# 3. Проверить логи бота
docker logs telegram-bot --tail 50 | grep -E "(started|error|Error)"

# Должны увидеть:
# - "Bot is running! Press Ctrl+C to stop."
# - "Daily reminders started (9:00 morning, 20:00 evening)"
# - "Event reminders started (30 minutes before events)"
# - "Uvicorn running on http://0.0.0.0:8000"

# 4. Проверить Radicale
docker logs radicale-calendar --tail 20

# Должно быть: "Radicale server ready"

# 5. Проверить бот в Telegram
# Отправьте /start в @aibroker_bot
# Попробуйте создать событие: "Встреча завтра в 15:00"
```

---

## 🗂 Список всех бэкапов

Посмотреть все доступные бэкапы:

```bash
ssh root@91.229.8.221 "ls -lh /root/backups/full/"
```

---

## ⚠️ Важные замечания

1. **Перед восстановлением** всегда создавайте бэкап текущего состояния
2. **После восстановления** обязательно проверьте все сервисы
3. **Данные пользователей** хранятся в Docker volumes и восстанавливаются отдельно
4. **Переменные окружения** (.env) содержат секреты - храните их в безопасности
5. **Автоматические бэкапы:** система хранит последние 5 бэкапов

---

## 📞 Контакты для доступа

- **Сервер:** 91.229.8.221
- **Пользователь:** root
- **Пароль:** upvzrr3LH4pxsaqs
- **Telegram бот:** @aibroker_bot
- **Web UI:** https://этонесамыйдлинныйдомен.рф

---

## 🔧 Техническая информация о бэкапе

**Структура файлов:**
```
/root/backups/full/
├── working_backup_20251101_170943.tar.gz          # Код проекта
├── working_backup_20251101_170943_radicale_data.tar.gz  # Календари
├── working_backup_20251101_170943_property_db_data.tar.gz  # БД
├── working_backup_20251101_170943_docker-compose.yml
├── working_backup_20251101_170943_docker-compose.production.yml
└── working_backup_20251101_170943_env             # Переменные окружения
```

**Ключевые файлы в бэкапе:**
- `run_polling.py` - запуск бота с EventRemindersService
- `start.sh` - скрипт запуска бота + FastAPI
- `Dockerfile.bot` - конфигурация контейнера
- `app/services/event_reminders.py` - сервис напоминаний за 30 минут
- `app/services/daily_reminders.py` - утренние/вечерние дайджесты
- `app/main.py` - FastAPI приложение

---

Бэкап создан автоматически 2025-11-01 в 17:09:43 после успешного внедрения всех функций.
