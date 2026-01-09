# Инструкция для Claude Code

> **Последнее обновление:** 2026-01-09
> **Проект:** calendar.housler.ru - AI Calendar Assistant

Этот файл содержит инструкции для AI-ассистента по работе с проектом AI Calendar Assistant.

**Общая документация Housler:** [SHARED/](../housler_pervichka/docs/SHARED/)

---

## CREDENTIALS (ВАЖНО!)

**Пароли НЕ хранятся в git!** Все credentials находятся в локальном файле:

```
../../CREDENTIALS.local
```

Переменные в этом файле:
- `$SERVER_PASSWORD` - пароль SSH для сервера
- `$ADMIN_PRIMARY_PASSWORD` - пароль админки
- `$ADMIN_SECONDARY_PASSWORD` - второй пароль админки

**Перед деплоем:** прочитай CREDENTIALS.local и подставь значения.

---

## ПЕРЕД НАЧАЛОМ ЛЮБОЙ РАБОТЫ

### 1. Прочитай ключевые документы

```
ОБЯЗАТЕЛЬНО прочитать перед любыми изменениями:
1. BACKLOG.md                      - текущие задачи и приоритеты (Kanban)
2. PROJECT_STATUS.md               - снимок состояния проекта
3. RISKS_AND_BLOCKERS.md           - активные блокеры и риски
4. CHANGELOG.md                    - что уже сделано, какие версии
5. DEPLOY.md                       - как деплоить, структура сервера
6. FULL_CODE_REVIEW_2026-01-09.md  - полный аудит кода (45 проблем)
```

### 2. Структура проекта

```
/root/ai-calendar-assistant/                    # Git root на сервере
└── ai-calendar-assistant/                      # Рабочая директория
    ├── CHANGELOG.md              # ⭐ История изменений (ЧИТАТЬ ПЕРВЫМ)
    ├── DEPLOY.md                 # ⭐ Инструкция по деплою
    ├── CLAUDE.md                 # ⭐ Этот файл - инструкции для AI
    ├── README.md                 # Описание проекта
    ├── .env                      # Конфигурация (НЕ в git!)
    ├── Dockerfile.bot            # Docker для бота
    ├── docker-compose.secure.yml # Docker compose
    ├── app/                      # Исходный код
    │   ├── main.py              # FastAPI приложение
    │   ├── config.py            # Конфигурация
    │   ├── routers/             # API endpoints
    │   ├── services/            # Бизнес-логика
    │   ├── static/              # Статика (index.html - WebApp)
    │   └── middleware/          # Middleware (auth, rate limit)
    ├── docs/                     # Документация
    │   ├── QUICK_INDEX.md       # ⭐ Быстрый поиск
    │   ├── 01-core/             # Архитектура, разработка
    │   ├── 02-deployment/       # Деплой, настройка
    │   ├── 03-features/         # Фичи (webapp, calendar, ai)
    │   ├── 04-security/         # Безопасность
    │   ├── 05-property-bot/     # Property Bot (отключен)
    │   ├── 06-testing/          # Тестирование
    │   └── 07-archive/          # Архив старых документов
    └── scripts/                  # Скрипты
```

### 3. Критически важные файлы

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `app/static/index.html` | WebApp интерфейс | При работе с UI |
| `app/services/telegram_handler.py` | Обработчик Telegram сообщений | При работе с ботом |
| `app/services/calendar_radicale.py` | CalDAV интеграция | При работе с событиями |
| `app/services/llm_agent_yandex.py` | AI обработка (Yandex GPT) | При работе с NLP |
| `app/services/todos_service.py` | Задачи (шифрованные) | При работе с todos |
| `app/services/encrypted_storage.py` | Шифрование данных | При работе с безопасностью |
| `app/routers/` | API endpoints | При работе с API |

### 4. Проектное управление

| Файл | Описание |
|------|----------|
| `BACKLOG.md` | Kanban-доска: все задачи, статусы, DoD |
| `PROJECT_STATUS.md` | Снимок состояния проекта |
| `RISKS_AND_BLOCKERS.md` | Активные риски и блокеры |
| `DECISIONS_LOG.md` | Журнал архитектурных решений |
| `FULL_CODE_REVIEW_2026-01-09.md` | Полный аудит кода (45 проблем) |

---

## ПРАВИЛА РАБОТЫ

### Работаем ТОЛЬКО через Git

1. **НЕТ локальной разработки** - всё через git
2. **НЕТ ручного копирования файлов** - только git pull
3. **НЕТ редактирования на сервере** - коммит → push → pull → rebuild

### Перед изменениями

1. **ВСЕГДА** проверь `CHANGELOG.md` - возможно это уже делалось
2. **ВСЕГДА** проверь git log последних коммитов
3. **НЕ НАЧИНАЙ** изменения без понимания текущего состояния
4. **СПРОСИ** если что-то неясно

### При изменениях

1. **Версионируй** - обновляй `APP_VERSION` в `index.html` при изменениях WebApp
2. **Документируй** - добавляй записи в `CHANGELOG.md`
3. **Тестируй** - проверяй что ничего не сломал
4. **Коммить** - с понятными сообщениями

### После изменений

1. **Обнови CHANGELOG.md** - добавь запись о том что сделал
2. **Запуши в git** - `git push origin main`
3. **Задеплой** - команды ниже
4. **Проверь** - что на проде работает

---

## ДЕПЛОЙ

### Полный цикл деплоя

```bash
# 1. Локально: коммит и пуш
git add -A && git commit -m "fix: описание" && git push origin main

# 2. На сервере: pull и rebuild
sshpass -p '$SERVER_PASSWORD' ssh root@95.163.227.26 '
  cd /root/ai-calendar-assistant &&
  git pull origin main &&
  docker compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Проверка деплоя

```bash
# Проверить здоровье API
curl http://95.163.227.26:8000/health

# Проверить статус контейнеров
sshpass -p '$SERVER_PASSWORD' ssh root@95.163.227.26 'docker ps'

# Проверить логи
sshpass -p '$SERVER_PASSWORD' ssh root@95.163.227.26 'docker logs telegram-bot --tail 50'
```

---

## СТРУКТУРА НА СЕРВЕРЕ

```
/root/ai-calendar-assistant/              # Git clone root
├── .git/                                 # Git данные
├── README.md                             # Корневой README
└── ai-calendar-assistant/                # ⭐ РАБОЧАЯ ДИРЕКТОРИЯ
    ├── .env                              # Конфигурация (только на сервере)
    ├── app/                              # Код приложения
    ├── docker-compose.secure.yml         # Docker конфиг
    ├── Dockerfile.bot                    # Dockerfile
    └── ...                               # Остальные файлы
```

**ВАЖНО:** Docker запускается из `/root/ai-calendar-assistant/ai-calendar-assistant/`

---

## ИЗВЕСТНЫЕ ОСОБЕННОСТИ

### WebApp версионирование

При изменении `app/static/index.html` ОБЯЗАТЕЛЬНО обнови ОБЕ версии:

1. **APP_VERSION** (для отладки в коде):
```javascript
const APP_VERSION = 'YYYY-MM-DD-vN';  // Пример: 2025-12-04-v2
```

2. **UI версия** (видимая пользователю, числовая, инкрементируется):
```html
<span class="...">v981</span>  <!-- Текущая: 981, следующая: 982 -->
```

**ВАЖНО:** UI версия - это простой счётчик. При каждом деплое увеличивай на 1.
Это позволяет пользователю сразу видеть что WebApp обновился.

### Частые ошибки (НЕ ПОВТОРЯТЬ)

1. **Скролл на каждый рендер** - используй флаг `initialScrollDone`
2. **Функции не в window** - для onclick нужно `window.functionName = function() {}`
3. **Редактирование файлов на сервере** - ТОЛЬКО через git!
4. **Изменения без проверки истории** - сначала читай CHANGELOG
5. **Деплой не из той директории** - всегда из `ai-calendar-assistant/ai-calendar-assistant/`

---

## ДОКУМЕНТАЦИЯ

### Где искать информацию

| Нужно | Документ |
|-------|----------|
| Быстрый поиск | `docs/QUICK_INDEX.md` |
| Архитектура | `docs/01-core/ARCHITECTURE.md` |
| Деплой | `DEPLOY.md` или `docs/02-deployment/` |
| WebApp | `docs/03-features/webapp/` |
| Безопасность | `docs/04-security/SECURITY.md` |
| Баги/фиксы | `docs/06-testing/bugfixes/` |

### Как обновлять документацию

1. **CHANGELOG.md** - при ЛЮБЫХ изменениях кода
2. **WEBAPP_FIX_REPORT.md** - при фиксах WebApp
3. **Соответствующий docs/** файл - при изменении фичи

---

## КОНТАКТЫ И ДОСТУПЫ

- **Сервер:** 95.163.227.26
- **SSH:** `sshpass -p '$SERVER_PASSWORD' ssh root@95.163.227.26`
- **Root пароль:** `$SERVER_PASSWORD`
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant
- **Прод URL:** https://calendar.housler.ru (домен нужно перенастроить на новый IP)
- **API URL:** http://95.163.227.26:8000
- **Рабочая директория на сервере:** `/root/ai-calendar-assistant/`

---

## ЧЕКЛИСТ ПЕРЕД РАБОТОЙ

- [ ] Прочитал CHANGELOG.md
- [ ] Проверил git log последних коммитов
- [ ] Понял текущее состояние кода
- [ ] Знаю что именно нужно изменить
- [ ] Знаю как это задеплоить
- [ ] Знаю как проверить что работает

---

**Последнее обновление:** 2026-01-08

---

## ЭКОСИСТЕМА HOUSLER

Этот проект — часть экосистемы Housler. Общие сервисы:

| Сервис | Провайдер | Документация |
|--------|-----------|--------------|
| **SMS авторизация** | agent.housler.ru (SMS.RU) | [AUTH_API.md](../../housler_pervichka/docs/SHARED/AUTH_API.md) |
| **Email авторизация** | agent.housler.ru (Yandex SMTP) | [AUTH_API.md](../../housler_pervichka/docs/SHARED/AUTH_API.md) |
| **Сервер** | 95.163.227.26 (reg.ru) | [SERVER_ACCESS.md](../../housler_pervichka/docs/SHARED/SERVER_ACCESS.md) |

> **Примечание:** calendar.housler.ru использует Telegram авторизацию, не централизованный Auth API.

---

## ВАЖНО: НОВЫЙ СЕРВЕР (с 07.01.2026)

Старый сервер (91.229.8.221) был удалён. Данные пользователей (календари) потеряны.

Новый сервер:
- **IP:** 95.163.227.26
- **Пароль root:** $SERVER_PASSWORD
- **Reg.ru панель:** https://cloud.reg.ru/panel/servers/
- **Сервер:** Peach Lutetium (Ubuntu 24.04)
