# 🗓️ AI Calendar Assistant

> Умный календарь-бот для Telegram с поддержкой естественного языка, голосовых команд и AI-ассистентом

[![Production Ready](https://img.shields.io/badge/status-production%20ready-success)](https://github.com/nikita-tita/ai-calendar-assistant)
[![Security Score](https://img.shields.io/badge/security-8.5%2F10-green)](CODE_REVIEW.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 Основные возможности

✨ **Умный ввод событий**
- 🗣️ Естественный язык: "Встреча с Иваном завтра в 15:00"
- 🎤 Голосовой ввод через Telegram
- 🤖 AI-понимание контекста (Yandex GPT)

📅 **Управление календарём**
- ➕ Создание, изменение, удаление событий
- 🔄 Повторяющиеся события (ежедневно, еженедельно, ежемесячно)
- 🔍 Поиск свободных слотов
- 📋 Пакетное создание событий из расписания

🌍 **Многоязычность**
- 🇷🇺 Русский (основной)
- 🇬🇧 English
- 🇪🇸 Español
- 🇸🇦 العربية

🔐 **Безопасность**
- ✅ HMAC-авторизация Telegram WebApp
- 🔒 Валидация секретов в production
- 🛡️ Rate limiting и защита от спама
- 📊 Структурированное логирование (structlog)

---

## 📁 Структура проекта

```
ai-calendar-assistant/
├── CODE_REVIEW.md          # 📋 Детальный отчёт о code review
├── SECURITY.md             # 🔐 Руководство по безопасности
├── README.md               # 📖 Этот файл
├── ai-calendar-assistant/  # 💼 Основной проект
│   ├── app/                # 🐍 Исходный код
│   │   ├── main.py         #    FastAPI приложение
│   │   ├── config.py       #    Конфигурация
│   │   ├── routers/        #    API endpoints
│   │   ├── services/       #    Бизнес-логика
│   │   └── models/         #    Pydantic models
│   ├── Dockerfile          # 🐳 Multi-stage Docker build
│   ├── docker-compose.yml  # 🎼 Orchestration
│   ├── requirements.txt    # 📦 Python зависимости
│   └── .env.example        # 🔧 Шаблон конфигурации
├── .gitlab-ci.yml          # 🚀 CI/CD pipeline
└── screenshots/            # 📸 Демо (31 скриншот)
```

---

## 🚀 Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.11+ (для локальной разработки)
- Telegram Bot Token ([получить от @BotFather](https://t.me/botfather))
- Yandex GPT API ключ ([получить в Yandex Cloud](https://cloud.yandex.ru/))

### 1️⃣ Установка

```bash
# Клонируем репозиторий
git clone https://github.com/nikita-tita/ai-calendar-assistant.git
cd ai-calendar-assistant/ai-calendar-assistant

# Создаём .env из примера
cp .env.example .env
```

### 2️⃣ Генерация секретов

⚠️ **ВАЖНО!** Сгенерируйте уникальные секреты для production:

```bash
# SECRET_KEY (минимум 32 символа)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# RADICALE_BOT_PASSWORD
python -c "import secrets; print('RADICALE_BOT_PASSWORD=' + secrets.token_urlsafe(24))"

# DB_PASSWORD
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"
```

Скопируйте вывод и вставьте в `.env` файл.

📖 **Подробная инструкция:** [SECURITY.md](SECURITY.md)

### 3️⃣ Настройка .env

Отредактируйте `.env` и заполните обязательные поля:

```bash
# ⚡ Обязательные переменные
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBAPP_URL=https://your-domain.com
YANDEX_GPT_API_KEY=your_yandex_gpt_api_key_here
YANDEX_GPT_FOLDER_ID=your_folder_id_here

# 🔐 Безопасность (используйте сгенерированные выше)
SECRET_KEY=<сгенерированный_ключ>
RADICALE_BOT_PASSWORD=<сгенерированный_пароль>
DB_PASSWORD=<сгенерированный_пароль>

# 🌐 Окружение
APP_ENV=production
DEBUG=False
```

Полный список переменных: [.env.example](ai-calendar-assistant/.env.example)

### 4️⃣ Запуск

```bash
# Запуск в production режиме
docker-compose up -d

# Проверка логов
docker-compose logs -f calendar-assistant

# Проверка health check
curl http://localhost:8000/health
```

✅ Готово! Бот должен ответить в Telegram.

---

## 🛠️ Технологический стек

### Backend
- **FastAPI** 0.115+ - современный async web framework
- **Python** 3.11+ - основной язык
- **Pydantic** v2 - валидация данных
- **Uvicorn** - ASGI сервер

### AI & NLP
- **Yandex GPT** - понимание естественного языка
- **OpenAI Whisper** - распознавание речи (опционально)
- **dateparser** - парсинг дат

### Календарь
- **Radicale** - CalDAV сервер (multi-user)
- **caldav** - Python клиент
- **icalendar** - работа с iCal форматом

### Telegram Bot
- **python-telegram-bot** v21 - Telegram Bot API
- **Telegram WebApp** - веб-интерфейс в боте

### Базы данных
- **PostgreSQL** 14 - для Property Bot (опционально)
- **SQLite** - для локальной разработки
- **JSON файлы** - analytics_service

### DevOps
- **Docker** + **Docker Compose** - контейнеризация
- **GitLab CI/CD** - автоматический деплой
- **structlog** - структурированное логирование

---

## 📚 Документация

| Файл | Описание |
|------|----------|
| [CODE_REVIEW.md](CODE_REVIEW.md) | 📋 Полный отчёт о code review (988 строк) |
| [SECURITY.md](SECURITY.md) | 🔐 Руководство по безопасности |
| [ai-calendar-assistant/.env.example](ai-calendar-assistant/.env.example) | 🔧 Пример конфигурации с комментариями |
| [.gitlab-ci.yml](.gitlab-ci.yml) | 🚀 CI/CD pipeline конфигурация |

---

## 🔒 Безопасность

### Статус безопасности

**Текущая оценка:** ✅ **8.5/10** (Production Ready)

После недавнего security review исправлены все критические уязвимости:

✅ **Исправлено:**
- Убраны дефолтные SECRET_KEY и пароли
- DEBUG=False по умолчанию
- .env не попадает в Docker образ
- Добавлена валидация секретов в production
- Исправлены bare except blocks
- Добавлена ротация логов

📊 **Детальный отчёт:** [CODE_REVIEW.md](CODE_REVIEW.md)

### Чеклист для production

Перед деплоем убедитесь:

- [ ] `SECRET_KEY` установлен (минимум 32 символа)
- [ ] `RADICALE_BOT_PASSWORD` установлен
- [ ] `DB_PASSWORD` установлен
- [ ] `DEBUG=False`
- [ ] `.env` не коммитится в git
- [ ] HTTPS настроен (Let's Encrypt)
- [ ] Firewall настроен (только 80, 443, 22)
- [ ] `TELEGRAM_WEBAPP_URL` указывает на ваш домен

---

## 🚀 CI/CD Pipeline

Проект использует GitLab CI/CD с автоматическим деплоем:

### Стадии pipeline:

1. **🧪 Test** - Юнит-тесты, coverage, code quality
2. **🏗️ Build** - Сборка Docker образов
3. **📦 Deploy** - Деплой на сервер (manual)
4. **🔒 Security** - Bandit + Safety сканирование

Pipeline запускается автоматически при push в `main` или `develop`.

### Переменные для CI/CD:

```bash
# GitLab Settings → CI/CD → Variables
TELEGRAM_BOT_TOKEN
YANDEX_GPT_API_KEY
YANDEX_GPT_FOLDER_ID
SECRET_KEY
DB_PASSWORD
RADICALE_BOT_PASSWORD
SSH_PRIVATE_KEY  # Для деплоя
```

---

## 🖼️ Скриншоты

31 скриншот работы бота доступны в папке [screenshots/](screenshots/)

Примеры:
- Создание события естественным языком
- Голосовой ввод
- Повторяющиеся события
- Поиск свободных слотов
- WebApp интерфейс

---

## 🤝 Contributing

Мы приветствуем вклад в проект!

1. Fork репозитория
2. Создайте feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit изменения:
   ```bash
   git commit -m "✨ Add amazing feature"
   ```
4. Push в branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. Откройте Pull Request

### Code style

- Python: PEP 8, Black formatter
- Commits: [Conventional Commits](https://www.conventionalcommits.org/)
- Тесты обязательны для новых фич

---

## 🐛 Известные проблемы

Текущие ограничения (не критичны для использования):

- [ ] Rate limiter хранит данные в памяти (рекомендуется Redis)
- [ ] Admin пароли используют SHA-256 (рекомендуется bcrypt)
- [ ] Функция `_handle_text` слишком большая (869 строк)
- [ ] Некоторые библиотеки устарели

Подробнее: [CODE_REVIEW.md - "Когда будет время"](CODE_REVIEW.md#-когда-будет-время)

---

## 📈 Roadmap

### v1.1 (Q1 2026)
- [ ] Redis для rate limiter
- [ ] bcrypt для admin паролей
- [ ] Рефакторинг больших функций
- [ ] Обновление зависимостей

### v1.2 (Q2 2026)
- [ ] Google Calendar интеграция
- [ ] OCR для изображений расписаний
- [ ] Telegram Mini App (расширенная версия)
- [ ] Мультитенантность

### v2.0 (Q3 2026)
- [ ] Web dashboard
- [ ] Мобильное приложение
- [ ] Интеграция с другими календарями (Outlook, iCloud)

---

## 📄 Лицензия

MIT License - смотрите [LICENSE](LICENSE) для деталей.

---

## 📞 Контакты и поддержка

- 🐛 **Баг-репорты:** [GitHub Issues](https://github.com/nikita-tita/ai-calendar-assistant/issues)
- 💡 **Feature requests:** [GitHub Discussions](https://github.com/nikita-tita/ai-calendar-assistant/discussions)
- 🔒 **Security issues:** См. [SECURITY.md](SECURITY.md)

---

## ⭐ Благодарности

Спасибо всем, кто внёс вклад в проект!

- [Yandex Cloud](https://cloud.yandex.ru/) за GPT API
- [Radicale](https://radicale.org/) за открытый CalDAV сервер
- [FastAPI](https://fastapi.tiangolo.com/) за отличный framework
- [python-telegram-bot](https://python-telegram-bot.org/) за Telegram интеграцию

---

<div align="center">

**Последнее обновление:** 10 ноября 2025
**Версия:** 1.0.1
**Статус:** ✅ Production Ready (Security Score: 8.5/10)

Made with ❤️ in Russia 🇷🇺

[⬆ Наверх](#-ai-calendar-assistant)

</div>
