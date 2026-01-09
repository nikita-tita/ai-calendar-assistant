# ⚡ Быстрый старт AI Calendar Assistant

## За 5 минут до запуска!

### 1️⃣ Клонирование и установка (1 мин)

```bash
cd ai-calendar-assistant
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2️⃣ Настройка .env файла (2 мин)

```bash
cp .env.example .env
```

**Обязательные переменные для MVP:**
```bash
# Telegram (получить у @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_WEBHOOK_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Anthropic Claude (получить на console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI для Whisper (получить на platform.openai.com)
OPENAI_API_KEY=sk-proj-...

# Google OAuth (получить в console.cloud.google.com)
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...

# Остальное (можно оставить по умолчанию)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
DEFAULT_TIMEZONE=Europe/Moscow
```

### 3️⃣ Запуск (30 сек)

```bash
# Запустите приложение
uvicorn app.main:app --reload

# В другом терминале - ngrok для webhook (для локального теста)
ngrok http 8000
```

### 4️⃣ Настройка webhook (30 сек)

```bash
# Скопируйте URL из ngrok (например: https://abc123.ngrok.io)
export TELEGRAM_WEBHOOK_URL=https://abc123.ngrok.io/telegram/webhook

# Установите webhook
python scripts/set_webhook.py set
```

### 5️⃣ Тестирование (1 мин)

1. Найдите своего бота в Telegram
2. Отправьте `/start`
3. Отправьте `/auth` и авторизуйтесь в Google
4. Отправьте: **"Запланируй встречу завтра в 10:00"**

✅ Готово! Бот работает!

---

## 🔧 Альтернатива: Docker запуск

Если не хотите устанавливать зависимости локально:

```bash
# Создайте .env файл (см. шаг 2)
cp .env.example .env
nano .env  # Заполните ключи

# Запустите в Docker
docker-compose up --build

# Установите webhook
docker-compose exec calendar-assistant python scripts/set_webhook.py set
```

---

## 📝 Минимальная конфигурация для теста

Если хотите быстро протестировать **без голосовых команд**:

**.env минимальный:**
```bash
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_WEBHOOK_SECRET=random_secret
ANTHROPIC_API_KEY=your_key
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret

# Можно закомментировать (не обязательно для базового теста):
# OPENAI_API_KEY=...
```

Голосовые команды работать не будут, но текстовые - да!

---

## 🆘 Проблемы?

### Ошибка: "Module not found"
```bash
pip install -r requirements.txt --force-reinstall
```

### Webhook не работает
```bash
# Проверьте статус
python scripts/set_webhook.py info

# Удалите и установите заново
python scripts/set_webhook.py delete
python scripts/set_webhook.py set
```

### "Invalid API key"
Проверьте, что ключи скопированы **полностью** без пробелов в .env

### Порт 8000 занят
```bash
# Используйте другой порт
uvicorn app.main:app --reload --port 8080

# Не забудьте обновить ngrok
ngrok http 8080
```

---

## 📚 Что дальше?

После успешного запуска:

1. 📖 Прочитайте [SETUP_GUIDE.md](SETUP_GUIDE.md) для production setup
2. 🏗️ Изучите [ARCHITECTURE.md](ARCHITECTURE.md) для понимания структуры
3. 💻 Посмотрите [DEVELOPMENT.md](DEVELOPMENT.md) для разработки
4. ✅ Запустите тесты: `pytest`

---

## 🎯 Примеры команд для теста

```
Запланируй встречу с командой завтра в 10:00
Добавь звонок с клиентом на пятницу в 15:30
Какие у меня встречи на сегодня?
Какие свободные слоты завтра?
Создай событие "Обед" послезавтра в 13:00 на час
```

**Голосовые:** просто запишите и отправьте аудио с командой!

---

**Время до первого запуска: ~5 минут** ⏱️

**Удачи! 🚀**
