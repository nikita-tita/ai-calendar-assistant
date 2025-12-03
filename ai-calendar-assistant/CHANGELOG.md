# Changelog

Все важные изменения в проекте документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

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
