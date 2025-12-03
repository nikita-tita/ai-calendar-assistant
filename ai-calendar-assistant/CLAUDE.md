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
| `app/services/telegram_service.py` | Telegram бот | При работе с ботом |
| `app/services/calendar_service.py` | Календарь | При работе с событиями |
| `app/services/todos_service.py` | Задачи | При работе с todos |
| `app/routers/` | API endpoints | При работе с API |

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
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

### Проверка деплоя

```bash
# Проверить версию WebApp
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"

# Проверить здоровье API
curl https://calendar.housler.ru/health

# Проверить логи
ssh -i ~/.ssh/id_housler root@91.229.8.221 'docker logs telegram-bot --tail 50'
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

При изменении `app/static/index.html` ОБЯЗАТЕЛЬНО обнови версию:
```javascript
const APP_VERSION = 'YYYY-MM-DD-vN';  // Пример: 2025-12-04-v2
```

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

- **Сервер:** 91.229.8.221
- **SSH ключ:** `~/.ssh/id_housler`
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant
- **Прод URL:** https://calendar.housler.ru
- **Рабочая директория:** `/root/ai-calendar-assistant/ai-calendar-assistant/`

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
