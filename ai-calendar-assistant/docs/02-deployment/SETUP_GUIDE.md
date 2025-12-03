# Руководство по установке и настройке AI Calendar Assistant

## 📋 Предварительные требования

- Python 3.11 или выше
- Git
- Аккаунт Google
- Telegram аккаунт
- API ключи:
  - Anthropic Claude API
  - OpenAI API (для Whisper)
  - Google Cloud Project

## 🚀 Быстрый старт

### Шаг 1: Клонирование репозитория

```bash
git clone <your-repo-url>
cd ai-calendar-assistant
```

### Шаг 2: Создание виртуального окружения

```bash
python -m venv venv

# На macOS/Linux:
source venv/bin/activate

# На Windows:
venv\Scripts\activate
```

### Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

### Шаг 4: Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` и заполните все необходимые ключи (см. раздел "Получение API ключей" ниже).

## 🔑 Получение API ключей

### 1. Anthropic Claude API

1. Перейдите на https://console.anthropic.com/
2. Зарегистрируйтесь или войдите
3. Перейдите в раздел API Keys
4. Создайте новый API ключ
5. Скопируйте ключ в `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

### 2. OpenAI API (для Whisper)

1. Перейдите на https://platform.openai.com/
2. Войдите в аккаунт
3. Перейдите в API keys
4. Создайте новый ключ
5. Скопируйте в `.env`:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```

### 3. Google Calendar API

#### 3.1. Создание проекта в Google Cloud

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Нажмите "Select a project" → "NEW PROJECT"
3. Введите название проекта: "AI Calendar Assistant"
4. Нажмите "CREATE"

#### 3.2. Включение Google Calendar API

1. В боковом меню: "APIs & Services" → "Library"
2. Найдите "Google Calendar API"
3. Нажмите "ENABLE"

#### 3.3. Создание OAuth 2.0 credentials

1. "APIs & Services" → "Credentials"
2. Нажмите "CREATE CREDENTIALS" → "OAuth client ID"
3. Если попросит, настройте "OAuth consent screen":
   - User Type: External
   - App name: AI Calendar Assistant
   - User support email: ваш email
   - Developer contact: ваш email
   - Scopes: добавьте `.../auth/calendar`
   - Test users: добавьте свой email
4. Вернитесь к созданию OAuth client ID:
   - Application type: Web application
   - Name: AI Calendar Assistant
   - Authorized redirect URIs:
     - `http://localhost:8000/oauth/google/callback`
     - `https://your-domain.com/oauth/google/callback` (для продакшн)
5. Нажмите "CREATE"
6. Скопируйте Client ID и Client Secret в `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

### 4. Telegram Bot

#### 4.1. Создание бота

1. Откройте Telegram
2. Найдите @BotFather
3. Отправьте команду `/newbot`
4. Следуйте инструкциям:
   - Введите имя бота (например: "My Calendar Assistant")
   - Введите username (например: "my_calendar_ai_bot")
5. Сохраните токен, который даст BotFather

#### 4.2. Настройка бота

```
/setdescription - Установите описание бота
/setabouttext - Установите текст "About"
/setuserpic - Загрузите аватар бота (опционально)
```

#### 4.3. Добавление ключей в .env

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz...
TELEGRAM_WEBHOOK_SECRET=your-random-secret-string-here
```

Для `TELEGRAM_WEBHOOK_SECRET` используйте случайную строку:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🏃 Запуск приложения

### Локальный запуск (для разработки)

```bash
# Убедитесь, что виртуальное окружение активировано
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу: http://localhost:8000

API документация: http://localhost:8000/docs

### Запуск с Docker

```bash
# Сборка и запуск
docker-compose up --build

# В фоновом режиме
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

## 🌐 Настройка для продакшна

### 1. Развертывание на сервере

Вы можете использовать:
- VPS (DigitalOcean, Linode, AWS EC2)
- PaaS (Heroku, Railway, Render)
- Serverless (AWS Lambda, Google Cloud Run)

### 2. Настройка HTTPS

Для работы Telegram webhook необходим HTTPS. Используйте:
- Nginx + Let's Encrypt (для VPS)
- Cloudflare (бесплатный SSL)
- Встроенный SSL в PaaS провайдерах

### 3. Настройка webhook

После развертывания на публичном URL:

```bash
# Обновите .env
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook

# Установите webhook
python scripts/set_webhook.py set

# Проверьте статус
python scripts/set_webhook.py info
```

### 4. Environment Variables для продакшна

```bash
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO
```

## ✅ Проверка установки

### 1. Проверка health endpoint

```bash
curl http://localhost:8000/health
# Ожидаемый ответ: {"status":"ok","version":"0.1.0"}
```

### 2. Проверка Telegram бота

```bash
python scripts/set_webhook.py info
```

### 3. Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=app

# Только unit-тесты
pytest tests/unit/
```

## 🔧 Использование бота

### 1. Первый запуск

1. Найдите своего бота в Telegram по username
2. Отправьте `/start`
3. Отправьте `/auth` для авторизации Google Calendar
4. Перейдите по ссылке и разрешите доступ к календарю

### 2. Примеры команд

**Создание событий:**
```
Запланируй встречу с командой завтра в 10:00
Добавь звонок с клиентом на пятницу в 15:30 на час
Создай событие "Обед с Иваном" послезавтра в 13:00
```

**Запрос расписания:**
```
Какие у меня встречи сегодня?
Что запланировано на завтра?
Покажи расписание на следующую неделю
```

**Поиск свободного времени:**
```
Какие свободные слоты завтра?
Когда я свободен в пятницу?
```

**Голосовые команды:**
Просто запишите и отправьте голосовое сообщение с командой.

## 🐛 Troubleshooting

### Проблема: "Module not found"

```bash
# Переустановите зависимости
pip install -r requirements.txt --force-reinstall
```

### Проблема: "Invalid API key"

- Проверьте, что все API ключи правильно скопированы в `.env`
- Убедитесь, что в ключах нет лишних пробелов
- Проверьте, что `.env` файл находится в корневой директории

### Проблема: Telegram webhook не работает

```bash
# Проверьте статус webhook
python scripts/set_webhook.py info

# Удалите и установите заново
python scripts/set_webhook.py delete
python scripts/set_webhook.py set
```

### Проблема: Google OAuth не работает

- Убедитесь, что redirect URI в Google Console совпадает с `GOOGLE_REDIRECT_URI` в `.env`
- Проверьте, что Google Calendar API включен в проекте
- Добавьте свой email в Test Users в OAuth consent screen

### Проблема: Whisper не распознает голос

- Убедитесь, что установлен ffmpeg:
  ```bash
  # macOS
  brew install ffmpeg

  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  ```

## 📚 Дополнительные ресурсы

- [Документация FastAPI](https://fastapi.tiangolo.com/)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [Google Calendar API](https://developers.google.com/calendar)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text)

## 💡 Следующие шаги

После успешной установки:

1. Изучите [ARCHITECTURE.md](ARCHITECTURE.md) для понимания структуры проекта
2. Прочитайте [README.md](README.md) для общего обзора
3. Посмотрите примеры использования в документации
4. Настройте под свои нужды (часовой пояс, рабочие часы и т.д.)

## 🤝 Поддержка

Если возникли проблемы:
1. Проверьте раздел Troubleshooting выше
2. Изучите логи приложения
3. Создайте issue в репозитории с описанием проблемы
