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
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Проверка деплоя

```bash
# Версия WebApp
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"

# Health check
curl https://calendar.housler.ru/health
```

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

- **Сервер:** 91.229.8.221 (REG.RU, Москва)
- **Домен:** calendar.housler.ru
- **SSL:** Let's Encrypt (auto-renewal)
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant

---

## Лицензия

MIT License

---

**Последнее обновление:** 2025-12-04
