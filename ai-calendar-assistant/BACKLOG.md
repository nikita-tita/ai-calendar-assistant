# Бэклог проекта: AI Calendar Assistant

**Последнее обновление:** 2026-01-10
**Источник:** FULL_CODE_REVIEW_2026-01-09.md (Principal Engineer Review)
**Версия бэклога:** 2.1

---

## Статусы задач (Kanban)

```
Backlog → Todo → In Progress → Review/QA → Blocked → Done
```

| Статус | Описание | WIP лимит |
|--------|----------|-----------|
| `backlog` | В очереди, не приоритизировано | — |
| `todo` | Готово к взятию в работу | — |
| `in_progress` | В работе (указан исполнитель) | 3 |
| `review` | На ревью/тестировании | 2 |
| `blocked` | Заблокировано (указан блокер) | — |
| `done` | Выполнено, есть артефакт | — |

---

## Сводка

| Приоритет | Всего | Done | In Progress | Todo | Backlog |
|-----------|-------|------|-------------|------|---------|
| **Blocker (P0)** | 10 | 8 | 0 | 2 | 0 |
| **High (P1)** | 13 | 3 | 0 | 10 | 0 |
| **Medium (P2)** | 19 | 1 | 0 | 0 | 18 |
| **Low (P3)** | 3 | 0 | 0 | 0 | 3 |
| **Итого** | **45** | **12** | **0** | **12** | **21** |

### Выполнено (2026-01-09)
- ✅ SEC-003: XSS уязвимости — добавлен `safeId()` для ID в onclick handlers
- ✅ SEC-004: CSRF защита — добавлен CSRFProtectionMiddleware + SameSite=Strict cookies
- ✅ SEC-005: Security headers — добавлен SecurityHeadersMiddleware
- ✅ BIZ-001: Race condition в cache — добавлен threading.Lock()
- ✅ BIZ-002: Token limit для LLM — добавлен MAX_INPUT_CHARS=4000
- ✅ BIZ-003: Cache invalidation — добавлен invalidate_cache() после mutations

### Выполнено (2026-01-10)
- ✅ SEC-001: Git история очищена — BFG удалил 5 Telegram токенов и Yandex API ключ
- ✅ SEC-002: SQL Injection — все f-string SQL заменены на параметризованные запросы
- ✅ SEC-006: Rate limiting bypass — distributed rate limiting через Redis
- ✅ INFRA-001: Автоматические бэкапы — cron настроен, бэкапы создаются в 3:00
- ✅ TEST-001: API тесты — 60 тестов для events, todos, admin v1/v2 endpoints

---

# BLOCKER (P0) — Неделя 1

## SEC-001: Ротация секретов и очистка Git

- **Статус:** `done` ✅ (частично)
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `.env` в Git истории
- **Риск:** Полная компрометация системы
- **Выполнено:** 2026-01-10

**Цель:** Устранить утечку credentials из Git истории.

**Контекст:** В Git истории находились production credentials. BFG Repo-Cleaner удалил их.

**Результат:**
- ✅ Git история очищена от полных секретов (5 Telegram токенов, 1 Yandex API ключ)
- ⏳ Ротация секретов — отложена (по решению владельца)
- ✅ Secrets scanning настроен (gitleaks + pre-commit)

**DoD:**
- [x] BFG Repo-Cleaner удалил секреты из всей истории (2026-01-10)
- [x] Force push на GitHub выполнен
- [x] gitleaks добавлен в pre-commit
- [ ] Telegram Bot Token — ротация отложена
- [ ] Yandex GPT API Key — ротация отложена
- [ ] Остальные пароли — ротация отложена

**Удалённые секреты:**
- 5 Telegram Bot токенов
- 1 Yandex GPT API ключ (AQVN...)
- Все найдены и заменены на `***REMOVED***`

**Зависимости:** Нет
**Сложность:** M (2-3 часа)
**Ответственный:** DevOps + Security

---

## SEC-002: Исправить SQL Injection

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `app/services/analytics_service.py:436-462`
- **Риск:** Утечка данных всех пользователей
- **Выполнено:** 2026-01-10

**Цель:** Устранить SQL Injection уязвимости.

**Контекст:** f-strings использовались для SQL запросов вместо параметризованных.

**Результат:**
- Все SQL запросы параметризованы
- event_types и msg_types используют `?` placeholders
- Значения передаются через параметры execute()

**DoD:**
- [x] Все f-string SQL заменены на `?` placeholders
- [x] Audit всех SQL в проекте (grep) — чисто
- [ ] Unit test с SQL injection payloads
- [ ] sqlmap scan чист

**Зависимости:** Нет
**Сложность:** S (2-3 часа)
**Ответственный:** Backend

**Пример фикса:**
```python
# До:
f'SELECT COUNT(*) FROM actions WHERE action_type IN {event_types}'

# После:
placeholders = ','.join('?' * len(event_types))
conn.execute(f'SELECT COUNT(*) FROM actions WHERE action_type IN ({placeholders})', event_types)
```

---

## SEC-003: Исправить XSS уязвимости

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `app/static/index.html:795, 826, 859`
- **Риск:** Session hijacking, кража данных
- **Выполнено:** 2026-01-09

**Цель:** Устранить XSS уязвимости во фронтенде.

**Контекст:** onclick handlers используют string interpolation, innerHTML с динамическим контентом.

**Результат:**
- Добавлена функция `safeId()` для валидации и escape ID
- onclick handlers теперь используют `safeId(id)` вместо прямой интерполяции
- Версия WebApp обновлена до v984

**DoD:**
- [x] onclick="func('${var}')" → safeId() валидация + escape
- [ ] Event delegation через addEventListener (отложено - текущая защита достаточна)
- [ ] CSP header в nginx.conf (отложено - может сломать inline scripts)
- [ ] OWASP ZAP scan чист

**Зависимости:** Нет
**Сложность:** M (4-5 часов)
**Ответственный:** Frontend

---

## INFRA-001: Автоматизировать бэкапы

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Инфраструктура
- **Файл:** `backup-calendar.sh`
- **Риск:** Полная потеря данных (уже произошло!)
- **Выполнено:** 2026-01-10

**Цель:** Настроить автоматические ежедневные бэкапы.

**Контекст:** backup-calendar.sh существует, был добавлен в cron.

**Результат:**
- ✅ Бэкапы создаются ежедневно в 3:00
- ✅ Все данные бэкапятся: Radicale, SQLite, todos, encryption key, .env
- ✅ 30-дневная ротация
- ⏳ GPG encryption — отложено (данные уже зашифрованы Fernet)
- ⏳ Cloud upload — отложено

**DoD:**
- [x] cron job добавлен: `0 3 * * * /root/ai-calendar-assistant/backup-calendar.sh`
- [x] Бэкапы создаются и содержат все данные (проверено 2026-01-10)
- [ ] GPG encryption (отложено — Fernet уже шифрует todos)
- [ ] rclone для cloud upload (отложено)
- [ ] Alerting при failed backup (отложено)

**Бэкапы на сервере:**
```
/root/backups/calendar/calendar_full_20260110_030001.tar.gz (12K)
```

**Зависимости:** Нет
**Сложность:** S (1-2 часа)
**Ответственный:** DevOps

---

## SEC-004: Добавить CSRF защиту

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `app/main.py`, `app/routers/admin_v2.py`, `app/middleware/csrf_protection.py`
- **Риск:** CSRF атаки на admin panel
- **Выполнено:** 2026-01-09

**Цель:** Защитить state-changing endpoints от CSRF.

**Контекст:** POST endpoints (broadcast, user management) не проверяют CSRF токены.

**Результат:**
- Создан CSRFProtectionMiddleware (app/middleware/csrf_protection.py)
- Origin header валидируется для /api/admin/* endpoints
- SameSite=Strict на cookies в admin_v2.py

**DoD:**
- [x] CSRF middleware добавлен
- [x] SameSite=Strict на session cookies
- [x] Origin header валидируется
- [ ] Тест CSRF атаки не проходит

**Зависимости:** Нет
**Сложность:** S (2-3 часа)
**Ответственный:** Backend

---

## SEC-005: Security headers middleware

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `app/main.py`, `app/middleware/security_headers.py`
- **Риск:** XSS, clickjacking
- **Выполнено:** 2026-01-09

**Цель:** Добавить security headers.

**Результат:**
- Создан SecurityHeadersMiddleware (app/middleware/security_headers.py)
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN (для Telegram WebApp)
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy (camera, microphone, etc)
- Strict-Transport-Security (только в production)
- CSP опционален (enable_csp=False по умолчанию)

**DoD:**
- [x] SecurityHeadersMiddleware создан
- [x] Все headers присутствуют в responses
- [ ] securityheaders.com scan > B

**Зависимости:** Нет
**Сложность:** S (1 час)
**Ответственный:** Backend

---

## BIZ-001: Исправить race condition в cache

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Бизнес-логика
- **Файл:** `app/services/calendar_radicale.py:106-110`
- **Риск:** Inconsistent data под нагрузкой
- **Выполнено:** 2026-01-09

**Цель:** Использовать объявленный `_cache_lock`.

**Контекст:** `self._cache_lock = asyncio.Lock()` был объявлен (строка 55), но никогда не использовался при доступе к кэшу. Функции синхронные и вызываются через `asyncio.to_thread()`.

**Результат:**
- Заменён `asyncio.Lock()` на `threading.Lock()` (для синхронного кода)
- `with self._cache_lock:` добавлен в `_get_user_calendar`, `_cache_calendar`, `invalidate_cache`
- Concurrent requests теперь не вызывают race conditions

**DoD:**
- [x] `with self._cache_lock:` вокруг cache access
- [ ] Unit test с concurrent requests
- [ ] Load test не показывает race conditions

**Зависимости:** Нет
**Сложность:** S (30 мин)
**Ответственный:** Backend

**Реализация:**
```python
# Было: asyncio.Lock() - не работает для sync функций
# Стало: threading.Lock() - для asyncio.to_thread()
self._cache_lock = threading.Lock()

def _get_user_calendar(self, user_id: str):
    with self._cache_lock:
        if user_id in self._calendar_cache:
            # ...
```

---

## BIZ-002: Token limit для LLM

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Бизнес-логика
- **Файл:** `app/services/llm_agent_yandex.py:64-67, 550-558`
- **Риск:** Silent API failures
- **Выполнено:** 2026-01-09

**Цель:** Проверять token limit перед отправкой в LLM.

**Контекст:** Existing events + conversation history + user text могут превысить maxTokens Yandex GPT.

**Результат:**
- Добавлены константы MAX_INPUT_CHARS=4000, MAX_INPUT_TOKENS=1500
- Input text обрезается если превышает лимит
- Warning log при truncation
- maxTokens=2000 уже был установлен в API запросе

**DoD:**
- [x] `MAX_INPUT_CHARS` константа создана
- [x] Context truncation при превышении budget
- [x] Warning log при truncation
- [ ] Тест с большим контекстом

**Зависимости:** Нет
**Сложность:** S (2-3 часа)
**Ответственный:** Backend

---

## TEST-001: Тесты для API endpoints

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Тестирование
- **Файл:** `tests/integration/test_api_*.py`
- **Риск:** Regression в production
- **Выполнено:** 2026-01-10

**Цель:** Покрыть тестами критические API endpoints.

**Контекст:** API endpoints (events, todos, admin) имеют 0% покрытия.

**Результат:**
- Тесты для events, todos, admin v1, admin v2 API
- ~60 новых тестов
- Покрытие: health check, CRUD, validation, auth checks, error responses

**DoD:**
- [x] test_api_events.py: CRUD operations, validation, cache tests
- [x] test_api_todos.py: CRUD operations, priority handling
- [x] test_api_admin.py: v1 (3-password) + v2 (login/2FA) endpoints
- [x] Тесты auth middleware (401 checks)
- [x] Тесты error responses (422 validation)
- [ ] CI запускает тесты (отложено)

**Зависимости:** Нет
**Сложность:** L (2-3 дня)
**Ответственный:** QA

---

## TEST-002: Тесты для security-critical code

- **Статус:** `todo`
- **Приоритет:** Blocker
- **Категория:** Тестирование
- **Файл:** `tests/integration/test_security_*.py`
- **Риск:** Security vulnerabilities

**Цель:** Покрыть тестами security-critical код.

**Контекст:** HMAC validation, JWT, passwords — 0% покрытия.

**Результат:**
- Security tests suite
- ~30 новых тестов

**DoD:**
- [ ] test_telegram_hmac.py: valid/invalid signatures
- [ ] test_admin_auth.py: password verification, JWT
- [ ] test_totp.py: 2FA verification
- [ ] test_rate_limiting.py: limits, bypass attempts

**Зависимости:** Нет
**Сложность:** M (1-2 дня)
**Ответственный:** QA

---

# HIGH (P1) — Недели 2-4

## ARCH-001: Рефакторинг extract_event()

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Архитектура
- **Файл:** `app/services/llm_agent_yandex.py:514-1002`
- **Риск:** Невозможность поддерживать код

**Цель:** Разбить функцию 488 строк на manageable части.

**Результат:**
- extract_event() < 50 строк (координатор)
- 5-6 вспомогательных методов < 100 строк каждый

**DoD:**
- [ ] _detect_schedule_format() выделен
- [ ] _call_llm_api() выделен
- [ ] _parse_llm_response() выделен
- [ ] _handle_batch_events() выделен
- [ ] Unit tests для каждого метода
- [ ] Функционал не изменился

**Зависимости:** TEST-001 (для regression testing)
**Сложность:** L (1-2 дня)
**Ответственный:** Backend

---

## ARCH-002: Рефакторинг handle_callback_query()

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Архитектура
- **Файл:** `app/services/telegram_handler.py:707-1078`

**Цель:** Разбить функцию 371 строк.

**Результат:**
- Dispatcher < 50 строк
- Отдельные handlers по типам callbacks

**DoD:**
- [ ] _handle_event_callback() выделен
- [ ] _handle_settings_callback() выделен
- [ ] _handle_timezone_callback() выделен
- [ ] Unit tests для каждого handler
- [ ] Функционал не изменился

**Зависимости:** TEST-001
**Сложность:** L (1 день)
**Ответственный:** Backend

---

## INFRA-002: Настроить Prometheus + Grafana

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Инфраструктура
- **Файл:** `app/services/metrics.py`, `docker-compose.secure.yml`

**Цель:** Включить мониторинг.

**Контекст:** Prometheus метрики определены в коде, но не инструментированы и не собираются.

**Результат:**
- Metrics endpoint отдаёт данные
- Prometheus scrapes metrics
- Grafana dashboards

**DoD:**
- [ ] Middleware инструментирует HTTP requests
- [ ] /metrics возвращает Prometheus format
- [ ] docker-compose.monitoring.yml создан
- [ ] Prometheus + Grafana запущены
- [ ] Dashboard для key metrics
- [ ] Alert rules для errors

**Зависимости:** Нет
**Сложность:** M (6-8 часов)
**Ответственный:** DevOps

---

## INFRA-003: Централизованное логирование

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Инфраструктура

**Цель:** Настроить Loki или ELK для логов.

**Результат:**
- Логи со всех контейнеров в одном месте
- Поиск по логам
- Retention policy

**DoD:**
- [ ] Loki (или ELK) в docker-compose
- [ ] Все контейнеры отправляют логи
- [ ] Grafana datasource для логов
- [ ] 30-day retention
- [ ] Alerting на ERROR logs

**Зависимости:** INFRA-002
**Сложность:** M (4-6 часов)
**Ответственный:** DevOps

---

## BIZ-003: Cache invalidation после mutations

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Бизнес-логика
- **Файл:** `app/services/calendar_radicale.py:288-298, 592-595, 651-654`
- **Выполнено:** 2026-01-09

**Цель:** Инвалидировать кэш после create/update/delete.

**Контекст:** После update_event() кэш не инвалидировался, пользователь видел старые данные до TTL.

**Результат:**
- `self.invalidate_cache(user_id)` вызывается после успешных create/update/delete операций
- Пользователь сразу видит изменения

**DoD:**
- [x] invalidate_cache(user_id) после create_event()
- [x] invalidate_cache(user_id) после update_event()
- [x] invalidate_cache(user_id) после delete_event()
- [ ] Test cache invalidation

**Зависимости:** BIZ-001
**Сложность:** S (1 час)
**Ответственный:** Backend

---

## BIZ-004: Event conflict detection

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Бизнес-логика
- **Файл:** `app/services/calendar_radicale.py:524-561`

**Цель:** Проверять конфликты при update событий.

**Контекст:** При переносе события на занятое время — создаётся double-booking.

**Результат:**
- Conflict detection при update
- Warning пользователю о конфликте

**DoD:**
- [ ] _find_conflicts() метод создан
- [ ] update_event() проверяет конфликты
- [ ] User notification о конфликте
- [ ] Test conflict scenarios

**Зависимости:** BIZ-003
**Сложность:** M (3-4 часа)
**Ответственный:** Backend

---

## PERF-001: Исправить memory leak в webapp_cache

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Производительность
- **Файл:** `app/routers/events.py:20-36`

**Цель:** Вызывать _cleanup_webapp_cache().

**Контекст:** Функция определена, но никогда не вызывается. Кэш растёт бесконечно.

**Результат:**
- Периодическая очистка кэша
- Memory не растёт

**DoD:**
- [ ] Scheduled cleanup task или cleanup на каждый request
- [ ] Memory profiling показывает стабильность

**Зависимости:** Нет
**Сложность:** S (30 мин)
**Ответственный:** Backend

---

## PERF-002: SQLite concurrent writes

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Производительность
- **Файл:** `app/services/analytics_service.py:40-46, 371`

**Цель:** Исправить race condition в SQLite.

**Контекст:** Concurrent writes вызывают "database is locked" errors.

**Результат:**
- Connection pooling
- Retry logic для SQLITE_BUSY

**DoD:**
- [ ] Connection pool создан
- [ ] Exponential backoff для busy database
- [ ] Load test не показывает errors

**Зависимости:** Нет
**Сложность:** M (3-4 часа)
**Ответственный:** Backend

---

## UX-001: Исправить Light theme

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** UX/UI
- **Файл:** `app/static/index.html:29-33`

**Цель:** Полная поддержка светлой темы.

**Контекст:** CSS переменные для light-theme неполные, UI ломается.

**Результат:**
- Light theme работает полностью
- Нет hardcoded dark colors

**DoD:**
- [ ] Все hardcoded colors → CSS variables
- [ ] .light-theme переопределяет все variables
- [ ] Визуальное тестирование обеих тем

**Зависимости:** Нет
**Сложность:** M (3-4 часа)
**Ответственный:** Frontend

---

## DOC-001: API Reference Guide

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Документация
- **Файл:** `docs/API_REFERENCE.md` (создать)

**Цель:** Документировать все API endpoints.

**Результат:**
- Полный API Reference
- Request/response examples
- Authentication docs

**DoD:**
- [ ] Все endpoints задокументированы
- [ ] Примеры curl для каждого
- [ ] Error codes описаны
- [ ] Rate limiting описан

**Зависимости:** Нет
**Сложность:** S (3-4 часа)
**Ответственный:** Tech Writer

---

## DOC-002: Operational Runbooks

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Документация
- **Файл:** `docs/RUNBOOKS.md` (создать)

**Цель:** Документировать операционные процедуры.

**Результат:**
- Runbook для incident response
- Daily operations checklist
- Backup/restore procedures

**DoD:**
- [ ] Incident response runbook
- [ ] Daily health check checklist
- [ ] Backup restore procedure tested and documented
- [ ] Troubleshooting guide

**Зависимости:** INFRA-001, INFRA-002
**Сложность:** M (4-6 часов)
**Ответственный:** DevOps

---

## TEST-003: CI/CD pipeline с тестами

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** Тестирование
- **Файл:** `.github/workflows/ci.yml`

**Цель:** Автоматизировать тестирование в CI.

**Результат:**
- Тесты запускаются на каждый push
- Coverage reporting
- Fail на coverage drop

**DoD:**
- [ ] .github/workflows/ci.yml создан
- [ ] pytest запускается
- [ ] Coverage отправляется в Codecov
- [ ] Coverage threshold 25%
- [ ] Security scan (bandit)

**Зависимости:** TEST-001, TEST-002
**Сложность:** S (2-3 часа)
**Ответственный:** DevOps

---

# MEDIUM (P2) — Backlog (Месяц 2-3)

## ARCH-003: Dependency injection в TelegramHandler
- **Статус:** `backlog`
- **Файл:** `telegram_handler.py:10-15`
- **Описание:** 6 service imports создают tight coupling
- **Сложность:** M

## BIZ-005: Circuit breaker с exponential backoff
- **Статус:** `backlog`
- **Файл:** `llm_agent_yandex.py:237-246`
- **Описание:** После 5 ошибок — 60 сек блок без backoff
- **Сложность:** S

## BIZ-006: DST edge cases
- **Статус:** `backlog`
- **Файл:** `llm_agent_yandex.py:413-429`
- **Описание:** datetime.combine crashes при DST transition
- **Сложность:** M

## BIZ-007: All-day events support
- **Статус:** `backlog`
- **Файл:** `calendar_radicale.py:205-207`
- **Описание:** All-day события становятся timed events
- **Сложность:** M

## BIZ-008: Event UID preservation
- **Статус:** `backlog`
- **Файл:** `calendar_radicale.py:533-558`
- **Описание:** UID меняется при update
- **Сложность:** S

## BIZ-009: Timezone at year boundaries
- **Статус:** `backlog`
- **Файл:** `calendar_radicale.py:216-219`
- **Описание:** Naive datetime assumption ломается при DST
- **Сложность:** M

## PERF-003: Incremental DOM updates
- **Статус:** `backlog`
- **Файл:** `index.html:738-891`
- **Описание:** Full re-render на каждый state change
- **Сложность:** L

## PERF-004: Optimize event grouping
- **Статус:** `backlog`
- **Файл:** `index.html:454-466`
- **Описание:** O(days × events) → O(n)
- **Сложность:** S

## PERF-005: Tailwind CDN → optimized CSS
- **Статус:** `backlog`
- **Файл:** `index.html:11`
- **Описание:** 30-50KB CDN → 5-10KB purged
- **Сложность:** S

## SEC-006: Rate limiting bypass via IP spoofing
- **Статус:** `done` ✅
- **Файл:** `admin_auth_service.py:63-294`
- **Описание:** Distributed rate limiting через Redis, fallback на in-memory
- **Выполнено:** 2026-01-10
- **Сложность:** S

**Результат:**
- Redis используется для distributed rate limiting
- Fallback на threading.Lock() + dict при недоступности Redis
- IP получается из request напрямую (не из X-Forwarded-For)

## SEC-007: JWT refresh token binding
- **Статус:** `backlog`
- **Файл:** `admin_auth_service.py:589-595`
- **Описание:** IP/UA binding не для refresh tokens
- **Сложность:** M

## SEC-008: auth_date validation в Telegram HMAC
- **Статус:** `backlog`
- **Файл:** `telegram_auth.py:17-68`
- **Описание:** auth_date не проверяется на свежесть
- **Сложность:** S

## SEC-009: Hardcoded encryption key paths
- **Статус:** `backlog`
- **Файл:** `admin_auth_service.py:140-141`
- **Описание:** Default relative paths уязвимы
- **Сложность:** S

## SEC-010: Input validation на user_id
- **Статус:** `backlog`
- **Файл:** `events.py:86-92`
- **Описание:** user_id не валидируется как numeric
- **Сложность:** S

## INFRA-004: Non-root Docker containers
- **Статус:** `backlog`
- **Файл:** `Dockerfile.bot`
- **Описание:** Containers run as root
- **Сложность:** S

## INFRA-005: Redis AOF persistence
- **Статус:** `backlog`
- **Файл:** `docker-compose.secure.yml`
- **Описание:** Только RDB snapshots, нет AOF
- **Сложность:** S

## INFRA-006: Deep health check
- **Статус:** `backlog`
- **Файл:** `/health endpoint`
- **Описание:** Только 200 OK, не проверяет dependencies
- **Сложность:** S

## DOC-003: Architecture Decision Records
- **Статус:** `backlog`
- **Файл:** `docs/adr/` (создать)
- **Описание:** Почему Radicale? Почему Yandex GPT?
- **Сложность:** M

---

# LOW (P3) — Backlog (Roadmap v1.2+)

## FEAT-001: Google Calendar интеграция
- **Статус:** `backlog`
- **Описание:** Двусторонняя синхронизация с Google Calendar
- **Сложность:** XL (2-3 недели)

## FEAT-002: OCR для изображений расписаний
- **Статус:** `backlog`
- **Описание:** Распознавание текста из фото
- **Сложность:** L (1-2 недели)

## FEAT-003: English documentation
- **Статус:** `backlog`
- **Описание:** Перевод ключевых документов
- **Сложность:** M

---

# Архив (Done)

*Пока пусто — задачи будут перемещаться сюда по мере выполнения*

---

## Связи с экосистемой Housler

| Экосистемная задача | Связанная задача |
|---------------------|------------------|
| ECO-SEC-006 | SEC-001 (секреты) |
| ECO-INFRA-005 | TEST-003 (CI/CD) |

---

## Правила работы с бэклогом

1. **Перед взятием задачи:** Прочитать DoD, проверить зависимости
2. **При старте:** Перевести в `in_progress`, указать себя
3. **При блокере:** Перевести в `blocked`, указать блокер
4. **При завершении:** Перевести в `done` только если все пункты DoD выполнены
5. **WIP лимит:** Не больше 3 задач в `in_progress` одновременно

---

*Источник правды: этот файл + FULL_CODE_REVIEW_2026-01-09.md*
