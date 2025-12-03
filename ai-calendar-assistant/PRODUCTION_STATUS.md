# 📊 Production Status Report

**Сервер:** 91.229.8.221
**Дата проверки:** 2025-11-23
**Время работы контейнера:** 6+ часов

---

## ✅ ЧТО РАБОТАЕТ

### 1. **Telegram Bot (Polling Mode)**
- **Статус:** 🟢 Running (healthy)
- **Контейнер:** `telegram-bot`
- **Порт:** 8000 (открыт публично)
- **Режим:** Polling (опрашивает Telegram API каждые ~10 секунд)
- **Функции:**
  - ✅ Принимает сообщения от пользователей
  - ✅ Обрабатывает команды
  - ✅ Telegram authentication middleware работает
  - ✅ Security fixes применены:
    - `/api/events/*` защищен
    - `/api/todos/*` защищен
    - `DEBUG=False` в production

### 2. **Инфраструктура**
- **Память:** 2.9GB total, 1.9GB доступно (👍 достаточно)
- **Диск:** 59GB total, 28GB свободно (53% использовано - 👍 норма)
- **Docker:** Работает стабильно
- **Логи:** Чистые, нет критических ошибок

---

## ❌ ЧТО НЕ РАБОТАЕТ

### 1. **Radicale CalDAV Server** (КРИТИЧНО для календаря)
- **Статус:** 🔴 NOT RUNNING
- **Порт:** 5232 (не слушает)
- **Ошибка в логах:**
  ```
  ConnectionRefusedError: [Errno 111] Connection refused
  HTTPConnectionPool(host='localhost', port=5232)
  ```

**Последствия:**
- ❌ Создание событий в календаре НЕ работает
- ❌ Просмотр календаря НЕ работает
- ❌ Напоминания НЕ работают
- ❌ Синхронизация календарей НЕ работает
- ⚠️ Бот пытается каждые N минут подключиться к Radicale, получает ошибку

### 2. **Property Bot & Database**
- **Статус:** 🔴 NOT RUNNING
- **Сервисы:**
  - `property-bot` - контейнер отсутствует
  - `property-bot-db` (PostgreSQL) - контейнер отсутствует

**Последствия:**
- ❌ Функции работы с недвижимостью НЕ работают
- ❌ База данных объектов недвижимости недоступна

---

## 🔍 ТЕКУЩАЯ КОНФИГУРАЦИЯ

### Используется: `docker-compose.production.yml`
```yaml
services:
  telegram-bot:
    container_name: telegram-bot
    ports:
      - "8000:8000"
    # Только базовый бот, БЕЗ Radicale
```

### Доступные compose файлы:
1. **docker-compose.yml** (ПОЛНЫЙ) - 4 сервиса:
   - radicale-calendar
   - ai-calendar-assistant
   - property-bot
   - property-bot-db

2. **docker-compose.production.yml** (ТЕКУЩИЙ) - 1 сервис:
   - telegram-bot (только бот)

3. **docker-compose.hybrid.yml** - гибридная конфигурация
4. **docker-compose.polling.yml** - polling режим
5. И другие варианты...

---

## 🛠️ КАК ИСПРАВИТЬ

### Вариант 1: Запустить ПОЛНУЮ версию (РЕКОМЕНДУЕТСЯ)

**Что даст:**
- ✅ Полная функциональность календаря
- ✅ Radicale для хранения событий
- ✅ Property bot для недвижимости
- ✅ PostgreSQL база данных

**Команды:**
```bash
ssh root@91.229.8.221

cd /root/ai-calendar-assistant

# Остановить текущий контейнер
docker-compose -f docker-compose.production.yml down

# Запустить ПОЛНУЮ версию
docker-compose up -d

# Проверить статус
docker-compose ps

# Проверить логи
docker-compose logs -f
```

**Ожидаемые контейнеры после запуска:**
```
NAME                     STATUS
telegram-bot             Up (healthy)
radicale-calendar        Up (healthy)
property-bot             Up (healthy)
property-bot-db          Up (healthy)
```

---

### Вариант 2: Запустить ТОЛЬКО Radicale (минимальный фикс)

**Если не нужен Property Bot, но нужен календарь:**

```bash
ssh root@91.229.8.221
cd /root/ai-calendar-assistant

# Создать минимальный compose с ботом + radicale
cat > docker-compose.minimal-calendar.yml << 'EOF'
version: '3.8'

services:
  radicale:
    image: tomsquest/docker-radicale:latest
    container_name: radicale-calendar
    ports:
      - "5232:5232"
    volumes:
      - radicale_data:/data
      - ./radicale_config:/config
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5232"]
      interval: 30s
      timeout: 10s
      retries: 3

  telegram-bot:
    container_name: telegram-bot
    build:
      context: .
      dockerfile: Dockerfile.bot
    env_file:
      - .env
    restart: always
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
      - ./credentials:/app/credentials
      - ./data:/var/lib/calendar-bot
    depends_on:
      - radicale
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  radicale_data:
EOF

# Остановить старый
docker-compose -f docker-compose.production.yml down

# Запустить новый
docker-compose -f docker-compose.minimal-calendar.yml up -d

# Проверить
docker-compose -f docker-compose.minimal-calendar.yml ps
```

---

### Вариант 3: Использовать docker-compose.polling.yml

**Проверить содержимое:**
```bash
ssh root@91.229.8.221
cat /root/ai-calendar-assistant/docker-compose.polling.yml
```

Если там есть Radicale:
```bash
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.polling.yml up -d
docker-compose -f docker-compose.polling.yml ps
```

---

## 🔐 ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

**Уже настроены в .env:**
```bash
TELEGRAM_BOT_TOKEN=***REDACTED_BOT_TOKEN***
RADICALE_URL=http://localhost:5232
RADICALE_BOT_PASSWORD=***REDACTED_RADICALE***
```

**Проблема:** Radicale не запущен, поэтому `RADICALE_URL=http://localhost:5232` указывает в никуда.

---

## 📈 МОНИТОРИНГ

### Проверить здоровье после запуска Radicale:

```bash
# 1. Проверить контейнеры
docker ps

# 2. Проверить порт Radicale
netstat -tlnp | grep 5232

# 3. Проверить доступность Radicale
curl http://localhost:5232

# 4. Проверить логи бота (не должно быть ошибок подключения)
docker logs telegram-bot 2>&1 | grep -i "radicale\|5232" | tail -20

# 5. Проверить что напоминания работают
docker logs telegram-bot 2>&1 | grep "events_fetched" | tail -5
```

---

## 🎯 РЕКОМЕНДАЦИИ

### Для минимальной работоспособности:
1. ✅ **Сейчас:** Telegram bot работает (сообщения принимаются)
2. ❌ **Нужно:** Запустить Radicale для функций календаря
3. 🤔 **Опционально:** Запустить Property Bot если нужна работа с недвижимостью

### Для полной функциональности:
```bash
# Запустить ВСЁ одной командой:
ssh root@91.229.8.221 'cd /root/ai-calendar-assistant && \
  docker-compose -f docker-compose.production.yml down && \
  docker-compose up -d && \
  sleep 10 && \
  docker-compose ps && \
  docker-compose logs --tail=20'
```

---

## 📞 TROUBLESHOOTING

### Если после запуска Radicale бот всё равно не подключается:

1. **Проверить network в docker-compose:**
   ```bash
   docker network ls
   docker inspect ai-calendar-assistant_default
   ```

2. **Проверить что Radicale доступен внутри Docker network:**
   ```bash
   docker exec telegram-bot curl -I http://radicale:5232
   # или
   docker exec telegram-bot curl -I http://radicale-calendar:5232
   ```

3. **Обновить RADICALE_URL в .env если нужно:**
   ```bash
   # Если контейнер называется radicale-calendar:
   RADICALE_URL=http://radicale-calendar:5232

   # Перезапустить бота:
   docker-compose restart telegram-bot
   ```

---

## 💡 ИТОГОВЫЕ ВЫВОДЫ

**Текущее состояние: ЧАСТИЧНО РАБОТАЕТ**

- 🟢 **Работает:** Telegram bot (базовые команды, аутентификация)
- 🔴 **НЕ работает:** Календарь (нет Radicale), Property bot
- 🟡 **Статус:** Стабильно, но ограниченная функциональность

**Рекомендуемое действие:**
1. Запустить полный `docker-compose.yml` для восстановления всех функций
2. Проверить логи и убедиться что все сервисы healthy
3. Протестировать создание события в календаре через бота

**Приоритет:** 🔴 ВЫСОКИЙ (основная функциональность недоступна)
