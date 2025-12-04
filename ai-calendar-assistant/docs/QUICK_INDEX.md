# 🚀 Быстрый индекс документации

Это краткий справочник для быстрого поиска нужной информации.

## 🎯 По задачам

### Я хочу начать работу с проектом
1. [Быстрый старт](02-deployment/QUICKSTART.md)
2. [Руководство по установке](02-deployment/SETUP_GUIDE.md)
3. [Архитектура проекта](01-core/ARCHITECTURE.md)

### Я хочу задеплоить на сервер
1. [Деплой на REG.RU (детально)](02-deployment/deployment/DEPLOY_REGRU_DETAILED.md)
2. [Быстрый деплой](02-deployment/deployment/QUICK_DEPLOY.md)
3. [Настройка Yandex GPT](02-deployment/setup/YANDEX_GPT_SETUP.md)

### Я хочу настроить безопасность
1. [Главный документ безопасности](04-security/SECURITY.md)
2. [Финальный аудит безопасности](04-security/audits/SECURITY_AUDIT_FINAL_REPORT.md)
3. [Руководство по улучшениям](04-security/improvements/SECURITY_IMPROVEMENTS_GUIDE.md)

### Я работаю с Property Bot
1. [Главный документ Property Bot](05-property-bot/PROPERTY_BOT_MASTER_DOC.md)
2. [Руководство пользователя](05-property-bot/guides/PROPERTY_BOT_USER_FLOW_GUIDE.md)
3. [API документация](05-property-bot/guides/PROPERTY_BOT_API_GUIDE.md)

### Я хочу понять работу календаря
1. [Синхронизация календарей](03-features/calendar/CALENDAR_SYNC_IMPLEMENTATION.md)
2. [Пакетное планирование](03-features/calendar/BATCH_SCHEDULE_FEATURE.md)
3. [Формат расписаний](03-features/calendar/SCHEDULE_FORMAT_IMPROVEMENTS.md)

### Я хочу работать с веб-приложением
1. [Деплой веб-приложения](03-features/webapp/WEBAPP_DEPLOY_GUIDE.md)
2. [Публичный доступ](03-features/webapp/PUBLIC_ACCESS_INFO.md)
3. [Админ панель](03-features/webapp/ADMIN_ACCESS_INFO.md)

### Я хочу протестировать систему
1. [План тестирования](06-testing/TESTING_PLAN.md)
2. [Тестовые сценарии](06-testing/TEST_CASES.md)
3. [Быстрое тестирование](06-testing/QUICK_TEST.md)

---

## 📂 По компонентам

### AI / LLM
- [Разделение AI агентов](03-features/ai/AI_AGENTS_SEPARATION.md)
- [Настройка Yandex GPT](02-deployment/setup/YANDEX_GPT_SETUP.md)

### Календарь
- [Синхронизация](03-features/calendar/CALENDAR_SYNC_IMPLEMENTATION.md)
- [Google Calendar](02-deployment/setup/GOOGLE_CALENDAR_SETUP.md)
- [Пакетное планирование](03-features/calendar/BATCH_SCHEDULE_FEATURE.md)
- [Формат расписаний](03-features/calendar/SCHEDULE_FORMAT_IMPROVEMENTS.md)

### Веб-приложение
- [Деплой](03-features/webapp/WEBAPP_DEPLOY_GUIDE.md)
- [Быстрый деплой](03-features/webapp/QUICK_DEPLOY_WEBAPP.md)
- [Публичный доступ](03-features/webapp/PUBLIC_ACCESS_INFO.md)
- [Админ панель](03-features/webapp/ADMIN_ACCESS_INFO.md)

### Безопасность
- [Главный документ](04-security/SECURITY.md)
- [Финальный аудит](04-security/audits/SECURITY_AUDIT_FINAL_REPORT.md)
- [Руководство по улучшениям](04-security/improvements/SECURITY_IMPROVEMENTS_GUIDE.md)
- [Быстрый старт безопасности](04-security/improvements/QUICK_START_SECURITY.md)

### Property Bot
- [Master документ](05-property-bot/PROPERTY_BOT_MASTER_DOC.md)
- [README](05-property-bot/PROPERTY_BOT_README.md)
- [Краткая сводка](05-property-bot/PROPERTY_BOT_EXECUTIVE_SUMMARY.md)
- [API руководство](05-property-bot/guides/PROPERTY_BOT_API_GUIDE.md)

---

## 🛠️ Скрипты

### Деплой
```bash
./deploy-to-regru.sh              # Основной деплой на REG.RU
./deploy-safe.sh                  # Безопасный деплой
./QUICK_DEPLOY.sh                 # Быстрый деплой
./deploy-property-bot-complete.sh # Деплой Property Bot
```

### Безопасность
```bash
./test-security.sh                    # Тест безопасности
./deploy-security-improvements.sh     # Деплой security фиксов
./final_security_check.sh             # Финальная проверка
```

### Обслуживание
```bash
./backup-calendar.sh              # Создать бэкап
./restore-from-backup.sh [file]   # Восстановить из бэкапа
```

Подробнее: [Документация скриптов](scripts/README.md)

---

## 🔍 Поиск по ключевым словам

### Yandex GPT
- [Настройка](02-deployment/setup/YANDEX_GPT_SETUP.md)
- [Разделение агентов](03-features/ai/AI_AGENTS_SEPARATION.md)

### Docker
- [Архитектура](01-core/ARCHITECTURE.md)
- [Установка](02-deployment/SETUP_GUIDE.md)
- [Деплой](02-deployment/deployment/DEPLOY_REGRU_DETAILED.md)

### Telegram
- [HMAC авторизация](04-security/deployment/TELEGRAM_HMAC_AUTH_DEPLOYED.md)
- [Бот хендлер](01-core/ARCHITECTURE.md)

### API
- [Property Bot API](05-property-bot/guides/PROPERTY_BOT_API_GUIDE.md)
- [Архитектура API](01-core/ARCHITECTURE.md)

### База данных
- [Архитектура](01-core/ARCHITECTURE.md)
- [Миграция Radicale](02-deployment/migration/RADICALE_MIGRATION.md)

---

## 📊 Статус проекта

- [Завершенные задачи](06-testing/completion/TASKS_COMPLETED.md)
- [Фаза 2 завершена](06-testing/completion/PHASE2_COMPLETE.md)
- [Финальный статус](06-testing/completion/FINAL_STATUS.md)
- [Полная документация](06-testing/completion/COMPLETE_DOCUMENTATION.md)

---

## 🐛 Багфиксы и улучшения

### Критичные
- [Критичные улучшения](03-features/improvements/CRITICAL_IMPROVEMENTS.md)
- [Финальный багфикс](06-testing/bugfixes/FINAL_BUGFIX.md)

### Стабильность
- [Улучшения стабильности](03-features/improvements/STABILITY_IMPROVEMENTS.md)
- [Стабильность архитектуры](03-features/improvements/ARCHITECTURE_STABILITY.md)

### Сводки
- [Сводка багфиксов](06-testing/bugfixes/FIXES_SUMMARY.md)
- [Сводка улучшений](03-features/improvements/IMPROVEMENTS_SUMMARY.md)

---

## 🎓 Обучающие материалы

### Для новичков
1. [Быстрый старт](02-deployment/QUICKSTART.md)
2. [Краткое описание проекта](01-core/PROJECT_SUMMARY.md)
3. [Продуктовое описание](01-core/PRODUCT_SUMMARY.md)

### Для разработчиков
1. [Архитектура](01-core/ARCHITECTURE.md)
2. [Руководство разработчика](01-core/DEVELOPMENT.md)
3. [TODO список](01-core/TODO.md)

### Для DevOps
1. [Деплой на REG.RU](02-deployment/deployment/DEPLOY_REGRU_DETAILED.md)
2. [Безопасность](04-security/SECURITY.md)
3. [Скрипты обслуживания](scripts/README.md)

---

## 📞 Часто используемые команды

### Просмотр логов
```bash
docker logs telegram-bot -f
docker logs radicale-calendar -f
```

### Проверка статуса
```bash
docker ps
docker-compose -f docker-compose.secure.yml ps
```

### Деплой через Git (рекомендуется)
```bash
# 1. Локально: коммит и пуш
git add -A && git commit -m "fix: описание" && git push origin main

# 2. На сервере: pull и rebuild (одна команда)
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Проверка версии WebApp
```bash
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"
```

### Бэкап и восстановление
```bash
./scripts/backup-radicale.sh
./scripts/restore-radicale.sh --list
./scripts/restore-radicale.sh --latest
```

---

## 🔗 Полезные ссылки

- [Главная навигация](README.md) - Полная структура документации
- [Руководство по использованию](USAGE_GUIDE.md) - Как работать с документацией
- [Скрипты](scripts/README.md) - Все доступные скрипты

---

**Последнее обновление**: 2025-12-04
