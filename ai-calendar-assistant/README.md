# AI Calendar Assistant

Telegram-бот для управления календарём с поддержкой естественного языка и голосовых команд.

---

## Основные возможности

- **Естественный язык**: "Встреча с Иваном завтра в 15:00"
- **Голосовой ввод**: распознавание речи через Yandex SpeechKit
- **AI-понимание**: Yandex GPT для интерпретации команд
- **Управление задачами**: создание, редактирование, удаление todos
- **WebApp интерфейс**: календарь и задачи в Telegram Mini App
- **Шифрование данных**: задачи и аналитика хранятся зашифрованными

---

## Технологии

| Компонент | Технология |
|-----------|------------|
| Backend | FastAPI (Python 3.11) |
| AI | Yandex GPT |
| Календарь | Radicale CalDAV Server |
| Бот | python-telegram-bot v21 |
| Инфраструктура | Docker Compose |
| Шифрование | Fernet (symmetric) |

---

## Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Telegram Bot Token ([@BotFather](https://t.me/botfather))
- Yandex GPT API ключ ([Yandex Cloud](https://cloud.yandex.ru/))

### Установка

```bash
# Клонируем репозиторий
git clone https://github.com/nikita-tita/ai-calendar-assistant.git
cd ai-calendar-assistant/ai-calendar-assistant

# Создаём .env из примера
cp .env.example .env

# Редактируем .env - заполняем токены
nano .env

# Запуск
docker-compose -f docker-compose.secure.yml up -d
```

### Обязательные переменные .env

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_WEBAPP_URL=https://your-domain.com

# Yandex GPT
YANDEX_GPT_API_KEY=your_api_key
YANDEX_GPT_FOLDER_ID=your_folder_id

# Radicale (CalDAV)
RADICALE_URL=http://radicale:5232
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=secure_password

# Security
SECRET_KEY=minimum_32_characters_secret_key
APP_ENV=production
DEBUG=False
```

---

## Структура проекта

```
ai-calendar-assistant/
├── app/                          # Исходный код
│   ├── main.py                   # FastAPI приложение
│   ├── config.py                 # Конфигурация
│   ├── routers/                  # API endpoints
│   │   ├── events.py             # /api/events/*
│   │   ├── todos.py              # /api/todos/*
│   │   └── telegram.py           # /telegram/webhook
│   ├── services/                 # Бизнес-логика
│   │   ├── telegram_handler.py   # Обработка сообщений
│   │   ├── calendar_radicale.py  # CalDAV интеграция
│   │   ├── llm_agent_yandex.py   # AI обработка
│   │   ├── todos_service.py      # Управление задачами
│   │   └── encrypted_storage.py  # Шифрование данных
│   ├── middleware/               # HMAC авторизация WebApp
│   └── static/                   # WebApp (index.html)
├── docker-compose.secure.yml     # Docker конфигурация
├── Dockerfile.bot                # Docker образ
├── CLAUDE.md                     # Инструкции для AI
├── DEPLOY.md                     # Инструкция деплоя
└── docs/                         # Документация
```

---

## Хранение данных

| Данные | Хранение | Шифрование |
|--------|----------|------------|
| События календаря | Radicale CalDAV | Нет (CalDAV стандарт) |
| Задачи (todos) | JSON файлы | Да (Fernet) |
| Настройки пользователей | JSON файл | Нет |
| Аналитика | JSON файл | Да (Fernet) |

Каждый пользователь получает отдельный календарь с именем `telegram_{user_id}`.

---

## Docker контейнеры

| Контейнер | Образ | Назначение |
|-----------|-------|------------|
| telegram-bot | Dockerfile.bot | FastAPI + Telegram Bot |
| calendar-redis | redis:7-alpine | Кэширование |
| radicale-calendar | tomsquest/docker-radicale | CalDAV сервер |

```bash
# Проверка статуса
docker ps

# Логи бота
docker logs telegram-bot --tail 50 -f

# Health check
curl http://localhost:8000/health
```

---

## Деплой

### Деплой через Git (рекомендуется)

```bash
# 1. Локально: коммит и пуш
git add -A && git commit -m "fix: описание" && git push origin main

# 2. На сервере: pull и rebuild
ssh root@95.163.227.26 '
  cd /root/ai-calendar-assistant &&
  git pull origin main &&
  docker compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker compose -f docker-compose.secure.yml up -d telegram-bot
'
```

> **Note:** Используйте SSH-ключи для авторизации. Настройка: `~/.ssh/config`

### Проверка деплоя

```bash
# Health check
curl http://95.163.227.26:8000/health

# Статус контейнеров
ssh root@95.163.227.26 'docker ps'
```

---

## Админ-панель

### Доступ

- **UI интерфейс:** `/admin`
- **API v1:** `/api/admin/` (3 пароля)
- **API v2:** `/api/admin/v2/` (логин + 2FA)

### Авторизация

**Версия 1 — три пароля:**
```bash
# POST /api/admin/verify
curl -X POST http://localhost:8000/api/admin/verify \
  -H "Content-Type: application/json" \
  -d '{"password1": "...", "password2": "...", "password3": "..."}'
```

Переменные окружения:
```bash
ADMIN_PASSWORD_1=первый_пароль
ADMIN_PASSWORD_2=второй_пароль
ADMIN_PASSWORD_3=третий_пароль
```

> **Fake mode:** Если пароли 1 и 2 верные, а 3 — неверный, показываются фейковые данные (защита от принуждения).

**Версия 2 — логин + Google Authenticator:**
```bash
# POST /api/admin/v2/login
curl -X POST http://localhost:8000/api/admin/v2/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "...", "totp_code": "123456"}'
```

### Основные эндпоинты

| Эндпоинт | Описание |
|----------|----------|
| `GET /stats` | Статистика (пользователи, события, сообщения) |
| `GET /users` | Список пользователей с метриками |
| `GET /users/{id}/dialog` | История сообщений пользователя |
| `GET /users/{id}/events` | Календарные события пользователя |
| `GET /timeline` | Лента активности по часам |
| `GET /timeline/daily` | Ежедневная статистика (v2) |
| `GET /users/metrics` | DAU/WAU/MAU, retention, сегменты (v2) |
| `GET /users/top` | Топ активных пользователей (v2) |
| `GET /llm/costs` | Расходы на LLM по дням/моделям (v2) |
| `GET /errors` | Системные ошибки |
| `POST /broadcast` | Рассылка сообщений всем пользователям |

### Сравнение версий

| Функция | v1 | v2 |
|---------|:--:|:--:|
| JWT токены | HS256 | RS256 (асимметричные) |
| 2FA (TOTP) | ❌ | ✅ |
| httpOnly cookies | ❌ | ✅ |
| Привязка к IP | ❌ | ✅ |
| Аудит действий | ❌ | ✅ |
| Несколько админов | ❌ | ✅ |
| Роли (admin/moderator/viewer) | ❌ | ✅ |
| Rate limiting | 5/мин | 3/5мин + блокировка 15мин |

Подробное сравнение: [ADMIN_COMPARISON.md](../ADMIN_COMPARISON.md)

---

## Безопасность

- **HMAC-авторизация** — WebApp запросы проверяются подписью Telegram
- **Шифрование at-rest** — задачи и аналитика шифруются Fernet
- **Изоляция сервисов** — Redis и Radicale не публикуются наружу
- **HTTPS** — Let's Encrypt сертификаты
- **Rate limiting** — ограничение запросов на пользователя
- **PII masking** — маскирование персональных данных в логах

---

## Документация

| Документ | Описание |
|----------|----------|
| [CLAUDE.md](CLAUDE.md) | Инструкции для AI-ассистента |
| [DEPLOY.md](DEPLOY.md) | Подробная инструкция деплоя |
| [CHANGELOG.md](CHANGELOG.md) | История изменений |
| [docs/01-core/ARCHITECTURE.md](docs/01-core/ARCHITECTURE.md) | Архитектура системы |
| [docs/QUICK_INDEX.md](docs/QUICK_INDEX.md) | Быстрый поиск по документации |

---

## Production

- **Сервер:** 95.163.227.26 (REG.RU Cloud VPS, Москва)
- **SSH:** Используйте SSH-ключи (см. `~/.ssh/config`)
- **API URL:** http://95.163.227.26:8000
- **Домен:** calendar.housler.ru (нужно перенастроить DNS на новый IP)
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant

> **Security:** Credentials хранятся в 1Password. Никогда не коммитьте пароли в репозиторий.

---

## Лицензия

MIT License

---

**Последнее обновление:** 2026-01-09
