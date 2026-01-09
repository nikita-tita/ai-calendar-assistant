# AI Calendar Assistant - Полное руководство по системе

> Последнее обновление: 2025-12-04

---

## Содержание

1. [Обзор системы](#1-обзор-системы)
2. [Архитектура](#2-архитектура)
3. [Файловая структура](#3-файловая-структура)
4. [Docker и контейнеры](#4-docker-и-контейнеры)
5. [Git workflow](#5-git-workflow)
6. [Деплой](#6-деплой)
7. [Мониторинг](#7-мониторинг)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Обзор системы

**AI Calendar Assistant** — Telegram-бот с интеллектуальным календарём на естественном языке.

### Основные возможности
- Создание событий голосом или текстом ("Встреча завтра в 15:00")
- Управление задачами (todos) с шифрованием
- WebApp интерфейс в Telegram
- Напоминания о событиях (за 30 мин) и ежедневные сводки (9:00 и 20:00)
- Yandex GPT для обработки естественного языка

### Технологический стек
| Компонент | Технология |
|-----------|------------|
| Backend | Python 3.11 + FastAPI |
| Telegram Bot | python-telegram-bot (polling) |
| LLM | Yandex GPT |
| Календарь | Radicale CalDAV |
| Кэш | Redis |
| Контейнеризация | Docker Compose |
| Хостинг | VPS 95.163.227.26 |

---

## 2. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        ИНТЕРНЕТ                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Nginx (внешний)                          │
│                 calendar.housler.ru:443                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Docker Network: calendar-network                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              telegram-bot:8000                       │   │
│  │  ┌─────────────┐    ┌─────────────────────────┐    │   │
│  │  │   FastAPI   │    │   Telegram Bot (polling) │    │   │
│  │  │   /health   │    │   Обработка сообщений    │    │   │
│  │  │   /app      │    │   Напоминания           │    │   │
│  │  │   /api/*    │    │   Yandex GPT            │    │   │
│  │  └─────────────┘    └─────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
│                    │                    │                    │
│                    ▼                    ▼                    │
│  ┌──────────────────────┐    ┌──────────────────────┐      │
│  │   radicale:5232      │    │     redis:6379       │      │
│  │   CalDAV сервер      │    │   Rate limiting      │      │
│  │   Хранение событий   │    │   Кэширование        │      │
│  └──────────────────────┘    └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Контейнеры

| Контейнер | Образ | Порт | Назначение |
|-----------|-------|------|------------|
| `telegram-bot` | Custom (Dockerfile.bot) | 8000 | FastAPI + Telegram Bot |
| `radicale-calendar` | tomsquest/docker-radicale | 5232 (internal) | CalDAV хранилище |
| `calendar-redis` | redis:7-alpine | 6379 (internal) | Rate limiting + кэш |

### Потоки данных

1. **Сообщение пользователя** → Telegram API → Bot (polling) → Yandex GPT → Radicale
2. **WebApp запрос** → Nginx → FastAPI → HMAC auth → Radicale/Redis
3. **Напоминание** → Scheduler → Bot → Telegram API → Пользователь

---

## 3. Файловая структура

### Локальная машина (разработка)
```
~/ai-calendar-assistant/ai-calendar-assistant/
├── .env.example              # Шаблон переменных окружения
├── .gitignore                # Git ignore rules
├── CHANGELOG.md              # История изменений
├── CLAUDE.md                 # Инструкции для AI-ассистента
├── DEPLOY.md                 # Инструкция по деплою
├── SYSTEM_GUIDE.md           # ЭТО руководство
├── README.md                 # Описание проекта
│
├── docker-compose.secure.yml # Docker Compose (ЕДИНСТВЕННЫЙ!)
├── Dockerfile.bot            # Dockerfile для telegram-bot
├── start.sh                  # Скрипт запуска (FastAPI + Bot)
├── run_polling.py            # Точка входа Telegram бота
├── requirements.txt          # Python зависимости
│
├── app/                      # Исходный код приложения
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Настройки из .env
│   │
│   ├── routers/             # API endpoints
│   │   ├── events.py        # /api/events/* - CRUD событий
│   │   ├── todos.py         # /api/todos/* - CRUD задач
│   │   ├── telegram.py      # /telegram/* - webhook (не используется)
│   │   ├── admin.py         # /api/admin/* - админка
│   │   └── health.py        # /health - healthcheck
│   │
│   ├── services/            # Бизнес-логика
│   │   ├── telegram_handler.py    # Обработчик Telegram сообщений
│   │   ├── llm_agent_yandex.py    # Yandex GPT интеграция
│   │   ├── calendar_radicale.py   # CalDAV клиент
│   │   ├── todos_service.py       # Сервис задач
│   │   ├── encrypted_storage.py   # Шифрование данных
│   │   ├── daily_reminders.py     # Ежедневные напоминания
│   │   ├── event_reminders.py     # Напоминания о событиях
│   │   ├── rate_limiter_redis.py  # Rate limiting
│   │   └── translations.py        # Переводы UI
│   │
│   ├── middleware/          # Middleware
│   │   └── telegram_auth.py # HMAC аутентификация WebApp
│   │
│   ├── static/              # Статические файлы
│   │   └── index.html       # WebApp (события + задачи)
│   │
│   ├── schemas/             # Pydantic модели
│   │   ├── events.py        # Схемы событий
│   │   └── todos.py         # Схемы задач
│   │
│   └── utils/               # Утилиты
│       ├── logger.py        # Настройка логирования
│       ├── datetime_parser.py # Парсинг дат
│       └── pii_masking.py   # Маскирование PII
│
├── scripts/                  # Скрипты
│   ├── monitoring/
│   │   ├── smoke_test.sh    # Автоматический smoke-тест
│   │   └── setup_cron.sh    # Установка cron для тестов
│   ├── backup-radicale.sh   # Бэкап Radicale
│   ├── restore-radicale.sh  # Восстановление из бэкапа
│   └── safe-deploy.sh       # Безопасный деплой с бэкапом
│
├── radicale_config/          # Конфигурация Radicale
│   └── config               # Настройки CalDAV сервера
│
├── docs/                     # Документация
│   ├── QUICK_INDEX.md       # Быстрый поиск по документации
│   ├── 01-core/             # Архитектура, разработка
│   ├── 02-deployment/       # Деплой
│   ├── 03-features/         # Фичи (webapp, calendar)
│   ├── 04-security/         # Безопасность
│   ├── 06-testing/          # Тестирование
│   └── 07-archive/          # Архив
│
└── tests/                    # Тесты
    ├── unit/                # Unit тесты
    └── integration/         # Интеграционные тесты
```

### Сервер (production)
```
/root/
├── ai-calendar-assistant/           # Git clone root
│   ├── .git/                        # Git данные
│   └── ai-calendar-assistant/       # РАБОЧАЯ ДИРЕКТОРИЯ
│       ├── .env                     # Конфигурация (ТОЛЬКО на сервере!)
│       ├── docker-compose.secure.yml
│       ├── Dockerfile.bot
│       ├── app/
│       ├── logs/                    # Bind mount → /app/logs
│       ├── data/                    # Bind mount → /app/data
│       └── credentials/             # Bind mount → /app/credentials
│
├── backups/                         # Бэкапы Radicale
│   └── radicale_YYYYMMDD_HHMMSS.tar.gz
│
└── backup_before_cleanup_*/         # Старые бэкапы
```

### Docker Volumes (на сервере)
```
/var/lib/docker/volumes/
├── ai-calendar-assistant_bot-data/      # Задачи + ключ шифрования
│   └── _data/
│       ├── .encryption_key              # Ключ Fernet
│       └── todos/
│           └── user_*.json.enc          # Зашифрованные задачи
│
├── ai-calendar-assistant_radicale-data/ # Календарные события
│   └── _data/
│       └── collections/
│           └── user_*/
│               └── calendar/
│                   └── *.ics            # iCalendar файлы
│
└── ai-calendar-assistant_redis-data/    # Redis persistence
    └── _data/
        └── dump.rdb
```

---

## 4. Docker и контейнеры

### docker-compose.secure.yml (единственный файл!)

```yaml
version: '3.8'

services:
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
      - ./data:/app/data
      - ./credentials:/app/credentials
      - bot-data:/var/lib/calendar-bot    # Задачи + ключ шифрования
    depends_on:
      redis:
        condition: service_healthy
      radicale:
        condition: service_healthy
    networks:
      - calendar-network
    environment:
      - APP_ENV=production
      - DEBUG=False
      - RADICALE_URL=http://radicale:5232
      - REDIS_URL=redis://redis:6379/0

  redis:
    image: redis:7-alpine
    container_name: calendar-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - calendar-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  radicale:
    image: tomsquest/docker-radicale:latest
    container_name: radicale-calendar
    restart: unless-stopped
    expose:
      - "5232"
    volumes:
      - radicale-data:/data
      - ./radicale_config:/config:ro
    networks:
      - calendar-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5232"]
      interval: 30s

networks:
  calendar-network:
    driver: bridge

volumes:
  redis-data:
  radicale-data:
  bot-data:
```

### Основные команды Docker

```bash
# Проверить статус контейнеров
docker ps --format "table {{.Names}}\t{{.Status}}"

# Логи telegram-bot (последние 100 строк)
docker logs telegram-bot --tail 100

# Логи в реальном времени
docker logs telegram-bot -f

# Зайти внутрь контейнера
docker exec -it telegram-bot bash

# Проверить здоровье
docker inspect telegram-bot --format '{{.State.Health.Status}}'

# Перезапустить контейнер
docker-compose -f docker-compose.secure.yml restart telegram-bot

# Пересобрать и запустить (без --no-cache)
docker-compose -f docker-compose.secure.yml up -d --build telegram-bot

# Полная пересборка (ОСТОРОЖНО: используй только при необходимости)
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot
docker-compose -f docker-compose.secure.yml up -d telegram-bot

# Остановить все контейнеры
docker-compose -f docker-compose.secure.yml down

# ⚠️ ОПАСНО: Удалить контейнеры И ДАННЫЕ
docker-compose -f docker-compose.secure.yml down -v
```

### Важные правила Docker

1. **НЕ используй `down -v`** — удалит все данные (задачи, события, ключи)
2. **Предпочитай `up -d --build`** вместо `build --no-cache` — быстрее и безопаснее
3. **Всегда проверяй volumes** после деплоя: `docker volume ls | grep calendar`
4. **Healthcheck** работает через `/health` endpoint FastAPI

---

## 5. Git workflow

### Репозиторий
- **GitHub**: https://github.com/nikita-tita/ai-calendar-assistant
- **Ветка**: `main` (единственная)
- **Workflow**: Git-only (никакого редактирования на сервере!)

### Основные команды

```bash
# Локально: проверить статус
git status

# Локально: посмотреть изменения
git diff

# Локально: добавить все файлы
git add -A

# Локально: коммит
git commit -m "fix: описание изменения"

# Локально: запушить
git push origin main

# На сервере: получить изменения
git pull origin main

# Посмотреть историю
git log --oneline -10
```

### Правила коммитов

Формат: `тип: описание`

| Тип | Описание |
|-----|----------|
| `fix` | Исправление бага |
| `feat` | Новая функциональность |
| `docs` | Документация |
| `refactor` | Рефакторинг |
| `style` | Форматирование |
| `test` | Тесты |
| `chore` | Служебные изменения |

Примеры:
```bash
git commit -m "fix: Add bot-data volume to persist todos"
git commit -m "feat: Add smoke test automation"
git commit -m "docs: Update SYSTEM_GUIDE.md"
```

### Что НЕ коммитить

Эти файлы в `.gitignore`:
- `.env` — секреты и токены
- `logs/` — логи
- `data/` — данные приложения
- `*.pyc`, `__pycache__/` — байткод Python
- `.DS_Store` — macOS файлы

---

## 6. Деплой

### Быстрый деплой (одна команда)

```bash
# Выполнить локально — задеплоит на сервер
ssh -i ~/.ssh/id_housler root@95.163.227.26 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Безопасный деплой (с бэкапом)

```bash
# На сервере
cd /root/ai-calendar-assistant/ai-calendar-assistant
./scripts/safe-deploy.sh
```

### Пошаговый деплой

```bash
# 1. Локально: коммит и пуш
git add -A
git commit -m "fix: описание"
git push origin main

# 2. SSH на сервер
ssh -i ~/.ssh/id_housler root@95.163.227.26

# 3. На сервере: перейти в директорию
cd /root/ai-calendar-assistant/ai-calendar-assistant

# 4. На сервере: получить изменения
git pull origin main

# 5. На сервере: пересобрать и запустить
docker-compose -f docker-compose.secure.yml up -d --build telegram-bot

# 6. На сервере: проверить статус
docker ps
docker logs telegram-bot --tail 20
```

### Проверка деплоя

```bash
# Health check
curl https://calendar.housler.ru/health

# Версия WebApp
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"

# Контейнеры
ssh -i ~/.ssh/id_housler root@95.163.227.26 'docker ps --format "table {{.Names}}\t{{.Status}}"'

# Логи
ssh -i ~/.ssh/id_housler root@95.163.227.26 'docker logs telegram-bot --tail 50'
```

### Откат изменений

```bash
# На сервере: вернуться к предыдущему коммиту
cd /root/ai-calendar-assistant/ai-calendar-assistant
git log --oneline -5  # посмотреть историю
git checkout HEAD~1 -- .  # откатить файлы
docker-compose -f docker-compose.secure.yml up -d --build telegram-bot
```

---

## 7. Мониторинг

### Smoke Test (автоматический)

Скрипт `scripts/monitoring/smoke_test.sh` проверяет:
1. Health endpoint (`/health`)
2. WebApp endpoint (`/app`)
3. Static files + версия
4. Events API auth (HMAC защита)
5. Todos API auth
6. SSL сертификат (срок действия)
7. Response time
8. Docker контейнеры (3/3 healthy)
9. Ошибки в логах за 6 часов
10. Количество событий в календаре

### Запуск smoke test

```bash
# Локально (с отправкой в Telegram)
SMOKE_TEST_CHAT_ID=2296243 ./scripts/monitoring/smoke_test.sh

# На сервере
SMOKE_TEST_CHAT_ID=2296243 /root/ai-calendar-assistant/ai-calendar-assistant/scripts/monitoring/smoke_test.sh
```

### Cron расписание

Тесты запускаются автоматически в 10:00 и 17:00 по Москве.

```bash
# Установка cron на сервере
./scripts/monitoring/setup_cron.sh

# Проверить cron
crontab -l

# Логи smoke test
tail -f /var/log/smoke_test.log
```

### Ручной мониторинг

```bash
# Проверить все контейнеры
docker ps

# Логи с фильтром по ошибкам
docker logs telegram-bot 2>&1 | grep -i error

# Использование диска
df -h

# Размер volumes
docker system df -v

# Количество событий в Radicale
docker exec radicale-calendar find /data -name "*.ics" | wc -l
```

---

## 8. Troubleshooting

### Бот не отвечает

```bash
# 1. Проверить контейнер
docker ps | grep telegram-bot

# 2. Проверить логи
docker logs telegram-bot --tail 100

# 3. Перезапустить
docker-compose -f docker-compose.secure.yml restart telegram-bot

# 4. Если не помогло — пересобрать
docker-compose -f docker-compose.secure.yml up -d --build telegram-bot
```

### WebApp не загружается

```bash
# 1. Проверить endpoint
curl -I https://calendar.housler.ru/app

# 2. Проверить static files
curl -I https://calendar.housler.ru/static/index.html

# 3. Проверить логи FastAPI
docker logs telegram-bot | grep -i "error\|exception"
```

### Пропали задачи

**Причина**: Volume `bot-data` не примонтирован или был удалён.

```bash
# 1. Проверить volume
docker volume ls | grep bot-data

# 2. Проверить mount
docker inspect telegram-bot --format '{{json .Mounts}}' | grep bot-data

# 3. Проверить данные внутри контейнера
docker exec telegram-bot ls -la /var/lib/calendar-bot/
docker exec telegram-bot ls -la /var/lib/calendar-bot/todos/
```

### Ошибки Yandex GPT

```bash
# Проверить API ключ
docker exec telegram-bot env | grep YANDEX

# Логи с фильтром по Yandex
docker logs telegram-bot 2>&1 | grep -i yandex
```

### Ошибки Radicale

```bash
# Проверить контейнер
docker logs radicale-calendar --tail 50

# Проверить healthcheck
docker inspect radicale-calendar --format '{{.State.Health.Status}}'

# Проверить данные
docker exec radicale-calendar ls -la /data/
```

### Ошибки Redis

```bash
# Проверить контейнер
docker logs calendar-redis --tail 50

# Проверить подключение
docker exec calendar-redis redis-cli ping
```

### SSL сертификат истекает

```bash
# Проверить срок действия
echo | openssl s_client -servername calendar.housler.ru -connect calendar.housler.ru:443 2>/dev/null | openssl x509 -noout -dates

# Обновить (если используется certbot)
certbot renew
```

---

## Приложение: Важные файлы

### .env (пример)
```env
APP_ENV=production
DEBUG=False
TELEGRAM_BOT_TOKEN=***REDACTED_BOT_TOKEN***
TELEGRAM_WEBAPP_URL=https://calendar.housler.ru/app
YANDEX_GPT_API_KEY=AQVN0TVa...
YANDEX_GPT_FOLDER_ID=b1gga6i2l1rmfei43br9
RADICALE_URL=http://radicale:5232
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=***REDACTED_RADICALE***
REDIS_URL=redis://redis:6379/0
SECRET_KEY=***REDACTED_SECRET***
DEFAULT_TIMEZONE=Europe/Moscow
```

### Контакты и доступы

| Ресурс | Значение |
|--------|----------|
| Сервер | 95.163.227.26 |
| SSH ключ | `~/.ssh/id_housler` |
| SSH команда | `ssh -i ~/.ssh/id_housler root@95.163.227.26` |
| Production URL | https://calendar.housler.ru |
| GitHub | https://github.com/nikita-tita/ai-calendar-assistant |
| Telegram бот (основной) | @aibroker_bot |
| Telegram бот (админский) | @dogovorarenda_bot |
| Admin chat ID | 2296243 |

---

*Документ создан: 2025-12-04*
*Автор: Claude Code*
