# 📚 Документация проекта AI Calendar Assistant

## 🗂️ Навигация по структуре документации

Вся документация проекта организована в древовидную структуру для удобного поиска и управления.

### 📋 Как работать с документацией

1. **Поиск информации**: Используйте навигацию ниже для быстрого доступа к нужному разделу
2. **Создание новых документов**: Размещайте в соответствующей категории (01-08)
3. **Обновление документов**: Редактируйте файлы напрямую в соответствующих папках
4. **Отчёты по сессиям**: Создавайте в `08-session-reports/` с датой
5. **Архивация**: Устаревшие документы перемещайте в `07-archive/` с указанием даты

**ВАЖНО:** Все документы должны храниться ТОЛЬКО в папке `docs/`. Корневая директория проекта содержит только код и `README.md`.

---

## 🌳 Структура документации

```
docs/
├── README.md (этот файл - главная навигация)
│
├── 01-core/                    # Основная документация проекта
│   ├── README.md              # Главный README проекта
│   ├── ARCHITECTURE.md        # Архитектура системы
│   ├── PROJECT_SUMMARY.md     # Краткое описание проекта
│   ├── PRODUCT_SUMMARY.md     # Продуктовое описание
│   ├── TODO.md                # Задачи и планы развития
│   └── diagrams/              # Диаграммы архитектуры
│
├── 02-deployment/             # Развертывание и установка
│   ├── QUICKSTART.md         # Быстрый старт
│   ├── SETUP_GUIDE.md        # Полное руководство по установке
│   ├── deployment/
│   │   ├── DEPLOY_REGRU.md           # Деплой на REG.RU
│   │   ├── DEPLOY_REGRU_DETAILED.md  # Детальный деплой REG.RU
│   │   ├── QUICK_DEPLOY.md           # Быстрый деплой
│   │   ├── MANUAL_DEPLOY.md          # Ручной деплой
│   │   ├── MANUAL_DEPLOY_STEPS.md    # Шаги ручного деплоя
│   │   ├── DEPLOY_INSTRUCTIONS.md    # Общие инструкции
│   │   └── DEPLOYMENT_COMPLETE.md    # Завершенные деплои
│   ├── setup/
│   │   ├── SETUP_COMPLETE.md         # Завершенная настройка
│   │   ├── YANDEX_GPT_SETUP.md      # Настройка Yandex GPT
│   │   └── GOOGLE_CALENDAR_SETUP.md  # Настройка Google Calendar
│   └── migration/
│       ├── CALCOM_MIGRATION.md       # Миграция с Cal.com
│       └── RADICALE_MIGRATION.md     # Миграция Radicale
│
├── 03-features/               # Функциональность и фичи
│   ├── calendar/
│   │   ├── CALENDAR_SYNC_IMPLEMENTATION.md  # Синхронизация календарей
│   │   ├── BATCH_SCHEDULE_FEATURE.md        # Пакетное планирование
│   │   ├── SCHEDULE_FORMAT_IMPROVEMENTS.md  # Улучшения формата
│   │   ├── YEAR_CLARIFICATION_GUIDE.md      # Уточнение года
│   │   └── QUICK_SCHEDULE_GUIDE.md          # Быстрое руководство
│   ├── ai/
│   │   ├── AI_AGENTS_SEPARATION.md          # Разделение AI агентов
│   │   └── YANDEX_GPT_SETUP.md             # Настройка Yandex GPT
│   ├── webapp/
│   │   ├── WEBAPP_DEPLOY_GUIDE.md          # Деплой веб-приложения
│   │   ├── QUICK_DEPLOY_WEBAPP.md          # Быстрый деплой webapp
│   │   ├── PUBLIC_ACCESS_INFO.md           # Публичный доступ
│   │   ├── ADMIN_ACCESS_INFO.md            # Админ доступ
│   │   ├── WEBAPP_FIX_REPORT.md           # Отчеты о фиксах
│   │   └── WEBAPP_REAL_FIX.md             # Реальные фиксы
│   └── improvements/
│       ├── CRITICAL_IMPROVEMENTS.md        # Критичные улучшения
│       ├── IMPROVEMENTS_SUMMARY.md         # Сводка улучшений
│       ├── STABILITY_IMPROVEMENTS.md       # Улучшения стабильности
│       └── ARCHITECTURE_STABILITY.md       # Стабильность архитектуры
│
├── 04-security/              # Безопасность
│   ├── SECURITY.md                         # Главный документ безопасности
│   ├── audits/
│   │   ├── SECURITY_AUDIT_REPORT.md       # Отчет аудита
│   │   ├── SECURITY_AUDIT_FINAL_REPORT.md # Финальный отчет
│   │   ├── EXEC_SUMMARY_SECURITY.md       # Краткая сводка
│   │   └── README_SECURITY_REVIEW.md      # Обзор безопасности
│   ├── improvements/
│   │   ├── SECURITY_IMPROVEMENTS_APPLIED.md # Примененные улучшения
│   │   ├── SECURITY_IMPROVEMENTS_GUIDE.md   # Руководство
│   │   ├── QUICK_START_SECURITY.md          # Быстрый старт
│   │   └── CORE_FUNCTIONALITY_PROTECTION.md # Защита функций
│   ├── deployment/
│   │   ├── SECURITY_DEPLOYMENT_COMPLETE.md  # Завершенный деплой
│   │   ├── SECURITY_FIX_WEBAPP.md          # Фиксы webapp
│   │   ├── SECURITY_FIX_DEPLOYED.md        # Развернутые фиксы
│   │   ├── SECURITY_STATUS_AFTER_FIX.md    # Статус после фикса
│   │   └── TELEGRAM_HMAC_AUTH_DEPLOYED.md  # HMAC авторизация
│   └── compliance/
│       └── COMPLIANCE_CHECK.md             # Проверка соответствия
│
├── 05-property-bot/          # Property Bot (отдельный модуль)
│   ├── PROPERTY_BOT_MASTER_DOC.md          # Главный документ
│   ├── PROPERTY_BOT_README.md              # README бота
│   ├── PROPERTY_BOT_EXECUTIVE_SUMMARY.md   # Краткая сводка
│   ├── implementation/
│   │   ├── PROPERTY_BOT_IMPLEMENTATION.md        # Реализация
│   │   ├── PROPERTY_BOT_IMPLEMENTATION_SUMMARY.md # Сводка реализации
│   │   ├── PROPERTY_BOT_DEVELOPMENT_STATUS.md    # Статус разработки
│   │   ├── PROPERTY_BOT_STAGE2_COMPLETE.md       # Завершение этапа 2
│   │   └── PROPERTY_BOT_COMPLETE.md              # Завершение проекта
│   ├── deployment/
│   │   ├── PROPERTY_BOT_DEPLOYMENT.md      # Деплой
│   │   └── PROPERTY_BOT_FINAL_SUMMARY.md   # Финальная сводка
│   ├── guides/
│   │   ├── PROPERTY_BOT_API_GUIDE.md       # API руководство
│   │   ├── PROPERTY_BOT_USER_FLOW_GUIDE.md # Пользовательский поток
│   │   └── PROPERTY_FEED_INTEGRATION_PLAN.md # План интеграции фидов
│   └── improvements/
│       └── PROPERTY_BOT_RELEVANCE_IMPROVEMENT_PLAN.md # План улучшений
│
├── 06-testing/               # Тестирование и отладка
│   ├── TESTING_PLAN.md      # План тестирования
│   ├── TEST_CASES.md        # Тестовые сценарии
│   ├── QUICK_TEST.md        # Быстрое тестирование
│   ├── bugfixes/
│   │   ├── BUGFIX_REPORT.md            # Отчеты о багах
│   │   ├── BUGFIX_DATE_DETECTION.md    # Фикс детекции дат
│   │   ├── FINAL_BUGFIX.md             # Финальные фиксы
│   │   └── FIXES_SUMMARY.md            # Сводка фиксов
│   ├── reviews/
│   │   ├── REVIEW_REPORT.md            # Отчеты ревью
│   │   └── CLEANUP_REPORT.md           # Отчет о чистке кода
│   └── completion/
│       ├── FINAL_STATUS.md             # Финальный статус
│       ├── PHASE2_COMPLETE.md          # Завершение фазы 2
│       ├── TASKS_COMPLETED.md          # Завершенные задачи
│       └── COMPLETE_DOCUMENTATION.md   # Полная документация
│
├── 07-archive/              # Архив устаревших документов
│   ├── 2024-Q4/            # Архив по кварталам
│   └── deprecated/         # Устаревшие документы
│
├── 08-session-reports/    # Отчёты по рабочим сессиям
│   ├── README.md          # Правила работы с отчётами
│   └── YYYY-MM-DD-название/  # Папки по датам
│       └── REPORT.md      # Детальный отчёт
│
├── templates/              # Шаблоны и исходники
│   ├── admin/             # HTML шаблоны админ-панели
│   │   ├── admin.html
│   │   ├── admin_v2.html
│   │   ├── admin_new.html
│   │   ├── admin_panel.html
│   │   ├── admin_server.html
│   │   └── admin_fbc36dd546d7746b862e45a7.html
│   ├── webapp/            # HTML шаблоны веб-приложения
│   │   ├── webapp_improved.html
│   │   ├── webapp_enhanced.html
│   │   ├── webapp_current.html
│   │   ├── webapp_fixed.html
│   │   ├── webapp_server.html
│   │   ├── webapp_working.html
│   │   └── webapp_current_prod.html
│   └── notes/            # Текстовые заметки
│       ├── CREATE_YANDEX_AGENT_ON_SERVER.txt
│       └── UPDATE_OTHER_FILES_ON_SERVER.txt
│
└── scripts/              # Скрипты деплоя и управления
    ├── deployment/       # Скрипты деплоя
    ├── security/        # Скрипты безопасности
    ├── maintenance/     # Обслуживание
    └── property-bot/    # Скрипты property bot

```

---

## 🔍 Быстрая навигация по темам

### Начало работы
- [Быстрый старт](02-deployment/QUICKSTART.md)
- [Руководство по установке](02-deployment/SETUP_GUIDE.md)
- [Архитектура проекта](01-core/ARCHITECTURE.md)

### Развертывание
- [Деплой на REG.RU](02-deployment/deployment/DEPLOY_REGRU_DETAILED.md)
- [Быстрый деплой](02-deployment/deployment/QUICK_DEPLOY.md)
- [Ручной деплой](02-deployment/deployment/MANUAL_DEPLOY_STEPS.md)

### Основные функции
- [Синхронизация календарей](03-features/calendar/CALENDAR_SYNC_IMPLEMENTATION.md)
- [Пакетное планирование](03-features/calendar/BATCH_SCHEDULE_FEATURE.md)
- [Веб-приложение](03-features/webapp/WEBAPP_DEPLOY_GUIDE.md)
- [AI агенты](03-features/ai/AI_AGENTS_SEPARATION.md)

### Безопасность
- [Главный документ безопасности](04-security/SECURITY.md)
- [Финальный аудит](04-security/audits/SECURITY_AUDIT_FINAL_REPORT.md)
- [Руководство по улучшениям](04-security/improvements/SECURITY_IMPROVEMENTS_GUIDE.md)

### Property Bot
- [Главный документ](05-property-bot/PROPERTY_BOT_MASTER_DOC.md)
- [Руководство пользователя](05-property-bot/guides/PROPERTY_BOT_USER_FLOW_GUIDE.md)
- [API документация](05-property-bot/guides/PROPERTY_BOT_API_GUIDE.md)

### Тестирование
- [План тестирования](06-testing/TESTING_PLAN.md)
- [Тестовые сценарии](06-testing/TEST_CASES.md)
- [Отчеты о багах](06-testing/bugfixes/)

---

## 📝 Правила работы с документацией

### Создание новых документов

1. Определите категорию (01-07)
2. Создайте файл в соответствующей подпапке
3. Используйте понятное имя файла: `НАЗВАНИЕ_ФУНКЦИИ.md`
4. Добавьте ссылку в этот README
5. Укажите дату создания в начале документа

### Обновление документов

1. Редактируйте файлы напрямую
2. Добавляйте дату обновления в начало документа
3. Сохраняйте историю изменений в конце документа

### Архивация

Когда документ устаревает:

1. Переместите в `07-archive/YYYY-QN/`
2. Добавьте префикс `[ARCHIVED_YYYY-MM-DD]` в название
3. Удалите ссылки из этого README
4. Добавьте запись в `07-archive/INDEX.md`

### Использование шаблонов

Шаблоны HTML и заметки хранятся в `templates/`:
- `templates/admin/` - шаблоны админ-панели
- `templates/webapp/` - шаблоны веб-приложения
- `templates/notes/` - текстовые заметки и инструкции

---

## 🔧 Скрипты

Все скрипты автоматизации находятся в корне проекта и в `docs/scripts/`:

### Деплоймент
- `deploy-to-regru.sh` - основной деплой на REG.RU
- `deploy-safe.sh` - безопасный деплой
- `QUICK_DEPLOY.sh` - быстрый деплой

### Безопасность
- `deploy-security-improvements.sh` - деплой улучшений безопасности
- `test-security.sh` - тест безопасности
- `final_security_check.sh` - финальная проверка

### Обслуживание
- `backup-calendar.sh` - резервное копирование
- `restore-from-backup.sh` - восстановление из бэкапа

### Property Bot
- `deploy-property-bot-complete.sh` - полный деплой property bot
- `deploy-property-bot.sh` - деплой property bot

---

## 📊 Статистика документации

- **Всего документов**: 80+ файлов
- **Категорий**: 7 основных разделов
- **HTML шаблонов**: 13 файлов
- **Скриптов деплоя**: 19 файлов
- **Последнее обновление**: 2025-10-29

---

## 🎯 Рекомендации

### Для новых разработчиков
1. Начните с [QUICKSTART.md](02-deployment/QUICKSTART.md)
2. Изучите [ARCHITECTURE.md](01-core/ARCHITECTURE.md)
3. Ознакомьтесь с [SECURITY.md](04-security/SECURITY.md)

### Для деплоя
1. [DEPLOY_REGRU_DETAILED.md](02-deployment/deployment/DEPLOY_REGRU_DETAILED.md)
2. [SECURITY_IMPROVEMENTS_GUIDE.md](04-security/improvements/SECURITY_IMPROVEMENTS_GUIDE.md)

### Для работы с функциями
1. [CALENDAR_SYNC_IMPLEMENTATION.md](03-features/calendar/CALENDAR_SYNC_IMPLEMENTATION.md)
2. [AI_AGENTS_SEPARATION.md](03-features/ai/AI_AGENTS_SEPARATION.md)
3. [WEBAPP_DEPLOY_GUIDE.md](03-features/webapp/WEBAPP_DEPLOY_GUIDE.md)

---

## 📧 Контакты и поддержка

При возникновении вопросов:
1. Проверьте соответствующий раздел документации
2. Изучите архив решенных проблем в `06-testing/bugfixes/`
3. Создайте issue с описанием проблемы

---

**Последнее обновление структуры**: 2025-10-29
**Версия документации**: 2.0
