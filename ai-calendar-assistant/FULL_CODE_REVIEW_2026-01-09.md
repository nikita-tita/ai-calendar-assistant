# Полное комплексное ревью проекта AI Calendar Assistant

**Дата:** 2026-01-09
**Ревьюер:** Principal Engineer / Security & Architecture Reviewer
**Версия:** 1.0
**Проект:** AI Calendar Assistant
**Кодовая база:** ~18,173 LOC (Python) + ~59KB Frontend

---

# A. EXECUTIVE SUMMARY

## 10-15 главных выводов

1. **Секреты в Git репозитории (CRITICAL)**: Файл `.env` с production credentials находится в истории Git — требуется немедленная ротация всех секретов и очистка истории.

2. **SQL Injection уязвимость**: В `analytics_service.py` используются f-string для SQL-запросов вместо параметризованных запросов.

3. **XSS уязвимости во фронтенде**: Использование `innerHTML` с динамическим контентом и onclick handlers с интерполяцией строк.

4. **Отсутствие автоматизированных бэкапов**: Скрипт backup-calendar.sh существует, но не добавлен в cron — критический риск потери данных.

5. **Мониторинг не настроен**: Prometheus метрики определены в коде, но не инструментированы и не собираются — невозможно диагностировать проблемы в production.

6. **Гигантские функции**: 5 функций превышают 200 строк (до 488 строк) — критически высокая когнитивная сложность.

7. **Тестовое покрытие 13%**: Критические пути (API endpoints, authentication, admin panel) практически не покрыты тестами.

8. **Race conditions в кэше календаря**: `_cache_lock` объявлен, но не используется — возможны inconsistent reads при concurrent requests.

9. **Отсутствие CSRF защиты**: POST endpoints принимают запросы без CSRF токенов — уязвимость для атак.

10. **JWT token binding можно обойти**: IP/User-Agent binding не применяется к refresh tokens — потенциальный token theft.

11. **Документация на 75%**: Отличная структура, но отсутствуют API Reference, Runbooks и ADR.

12. **Нет High Availability**: Single points of failure — один инстанс Redis, Radicale, API.

13. **Circuit breaker открывается навсегда**: После 5 ошибок LLM API блокируется на 60 секунд без exponential backoff.

14. **Memory leak в webapp cache**: `_cleanup_webapp_cache()` определена, но никогда не вызывается.

15. **Light theme не работает**: CSS переменные для светлой темы неполные — UI ломается.

---

## 5 самых критичных рисков

| # | Риск | Категория | Потенциальный ущерб |
|---|------|-----------|---------------------|
| 1 | **Секреты в Git** | Security | Полная компрометация системы: Telegram bot, API keys, DB passwords |
| 2 | **SQL Injection** | Security | Утечка данных всех пользователей, модификация БД |
| 3 | **Отсутствие бэкапов** | Uptime/Data | Полная потеря данных при сбое (уже произошло на старом сервере) |
| 4 | **XSS уязвимости** | Security | Session hijacking, кража данных, malware injection |
| 5 | **Нет мониторинга** | Uptime | Невозможность обнаружить и диагностировать инциденты |

---

## План действий

### Первая неделя (P0 — Blocker)

1. **Ротация всех секретов** — немедленно
2. **Удаление .env из Git истории** — BFG Repo-Cleaner
3. **Фикс SQL Injection** — параметризованные запросы
4. **Настройка автоматических бэкапов** — cron job
5. **Фикс XSS в onclick handlers** — data attributes

### Первый месяц (P1 — High)

1. Добавить CSRF токены для state-changing operations
2. Внедрить security headers middleware
3. Настроить Prometheus + Grafana мониторинг
4. Рефакторинг гигантских функций (extract_event, handle_callback_query)
5. Добавить тесты для API endpoints (~100 тестов)
6. Исправить cache locking в calendar service
7. Добавить валидацию auth_date в Telegram HMAC

---

# B. КЛАСТЕРЫ ПРОБЛЕМ

## 1. Архитектура и границы модулей

| ID | Проблема | Severity |
|----|----------|----------|
| ARCH-001 | Tight coupling в TelegramHandler (6 service imports) | Medium |
| ARCH-002 | Функция extract_event() — 488 строк | Critical |
| ARCH-003 | Функция handle_callback_query() — 371 строк | Critical |
| ARCH-004 | Нет dependency injection | Medium |
| ARCH-005 | Hardcoded values вместо конфигурации (10+ мест) | Medium |
| ARCH-006 | Single point of failure (Redis, Radicale, API) | High |

## 2. Бизнес-логика и корректность

| ID | Проблема | Severity |
|----|----------|----------|
| BIZ-001 | Race condition в calendar cache | Critical |
| BIZ-002 | Token limit не проверяется для LLM | Critical |
| BIZ-003 | Event UID меняется при update | High |
| BIZ-004 | Нет conflict detection при update событий | High |
| BIZ-005 | Cache invalidation отсутствует после mutations | Medium |
| BIZ-006 | Circuit breaker без exponential backoff | Medium |
| BIZ-007 | DST edge cases не обработаны | Medium |
| BIZ-008 | All-day events не поддерживаются корректно | Medium |

## 3. UX/UI и продуктовые флоу

| ID | Проблема | Severity |
|----|----------|----------|
| UX-001 | Light theme CSS неполный | High |
| UX-002 | Нет loading indicators на individual actions | Medium |
| UX-003 | Error messages показывают backend details | Medium |
| UX-004 | Нет Telegram Back Button | Medium |
| UX-005 | Form validation только на пустоту | Medium |
| UX-006 | Нет hapticFeedback в main app | Low |
| UX-007 | Tab switch теряет scroll position | Low |

## 4. Безопасность

| ID | Проблема | Severity |
|----|----------|----------|
| SEC-001 | Секреты в Git репозитории | Critical |
| SEC-002 | SQL Injection в analytics_service | Critical |
| SEC-003 | XSS через innerHTML и onclick | High |
| SEC-004 | JWT binding bypass через refresh token | High |
| SEC-005 | Отсутствие CSRF защиты | High |
| SEC-006 | Rate limiting bypass через IP spoofing | High |
| SEC-007 | Missing security headers | Medium |
| SEC-008 | Hardcoded encryption key paths | Medium |
| SEC-009 | Missing input validation на user_id | Medium |
| SEC-010 | Недостаточное audit logging | Medium |

## 5. Производительность и надежность

| ID | Проблема | Severity |
|----|----------|----------|
| PERF-001 | Full DOM re-render на каждый state change | High |
| PERF-002 | Memory leak в webapp_cache | High |
| PERF-003 | Tailwind CDN вместо optimized CSS | Medium |
| PERF-004 | Inefficient event grouping O(days × events) | Medium |
| PERF-005 | SQLite concurrent writes race condition | High |
| PERF-006 | Conversation history unbounded growth | Medium |

## 6. Прод окружение/инфраструктура/деплой

| ID | Проблема | Severity |
|----|----------|----------|
| INFRA-001 | Нет автоматизированных бэкапов | Critical |
| INFRA-002 | Prometheus метрики не инструментированы | High |
| INFRA-003 | Нет централизованного логирования | High |
| INFRA-004 | Docker containers run as root | Medium |
| INFRA-005 | Redis без AOF persistence | Medium |
| INFRA-006 | Нет health check deep validation | Medium |
| INFRA-007 | Radicale image не pinned (latest) | Low |

## 7. Качество кода и поддерживаемость

| ID | Проблема | Severity |
|----|----------|----------|
| CODE-001 | 5 функций > 200 строк | Critical |
| CODE-002 | Missing type hints (10 public functions) | Low |
| CODE-003 | Dead code: record_message() | Low |
| CODE-004 | Console.log в production коде | Low |
| CODE-005 | Deprecated env var names поддерживаются | Low |

## 8. Тестирование и контроль регрессий

| ID | Проблема | Severity |
|----|----------|----------|
| TEST-001 | Test coverage 13% (target: 25-30%) | Critical |
| TEST-002 | API endpoints не покрыты тестами | Critical |
| TEST-003 | Security-critical code не тестируется | Critical |
| TEST-004 | Skipped tests (требуют Radicale/Yandex) | High |
| TEST-005 | Нет E2E тестов | High |
| TEST-006 | Нет CI/CD pipeline для тестов | High |

## 9. Git/процессы/документация

| ID | Проблема | Severity |
|----|----------|----------|
| DOC-001 | Отсутствует API Reference Guide | High |
| DOC-002 | Отсутствуют Runbooks | High |
| DOC-003 | Отсутствуют ADR | Medium |
| DOC-004 | .env.example outdated (Claude vs Yandex) | Medium |
| DOC-005 | Нет English версии документации | Low |

---

# C. КАРТОЧКИ ПРОБЛЕМ

## SEC-001: Секреты в Git репозитории

**Симптом / где проявляется:**
Файл `.env` с production credentials доступен в Git истории: `ai-calendar-assistant/.env`

**Почему это важно (impact):**
- Telegram Bot Token — полный контроль над ботом
- Yandex GPT API Key — финансовые потери
- Database passwords — доступ ко всем данным пользователей
- Admin passwords — полный административный доступ
- Encryption keys — расшифровка всех приватных данных

**Корневая причина (root cause):**
`.env` файл был закоммичен в репозиторий до добавления в `.gitignore`

**Уровень критичности:** Blocker

**Риск:** Security — полная компрометация системы

**Как воспроизвести:**
```bash
git log --all --full-history -- .env
git show HEAD:.env
```

**Предлагаемое решение:**

*Быстрый фикс (30 мин):*
1. Ротировать ВСЕ секреты немедленно
2. Убедиться что .env в .gitignore

*Правильная реализация (2-3 часа):*
1. Удалить .env из всей Git истории:
```bash
# Установить BFG Repo-Cleaner
brew install bfg
# Удалить .env из истории
bfg --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive
git push --force
```
2. Ротировать все секреты
3. Настроить secrets scanning в CI (gitleaks, detect-secrets)
4. Использовать HashiCorp Vault или AWS Secrets Manager

**Оценка сложности:** M (зависит от кол-ва секретов для ротации)

**Как протестировать после фикса:**
- [ ] `git log --all -- .env` не показывает результатов
- [ ] Старые токены не работают
- [ ] Новые токены в .env работают
- [ ] CI secrets scanning настроен и проходит

---

## SEC-002: SQL Injection в analytics_service

**Симптом / где проявляется:**
`app/services/analytics_service.py` строки 437-458, 783-787

**Почему это важно (impact):**
Атакующий может:
- Извлечь все данные пользователей
- Модифицировать статистику
- Удалить данные
- Получить административный доступ

**Корневая причина (root cause):**
Использование f-strings для SQL запросов вместо параметризованных:
```python
# УЯЗВИМО
f'SELECT COUNT(*) FROM actions WHERE action_type IN {event_types}'
```

**Уровень критичности:** Blocker

**Риск:** Security — утечка данных, модификация БД

**Как воспроизвести:**
```python
# Если error_types приходит из request params:
error_types = ["test' OR '1'='1;--"]
# SQL становится: WHERE action_type IN ('test' OR '1'='1;--')
```

**Предлагаемое решение:**

*Быстрый фикс (1 час):*
```python
# БЕЗОПАСНО — параметризованный запрос
placeholders = ','.join('?' * len(event_types))
query = f'SELECT COUNT(*) FROM actions WHERE action_type IN ({placeholders})'
conn.execute(query, event_types)
```

*Правильная реализация (3-4 часа):*
1. Audit всех SQL запросов в проекте
2. Заменить все f-strings на параметризованные запросы
3. Добавить SQLAlchemy ORM для type-safe запросов
4. Добавить тесты на SQL injection

**Оценка сложности:** S (техническое изменение)

**Пример изменения:**
```python
# До (уязвимо):
cursor = conn.execute(f'''
    SELECT * FROM actions
    WHERE action_type IN ({placeholders})
''')

# После (безопасно):
cursor = conn.execute('''
    SELECT * FROM actions
    WHERE action_type IN (?, ?, ?)
''', tuple(action_types))
```

**Как протестировать после фикса:**
- [ ] Unit test с SQL injection payloads
- [ ] sqlmap scan не находит уязвимостей
- [ ] Code review подтверждает параметризацию

---

## SEC-003: XSS уязвимости во фронтенде

**Симптом / где проявляется:**
`app/static/index.html` строки 795, 826, 859 — onclick handlers с интерполяцией

**Почему это важно (impact):**
- Session hijacking через украденные cookies
- Кража данных пользователей
- Malware injection
- Фишинг атаки от имени бота

**Корневая причина (root cause):**
Dynamic onclick handlers используют string interpolation:
```javascript
onclick="toggleTodo('${todo.id}')"
// Если todo.id = "'; alert('XSS'); //"
// Результат: onclick="toggleTodo(''; alert('XSS'); //')"
```

**Уровень критичности:** High

**Риск:** Security — XSS атаки

**Как воспроизвести:**
1. Создать event с title: `<img src=x onerror='alert(document.cookie)'>`
2. Открыть WebApp
3. JavaScript выполняется

**Предлагаемое решение:**

*Быстрый фикс (2 часа):*
Использовать data attributes вместо onclick:
```html
<!-- Было -->
<button onclick="toggleTodo('${todo.id}')">

<!-- Стало -->
<button data-todo-id="${escapeAttr(todo.id)}">
```

```javascript
// Event delegation
document.addEventListener('click', (e) => {
    const todoId = e.target.dataset.todoId;
    if (todoId) toggleTodo(todoId);
});
```

*Правильная реализация (1 день):*
1. Внедрить Content Security Policy (CSP) headers
2. Использовать DOMPurify для HTML sanitization
3. Рефакторить все innerHTML на createElement/textContent
4. Добавить CSP reporting

**Оценка сложности:** M (требует рефакторинг фронтенда)

**Как протестировать после фикса:**
- [ ] XSS payloads не выполняются
- [ ] CSP headers присутствуют в responses
- [ ] Browser console не показывает CSP violations
- [ ] OWASP ZAP scan чист

---

## INFRA-001: Нет автоматизированных бэкапов

**Симптом / где проявляется:**
`backup-calendar.sh` существует но не в cron. Предыдущий сервер (91.229.8.221) был удалён с потерей всех данных.

**Почему это важно (impact):**
- Полная потеря данных пользователей при сбое
- Потеря календарей, задач, настроек
- Невозможность восстановления после инцидента
- Репутационные потери

**Корневая причина (root cause):**
Backup script не добавлен в crontab, запускается только вручную

**Уровень критичности:** Blocker

**Риск:** Uptime/Data — полная потеря данных

**Как воспроизвести:**
```bash
crontab -l | grep backup  # Ничего не найдено
```

**Предлагаемое решение:**

*Быстрый фикс (15 мин):*
```bash
# SSH на сервер и добавить в cron
(crontab -l 2>/dev/null; echo "0 3 * * * /root/ai-calendar-assistant/backup-calendar.sh >> /var/log/calendar-backup.log 2>&1") | crontab -
```

*Правильная реализация (4-6 часов):*
1. Включить GPG encryption в backup script
2. Настроить upload в S3/Yandex Cloud Storage
3. Добавить backup verification (test restore)
4. Настроить alerting при failed backups
5. Документировать RTO/RPO

**Оценка сложности:** S (добавить cron) / M (полная реализация)

**Пример изменения:**
```bash
# В backup-calendar.sh — раскомментировать:
gpg --symmetric --cipher-algo AES256 --batch --yes \
    --passphrase "$BACKUP_ENCRYPTION_KEY" \
    -o "${BACKUP_DIR}/${DATE}.tar.gz.gpg" \
    "${BACKUP_DIR}/${DATE}.tar.gz"

# Добавить upload:
rclone copy "${BACKUP_DIR}/${DATE}.tar.gz.gpg" remote:calendar-backups/
```

**Как протестировать после фикса:**
- [ ] `crontab -l` показывает backup job
- [ ] Backup создаётся ежедневно в 3:00
- [ ] Backup можно расшифровать и восстановить
- [ ] Cloud storage содержит последние 30 дней

---

## ARCH-002: Функция extract_event() — 488 строк

**Симптом / где проявляется:**
`app/services/llm_agent_yandex.py` строки 514-1002

**Почему это важно (impact):**
- Невозможно понять логику без часа чтения
- Невозможно протестировать отдельные части
- Высокая вероятность багов при изменениях
- Новые разработчики не могут работать с кодом

**Корневая причина (root cause):**
Органический рост функции без рефакторинга. Одна функция выполняет:
- Schedule format detection
- LLM API calls
- Response parsing
- Batch operations
- Refusal handling
- Circuit breaking

**Уровень критичности:** Critical

**Риск:** Code quality — невозможность поддерживать код

**Как воспроизвести:**
```bash
wc -l app/services/llm_agent_yandex.py  # 1600+ строк
# extract_event: строки 514-1002 = 488 строк
```

**Предлагаемое решение:**

*Быстрый фикс (не применимо):*
Требуется полный рефакторинг

*Правильная реализация (1-2 дня):*
Разбить на отдельные методы:
```python
class LLMAgentYandex:
    async def extract_event(self, user_text: str, ...) -> EventDTO:
        # Координирующий метод ~50 строк
        schedule_result = self._detect_schedule_format(user_text, timezone)
        if schedule_result:
            return schedule_result

        llm_response = await self._call_llm_api(user_text, context)
        return self._parse_llm_response(llm_response)

    def _detect_schedule_format(self, text: str, tz: str) -> Optional[EventDTO]:
        # ~100 строк
        pass

    async def _call_llm_api(self, text: str, context: dict) -> dict:
        # ~80 строк
        pass

    def _parse_llm_response(self, response: dict) -> EventDTO:
        # ~100 строк
        pass

    def _handle_batch_events(self, events: list) -> EventDTO:
        # ~50 строк
        pass

    def _handle_refusal(self, response: dict) -> Optional[EventDTO]:
        # ~30 строк
        pass
```

**Оценка сложности:** L (требует careful refactoring с тестами)

**Как протестировать после фикса:**
- [ ] Все существующие тесты проходят
- [ ] Каждый новый метод имеет unit test
- [ ] Code coverage увеличился
- [ ] Cyclomatic complexity < 10 для каждого метода

---

## BIZ-001: Race condition в calendar cache

**Симптом / где проявляется:**
`app/services/calendar_radicale.py` строки 106-110

**Почему это важно (impact):**
- Concurrent requests получают inconsistent данные
- Redundant Radicale lookups под нагрузкой
- Потенциальная потеря данных при concurrent updates
- Memory exhaustion при high concurrency

**Корневая причина (root cause):**
`_cache_lock` объявлен (строка 55), но никогда не используется:
```python
self._cache_lock = asyncio.Lock()  # Объявлен

# Но в коде:
if user_id in self._calendar_cache:  # Не защищено lock'ом!
    cached_cal, cached_time = self._calendar_cache[user_id]
```

**Уровень критичности:** Critical

**Риск:** Data integrity — inconsistent calendar data

**Как воспроизвести:**
```python
# Запустить 10 concurrent requests для одного пользователя
import asyncio
tasks = [calendar_service.get_events(user_id) for _ in range(10)]
await asyncio.gather(*tasks)
# Возможны stale reads и redundant Radicale calls
```

**Предлагаемое решение:**

*Быстрый фикс (30 мин):*
```python
async def _get_user_calendar(self, user_id: str):
    async with self._cache_lock:  # Использовать существующий lock
        now = time.time()
        if user_id in self._calendar_cache:
            cached_cal, cached_time = self._calendar_cache[user_id]
            if now - cached_time < self.CACHE_TTL_SECONDS:
                return cached_cal
        # ... fetch from Radicale
```

*Правильная реализация (2-3 часа):*
1. Per-user locks вместо global lock
2. Cache invalidation после mutations
3. Read-through cache pattern
4. TTL refresh на read

**Оценка сложности:** S (использовать lock) / M (per-user locks)

**Как протестировать после фикса:**
- [ ] Concurrent requests не вызывают race conditions
- [ ] Performance под нагрузкой стабильна
- [ ] Cache invalidation работает после updates
- [ ] Unit tests с concurrent access

---

## TEST-001: Test coverage 13%

**Симптом / где проявляется:**
`tests/` директория: ~2,361 строк тестов для ~18,173 строк кода

**Почему это важно (impact):**
- Регрессии не обнаруживаются до production
- Refactoring невозможен без страха сломать функциональность
- Security-critical код не верифицирован
- Нет confidence в releases

**Корневая причина (root cause):**
Тесты писались ad-hoc, нет test-first culture. Критические пути игнорировались:
- API endpoints: 0% coverage
- Admin auth: 0% coverage
- Telegram HMAC: 0% coverage

**Уровень критичности:** Critical

**Риск:** Quality — регрессии в production

**Как воспроизвести:**
```bash
pytest --cov=app --cov-report=term-missing
# Coverage: ~13%
```

**Предлагаемое решение:**

*Быстрый фикс (1 неделя):*
Добавить тесты для критических путей:
1. API endpoints (events, todos, admin)
2. Authentication (HMAC, JWT, passwords)
3. Security validations

*Правильная реализация (1 месяц):*
1. Установить coverage threshold 60%
2. CI fails при coverage drop
3. Mock external services (Yandex GPT, Radicale)
4. E2E tests для user workflows
5. Security-focused test suite

**Оценка сложности:** L (требует continuous effort)

**Пример нового теста:**
```python
# tests/integration/test_api_events.py
@pytest.mark.asyncio
async def test_create_event_requires_auth(client):
    response = await client.post("/api/events/123", json={
        "title": "Test Event",
        "start": "2026-01-10T10:00:00"
    })
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_create_event_success(authenticated_client):
    response = await authenticated_client.post("/api/events/123", json={
        "title": "Test Event",
        "start": "2026-01-10T10:00:00"
    })
    assert response.status_code == 201
    assert response.json()["title"] == "Test Event"
```

**Как протестировать после фикса:**
- [ ] Coverage > 25%
- [ ] Critical paths 100% covered
- [ ] CI enforces coverage threshold
- [ ] No regressions after refactoring

---

## PERF-001: Full DOM re-render на каждый state change

**Симптом / где проявляется:**
`app/static/index.html` строки 738-891

**Почему это важно (impact):**
- UI freezes на slow devices (50-100ms per render)
- Memory leaks от unreleased event listeners
- Battery drain на mobile
- Poor user experience

**Корневая причина (root cause):**
```javascript
function render() {
    document.getElementById('app').innerHTML = `...1000+ строк HTML...`;
    // Все event listeners уничтожены и созданы заново
}
```

**Уровень критичности:** High

**Риск:** Performance — плохой UX

**Как воспроизвести:**
1. Открыть DevTools > Performance
2. Создать/удалить event
3. Измерить render time: 50-100ms

**Предлагаемое решение:**

*Быстрый фикс (2-3 часа):*
Использовать incremental updates:
```javascript
function updateEventList(events) {
    const container = document.getElementById('event-list');
    // Только обновить изменённые элементы
    events.forEach(event => {
        const existing = container.querySelector(`[data-id="${event.id}"]`);
        if (existing) {
            existing.querySelector('.title').textContent = event.title;
        } else {
            container.appendChild(createEventElement(event));
        }
    });
}
```

*Правильная реализация (1-2 недели):*
1. Внедрить lightweight VDOM (например, Preact)
2. Или использовать lit-html для efficient updates
3. Event delegation вместо inline handlers
4. Lazy rendering для long lists

**Оценка сложности:** M (incremental) / L (full rewrite)

**Как протестировать после фикса:**
- [ ] Render time < 16ms (60fps)
- [ ] Memory не растёт при repeated actions
- [ ] Chrome Lighthouse Performance > 90

---

## DOC-001: Отсутствует API Reference Guide

**Симптом / где проявляется:**
Нет файла `docs/API_REFERENCE.md` или аналога

**Почему это важно (impact):**
- Разработчики не знают как использовать API
- Интеграции требуют reverse engineering
- Onboarding занимает дольше
- Возможны ошибки при использовании API

**Корневая причина (root cause):**
Полагание на auto-generated Swagger UI (`/docs`), который не содержит примеров и best practices

**Уровень критичности:** High

**Риск:** Developer productivity

**Как воспроизвести:**
```bash
ls docs/ | grep -i api  # Нет API_REFERENCE
```

**Предлагаемое решение:**

*Быстрый фикс (2-3 часа):*
Создать базовый API Reference:
```markdown
# API Reference

## Authentication
All endpoints require Telegram WebApp initData in header:
X-Telegram-Init-Data: <initData>

## Endpoints

### GET /api/events/{user_id}
Returns events for user in date range.

**Parameters:**
- user_id (path): Telegram user ID
- start (query): ISO datetime, default: now
- end (query): ISO datetime, default: now + 30 days

**Response:**
{
  "events": [
    {"id": "abc", "title": "Meeting", "start": "2026-01-10T10:00:00Z"}
  ]
}

**Errors:**
- 401: Invalid or missing initData
- 403: user_id mismatch
```

*Правильная реализация (1 день):*
1. Полный API Reference со всеми endpoints
2. Request/response examples
3. Error codes и handling
4. Rate limiting documentation
5. Authentication flows

**Оценка сложности:** S

**Как протестировать после фикса:**
- [ ] Документ существует и актуален
- [ ] Все endpoints задокументированы
- [ ] Примеры работают
- [ ] Новый разработчик может использовать API по документации

---

# D. ПЛАН ИСПРАВЛЕНИЙ

## Roadmap: 0-7 дней (Critical/Blockers)

| День | Задача | Owner | Effort |
|------|--------|-------|--------|
| 1 | SEC-001: Ротация всех секретов | Security | 2h |
| 1 | SEC-001: Удаление .env из Git истории | DevOps | 1h |
| 1 | INFRA-001: Добавить backup в cron | DevOps | 15m |
| 2 | SEC-002: Фикс SQL Injection | Backend | 3h |
| 2-3 | SEC-003: Фикс XSS в onclick handlers | Frontend | 4h |
| 3 | BIZ-001: Использовать cache lock | Backend | 1h |
| 4 | SEC-005: Добавить CSRF токены | Backend | 3h |
| 5-7 | TEST-001: Тесты для API endpoints | QA | 16h |

**Результат недели:** Критические security issues закрыты, бэкапы работают

## Roadmap: 2-4 недели (High Priority)

| Неделя | Задача | Owner | Effort |
|--------|--------|-------|--------|
| 2 | SEC-007: Security headers middleware | Backend | 2h |
| 2 | INFRA-002: Настройка Prometheus + Grafana | DevOps | 8h |
| 2 | INFRA-003: Централизованное логирование (Loki) | DevOps | 6h |
| 2 | BIZ-002: Token limit enforcement для LLM | Backend | 3h |
| 3 | ARCH-002: Рефакторинг extract_event() | Backend | 12h |
| 3 | UX-001: Фикс Light theme CSS | Frontend | 4h |
| 3 | PERF-002: Фикс memory leak в webapp_cache | Backend | 1h |
| 4 | ARCH-003: Рефакторинг handle_callback_query() | Backend | 10h |
| 4 | DOC-001: API Reference Guide | Tech Writer | 4h |
| 4 | TEST-001: Security-focused tests | QA | 12h |

**Результат месяца:** Monitoring работает, код поддерживаемый, документация полная

## Roadmap: 1-3 месяца (Medium Priority)

| Месяц | Задача | Owner | Effort |
|-------|--------|-------|--------|
| 2 | PERF-001: Incremental DOM updates | Frontend | 20h |
| 2 | BIZ-004: Conflict detection при event update | Backend | 6h |
| 2 | INFRA-004: Non-root Docker containers | DevOps | 2h |
| 2 | DOC-002: Operational Runbooks | DevOps | 8h |
| 3 | ARCH-006: Redis Sentinel для HA | DevOps | 12h |
| 3 | TEST-001: E2E test suite | QA | 20h |
| 3 | DOC-003: Architecture Decision Records | Architect | 6h |

**Результат квартала:** Production-grade система с high availability

---

## Quick Wins (кратный эффект за минимум усилий)

| Задача | Effort | Impact | ROI |
|--------|--------|--------|-----|
| INFRA-001: Backup в cron | 15 мин | Предотвращение потери данных | ★★★★★ |
| BIZ-001: Использовать cache lock | 30 мин | Стабильность под нагрузкой | ★★★★★ |
| SEC-007: Security headers | 1 час | Защита от XSS/clickjacking | ★★★★☆ |
| PERF-002: Cache cleanup | 30 мин | Предотвращение memory leak | ★★★★☆ |
| UX-006: HapticFeedback | 30 мин | Улучшение UX | ★★★☆☆ |

---

## "Не делать сейчас" (отложить)

| Задача | Почему отложить |
|--------|-----------------|
| DOC-005: English documentation | Команда русскоязычная, нет международных пользователей |
| INFRA-007: Pin Radicale image | Low risk, не блокирует |
| CODE-002: Missing type hints | Cosmetic, не влияет на функциональность |
| ARCH-006: Kubernetes migration | Текущая нагрузка не требует |
| Property Bot docs | Функциональность отключена |

---

# Приложение: Self-Review Checklist

- [x] Советы не противоречат друг другу
- [x] Решения реализуемы в рамках типичного production
- [x] Для критичных проблем есть чёткий path to fix
- [x] Убрана вода, только факты и решения
- [x] Каждая рекомендация основана на факте из кода
- [x] Приоритеты соответствуют реальному risk assessment
- [x] Effort estimates реалистичны

---

**Документ подготовлен:** 2026-01-09
**Следующий review:** через 1 месяц после внедрения P0 fixes
