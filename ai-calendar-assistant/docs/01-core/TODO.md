# 📋 TODO List для запуска проекта

## 🔴 Критично (для первого запуска)

- [ ] **Получить API ключи:**
  - [ ] Anthropic Claude API key → https://console.anthropic.com/
  - [ ] OpenAI API key → https://platform.openai.com/
  - [ ] Google OAuth credentials → https://console.cloud.google.com/
  - [ ] Telegram Bot token → @BotFather в Telegram

- [ ] **Настроить .env файл:**
  - [ ] Скопировать .env.example в .env
  - [ ] Заполнить все API ключи
  - [ ] Сгенерировать TELEGRAM_WEBHOOK_SECRET и SECRET_KEY

- [ ] **Установить зависимости:**
  - [ ] Создать виртуальное окружение
  - [ ] pip install -r requirements.txt
  - [ ] (Опционально) Установить ffmpeg для Whisper

## 🟡 Важно (для production)

- [ ] **Настроить Google Cloud Project:**
  - [ ] Включить Google Calendar API
  - [ ] Настроить OAuth consent screen
  - [ ] Добавить redirect URIs
  - [ ] Добавить test users

- [ ] **Deployment:**
  - [ ] Выбрать хостинг (Heroku/Railway/VPS)
  - [ ] Настроить HTTPS
  - [ ] Установить Telegram webhook
  - [ ] Настроить переменные окружения

- [ ] **Тестирование:**
  - [ ] Запустить unit tests (pytest)
  - [ ] Протестировать локально с ngrok
  - [ ] Проверить все основные сценарии

## 🟢 Желательно (улучшения)

- [ ] **Расширенная функциональность:**
  - [ ] Редактирование событий
  - [ ] Удаление событий
  - [ ] Recurring events
  - [ ] Напоминания

- [ ] **Оптимизация:**
  - [ ] Добавить PostgreSQL
  - [ ] Настроить Redis для кэширования
  - [ ] Добавить rate limiting
  - [ ] Настроить мониторинг (Prometheus/Grafana)

- [ ] **Дополнительно:**
  - [ ] Text-to-Speech для ответов
  - [ ] OCR для изображений
  - [ ] Поддержка других календарей (Outlook)
  - [ ] Веб-интерфейс

## 📝 Заметки

### API Keys Checklist
```bash
✓ TELEGRAM_BOT_TOKEN - от @BotFather
✓ ANTHROPIC_API_KEY - Claude API
✓ OPENAI_API_KEY - для Whisper STT
✓ GOOGLE_CLIENT_ID - OAuth
✓ GOOGLE_CLIENT_SECRET - OAuth
```

### Быстрый старт команды
```bash
# 1. Setup
cp .env.example .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Run
uvicorn app.main:app --reload

# 3. Test (в другом терминале)
ngrok http 8000
python scripts/set_webhook.py set
```

### Production checklist
- [ ] APP_ENV=production
- [ ] DEBUG=False
- [ ] HTTPS настроен
- [ ] Webhook установлен на production URL
- [ ] Secrets в безопасном месте (не в git!)
- [ ] Мониторинг настроен
- [ ] Backup credentials настроен

---

**Начните с раздела 🔴 Критично!**
