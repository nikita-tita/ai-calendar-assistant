# AI Calendar Assistant Project

Умный календарь-бот для Telegram с поддержкой естественного языка и голосовых команд.

## 🎯 Возможности

- Создание событий на естественном языке
- Голосовой ввод через Telegram
- Запрос расписания и свободных слотов
- Интеграция с Radicale CalDAV
- Поддержка русского языка через Claude AI
- Автоматизированный деплой через GitLab CI/CD

## 📁 Структура проекта

```
AI-Calendar-Project/
├── .gitlab-ci.yml             # CI/CD конфигурация для GitLab
├── GITLAB_DEPLOYMENT.md       # Подробная инструкция по деплою
├── ai-calendar-assistant/     # Основной проект
│   ├── app/                   # Исходный код бота
│   ├── .dockerignore          # Исключения для Docker
│   ├── .env.example           # Шаблон переменных окружения
│   ├── Dockerfile             # Конфигурация Docker
│   ├── docker-compose.yml     # Multi-container setup
│   └── README.md              # Техническая документация
├── screenshots/               # Скриншоты работы (31 файл)
├── docs-old/                  # Архив старой документации
└── archive/                   # Архивные файлы
```

## 🚀 Быстрый старт

### Вариант 1: Локальный запуск

```bash
cd ai-calendar-assistant
cp .env.example .env
# Отредактируйте .env и добавьте свои API ключи
docker-compose up -d
```

### Вариант 2: Развертывание на GitLab

Следуйте подробной инструкции в [GITLAB_DEPLOYMENT.md](GITLAB_DEPLOYMENT.md)

**Краткие шаги:**

1. Создайте репозиторий на GitLab
2. Добавьте remote:
   ```bash
   git remote add gitlab https://gitlab.com/YOUR_USERNAME/ai-calendar-assistant.git
   ```
3. Загрузите код:
   ```bash
   git push -u gitlab main
   ```
4. Настройте CI/CD переменные в GitLab (Settings → CI/CD → Variables)
5. Запустите pipeline для автоматического деплоя

## 🛠️ Технологический стек

- **Backend**: FastAPI, Python 3.11+
- **Bot**: python-telegram-bot v21
- **AI**: Yandex GPT
- **Calendar**: Radicale CalDAV Server
- **STT**: OpenAI Whisper
- **Database**: PostgreSQL
- **Deployment**: Docker, GitLab CI/CD

## 📚 Документация

- [GITLAB_DEPLOYMENT.md](GITLAB_DEPLOYMENT.md) - Полная инструкция по развертыванию на GitLab
- [ai-calendar-assistant/README.md](ai-calendar-assistant/README.md) - Техническая документация проекта
- [ai-calendar-assistant/docs/](ai-calendar-assistant/docs/) - Дополнительная документация
- [docs-old/](docs-old/) - Архив старой документации

## 🔐 Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните следующие переменные:

```bash
# Обязательные
TELEGRAM_BOT_TOKEN=your_token
YANDEX_GPT_API_KEY=your_key
YANDEX_GPT_FOLDER_ID=your_folder_id
DB_PASSWORD=your_db_password

# Опциональные
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
```

Полный список переменных смотрите в [ai-calendar-assistant/.env.example](ai-calendar-assistant/.env.example)

## 🚢 CI/CD Pipeline

Проект использует GitLab CI/CD с тремя стадиями:

1. **Test** - Запуск тестов, проверка кода, security scanning
2. **Build** - Сборка и push Docker образов в Container Registry
3. **Deploy** - Автоматизированный деплой на сервер (manual trigger)

Pipeline запускается автоматически при push в main/develop ветки.

## 🖼️ Скриншоты

31 скриншот работы бота в папке [screenshots/](screenshots/)

## 📦 Архив

Старые deployment файлы в папке [archive/](archive/)

## 🤝 Contributing

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📄 Лицензия

MIT License

## 📞 Контакты

Для вопросов и предложений создавайте Issues в репозитории.

---

**Последнее обновление:** 31 октября 2025
**Версия:** 1.0.0
**Статус:** Production Ready с GitLab CI/CD
