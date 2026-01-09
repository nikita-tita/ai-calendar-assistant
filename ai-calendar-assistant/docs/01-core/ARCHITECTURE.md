# Архитектура AI Calendar Assistant

**Последнее обновление:** 2025-12-04

---

## Обзор системы

AI Calendar Assistant — это Telegram-бот для управления календарём с поддержкой естественного языка и голосовых команд.

### Ключевые технологии
- **Backend**: FastAPI (Python 3.11)
- **AI**: Yandex GPT (понимание естественного языка)
- **Календарь**: Radicale CalDAV Server
- **Бот**: python-telegram-bot v21
- **Инфраструктура**: Docker Compose

---

## Инфраструктура

### Сервер
| Параметр | Значение |
|----------|----------|
| IP-адрес | 95.163.227.26 |
| Хостинг | REG.RU (Москва) |
| ОС | Ubuntu 22.04 |
| Домен | calendar.housler.ru |
| SSL | Let's Encrypt (auto-renewal) |

### Docker-контейнеры
| Контейнер | Образ | Порт | Назначение |
|-----------|-------|------|------------|
| telegram-bot | ai-calendar-assistant-telegram-bot | 8000 | FastAPI + Telegram Bot |
| calendar-redis | redis:7-alpine | 6379 | Кэширование (внутренний) |
| radicale-calendar | tomsquest/docker-radicale | 5232 | CalDAV сервер (внутренний) |

### Сетевая схема
```
┌─────────────────────────────────────────────────────────────────┐
│                         Интернет                                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                       ┌────────▼────────┐
                       │    Nginx        │
                       │  (reverse proxy)│
                       │   :80, :443     │
                       └────────┬────────┘
                                │
                   ┌────────────▼────────────┐
                   │     telegram-bot        │
                   │    (FastAPI + Bot)      │
                   │        :8000            │
                   └──────┬─────────┬────────┘
                          │         │
              ┌───────────▼───┐ ┌───▼───────────┐
              │ calendar-redis │ │ radicale-     │
              │    :6379       │ │ calendar      │
              │  (внутренний)  │ │   :5232       │
              └───────────────┘ └───────────────┘
```

---

## Структура проекта

```
ai-calendar-assistant/
├── app/                          # Исходный код
│   ├── main.py                   # FastAPI приложение
│   ├── config.py                 # Конфигурация (pydantic-settings)
│   ├── routers/                  # API endpoints
│   │   ├── events.py             # /api/events/*
│   │   ├── todos.py              # /api/todos/*
│   │   ├── telegram.py           # /telegram/webhook
│   │   ├── admin.py              # /api/admin/*
│   │   └── logs.py               # /api/logs/*
│   ├── services/                 # Бизнес-логика
│   │   ├── telegram_handler.py   # Обработка Telegram сообщений
│   │   ├── calendar_radicale.py  # Работа с CalDAV
│   │   ├── llm_agent_yandex.py   # AI обработка (Yandex GPT)
│   │   ├── todos_service.py      # Управление задачами
│   │   ├── user_preferences.py   # Настройки пользователей
│   │   ├── encrypted_storage.py  # Шифрованное хранение
│   │   ├── daily_reminders.py    # Напоминания
│   │   ├── stt_yandex.py         # Распознавание речи
│   │   └── analytics_service.py  # Аналитика
│   ├── schemas/                  # Pydantic models
│   │   ├── events.py             # EventDTO, CalendarEvent
│   │   └── todos.py              # Todo, TodoDTO
│   ├── middleware/               # Middleware
│   │   └── telegram_auth.py      # HMAC авторизация WebApp
│   ├── utils/                    # Утилиты
│   │   ├── logger.py             # structlog настройка
│   │   ├── datetime_parser.py    # Парсинг дат
│   │   └── pii_masking.py        # Маскирование данных
│   └── static/                   # Статические файлы
│       └── index.html            # WebApp интерфейс
├── docker-compose.secure.yml     # Единственный docker-compose
├── Dockerfile.bot                # Docker образ
├── start.sh                      # Запуск FastAPI + Bot
├── run_polling.py                # Telegram polling mode
├── requirements.txt              # Python зависимости
├── radicale_config/              # Конфиг Radicale
├── .env.example                  # Пример переменных окружения
├── CHANGELOG.md                  # История изменений
├── CLAUDE.md                     # Инструкции для AI
├── DEPLOY.md                     # Инструкция деплоя
└── docs/                         # Документация
```

---

## Хранение данных

### Места хранения данных

| Данные | Хранение | Путь в контейнере | Тип |
|--------|----------|-------------------|-----|
| **События календаря** | Radicale (CalDAV) | /data | Docker volume |
| **Задачи (todos)** | Encrypted JSON | /var/lib/calendar-bot/todos/*.json.enc | Шифрованные файлы |
| **Настройки пользователей** | JSON | /app/data/user_preferences.json | Файл |
| **Аналитика** | Encrypted JSON | /var/lib/calendar-bot/analytics_data.json.enc | Шифрованный файл |
| **Напоминания** | JSON | /app/data/daily_reminder_users.json | Файл |
| **Ключ шифрования** | File | /var/lib/calendar-bot/.encryption_key | Файл (0600) |

### Docker Volumes

```yaml
volumes:
  redis-data:              # Данные Redis
  ai-calendar-assistant_radicale_data:  # События календаря (447+ событий)
```

### Структура данных Radicale

```
/data/collections/
└── collection-root/
    └── calendar_bot/           # Общий пользователь бота
        └── <calendar_uuid>/    # Календарь пользователя
            ├── *.ics           # События (iCalendar формат)
            └── .Radicale.cache/
```

Каждый Telegram пользователь получает отдельный календарь с именем `telegram_{user_id}`.

### Шифрование данных

Используется Fernet (симметричное шифрование) для:
- Задач пользователей (todos)
- Аналитики

Ключ генерируется автоматически и хранится в `.encryption_key` с правами 0600.

---

## API Endpoints

### Публичные (через Nginx)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /health | Health check |
| GET | /app | WebApp (index.html) |
| GET | /static/* | Статические файлы |

### Telegram WebApp (требует HMAC)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | /api/events | Список событий |
| POST | /api/events | Создать событие |
| PUT | /api/events/{id} | Обновить событие |
| DELETE | /api/events/{id} | Удалить событие |
| GET | /api/todos | Список задач |
| POST | /api/todos | Создать задачу |
| PUT | /api/todos/{id} | Обновить задачу |
| DELETE | /api/todos/{id} | Удалить задачу |

### Telegram Bot

Обработка через polling mode:
- `/start` — приветствие и кнопки
- Текстовые сообщения → Yandex GPT → создание/изменение событий
- Голосовые сообщения → STT → обработка текста
- Inline-кнопки для быстрых действий

---

## Потоки данных

### Создание события через текст

```
1. Пользователь отправляет: "Встреча завтра в 15:00"
2. telegram_handler.py получает Update
3. LLMAgentYandex.extract_event() анализирует текст
4. Yandex GPT возвращает JSON с полями события
5. RadicaleService.create_event() создаёт событие в CalDAV
6. Пользователю отправляется подтверждение
```

### Создание события через голос

```
1. Пользователь отправляет голосовое сообщение
2. telegram_handler.py скачивает OGG файл
3. STTYandex.transcribe() преобразует в текст
4. Далее как текстовое сообщение (см. выше)
```

### WebApp интерфейс

```
1. Пользователь открывает WebApp в Telegram
2. Telegram передаёт initData с HMAC подписью
3. Frontend вызывает /api/events с заголовком X-Telegram-Init-Data
4. TelegramAuthMiddleware проверяет HMAC
5. API возвращает данные для user_id из initData
```

---

## Конфигурация

### Переменные окружения (.env)

```bash
# Telegram
TELEGRAM_BOT_TOKEN=xxx           # Токен бота
TELEGRAM_WEBAPP_URL=https://calendar.housler.ru  # URL WebApp

# Yandex GPT
YANDEX_GPT_API_KEY=AQVNxxx       # API ключ
YANDEX_GPT_FOLDER_ID=b1gxxx      # Folder ID

# Radicale
RADICALE_URL=http://radicale:5232
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=xxx

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=xxx                   # Минимум 32 символа
APP_ENV=production
DEBUG=False
```

---

## Безопасность

### Реализованные меры

1. **HMAC-авторизация** — все WebApp запросы проверяются подписью Telegram
2. **Шифрование at-rest** — задачи и аналитика шифруются Fernet
3. **Изоляция сервисов** — Redis и Radicale не публикуются наружу
4. **HTTPS** — Let's Encrypt сертификаты
5. **Rate limiting** — ограничение запросов на пользователя
6. **PII masking** — маскирование персональных данных в логах

### Ограничения доступа

- Radicale: только внутренний доступ (docker network)
- Redis: только внутренний доступ
- Admin API: требует JWT авторизацию

---

## Деплой

### Единственный способ деплоя

```bash
# 1. Локально: коммит и пуш
git add -A && git commit -m "fix: описание" && git push origin main

# 2. На сервере: pull и rebuild
ssh -i ~/.ssh/id_housler root@95.163.227.26 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Проверка деплоя

```bash
# Статус контейнеров
docker ps | grep -E "(telegram-bot|redis|radicale)"

# Health check
curl https://calendar.housler.ru/health

# Логи бота
docker logs telegram-bot --tail 50

# Количество событий
docker exec radicale-calendar find /data -name "*.ics" | wc -l
```

---

## Мониторинг

### Логи

- **structlog** — структурированное JSON логирование
- **Ротация** — max 10MB, 3 файла
- Путь: `/app/logs/` в контейнере

### Health checks

- `telegram-bot`: HTTP /health каждые 30 секунд
- `calendar-redis`: redis-cli ping каждые 10 секунд
- `radicale-calendar`: HTTP localhost:5232 каждые 30 секунд

### Ключевые метрики

- События: количество .ics файлов в Radicale
- Пользователи: записи в user_preferences.json
- Ошибки: grep "error" в docker logs

---

## Архитектурные решения

### Почему один контейнер для FastAPI и Bot?

- **Простота** — один процесс для управления
- **Healthcheck** — FastAPI предоставляет /health endpoint
- **Ресурсы** — меньше overhead чем два контейнера

### Почему Radicale а не PostgreSQL для событий?

- **CalDAV стандарт** — можно синхронизировать с любым календарём
- **Простота** — нет схемы БД, автоматическое создание календарей
- **Надёжность** — проверенное решение с 2006 года

### Почему шифрование JSON а не БД для todos?

- **Независимость** — не требует PostgreSQL
- **Простота бэкапа** — достаточно скопировать файлы
- **Безопасность** — данные зашифрованы at-rest

---

## Известные ограничения

1. **Нет горизонтального масштабирования** — один инстанс
2. **Rate limiter в памяти** — теряется при перезапуске (Redis настроен, но не используется для rate limit)
3. **Нет multi-tenancy** — один бот, один домен
4. **Property Bot отключён** — архивирован как отдельный микросервис

---

## См. также

- [DEPLOY.md](../../DEPLOY.md) — инструкция деплоя
- [CLAUDE.md](../../CLAUDE.md) — инструкции для AI
- [CHANGELOG.md](../../CHANGELOG.md) — история изменений
- [QUICK_INDEX.md](../QUICK_INDEX.md) — быстрый поиск по документации
