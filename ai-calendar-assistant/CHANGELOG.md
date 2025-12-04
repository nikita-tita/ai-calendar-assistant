# Changelog

Все важные изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [2025-12-04] - Admin Panel Session Persistence

### Fixed
- **Сессия сохраняется при обновлении страницы** — больше не нужно вводить пароли заново
- **Сессия сохраняется даже после перезапуска сервера** — JWT токены вместо in-memory storage
- Использует `sessionStorage` — безопасно, очищается при закрытии вкладки

### Technical
- Файлы: `app/static/admin.html`, `app/routers/admin.py`
- **Frontend**: Токен сохраняется в `sessionStorage` под ключом `admin_session_token`
- **Backend**: JWT токены (PyJWT) вместо in-memory dict
  - Токен действителен 24 часа
  - Использует `JWT_SECRET` из `.env` (фиксированный между перезапусками)
  - Payload: `{mode: "real"|"fake", exp, iat}`
- При 401 ошибке (истёкший токен) сессия автоматически очищается

---

## [2025-12-04] - Error Tracking for Admin Panel

### Added
- **Новые типы ошибок в analytics** для детального отслеживания:
  - `LLM_ERROR` - ошибки Yandex GPT API
  - `LLM_PARSE_ERROR` - ошибки парсинга JSON ответа
  - `LLM_TIMEOUT` - таймауты API (30с)
  - `CALENDAR_ERROR` - ошибки Radicale (создание/удаление/обновление)
  - `STT_ERROR` - ошибки распознавания голоса
  - `INTENT_UNCLEAR` - когда LLM не понял запрос пользователя

- **API endpoint `/api/admin/errors`** - получение ошибок за N часов:
  - Параметры: `hours` (1-168), `limit` (1-500)
  - Возвращает список ошибок и статистику по типам
  - Поддержка fake mode (пустые данные)

- **Обновлённая админ-панель**:
  - Карточка "Ошибки" теперь показывает реальное количество за 24ч
  - Клик на карточку показывает детальный список ошибок
  - Breakdown ошибок по типам в подзаголовке
  - Показ error_message для каждой ошибки

### Technical
- Файлы изменены:
  - `app/models/analytics.py` - новые ActionType
  - `app/services/analytics_service.py` - методы get_errors(), get_error_stats()
  - `app/services/llm_agent_yandex.py` - логирование LLM ошибок
  - `app/services/calendar_radicale.py` - логирование calendar ошибок
  - `app/services/telegram_handler.py` - логирование STT и INTENT_UNCLEAR
  - `app/routers/admin.py` - новый endpoint /errors
  - `app/static/admin.html` - UI для отображения ошибок

### Зачем это нужно
Теперь в админке можно видеть:
1. Когда пользователь получил ошибку (и какую)
2. Что пользователь пытался сделать
3. Какой тип проблемы (API, парсинг, календарь, голос)
4. Сколько "уточнений" требуется пользователям (плохо распознанные запросы)

---

## [2025-12-04] - Admin Panel Fix

### Fixed
- **admin.html**: Исправлена синхронизация frontend с backend API
  - Форма логина теперь использует `/api/admin/verify` (было: `/login`)
  - Добавлено третье поле пароля для 3-факторной авторизации
  - Dashboard использует правильные эндпоинты (`/stats`, `/users`, `/timeline`, `/actions`)
  - Исправлена работа с токеном авторизации (`data.token` вместо `data.session_token`)

### Added
- **admin.py**: Новые API эндпоинты для админ-панели
  - `GET /api/admin/timeline` - временной ряд активности за N часов
  - `GET /api/admin/actions` - последние действия всех пользователей

- **telegram_handler.py**: Логирование событий календаря в analytics
  - `event_create` - создание события через бота
  - `event_update` - изменение события
  - `event_delete` - удаление события

### Technical
- Файлы: `admin.html`, `app/routers/admin.py`, `app/services/telegram_handler.py`
- Теперь все действия пользователей логируются в analytics_service
- Данные сохраняются в `/var/lib/calendar-bot/analytics_data.json.enc` (шифрованные)

### API Reference
```
POST /api/admin/verify    - Авторизация (3 пароля)
GET  /api/admin/stats     - Статистика
GET  /api/admin/users     - Список пользователей
GET  /api/admin/users/{id}/dialog - Диалог пользователя
GET  /api/admin/users/{id}/events - События пользователя
GET  /api/admin/timeline  - График активности
GET  /api/admin/actions   - Последние действия
GET  /api/admin/health    - Проверка здоровья
```

---

## [2025-12-04] - System Documentation

### Added
- **SYSTEM_GUIDE.md** — полное руководство по системе (500+ строк)
  - Обзор архитектуры с диаграммами
  - Файловая структура (локально и на сервере)
  - Docker команды и правила
  - Git workflow
  - Инструкции по деплою
  - Мониторинг и smoke-тесты
  - Troubleshooting

### Technical
- Объединяет всю информацию из DEPLOY.md, CLAUDE.md и docs/
- Служит единой точкой входа для работы с проектом

---

## [2025-12-04] - Fix Todos Data Loss (Critical)

### Fixed
- **КРИТИЧЕСКИЙ БАГ: Потеря задач при перезапуске контейнера**
- Путь `/var/lib/calendar-bot/` не был примонтирован как Docker volume
- При каждом `docker-compose build --no-cache` терялись:
  - Все задачи пользователей (`/var/lib/calendar-bot/todos/`)
  - Ключ шифрования (`/var/lib/calendar-bot/.encryption_key`)
  - Даже если файлы были восстановлены, ключ был новый = расшифровка невозможна

### Added
- **Docker volume `bot-data`** — персистентное хранилище для данных бота
- Mount: `bot-data:/var/lib/calendar-bot`

### Technical
- Файл: `docker-compose.secure.yml`
- Причина: TodosService и EncryptedStorage используют `/var/lib/calendar-bot/`
- Решение: добавлен named volume для сохранения данных между перезапусками
- Это НЕ влияет на календарные события (они в Radicale volume)

### Why this happened
```
# Было (НЕ монтировалось):
volumes:
  - ./logs:/app/logs
  - ./data:/app/data
  - ./credentials:/app/credentials
  # /var/lib/calendar-bot НЕ монтировался!

# Стало (теперь монтируется):
volumes:
  - ./logs:/app/logs
  - ./data:/app/data
  - ./credentials:/app/credentials
  - bot-data:/var/lib/calendar-bot  # <-- FIX
```

---

## [2025-12-04] - Automated Smoke Testing

### Added
- **Автоматический smoke-тест** — `scripts/monitoring/smoke_test.sh`
- **Отправка отчётов в Telegram** — бот @dogovorarenda_bot
- **10 проверок системы:**
  - Health endpoint
  - WebApp endpoint
  - Static files версия
  - Events/Todos API auth (защита HMAC)
  - SSL сертификат (срок действия)
  - Response time
  - Docker контейнеры (3/3 healthy)
  - Ошибки в логах за 6ч
  - Количество событий в календаре
- **Cron расписание** — 10:00 и 17:00 по Москве
- **Руководство по тестированию** — `docs/06-testing/SMOKE_TEST_GUIDE.md`

### Technical
- Chat ID: 2296243 (@nikita_tita)
- Скрипт установки cron: `scripts/monitoring/setup_cron.sh`
- Логи: `/var/log/smoke_test.log`

### Usage
```bash
# Запуск теста вручную
SMOKE_TEST_CHAT_ID=2296243 ./scripts/monitoring/smoke_test.sh

# Установка cron на сервере
./scripts/monitoring/setup_cron.sh
```

---

## [2025-12-04] - Docker Architecture Cleanup

### Changed
- **Унификация docker-compose** - теперь только один файл `docker-compose.secure.yml`
- **Единый контейнер** - `telegram-bot` запускает и FastAPI, и Telegram polling bot
- **Имена контейнеров** - `telegram-bot`, `calendar-redis`, `radicale-calendar`
- **Healthcheck** - HTTP проверка `/health` работает корректно (FastAPI слушает порт 8000)

### Removed
- `docker-compose.yml` - удалён (был дублем)
- `docker-compose.polling.yml` - удалён (устарел)
- `docker-compose.production.yml` - удалён (устарел)
- Файлы из `app/` директории - удалены дубли docker-compose

### Technical
- Архитектура: один контейнер `telegram-bot` с `Dockerfile.bot` + `start.sh`
- `start.sh` запускает uvicorn (FastAPI) и python run_polling.py параллельно
- Healthcheck проверяет `/health` endpoint через curl

### Deployment
```bash
# Единственный способ деплоя
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

---

## [2025-12-04] - Data Protection & External Volume

### Fixed
- **Восстановлены события календаря** - 447 событий восстановлены из старого Docker volume
- **Исправлена потеря данных при деплое** - данные теперь хранятся во внешнем volume

### Added
- `scripts/backup-radicale.sh` - автоматический бэкап данных Radicale
- `scripts/restore-radicale.sh` - восстановление из бэкапа
- `scripts/safe-deploy.sh` - безопасный деплой с автобэкапом
- Внешний Docker volume `calendar-radicale-data` для защиты данных

### Changed
- **docker-compose.secure.yml** - Radicale теперь использует external volume
- Volume `calendar-radicale-data` не удаляется при `docker-compose down -v`

### Technical
- Причина потери данных: Docker создавал новый volume при изменении имени проекта
- Старый volume: `ai-calendar-assistant_radicale_data` (подчёркивание)
- Новый volume: `ai-calendar-assistant_radicale-data` (дефис)
- Решение: внешний volume с фиксированным именем `calendar-radicale-data`

### Backup Commands
```bash
# Создать бэкап
./scripts/backup-radicale.sh

# Показать доступные бэкапы
./scripts/restore-radicale.sh --list

# Восстановить из последнего бэкапа
./scripts/restore-radicale.sh --latest

# Безопасный деплой (с автобэкапом)
./scripts/safe-deploy.sh
```

---

## [2025-12-04] - Production Cleanup & Git-only Workflow

### Changed
- **Полная реорганизация production сервера** - удалены все дубликаты файлов
- **Git-only workflow** - теперь работаем ТОЛЬКО через git, без локальных копий
- Чистый git clone на сервере без лишних файлов

### Added
- `Dockerfile.bot` добавлен в git (раньше был только на сервере)
- `CLAUDE.md` - инструкции для AI-ассистента
- Обновлённый `DEPLOY.md` с актуальными командами

### Technical
- Рабочая директория: `/root/ai-calendar-assistant/ai-calendar-assistant/`
- Docker запускается из рабочей директории
- Бэкап старой конфигурации: `/root/backup_before_cleanup_20251204/`

### Deployment
```bash
# Новый деплой (одна команда)
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

---

## [2025-12-04] - WebApp Fixes v1

### Fixed
- **Скролл к "Сегодня"**: Исправлена проблема когда страница прокручивалась к текущей дате при каждом действии. Теперь скролл происходит только при первой загрузке.
- **Кнопка создания задачи**: Добавлена отсутствующая функциональность создания новых задач в WebApp.

### Added
- `initialScrollDone` флаг для контроля однократного скролла
- `openNewTodo()` функция для открытия формы создания задачи
- `createTodo()` функция для POST-запроса на API создания задачи
- Кнопка "+ Новая задача" в списке задач
- Условная кнопка "Создать" / "Сохранить" в форме редактирования
- `scripts/deploy_sync.sh` - скрипт синхронизации git с docker build context

### Technical
- Версия WebApp: `2025-12-04-v1`
- Файл: `app/static/index.html`

### Deployment Notes
На сервере есть особенность структуры:
- Git repo: `/root/ai-calendar-assistant/ai-calendar-assistant/`
- Docker context: `/root/ai-calendar-assistant/`

Используйте `deploy_sync.sh` для корректного деплоя:
```bash
ssh root@91.229.8.221 '/root/ai-calendar-assistant/deploy_sync.sh'
```

---

## [2025-12-03] - Repository Cleanup

### Changed
- Удалено 518 избыточных файлов из репозитория
- Реорганизована структура проекта

---

## [2025-11-29] - Todos Integration

### Added
- Интеграция задач (todos) в основной WebApp
- Объединение `todos.html` и `index.html` в единый интерфейс
- Табы "События" и "Задачи" в WebApp

---

## [2025-10-28] - WebApp Click Fix

### Fixed
- Исправлена проблема когда клики на события не работали
- Функции перенесены в глобальную область видимости (`window.viewEvent`, etc.)
- Добавлено детальное логирование для отладки

### Technical
- Версия: `2025-10-28-17:30`
- Документация: `docs/03-features/webapp/WEBAPP_FIX_REPORT.md`

---

## Структура версий WebApp

| Версия | Дата | Описание |
|--------|------|----------|
| 2025-12-04-v1 | 2025-12-04 | Фикс скролла + создание задач |
| 2025-11-29-16:00 | 2025-11-29 | Интеграция todos |
| 2025-10-28-17:30 | 2025-10-28 | Фикс кликов |

---

## Как добавлять записи

При внесении изменений добавляйте запись в начало файла в формате:

```markdown
## [YYYY-MM-DD] - Краткое описание

### Added (новые функции)
- Описание

### Changed (изменения в существующем)
- Описание

### Fixed (исправления багов)
- Описание

### Removed (удалённый функционал)
- Описание

### Technical (технические детали)
- Версия, файлы, команды деплоя
```
