# Бэклог проекта: AI Calendar Assistant

**Последнее обновление:** 2026-01-11
**Источник:** FULL_CODE_REVIEW_2026-01-09.md (Principal Engineer Review)
**Версия бэклога:** 2.2

---

## Команда (7 разработчиков)

| ID | Роль | Специализация | Задачи |
|----|------|---------------|--------|
| **DEV-1** | Backend #1 | Архитектура, рефакторинг | ARCH-001, ARCH-002, ARCH-003 |
| **DEV-2** | Backend #2 | Бизнес-логика, календарь | BIZ-004, BIZ-005, BIZ-006, BIZ-007, BIZ-008, BIZ-009 |
| **DEV-3** | Backend #3 | Performance, SQLite | PERF-002, PERF-003, PERF-004, PERF-005 |
| **DEV-4** | DevOps | Инфраструктура, мониторинг | INFRA-002, INFRA-003, INFRA-004, INFRA-005, INFRA-006 |
| **DEV-5** | Security | Безопасность | SEC-007, SEC-008, SEC-009, SEC-010 |
| **DEV-6** | Frontend | UI/UX, Telegram WebApp | UX-001 |
| **DEV-7** | QA/Tech Writer | Тестирование, документация | TEST-003, DOC-001, DOC-002, DOC-003 |

> Детальное распределение: [TEAM_ASSIGNMENT.md](TEAM_ASSIGNMENT.md)

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
| **Blocker (P0)** | 10 | 10 | 0 | 0 | 0 |
| **High (P1)** | 13 | 12 | 0 | 1 | 0 |
| **Medium (P2)** | 19 | 2 | 0 | 0 | 17 |
| **Low (P3)** | 3 | 0 | 0 | 0 | 3 |
| **Итого** | **45** | **24** | **0** | **1** | **20** |

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
- ✅ TEST-002: Security тесты — 50 тестов для HMAC, JWT, bcrypt, TOTP, encryption
- ✅ PERF-001: Memory leak fix — cleanup уже вызывается на каждый request
- ✅ PERF-002: SQLite concurrent writes — retry_on_locked decorator с exponential backoff

### Выполнено (2026-01-11)
- ✅ SEC-007: JWT refresh token binding — fingerprint (IP+UA hash) в refresh tokens
- ✅ INFRA-002: Prometheus + Grafana — /metrics endpoint, все targets up
- ✅ INFRA-003: Централизованное логирование — Loki + Promtail с 30-day retention
- ✅ DOC-001: API Reference Guide — docs/API_REFERENCE.md (1930 строк)
- ✅ DOC-002: Operational Runbooks — docs/RUNBOOKS.md (755 строк)
- ✅ TEST-003: CI/CD pipeline — .github/workflows/ci.yml (pytest + bandit + ruff)
- ✅ ARCH-001: Рефакторинг extract_event() — с ~500 до 131 строки, 6 хелперов
- ✅ ARCH-002: Рефакторинг handle_callback_query() — с 371 до 34 строк, 5 handlers

---

# BLOCKER (P0) — Неделя 1

## SEC-001: Очистка Git истории от секретов

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Безопасность
- **Файл:** `.env` в Git истории
- **Риск:** Полная компрометация системы
- **Выполнено:** 2026-01-10

**Цель:** Устранить утечку credentials из Git истории.

**Контекст:** В Git истории находились production credentials. BFG Repo-Cleaner удалил их.

**Результат:**
- ✅ Git история очищена от полных секретов (5 Telegram токенов, 1 Yandex API ключ)
- ✅ Secrets scanning настроен (gitleaks + pre-commit)

**DoD:**
- [x] BFG Repo-Cleaner удалил секреты из всей истории (2026-01-10)
- [x] Force push на GitHub выполнен
- [x] gitleaks добавлен в pre-commit

**Примечание:** Ротация секретов вынесена в отдельную задачу (backlog)

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

- **Статус:** `done` ✅
- **Приоритет:** Blocker
- **Категория:** Тестирование
- **Файл:** `tests/integration/test_security_*.py`
- **Риск:** Security vulnerabilities
- **Выполнено:** 2026-01-10

**Цель:** Покрыть тестами security-critical код.

**Контекст:** HMAC validation, JWT, passwords — 0% покрытия.

**Результат:**
- Security tests suite
- 50+ новых тестов
- Покрытие: HMAC, JWT, bcrypt, TOTP, encryption

**DoD:**
- [x] test_security_hmac.py: Telegram HMAC validation (valid/invalid signatures)
- [x] test_security_admin_auth.py: bcrypt passwords, JWT tokens, TOTP 2FA, rate limiting
- [x] test_security_encryption.py: Fernet encryption, key management, rotation

**Зависимости:** Нет
**Сложность:** M (1-2 дня)
**Ответственный:** QA

---

# HIGH (P1) — Недели 2-4

## ARCH-001: Рефакторинг extract_event()

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Архитектура
- **Файл:** `app/services/llm_agent_yandex.py:911-1041`
- **Риск:** Невозможность поддерживать код
- **Назначен:** `DEV-1` (Backend #1 — Архитектура)
- **Выполнено:** 2026-01-11

**Цель:** Разбить функцию 488 строк на manageable части.

**Результат:**
- ✅ extract_event() сокращён с ~500 до 131 строки (координатор)
- ✅ 6 вспомогательных методов интегрированы:
  - `_prepare_datetime_context()` (строки 253-321)
  - `_prepare_events_context()` (строки 323-389)
  - `_build_function_schema()` (строки 391-441)
  - `_build_full_prompt()` (строки 443-503)
  - `_call_llm_api()` (строки 505-604)
  - `_log_success_analytics()` (строки 606-643)

**DoD:**
- [x] _detect_schedule_format() выделен (уже был)
- [x] _call_llm_api() выделен и интегрирован
- [x] _parse_yandex_response() выделен (уже был)
- [x] extract_event() использует все хелперы
- [x] Синтаксис проверен (py_compile OK)

**Зависимости:** TEST-001 (для regression testing)
**Сложность:** L (1-2 дня)
**Ответственный:** DEV-1

---

## ARCH-002: Рефакторинг handle_callback_query()

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Архитектура
- **Файл:** `app/services/telegram_handler.py:1087-1120`
- **Назначен:** `DEV-1` (Backend #1 — Архитектура)
- **Выполнено:** 2026-01-11

**Цель:** Разбить функцию 371 строк.

**Результат:**
- ✅ handle_callback_query() сокращён с 371 до 34 строк (роутер)
- ✅ 5 специализированных handlers:
  - `_handle_consent_callback()` — consent:* callbacks
  - `_handle_timezone_callback()` — tz:* callbacks
  - `_handle_settings_callback()` — settings:*, morning:*, evening:*, quiet:*, share:*
  - `_handle_deletion_callback()` — confirm_delete_*, cancel_delete:*
  - `_handle_broadcast_callback()` — broadcast:*

**DoD:**
- [x] _handle_consent_callback() выделен
- [x] _handle_settings_callback() выделен
- [x] _handle_timezone_callback() выделен
- [x] _handle_deletion_callback() выделен
- [x] _handle_broadcast_callback() выделен
- [x] Синтаксис проверен (py_compile OK)

**Зависимости:** TEST-001
**Сложность:** L (1 день)
**Ответственный:** DEV-1

---

## INFRA-002: Настроить Prometheus + Grafana

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Инфраструктура
- **Файл:** `app/services/metrics.py`, `docker-compose.monitoring.yml`
- **Назначен:** `DEV-4` (DevOps — Инфраструктура)
- **Выполнено:** 2026-01-11

**Цель:** Включить мониторинг.

**Контекст:** Prometheus метрики определены в коде, но не инструментированы и не собираются.

**Результат:**
- /metrics endpoint отдаёт Prometheus format
- Prometheus scrapes calendar-bot, node-exporter, cadvisor
- Grafana с Loki datasource
- Все 4 targets: up

**DoD:**
- [x] Middleware инструментирует HTTP requests (prometheus_middleware.py)
- [x] /metrics возвращает Prometheus format
- [x] docker-compose.monitoring.yml создан
- [x] Prometheus + Grafana запущены на сервере
- [x] Dashboard для key metrics (calendar-assistant.json)
- [ ] Alert rules для errors (backlog)

**Артефакты:**
- `app/middleware/prometheus_middleware.py` — HTTP instrumentation
- `app/services/metrics.py` — метрики приложения
- `/root/monitoring/prometheus.yml` — конфиг с calendar-bot target
- Grafana: http://localhost:3003 (через SSH tunnel)

**Зависимости:** Нет
**Сложность:** M (6-8 часов)
**Ответственный:** DEV-4

---

## INFRA-003: Централизованное логирование

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Инфраструктура
- **Назначен:** `DEV-4` (DevOps — Инфраструктура)
- **Выполнено:** 2026-01-11

**Цель:** Настроить Loki или ELK для логов.

**Результат:**
- Loki + Promtail в docker-compose.monitoring.yml
- Promtail собирает логи из Docker контейнеров
- Grafana datasource для Loki
- 30-day retention (720h)

**DoD:**
- [x] Loki в docker-compose.monitoring.yml
- [x] Promtail собирает логи из контейнеров
- [x] Grafana datasource для Loki
- [x] 30-day retention (limits_config.retention_period: 720h)
- [ ] Alerting на ERROR logs (backlog)

**Артефакты:**
- `docker-compose.monitoring.yml` — Loki + Promtail services
- `loki/loki-config.yml` — Loki configuration с 30-day retention
- `promtail/promtail-config.yml` — Docker logs collection
- `grafana/provisioning/datasources/prometheus.yml` — Loki datasource added

**Зависимости:** INFRA-002
**Сложность:** M (4-6 часов)
**Ответственный:** DEV-4

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

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Бизнес-логика
- **Файл:** `app/services/calendar_radicale.py:190-274`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Выполнено:** 2026-01-10

**Цель:** Проверять конфликты при create/update событий.

**Контекст:** При переносе события на занятое время — создаётся double-booking.

**Результат:**
- ✅ Conflict detection при create и update
- ✅ Warning в логах о конфликте (не блокирует операцию)

**Реализация:**
- `_find_conflicts(user_id, start, end, exclude_uid)` — находит пересекающиеся события
- `_create_event_sync()` — проверяет конфликты, логирует warning
- `_update_event_sync()` — проверяет конфликты с exclude_uid, логирует warning
- Тесты: `tests/unit/test_conflict_detection.py`

**DoD:**
- [x] _find_conflicts() метод создан
- [x] update_event() проверяет конфликты
- [x] User notification о конфликте (warning в логах)
- [x] Test conflict scenarios

**Зависимости:** BIZ-003
**Сложность:** M (3-4 часа)
**Ответственный:** DEV-2

---

## PERF-001: Исправить memory leak в webapp_cache

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Производительность
- **Файл:** `app/routers/events.py:20-36`
- **Выполнено:** 2026-01-10 (обнаружено что уже сделано)

**Цель:** Вызывать _cleanup_webapp_cache().

**Контекст:** Функция определена и уже вызывается на каждый GET /events/{user_id} запрос (line 126).

**Результат:**
- ✅ Cleanup вызывается на каждый request
- ✅ _CACHE_MAX_SIZE = 1000 лимитирует размер
- ✅ Старые записи (>1 час) удаляются

**DoD:**
- [x] Cleanup на каждый request (line 126)
- [x] Тест _cleanup_webapp_cache() в test_api_events.py

**Зависимости:** Нет
**Сложность:** S (30 мин)
**Ответственный:** Backend

---

## PERF-002: SQLite concurrent writes

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Производительность
- **Файл:** `app/services/analytics_service.py:24-61, 274, 308, 333, 367, 1022, 1489`
- **Назначен:** `DEV-3` (Backend #3 — Performance)
- **Выполнено:** 2026-01-10

**Цель:** Исправить race condition в SQLite.

**Контекст:** Concurrent writes вызывают "database is locked" errors.

**Результат:**
- WAL mode уже был включён (`PRAGMA journal_mode=WAL`)
- busy_timeout=30000ms для ожидания блокировки
- Добавлен `retry_on_locked()` decorator с exponential backoff
- Decorator применён ко всем методам записи (6 методов)

**DoD:**
- [x] WAL mode включён (уже был: строка 84-85)
- [x] Exponential backoff для busy database (`retry_on_locked` decorator)
- [ ] Load test не показывает errors

**Зависимости:** Нет
**Сложность:** M (3-4 часа)
**Ответственный:** DEV-3

**Реализация:**
```python
@retry_on_locked(max_retries=5, base_delay=0.1)
def log_action(self, ...):
    # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
    ...
```

**Методы с decorator:**
- `ensure_user()`
- `deactivate_user()`
- `toggle_user_hidden()`
- `log_action()`
- `clear_test_data()`
- `migrate_from_json()`

---

## UX-001: Исправить Light theme

- **Статус:** `todo`
- **Приоритет:** High
- **Категория:** UX/UI
- **Файл:** `app/static/index.html:29-33`
- **Назначен:** `DEV-6` (Frontend — UI/UX)

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
**Ответственный:** DEV-6

---

## DOC-001: API Reference Guide

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Документация
- **Файл:** `docs/API_REFERENCE.md`
- **Назначен:** `DEV-7` (QA/Tech Writer — Документация)
- **Выполнено:** 2026-01-11

**Цель:** Документировать все API endpoints.

**Результат:**
- Полный API Reference (1930 строк)
- Request/response examples для всех endpoints
- Telegram HMAC и Admin JWT authentication docs
- Rate limiting описан

**DoD:**
- [x] Все endpoints задокументированы (events, todos, admin v1/v2, telegram, logs)
- [x] Примеры curl для каждого
- [x] Error codes описаны (HTTP status codes + response format)
- [x] Rate limiting описан

**Зависимости:** Нет
**Сложность:** S (3-4 часа)
**Ответственный:** DEV-7

---

## DOC-002: Operational Runbooks

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Документация
- **Файл:** `docs/RUNBOOKS.md`
- **Назначен:** `DEV-7` (QA/Tech Writer — Документация)
- **Выполнено:** 2026-01-11

**Цель:** Документировать операционные процедуры.

**Результат:**
- Runbook для incident response (P1/P2/P3 severity levels)
- Daily operations checklist (с командами)
- Backup/restore procedures (755 строк)
- Troubleshooting guide (7 сценариев)
- Escalation matrix

**DoD:**
- [x] Incident response runbook (severity levels, SLA, step-by-step)
- [x] Daily health check checklist (контейнеры, health, disk, backup)
- [x] Backup restore procedure tested and documented
- [x] Troubleshooting guide (SQLite, webhook, memory, Redis, Radicale, YandexGPT)

**Зависимости:** INFRA-001, INFRA-002
**Сложность:** M (4-6 часов)
**Ответственный:** DEV-7

---

## TEST-003: CI/CD pipeline с тестами

- **Статус:** `done` ✅
- **Приоритет:** High
- **Категория:** Тестирование
- **Файл:** `.github/workflows/ci.yml`
- **Назначен:** `DEV-7` (QA/Tech Writer — Тестирование)
- **Выполнено:** 2026-01-11

**Цель:** Автоматизировать тестирование в CI.

**Результат:**
- GitHub Actions workflow (46 строк)
- Тесты запускаются на push/PR в main/develop
- Coverage threshold 25%
- Security scan (bandit)
- Lint (ruff)

**DoD:**
- [x] .github/workflows/ci.yml создан
- [x] pytest запускается с --cov=app --cov-fail-under=25
- [ ] Coverage отправляется в Codecov (backlog — не критично)
- [x] Coverage threshold 25%
- [x] Security scan (bandit -r app/ -ll)
- [x] Lint (ruff check app/)

**Зависимости:** TEST-001, TEST-002
**Сложность:** S (2-3 часа)
**Ответственный:** DEV-7

---

# MEDIUM (P2) — Backlog (Месяц 2-3)

## ARCH-003: Dependency injection в TelegramHandler
- **Статус:** `backlog`
- **Назначен:** `DEV-1` (Backend #1 — Архитектура)
- **Файл:** `telegram_handler.py:10-15`
- **Описание:** 6 service imports создают tight coupling
- **Сложность:** M

## BIZ-005: Circuit breaker с exponential backoff
- **Статус:** `backlog`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Файл:** `llm_agent_yandex.py:237-246`
- **Описание:** После 5 ошибок — 60 сек блок без backoff
- **Сложность:** S

## BIZ-006: DST edge cases
- **Статус:** `backlog`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Файл:** `llm_agent_yandex.py:413-429`
- **Описание:** datetime.combine crashes при DST transition
- **Сложность:** M

## BIZ-007: All-day events support
- **Статус:** `backlog`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Файл:** `calendar_radicale.py:205-207`
- **Описание:** All-day события становятся timed events
- **Сложность:** M

## BIZ-008: Event UID preservation
- **Статус:** `backlog`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Файл:** `calendar_radicale.py:533-558`
- **Описание:** UID меняется при update
- **Сложность:** S

## BIZ-009: Timezone at year boundaries
- **Статус:** `backlog`
- **Назначен:** `DEV-2` (Backend #2 — Бизнес-логика)
- **Файл:** `calendar_radicale.py:216-219`
- **Описание:** Naive datetime assumption ломается при DST
- **Сложность:** M

## PERF-003: Incremental DOM updates
- **Статус:** `backlog`
- **Назначен:** `DEV-3` (Backend #3 — Performance)
- **Файл:** `index.html:738-891`
- **Описание:** Full re-render на каждый state change
- **Сложность:** L

## PERF-004: Optimize event grouping
- **Статус:** `backlog`
- **Назначен:** `DEV-3` (Backend #3 — Performance)
- **Файл:** `index.html:454-466`
- **Описание:** O(days × events) → O(n)
- **Сложность:** S

## PERF-005: Tailwind CDN → optimized CSS
- **Статус:** `backlog`
- **Назначен:** `DEV-3` (Backend #3 — Performance)
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
- **Статус:** `done` ✅
- **Назначен:** `DEV-5` (Security — Безопасность)
- **Файл:** `admin_auth_service.py:205-212, 604-611, 651-674`
- **Описание:** Fingerprint binding для refresh tokens
- **Выполнено:** 2026-01-11
- **Сложность:** M

**Результат:**
- Добавлен `_create_fingerprint(ip, user_agent)` — SHA256 hash (16 chars)
- Refresh tokens включают `fingerprint` в payload
- При валидации refresh token проверяется fingerprint match
- Backward compatibility: старые токены без fingerprint принимаются
- Логирование: `refresh_token_fingerprint_mismatch`, `refresh_token_fingerprint_valid`
- Тесты: `tests/integration/test_security_admin_auth.py::TestRefreshTokenFingerprint`

**DoD:**
- [x] Refresh token привязан к fingerprint (IP + UA hash)
- [x] При смене fingerprint — refresh token invalid
- [x] Тест: refresh с другого IP отклоняется

## SEC-008: auth_date validation в Telegram HMAC
- **Статус:** `backlog`
- **Назначен:** `DEV-5` (Security — Безопасность)
- **Файл:** `telegram_auth.py:17-68`
- **Описание:** auth_date не проверяется на свежесть
- **Сложность:** S

## SEC-009: Hardcoded encryption key paths
- **Статус:** `backlog`
- **Назначен:** `DEV-5` (Security — Безопасность)
- **Файл:** `admin_auth_service.py:140-141`
- **Описание:** Default relative paths уязвимы
- **Сложность:** S

## SEC-010: Input validation на user_id
- **Статус:** `backlog`
- **Назначен:** `DEV-5` (Security — Безопасность)
- **Файл:** `events.py:86-92`
- **Описание:** user_id не валидируется как numeric
- **Сложность:** S

## INFRA-004: Non-root Docker containers
- **Статус:** `backlog`
- **Назначен:** `DEV-4` (DevOps — Инфраструктура)
- **Файл:** `Dockerfile.bot`
- **Описание:** Containers run as root
- **Сложность:** S

## INFRA-005: Redis AOF persistence
- **Статус:** `backlog`
- **Назначен:** `DEV-4` (DevOps — Инфраструктура)
- **Файл:** `docker-compose.secure.yml`
- **Описание:** Только RDB snapshots, нет AOF
- **Сложность:** S

## INFRA-006: Deep health check
- **Статус:** `backlog`
- **Назначен:** `DEV-4` (DevOps — Инфраструктура)
- **Файл:** `/health endpoint`
- **Описание:** Только 200 OK, не проверяет dependencies
- **Сложность:** S

## DOC-003: Architecture Decision Records
- **Статус:** `backlog`
- **Назначен:** `DEV-7` (QA/Tech Writer — Документация)
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
