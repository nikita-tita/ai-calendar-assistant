# Распределение задач между разработчиками

**Дата:** 2026-01-10
**Проект:** AI Calendar Assistant (calendar.housler.ru)
**Источник:** BACKLOG.md + FULL_CODE_REVIEW_2026-01-09.md

---

## Сводка по задачам

| Приоритет | Всего | Done | Осталось |
|-----------|-------|------|----------|
| **Blocker (P0)** | 10 | 10 | 0 |
| **High (P1)** | 13 | 9 | 4 |
| **Medium (P2)** | 19 | 2 | 17 |
| **Low (P3)** | 3 | 0 | 3 |
| **Итого** | **45** | **21** | **24** |

> **Обновлено:** 2026-01-11. Закрыты: DOC-001, DOC-002, TEST-003, SEC-007, INFRA-003.

---

## Команда (7 разработчиков)

| # | Роль | Специализация | Задачи |
|---|------|---------------|--------|
| 1 | Backend #1 | Архитектура, рефакторинг | ARCH-001, ARCH-002, ARCH-003 |
| 2 | Backend #2 | Бизнес-логика, календарь | BIZ-004, BIZ-005, BIZ-006, BIZ-007, BIZ-008, BIZ-009 |
| 3 | Backend #3 | Performance, SQLite | PERF-002, PERF-003, PERF-004, PERF-005 |
| 4 | DevOps | Инфраструктура, мониторинг | INFRA-002, INFRA-003, INFRA-004, INFRA-005, INFRA-006 |
| 5 | Security | Безопасность | SEC-007, SEC-008, SEC-009, SEC-010 |
| 6 | Frontend | UI/UX, Telegram WebApp | UX-001 |
| 7 | QA/Tech Writer | Тестирование, документация | TEST-003, DOC-001, DOC-002, DOC-003 |

---

# Детальное распределение

---

## DEV-1: Backend #1 — Архитектура и рефакторинг

**Фокус:** Разбиение монолитных функций без изменения функционала

### ARCH-001: Рефакторинг extract_event()
- **Приоритет:** High
- **Сложность:** L (1-2 дня)
- **Файл:** `app/services/llm_agent_yandex.py:514-1002`
- **Проблема:** Функция 488 строк — невозможно поддерживать
- **Цель:** extract_event() < 50 строк (координатор) + 5-6 методов < 100 строк

**DoD:**
- [ ] `_detect_schedule_format()` выделен
- [ ] `_call_llm_api()` выделен
- [ ] `_parse_llm_response()` выделен
- [ ] `_handle_batch_events()` выделен
- [ ] Unit tests для каждого метода
- [ ] Регрессионные тесты проходят (функционал не изменился)

**Зависимости:** TEST-001 (для regression testing)

**Как делать:**
1. Сначала покрыть функцию тестами (snapshot/golden tests)
2. Выделять методы по одному, после каждого — прогон тестов
3. Не менять логику, только структуру

---

### ARCH-002: Рефакторинг handle_callback_query()
- **Приоритет:** High
- **Сложность:** L (1 день)
- **Файл:** `app/services/telegram_handler.py:707-1078`
- **Проблема:** Функция 371 строка — один гигантский switch/if

**DoD:**
- [ ] Dispatcher < 50 строк
- [ ] `_handle_event_callback()` выделен
- [ ] `_handle_settings_callback()` выделен
- [ ] `_handle_timezone_callback()` выделен
- [ ] Unit tests для каждого handler
- [ ] Функционал не изменился

**Как делать:**
1. Определить все типы callbacks (event_*, settings_*, timezone_*)
2. Создать mapping callback_type → handler
3. Выделить handlers по одному

---

### ARCH-003: Dependency injection в TelegramHandler
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `app/services/telegram_handler.py:10-15`
- **Проблема:** 6 service imports = tight coupling, сложно тестировать

**DoD:**
- [ ] Services передаются через конструктор
- [ ] Mock-и для unit тестов
- [ ] Документация по DI pattern

---

**Загрузка DEV-1:** ~4-5 дней на HIGH, затем ARCH-003

---

## DEV-2: Backend #2 — Бизнес-логика и календарь

**Фокус:** Корректность работы с событиями, edge cases

### BIZ-004: Event conflict detection
- **Приоритет:** High
- **Сложность:** M (3-4 часа)
- **Файл:** `app/services/calendar_radicale.py:524-561`
- **Проблема:** При update события на занятое время — double-booking

**DoD:**
- [ ] `_find_conflicts(user_id, start, end, exclude_uid)` метод
- [ ] `update_event()` вызывает `_find_conflicts()`
- [ ] Предупреждение пользователю при конфликте
- [ ] Тесты conflict scenarios

**Реализация:**
```python
def _find_conflicts(self, user_id: str, start: datetime, end: datetime, exclude_uid: str = None) -> List[CalendarEvent]:
    """Найти события, пересекающиеся с указанным временем."""
    events = self.get_events(user_id, start.date(), end.date())
    conflicts = []
    for event in events:
        if exclude_uid and event.uid == exclude_uid:
            continue
        if event.start < end and event.end > start:
            conflicts.append(event)
    return conflicts
```

---

### BIZ-005: Circuit breaker с exponential backoff
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/services/llm_agent_yandex.py:237-246`
- **Проблема:** После 5 ошибок — 60 сек блок без backoff

**DoD:**
- [ ] Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s
- [ ] Max backoff: 60s
- [ ] Logging состояния circuit breaker

---

### BIZ-006: DST edge cases
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `app/services/llm_agent_yandex.py:413-429`
- **Проблема:** `datetime.combine()` падает при DST transition

**DoD:**
- [ ] Использовать `zoneinfo` для DST-aware операций
- [ ] Тесты на переход зимнее/летнее время
- [ ] Документация edge cases

---

### BIZ-007: All-day events support
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `app/services/calendar_radicale.py:205-207`
- **Проблема:** All-day события конвертируются в timed events

**DoD:**
- [ ] Поддержка DATE vs DATETIME в iCalendar
- [ ] UI показывает all-day события отдельно
- [ ] Тесты all-day scenarios

---

### BIZ-008: Event UID preservation
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/services/calendar_radicale.py:533-558`
- **Проблема:** UID меняется при update — ломает sync с внешними календарями

**DoD:**
- [ ] `update_event()` сохраняет оригинальный UID
- [ ] Тест: UID до и после update одинаковый

---

### BIZ-009: Timezone at year boundaries
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `app/services/calendar_radicale.py:216-219`
- **Проблема:** Naive datetime ломается на границе года с DST

**DoD:**
- [ ] Все datetime timezone-aware
- [ ] Тест: событие 31 дек 23:00 → 1 янв 01:00

---

**Загрузка DEV-2:** BIZ-004 (HIGH) первым, затем backlog задачи

---

## DEV-3: Backend #3 — Performance и SQLite

**Фокус:** Оптимизация производительности, работа с БД

### PERF-002: SQLite concurrent writes
- **Приоритет:** High
- **Сложность:** M (3-4 часа)
- **Файл:** `app/services/analytics_service.py:40-46, 371`
- **Проблема:** Concurrent writes = "database is locked" errors

**DoD:**
- [ ] Connection pool (можно SQLAlchemy или кастомный)
- [ ] Exponential backoff для SQLITE_BUSY
- [ ] WAL mode включён
- [ ] Load test не показывает errors

**Реализация:**
```python
import sqlite3
from tenacity import retry, stop_after_attempt, wait_exponential

class SQLitePool:
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        # Enable WAL mode for better concurrency
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.close()

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=0.1))
    def execute(self, query: str, params: tuple = None):
        # ...
```

---

### PERF-003: Incremental DOM updates
- **Приоритет:** Medium (backlog)
- **Сложность:** L
- **Файл:** `app/static/index.html:738-891`
- **Проблема:** Full re-render на каждый state change

**DoD:**
- [ ] Virtual DOM или diff-based updates
- [ ] Только изменённые элементы перерисовываются
- [ ] FPS не падает при 100+ событиях

---

### PERF-004: Optimize event grouping
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/static/index.html:454-466`
- **Проблема:** O(days × events) → можно O(n)

**DoD:**
- [ ] Группировка за один проход
- [ ] Benchmark: 1000 событий < 50ms

---

### PERF-005: Tailwind CDN → optimized CSS
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/static/index.html:11`
- **Проблема:** 30-50KB CDN → можно 5-10KB purged

**DoD:**
- [ ] Tailwind CLI с purge
- [ ] CSS inline или отдельный файл
- [ ] Bundle size < 15KB

---

**Загрузка DEV-3:** PERF-002 (HIGH) первым, критично для production

---

## DEV-4: DevOps — Инфраструктура и мониторинг

**Фокус:** Observability, надёжность production

### INFRA-002: Prometheus + Grafana
- **Приоритет:** High
- **Сложность:** M (6-8 часов)
- **Файлы:** `app/services/metrics.py`, `docker-compose.secure.yml`
- **Проблема:** Метрики определены, но не собираются

**DoD:**
- [ ] Middleware инструментирует HTTP requests (latency, status codes)
- [ ] `/metrics` endpoint возвращает Prometheus format
- [ ] `docker-compose.monitoring.yml` с Prometheus + Grafana
- [ ] Dashboard для key metrics (RPS, latency p50/p95, errors)
- [ ] Alert rules для errors > 1%

**Структура:**
```
/root/ai-calendar-assistant/monitoring/
├── docker-compose.monitoring.yml
├── prometheus/
│   └── prometheus.yml
└── grafana/
    └── dashboards/
        └── calendar-bot.json
```

---

### INFRA-003: Централизованное логирование (Loki)
- **Приоритет:** High
- **Сложность:** M (4-6 часов)
- **Зависимость:** INFRA-002

**DoD:**
- [ ] Loki в docker-compose
- [ ] Promtail собирает логи из всех контейнеров
- [ ] Grafana datasource для Loki
- [ ] 30-day retention
- [ ] Alerting на ERROR logs

---

### INFRA-004: Non-root Docker containers
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `Dockerfile.bot`
- **Проблема:** Контейнеры запускаются от root

**DoD:**
- [ ] USER directive в Dockerfile
- [ ] Volumes с правильными permissions
- [ ] Тест: whoami внутри контейнера != root

---

### INFRA-005: Redis AOF persistence
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `docker-compose.secure.yml`
- **Проблема:** Только RDB snapshots, при crash теряем данные

**DoD:**
- [ ] `appendonly yes` в redis.conf
- [ ] `appendfsync everysec`
- [ ] Volume для AOF файла

---

### INFRA-006: Deep health check
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `/health` endpoint
- **Проблема:** Возвращает 200 OK, не проверяет dependencies

**DoD:**
- [ ] Проверка SQLite connection
- [ ] Проверка Radicale доступности
- [ ] Проверка Redis connection
- [ ] Возвращает детальный статус каждого компонента

---

**Загрузка DEV-4:** INFRA-002 → INFRA-003 (последовательно), затем backlog

---

## DEV-5: Security — Безопасность

**Фокус:** Закрытие security backlog

### SEC-007: JWT refresh token binding
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `app/services/admin_auth_service.py:589-595`
- **Проблема:** IP/UA binding только для access tokens, не для refresh

**DoD:**
- [ ] Refresh token привязан к fingerprint (IP + UA hash)
- [ ] При смене fingerprint — refresh token invalid
- [ ] Тест: refresh с другого IP отклоняется

---

### SEC-008: auth_date validation в Telegram HMAC
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/services/telegram_auth.py:17-68`
- **Проблема:** auth_date не проверяется на свежесть — replay attacks возможны

**DoD:**
- [ ] `auth_date` не старше 5 минут
- [ ] Reject если auth_date в будущем
- [ ] Тест: старый auth_date отклоняется

**Реализация:**
```python
def validate_telegram_auth(init_data: str) -> bool:
    # ... existing HMAC check ...

    # Check auth_date freshness
    auth_date = int(params.get('auth_date', 0))
    now = int(time.time())

    if auth_date > now:
        raise ValueError("auth_date is in the future")
    if now - auth_date > 300:  # 5 minutes
        raise ValueError("auth_date is too old (possible replay attack)")

    return True
```

---

### SEC-009: Hardcoded encryption key paths
- **Приоритет:** Medium (backlog)
- **Sложность:** S
- **Файл:** `app/services/admin_auth_service.py:140-141`
- **Проблема:** Default relative paths уязвимы при запуске из другой директории

**DoD:**
- [ ] Paths через environment variables
- [ ] Fallback на абсолютные пути
- [ ] Validation что файлы существуют при старте

---

### SEC-010: Input validation на user_id
- **Приоритет:** Medium (backlog)
- **Сложность:** S
- **Файл:** `app/routers/events.py:86-92`
- **Проблема:** user_id не валидируется как numeric

**DoD:**
- [ ] user_id проверяется как int
- [ ] 400 Bad Request при невалидном user_id
- [ ] Тест: user_id="abc" → 400

---

**Загрузка DEV-5:** Все задачи Medium, можно делать параллельно с другими

---

## DEV-6: Frontend — UI/UX

**Фокус:** Telegram WebApp, пользовательский опыт

### UX-001: Исправить Light theme
- **Приоритет:** High
- **Сложность:** M (3-4 часа)
- **Файл:** `app/static/index.html:29-33`
- **Проблема:** CSS переменные для light-theme неполные, UI ломается

**DoD:**
- [ ] Аудит всех hardcoded colors (grep `#`, `rgb`, `hsl`)
- [ ] Все hardcoded colors → CSS variables
- [ ] `.light-theme` переопределяет все variables
- [ ] Визуальное тестирование обеих тем
- [ ] Screenshots light/dark для документации

**Что искать:**
```bash
grep -n "background:" app/static/index.html
grep -n "color:" app/static/index.html
grep -n "#[0-9a-fA-F]" app/static/index.html
```

---

**Дополнительно (если останется время):**

### FEAT-003: Telegram Mini App v2 (LOW, backlog)
- Календарь-вид в Mini App
- Drag-n-drop событий

---

**Загрузка DEV-6:** UX-001 на 3-4 часа, затем помощь с документацией или FEAT-003

---

## DEV-7: QA/Tech Writer — Тестирование и документация

**Фокус:** CI/CD, документация, quality gates

### TEST-003: CI/CD pipeline с тестами
- **Приоритет:** High
- **Сложность:** S (2-3 часа)
- **Файл:** `.github/workflows/ci.yml` (создать)
- **Зависимости:** TEST-001, TEST-002 (уже done)

**DoD:**
- [ ] `.github/workflows/ci.yml` создан
- [ ] pytest запускается на каждый push
- [ ] Coverage отправляется в Codecov (или встроенный GitHub)
- [ ] Coverage threshold 25% (fail if below)
- [ ] Security scan: bandit
- [ ] Lint: ruff

**Пример workflow:**
```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov bandit ruff
      - run: ruff check app/
      - run: bandit -r app/ -ll
      - run: pytest --cov=app --cov-fail-under=25
```

---

### DOC-001: API Reference Guide
- **Приоритет:** High
- **Сложность:** S (3-4 часа)
- **Файл:** `docs/API_REFERENCE.md` (создать)

**DoD:**
- [ ] Все endpoints задокументированы (events, todos, admin, health)
- [ ] Примеры curl для каждого
- [ ] Request/Response schemas
- [ ] Error codes описаны
- [ ] Rate limiting описан
- [ ] Authentication описана (Telegram HMAC, Admin JWT)

---

### DOC-002: Operational Runbooks
- **Приоритет:** High
- **Сложность:** M (4-6 часов)
- **Файл:** `docs/RUNBOOKS.md` (создать)
- **Зависимости:** INFRA-001 (бэкапы уже done), INFRA-002

**DoD:**
- [ ] Incident response runbook (что делать при падении)
- [ ] Daily health check checklist
- [ ] Backup restore procedure (tested and documented)
- [ ] Troubleshooting guide (частые ошибки и решения)
- [ ] Escalation procedures

---

### DOC-003: Architecture Decision Records
- **Приоритет:** Medium (backlog)
- **Сложность:** M
- **Файл:** `docs/adr/` (создать директорию)

**DoD:**
- [ ] ADR-001: Почему Radicale для CalDAV
- [ ] ADR-002: Почему Yandex GPT (а не OpenAI)
- [ ] ADR-003: Почему SQLite (а не Postgres)
- [ ] Template для новых ADR

---

**Загрузка DEV-7:** TEST-003 → DOC-001 → DOC-002 (последовательно)

---

# Roadmap

## Неделя 1 (приоритет: HIGH)

| День | DEV-1 | DEV-2 | DEV-3 | DEV-4 | DEV-5 | DEV-6 | DEV-7 |
|------|-------|-------|-------|-------|-------|-------|-------|
| 1 | ARCH-001 start | BIZ-004 | PERF-002 | INFRA-002 | SEC-008 | UX-001 | TEST-003 |
| 2 | ARCH-001 | BIZ-004 done | PERF-002 | INFRA-002 | SEC-010 | UX-001 done | TEST-003 done |
| 3 | ARCH-001 done | BIZ-005 | PERF-002 done | INFRA-002 done | SEC-009 | — | DOC-001 |
| 4 | ARCH-002 | BIZ-006 | PERF-003 | INFRA-003 | SEC-007 | — | DOC-001 |
| 5 | ARCH-002 done | BIZ-006 | PERF-003 | INFRA-003 | SEC-007 | — | DOC-001 done |

## Неделя 2-3 (приоритет: MEDIUM backlog)

| DEV | Задачи |
|-----|--------|
| DEV-1 | ARCH-003 |
| DEV-2 | BIZ-007, BIZ-008, BIZ-009 |
| DEV-3 | PERF-004, PERF-005 |
| DEV-4 | INFRA-003 done, INFRA-004, INFRA-005, INFRA-006 |
| DEV-5 | Все SEC задачи done, помощь другим |
| DEV-6 | Помощь с docs, FEAT-003 research |
| DEV-7 | DOC-002, DOC-003 |

## Месяц 2-3 (LOW backlog)

- FEAT-001: Google Calendar интеграция (XL, 2-3 недели)
- FEAT-002: OCR для изображений расписаний (L, 1-2 недели)
- FEAT-003: Telegram Mini App v2 (L, 1-2 недели)

---

# Правила работы команды

## Перед началом задачи

1. Прочитать BACKLOG.md — найти свою задачу
2. Прочитать DoD (Definition of Done) — понять критерии готовности
3. Проверить зависимости — не заблокирована ли задача
4. Изучить указанные файлы — понять текущий код

## Во время работы

1. Перевести задачу в `in_progress` в BACKLOG.md
2. Минимальные изменения — не трогать то, что не относится к задаче
3. Следовать стилю проекта — смотреть как сделано рядом
4. Писать тесты — особенно для новой логики
5. Не ломать существующее — регрессионные тесты должны проходить

## После завершения

1. Все пункты DoD выполнены
2. Тесты проходят
3. Код отревьюен (минимум 3 ревьюера)
4. Перевести задачу в `done` в BACKLOG.md
5. Обновить CHANGELOG.md

## WIP лимиты

- `in_progress`: максимум 3 задачи на всю команду
- `review`: максимум 2 задачи

---

# Контакты

- **Сервер:** 95.163.227.26
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant
- **Prod URL:** https://calendar.housler.ru
- **Документация:** `/docs/` в репозитории

---

*Источник правды: BACKLOG.md. При расхождениях — актуализировать оба файла.*
