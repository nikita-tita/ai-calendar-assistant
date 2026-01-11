# Operational Runbooks

> **Проект:** AI Calendar Assistant
> **Сервер:** 95.163.227.26
> **Последнее обновление:** 2026-01-11
> **Автор:** DEV-7 (QA/Tech Writer)

---

## Содержание

1. [Daily Health Check](#1-daily-health-check)
2. [Incident Response](#2-incident-response)
3. [Troubleshooting Guide](#3-troubleshooting-guide)
4. [Backup & Restore](#4-backup--restore)
5. [Escalation Matrix](#5-escalation-matrix)

---

## 1. Daily Health Check

### Чеклист ежедневной проверки

Выполнять ежедневно в 09:00 (или после 03:00, когда завершается бэкап):

- [ ] Проверить статус контейнеров
- [ ] Проверить /health endpoint
- [ ] Проверить свободное место на диске
- [ ] Проверить логи на ошибки за последние 24 часа
- [ ] Проверить ночной бэкап (выполняется в 03:00)
- [ ] Проверить метрики в Grafana (если настроен мониторинг)

### Команды для проверки

```bash
# SSH на сервер
ssh root@95.163.227.26

# Перейти в рабочую директорию
cd /root/ai-calendar-assistant/ai-calendar-assistant

# ============================================
# 1. Статус контейнеров
# ============================================
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Ожидаемый результат:
# NAMES               STATUS          PORTS
# telegram-bot        Up X hours      0.0.0.0:8000->8000/tcp
# calendar-redis      Up X hours      6379/tcp
# radicale-calendar   Up X hours      5232/tcp

# ============================================
# 2. Health check API
# ============================================
curl -s http://localhost:8000/health | jq

# Ожидаемый результат:
# {
#   "status": "healthy",
#   "version": "...",
#   "timestamp": "..."
# }

# Проверка с таймаутом (для алертов)
curl -s --max-time 5 http://localhost:8000/health || echo "ALERT: Health check failed!"

# ============================================
# 3. Disk space
# ============================================
df -h /

# Критическое значение: < 10% свободного места
# Для автоалерта:
FREE_SPACE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$FREE_SPACE" -gt 90 ]; then
    echo "ALERT: Disk usage is ${FREE_SPACE}%!"
fi

# ============================================
# 4. Логи ошибок (последние 24 часа)
# ============================================
docker logs telegram-bot --since 24h 2>&1 | grep -i -E "(error|exception|traceback|critical)" | tail -20

# Количество ошибок:
ERROR_COUNT=$(docker logs telegram-bot --since 24h 2>&1 | grep -ci "error")
echo "Ошибок за 24 часа: $ERROR_COUNT"

# ============================================
# 5. Проверка ночного бэкапа
# ============================================
ls -la /root/backups/calendar/ | tail -5

# Проверить что бэкап свежий (не старше 24 часов)
LATEST_BACKUP=$(ls -t /root/backups/calendar/*.tar.gz* 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "$LATEST_BACKUP")) / 3600 ))
    echo "Последний бэкап: $LATEST_BACKUP (${BACKUP_AGE}ч назад)"
    if [ "$BACKUP_AGE" -gt 25 ]; then
        echo "ALERT: Бэкап старше 25 часов!"
    fi
else
    echo "ALERT: Бэкапы не найдены!"
fi

# ============================================
# 6. Мониторинг (если развернут)
# ============================================
# Prometheus
curl -s http://localhost:9090/-/healthy && echo "Prometheus: OK" || echo "Prometheus: DOWN"

# Grafana
curl -s http://localhost:3000/api/health && echo "Grafana: OK" || echo "Grafana: DOWN"

# Loki
curl -s http://localhost:3100/ready && echo "Loki: OK" || echo "Loki: DOWN"
```

### Автоматический health check скрипт

```bash
#!/bin/bash
# /root/scripts/daily-health-check.sh

set -euo pipefail

LOG_FILE="/var/log/calendar-health-check.log"
ALERT_EMAIL="admin@example.com"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

alert() {
    log "ALERT: $1"
    # Раскомментировать для email алертов:
    # echo "$1" | mail -s "Calendar Health Alert" "$ALERT_EMAIL"
}

log "=== Daily Health Check Started ==="

# Check containers
for container in telegram-bot calendar-redis radicale-calendar; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        log "Container $container: UP"
    else
        alert "Container $container: DOWN"
    fi
done

# Check health endpoint
if curl -s --max-time 5 http://localhost:8000/health | grep -q "healthy"; then
    log "Health endpoint: OK"
else
    alert "Health endpoint: FAILED"
fi

# Check disk space
FREE_SPACE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$FREE_SPACE" -gt 90 ]; then
    alert "Disk usage is ${FREE_SPACE}%"
else
    log "Disk usage: ${FREE_SPACE}%"
fi

log "=== Daily Health Check Completed ==="
```

---

## 2. Incident Response

### Severity Levels (Уровни критичности)

| Level | Название | Описание | SLA Response | SLA Resolve |
|-------|----------|----------|--------------|-------------|
| **P1** | Critical | Полный даунтайм, все пользователи не могут использовать сервис | 5 мин | 1 час |
| **P2** | Major | Частичная деградация (напр. Telegram работает, WebApp нет) | 15 мин | 4 часа |
| **P3** | Minor | Косметические проблемы, влияние на <5% пользователей | 1 час | 24 часа |
| **P4** | Low | Улучшения, запросы на новые фичи | 24 часа | Backlog |

### P1: Сервис полностью недоступен

**Симптомы:**
- Бот не отвечает на сообщения
- /health endpoint не отвечает
- Все контейнеры упали

**Диагностика и восстановление:**

```bash
# SSH на сервер
ssh root@95.163.227.26
cd /root/ai-calendar-assistant/ai-calendar-assistant

# ============================================
# ШАГ 1: Быстрая диагностика (1 мин)
# ============================================
docker ps -a
docker logs telegram-bot --tail 50

# ============================================
# ШАГ 2: Попытка перезапуска (2 мин)
# ============================================
docker-compose -f docker-compose.secure.yml restart telegram-bot

# Подождать 30 секунд
sleep 30

# Проверить
curl -s http://localhost:8000/health | jq

# ============================================
# ШАГ 3: Если не помогло - полный рестарт (3 мин)
# ============================================
docker-compose -f docker-compose.secure.yml down
docker-compose -f docker-compose.secure.yml up -d

# Подождать healthcheck
sleep 60

# Проверить все контейнеры
docker ps --format "table {{.Names}}\t{{.Status}}"

# ============================================
# ШАГ 4: Если все еще не работает - проверить ресурсы
# ============================================
# Память
free -h

# Диск
df -h

# CPU
top -bn1 | head -5

# Если память < 100MB или диск > 95%, освободить:
docker system prune -f

# ============================================
# ШАГ 5: Проверить логи на root cause
# ============================================
docker logs telegram-bot 2>&1 | tail -100

# ============================================
# ШАГ 6: Escalation если > 15 мин без прогресса
# ============================================
# См. раздел Escalation Matrix
```

### P2: Частичная деградация

**Симптомы:**
- Telegram бот работает, но медленно
- WebApp не загружается
- Ошибки у части пользователей

**Диагностика:**

```bash
# Проверить все зависимости
docker-compose -f docker-compose.secure.yml ps

# Проверить Redis
docker exec calendar-redis redis-cli ping  # Должно вернуть PONG

# Проверить Radicale
docker exec radicale-calendar curl -s http://localhost:5232

# Проверить сетевую связность
docker exec telegram-bot ping -c 3 calendar-redis
docker exec telegram-bot ping -c 3 radicale-calendar

# Проверить память контейнера
docker stats --no-stream telegram-bot
```

### P3: Minor Issues

**Симптомы:**
- Отдельные фичи работают некорректно
- Задержки в ответах бота
- UI глитчи

**Действия:**
1. Собрать логи проблемы
2. Создать issue в GitHub
3. Включить в следующий спринт

---

## 3. Troubleshooting Guide

### 3.1 "database is locked" (SQLite)

**Симптомы:** В логах ошибка `sqlite3.OperationalError: database is locked`

**Причина:** Несколько процессов пытаются писать в SQLite одновременно

**Решение:**

```bash
# 1. Найти процессы с открытыми файлами БД
docker exec telegram-bot fuser /app/data/*.db

# 2. Перезапустить контейнер (освободит блокировки)
docker-compose -f docker-compose.secure.yml restart telegram-bot

# 3. Если повторяется часто - включить WAL mode:
docker exec telegram-bot python -c "
import sqlite3
conn = sqlite3.connect('/app/data/calendar.db')
conn.execute('PRAGMA journal_mode=WAL;')
conn.close()
"
```

**Превентивные меры:**
- Не запускать несколько экземпляров бота
- Использовать connection pooling с max_connections=1

---

### 3.2 Telegram webhook не работает

**Симптомы:** Бот не отвечает на сообщения в Telegram

**Диагностика:**

```bash
# 1. Проверить текущий режим работы
docker logs telegram-bot 2>&1 | grep -i "polling\|webhook"

# 2. Проверить webhook статус (если используется webhook)
TOKEN=$(grep TELEGRAM_BOT_TOKEN /root/ai-calendar-assistant/ai-calendar-assistant/.env | cut -d= -f2)
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | jq

# 3. Если используется polling - проверить подключение
docker logs telegram-bot 2>&1 | grep -i "polling" | tail -5
```

**Решение для polling mode (текущий режим):**

```bash
# Перезапустить бота
docker-compose -f docker-compose.secure.yml restart telegram-bot

# Проверить что polling запустился
docker logs telegram-bot 2>&1 | grep -i "polling"
```

**Решение для webhook mode:**

```bash
# Установить webhook
TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d= -f2)
WEBHOOK_URL="https://calendar.housler.ru/webhook"

curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
    -d "url=${WEBHOOK_URL}"

# Проверить
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo" | jq
```

---

### 3.3 Memory usage высокий (>80%)

**Симптомы:** Контейнер потребляет много памяти, система тормозит

**Диагностика:**

```bash
# Общая память системы
free -h

# Память по контейнерам
docker stats --no-stream

# Топ процессов в контейнере
docker exec telegram-bot top -bn1
```

**Решение:**

```bash
# 1. Очистить Docker cache
docker system prune -f

# 2. Перезапустить контейнер (сбросит память)
docker-compose -f docker-compose.secure.yml restart telegram-bot

# 3. Если проблема в логах - очистить
docker logs telegram-bot --tail 0  # Не работает - логи immutable
# Вместо этого - перезапустить с новым контейнером:
docker-compose -f docker-compose.secure.yml up -d --force-recreate telegram-bot

# 4. Ограничить память в docker-compose (уже сделано):
# deploy.resources.limits.memory: 1G
```

**Мониторинг памяти:**

```bash
# Добавить в cron для алертов
echo "*/5 * * * * /root/scripts/check-memory.sh" >> /etc/crontab
```

---

### 3.4 Redis connection refused

**Симптомы:** Ошибки `redis.exceptions.ConnectionError`

**Диагностика и решение:**

```bash
# 1. Проверить статус Redis
docker ps | grep redis

# 2. Если не запущен - запустить
docker-compose -f docker-compose.secure.yml up -d redis

# 3. Проверить healthcheck
docker exec calendar-redis redis-cli ping

# 4. Проверить сетевую связность
docker exec telegram-bot ping -c 3 calendar-redis

# 5. Если проблема с сетью - пересоздать network
docker network rm ai-calendar-assistant_calendar-network
docker-compose -f docker-compose.secure.yml up -d
```

---

### 3.5 Radicale (CalDAV) недоступен

**Симптомы:** События не сохраняются, ошибки `Connection refused` к Radicale

**Диагностика и решение:**

```bash
# 1. Проверить статус
docker ps | grep radicale

# 2. Проверить логи
docker logs radicale-calendar --tail 20

# 3. Проверить доступность внутри сети
docker exec telegram-bot curl -s http://radicale:5232

# 4. Если не работает - перезапустить
docker-compose -f docker-compose.secure.yml restart radicale

# 5. Проверить volume
docker volume inspect ai-calendar-assistant_radicale-data
```

---

### 3.6 Yandex GPT API ошибки

**Симптомы:** AI не распознает команды, ошибки `YandexGPT API error`

**Диагностика:**

```bash
# 1. Проверить логи
docker logs telegram-bot 2>&1 | grep -i "yandex\|gpt\|llm" | tail -20

# 2. Проверить API key в .env
grep YANDEX_GPT .env

# 3. Тест API напрямую
TOKEN=$(grep YANDEX_GPT_API_KEY .env | cut -d= -f2)
FOLDER=$(grep YANDEX_GPT_FOLDER_ID .env | cut -d= -f2)

curl -X POST \
    -H "Authorization: Api-Key ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "modelUri": "gpt://'"$FOLDER"'/yandexgpt-lite",
        "completionOptions": {"temperature": 0.3, "maxTokens": 100},
        "messages": [{"role": "user", "text": "Привет"}]
    }' \
    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
```

**Решение:**
- Проверить баланс в Yandex Cloud
- Проверить лимиты API
- Проверить срок действия API key

---

### 3.7 Контейнер перезапускается в цикле

**Симптомы:** `docker ps` показывает `Restarting (1) X seconds ago`

**Диагностика:**

```bash
# 1. Посмотреть причину exit
docker logs telegram-bot 2>&1 | tail -50

# 2. Проверить exit code
docker inspect telegram-bot --format='{{.State.ExitCode}}'

# Exit codes:
# 0 - нормальное завершение
# 1 - ошибка приложения
# 137 - killed (OOM)
# 139 - segfault

# 3. Если OOM - увеличить лимит памяти или найти утечку
docker stats telegram-bot
```

---

## 4. Backup & Restore

### 4.1 Автоматические бэкапы

**Расположение:** `/root/backups/calendar/`
**Расписание:** Ежедневно в 03:00 (cron)
**Retention:** 30 дней

**Что бэкапится:**
- Radicale data (календарные события всех пользователей)
- Bot data (настройки, аналитика, напоминания)
- .env конфигурация
- docker-compose.yml

**Проверка cron:**

```bash
crontab -l | grep backup

# Должно быть:
# 0 3 * * * /root/ai-calendar-assistant/ai-calendar-assistant/backup-calendar.sh >> /var/log/calendar-backup.log 2>&1
```

### 4.2 Ручной бэкап

```bash
cd /root/ai-calendar-assistant/ai-calendar-assistant

# Запустить скрипт бэкапа
./backup-calendar.sh

# Или создать quick backup вручную:
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p /root/backups/calendar/$DATE

# Бэкап Radicale
docker run --rm \
    --volumes-from radicale-calendar \
    -v /root/backups/calendar/$DATE:/backup \
    alpine tar czf /backup/radicale_data.tar.gz /data

# Бэкап bot data
docker exec telegram-bot tar czf - /var/lib/calendar-bot > /root/backups/calendar/$DATE/bot_data.tar.gz

# Бэкап конфигов
cp .env /root/backups/calendar/$DATE/.env.backup

echo "Backup created: /root/backups/calendar/$DATE"
ls -la /root/backups/calendar/$DATE
```

### 4.3 Восстановление из бэкапа

**ВНИМАНИЕ:** Восстановление ЗАМЕНИТ все текущие данные!

```bash
cd /root/ai-calendar-assistant/ai-calendar-assistant

# Список доступных бэкапов
ls -la /root/backups/calendar/

# Выбрать бэкап для восстановления
BACKUP_FILE="/root/backups/calendar/20260111_030000.tar.gz"

# Запустить restore script
./restore-from-backup.sh $BACKUP_FILE

# Или вручную:

# 1. Остановить сервисы
docker-compose -f docker-compose.secure.yml down

# 2. Распаковать бэкап (если зашифрован)
cd /tmp
gpg --decrypt $BACKUP_FILE.gpg > backup.tar.gz
tar xzf backup.tar.gz
BACKUP_DIR=$(ls -d */ | head -1)

# 3. Восстановить Radicale data
docker volume rm ai-calendar-assistant_radicale-data 2>/dev/null || true
docker run --rm \
    -v ai-calendar-assistant_radicale-data:/data \
    -v /tmp/$BACKUP_DIR:/backup \
    alpine sh -c "cd / && tar xzf /backup/radicale_data.tar.gz"

# 4. Восстановить bot data
docker volume rm ai-calendar-assistant_bot-data 2>/dev/null || true
docker run --rm \
    -v ai-calendar-assistant_bot-data:/var/lib/calendar-bot \
    -v /tmp/$BACKUP_DIR:/backup \
    alpine sh -c "cd / && tar xzf /backup/bot_data.tar.gz"

# 5. Восстановить конфиги
cp /tmp/$BACKUP_DIR/.env.backup /root/ai-calendar-assistant/ai-calendar-assistant/.env

# 6. Запустить сервисы
cd /root/ai-calendar-assistant/ai-calendar-assistant
docker-compose -f docker-compose.secure.yml up -d

# 7. Проверить
docker ps
curl http://localhost:8000/health
```

### 4.4 Верификация бэкапа

```bash
# Ежемесячно проверять что бэкапы можно восстановить:

# 1. Взять последний бэкап
LATEST=$(ls -t /root/backups/calendar/*.tar.gz* | head -1)

# 2. Проверить целостность
if [[ "$LATEST" == *.gpg ]]; then
    gpg --decrypt "$LATEST" | tar tzf - > /dev/null && echo "OK: Backup is valid"
else
    tar tzf "$LATEST" > /dev/null && echo "OK: Backup is valid"
fi

# 3. Проверить размер (не должен быть 0 или слишком маленьким)
SIZE=$(stat -c %s "$LATEST")
if [ "$SIZE" -lt 1000 ]; then
    echo "WARNING: Backup seems too small ($SIZE bytes)"
fi
```

---

## 5. Escalation Matrix

### Контакты для эскалации

| Level | Роль | Контакт | Когда эскалировать |
|-------|------|---------|-------------------|
| **L1** | On-call Engineer | @on_call_telegram | Любой P1/P2 инцидент |
| **L2** | Tech Lead | tech-lead@example.com | P1 без прогресса > 15 мин |
| **L3** | DevOps/SRE | devops@example.com | Инфраструктурные проблемы |
| **L4** | Management | cto@example.com | P1 > 1 час, потеря данных |

### Правила эскалации

```
P1 Critical:
├── 0-5 мин: L1 начинает диагностику
├── 5-15 мин: Если нет прогресса → эскалация на L2
├── 15-30 мин: Если нет решения → эскалация на L3
├── 30-60 мин: → эскалация на L4
└── > 60 мин: Постмортем обязателен

P2 Major:
├── 0-15 мин: L1 начинает диагностику
├── 15-60 мин: Если нет прогресса → эскалация на L2
└── > 4 часов: Постмортем рекомендован
```

### Шаблон уведомления об инциденте

```
[SEVERITY: P1/P2/P3]
[SERVICE: AI Calendar Assistant]
[TIME: 2026-01-11 10:30 UTC]

СИМПТОМЫ:
- Бот не отвечает на сообщения
- Health endpoint timeout

ДЕЙСТВИЯ ПРЕДПРИНЯТЫ:
1. Проверен статус контейнеров - telegram-bot DOWN
2. Попытка рестарта - failed
3. Проверены логи - OOM kill

ТЕКУЩИЙ СТАТУС: В работе

ТРЕБУЕТСЯ:
- Увеличение памяти сервера
- Или оптимизация приложения

ETA: 30 мин (после эскалации на L3)
```

---

## Appendix: Quick Reference

### Полезные однострочники

```bash
# Быстрая проверка всего
docker ps && curl -s http://localhost:8000/health | jq && df -h /

# Количество ошибок за последний час
docker logs telegram-bot --since 1h 2>&1 | grep -ci error

# Последние 10 ошибок
docker logs telegram-bot 2>&1 | grep -i error | tail -10

# Memory usage всех контейнеров
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"

# Перезапуск всего
docker-compose -f docker-compose.secure.yml down && docker-compose -f docker-compose.secure.yml up -d

# Проверка что мониторинг работает
for port in 9090 3000 3100; do curl -s "http://localhost:$port" > /dev/null && echo "Port $port: OK" || echo "Port $port: FAIL"; done
```

### Важные пути

| Путь | Описание |
|------|----------|
| `/root/ai-calendar-assistant/ai-calendar-assistant/` | Рабочая директория |
| `/root/backups/calendar/` | Бэкапы |
| `/var/log/calendar-backup.log` | Лог бэкапов |
| `docker-compose.secure.yml` | Основной compose файл |
| `docker-compose.monitoring.yml` | Мониторинг (Prometheus/Grafana/Loki) |

### Порты

| Порт | Сервис | Описание |
|------|--------|----------|
| 8000 | telegram-bot | FastAPI + Telegram Bot |
| 5232 | radicale | CalDAV server (internal) |
| 6379 | redis | Cache/Rate limiting (internal) |
| 9090 | prometheus | Metrics (monitoring stack) |
| 3000 | grafana | Dashboards (monitoring stack) |
| 3100 | loki | Log aggregation (monitoring stack) |

---

**Документ создан:** 2026-01-11
**Следующий review:** 2026-02-11
**Ответственный:** DevOps Team
