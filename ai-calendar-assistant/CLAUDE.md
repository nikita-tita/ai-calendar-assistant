# Инструкция для Claude Code

Этот файл содержит инструкции для AI-ассистента по работе с проектом AI Calendar Assistant.

---

## ПЕРЕД НАЧАЛОМ ЛЮБОЙ РАБОТЫ

### 1. Прочитай ключевые документы

```
ОБЯЗАТЕЛЬНО прочитать перед любыми изменениями:
1. CHANGELOG.md          - что уже сделано, какие версии
2. DEPLOY.md             - как деплоить, структура сервера
3. docs/QUICK_INDEX.md   - быстрый поиск по документации
```

### 2. Структура проекта

```
ai-calendar-assistant/
├── CHANGELOG.md              # ⭐ История изменений (ЧИТАТЬ ПЕРВЫМ)
├── DEPLOY.md                 # ⭐ Инструкция по деплою
├── CLAUDE.md                 # ⭐ Этот файл - инструкции для AI
├── README.md                 # Описание проекта
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
    └── deploy_sync.sh       # Скрипт деплоя
```

### 3. Критически важные файлы

| Файл | Описание | Когда читать |
|------|----------|--------------|
| `app/static/index.html` | WebApp интерфейс | При работе с UI |
| `app/services/telegram_service.py` | Telegram бот | При работе с ботом |
| `app/services/calendar_service.py` | Календарь | При работе с событиями |
| `app/services/todos_service.py` | Задачи | При работе с todos |
| `app/routers/` | API endpoints | При работе с API |

---

## ПРАВИЛА РАБОТЫ

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
3. **Задеплой** - используй `deploy_sync.sh`
4. **Проверь** - что на проде работает

---

## ДЕПЛОЙ

### Быстрый деплой (одна команда)

```bash
# После коммита и пуша:
ssh -i ~/.ssh/id_housler root@91.229.8.221 '/root/ai-calendar-assistant/deploy_sync.sh'
```

### Проверка деплоя

```bash
# Проверить версию на проде
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"

# Проверить здоровье API
curl https://calendar.housler.ru/health
```

---

## ИЗВЕСТНЫЕ ОСОБЕННОСТИ

### Структура на сервере

На проде есть особенность - git репозиторий в подпапке:
- Git: `/root/ai-calendar-assistant/ai-calendar-assistant/`
- Docker: `/root/ai-calendar-assistant/`

**Решение:** Скрипт `deploy_sync.sh` автоматически синхронизирует их.

### WebApp версионирование

При изменении `app/static/index.html` ОБЯЗАТЕЛЬНО обнови версию:
```javascript
const APP_VERSION = 'YYYY-MM-DD-vN';  // Пример: 2025-12-04-v2
```

### Частые ошибки (НЕ ПОВТОРЯТЬ)

1. **Скролл на каждый рендер** - используй флаг `initialScrollDone`
2. **Функции не в window** - для onclick нужно `window.functionName = function() {}`
3. **Деплой без синхронизации** - всегда используй `deploy_sync.sh`
4. **Изменения без проверки истории** - сначала читай CHANGELOG

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

- **Сервер:** 91.229.8.221
- **SSH ключ:** `~/.ssh/id_housler`
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant
- **Прод URL:** https://calendar.housler.ru

---

## ЧЕКЛИСТ ПЕРЕД РАБОТОЙ

- [ ] Прочитал CHANGELOG.md
- [ ] Проверил git log последних коммитов
- [ ] Понял текущее состояние кода
- [ ] Знаю что именно нужно изменить
- [ ] Знаю как это задеплоить
- [ ] Знаю как проверить что работает

---

**Последнее обновление:** 2025-12-04
