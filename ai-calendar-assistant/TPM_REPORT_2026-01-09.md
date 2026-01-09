# TPM Отчёт: AI Calendar Assistant

**Дата:** 2026-01-09
**Тип:** Стартовая калибровка + полная декомпозиция

---

## 1. Что я прочитал/проверил

### Файлы проекта
- `CLAUDE.md` — инструкции для AI (обновлён)
- `CHANGELOG.md` — история изменений
- `README.md` — описание проекта
- `DEPLOY.md` — инструкции деплоя
- `BACKLOG.md` (старый) — 12 задач, устаревший
- `docs/` — 80+ файлов документации
- `FULL_CODE_REVIEW_2026-01-09.md` — полный аудит (45 проблем)

### Код (через code review)
- `app/services/` — 23 сервисных файла
- `app/routers/` — 7 роутеров API
- `app/static/index.html` — WebApp (59KB)
- `tests/` — ~2,361 строк тестов

### Результаты аудита
- 18,173 строк Python кода
- 13% тестовое покрытие
- 45 выявленных проблем
- 10 Blocker, 13 High, 19 Medium, 3 Low

---

## 2. Текущее состояние проекта

Проект **AI Calendar Assistant** находится в production на новом сервере (95.163.227.26) после потери старого сервера с данными. Функционально работает: создание событий голосом/текстом, WebApp, admin panel. Однако code review выявил **критические security issues** (секреты в Git, SQL Injection, XSS) и значительный технический долг (гигантские функции, 13% покрытия тестами, отсутствие мониторинга). **Бэкапы не автоматизированы** — повторная потеря данных возможна. Приоритет: закрыть security blockers в течение недели.

---

## 3. Несоответствия "файлы ↔ доска ↔ факт"

| Проблема | Где | Что не так |
|----------|-----|------------|
| Устаревший BACKLOG.md | `BACKLOG.md` | Содержал 12 задач, не отражал 45 проблем из code review |
| Нет PROJECT_STATUS | Отсутствовал | Не было единого снимка состояния |
| Нет RISKS_AND_BLOCKERS | Отсутствовал | Риски не трекались централизованно |
| Нет DECISIONS_LOG | Отсутствовал | Архитектурные решения не документировались |
| SEC-001 в README "исправлено" | `BACKLOG.md` старый | На самом деле SEC-001 (Redis rate limiter) — другая задача, секреты в Git не упоминались |
| "8.5/10 Production Ready" | `BACKLOG.md` старый | Code review показал 10 Blocker issues — реально ~5/10 |

---

## 4. Что обновлено в документации

| Файл | Действие | Что сделано |
|------|----------|-------------|
| `BACKLOG.md` | Переписан | 45 задач с DoD, Kanban структура, приоритеты |
| `PROJECT_STATUS.md` | Создан | Снимок состояния, метрики, ограничения |
| `RISKS_AND_BLOCKERS.md` | Создан | 2 блокера, 6 рисков с митигацией |
| `DECISIONS_LOG.md` | Создан | 9 архитектурных решений |
| `CLAUDE.md` | Обновлён | Добавлены ссылки на новые документы |
| `FULL_CODE_REVIEW_2026-01-09.md` | Создан ранее | Полный аудит кода |

---

## 5. Обновления для Kanban

### Структура доски

```
Backlog (22) → Todo (23) → In Progress (0) → Review (0) → Blocked (0) → Done (0)
```

### Задачи в Todo (готовы к работе)

| ID | Название | Приоритет | Сложность |
|----|----------|-----------|-----------|
| SEC-001 | Ротация секретов и очистка Git | Blocker | M |
| SEC-002 | Исправить SQL Injection | Blocker | S |
| SEC-003 | Исправить XSS уязвимости | Blocker | M |
| SEC-004 | Добавить CSRF защиту | Blocker | S |
| SEC-005 | Security headers middleware | Blocker | S |
| INFRA-001 | Автоматизировать бэкапы | Blocker | S |
| BIZ-001 | Исправить race condition в cache | Blocker | S |
| BIZ-002 | Token limit для LLM | Blocker | S |
| TEST-001 | Тесты для API endpoints | Blocker | L |
| TEST-002 | Тесты для security-critical code | Blocker | M |
| ARCH-001 | Рефакторинг extract_event() | High | L |
| ARCH-002 | Рефакторинг handle_callback_query() | High | L |
| INFRA-002 | Настроить Prometheus + Grafana | High | M |
| ... | *(ещё 10 High задач)* | High | S-L |

### Задачи в Backlog (не приоритизированы)

22 задачи Medium/Low приоритета — см. `BACKLOG.md`

---

## 6. Следующие 10 конкретных задач

### Неделя 1 (Blockers)

| # | Задача | DoD | Зависимости | Ответственный |
|---|--------|-----|-------------|---------------|
| 1 | **SEC-001: Ротация секретов** | Все токены новые, Git история очищена, gitleaks в CI | Нет | DevOps |
| 2 | **INFRA-001: Бэкапы в cron** | cron job работает, тестовый restore выполнен | Нет | DevOps |
| 3 | **SEC-002: SQL Injection fix** | Все SQL параметризованы, sqlmap scan чист | Нет | Backend |
| 4 | **BIZ-001: Cache lock** | `async with _cache_lock` используется | Нет | Backend |
| 5 | **SEC-003: XSS fix** | onclick → data-*, CSP header добавлен | Нет | Frontend |
| 6 | **SEC-004: CSRF защита** | CSRF middleware, SameSite=Strict | Нет | Backend |
| 7 | **SEC-005: Security headers** | X-Frame-Options, CSP, HSTS в responses | Нет | Backend |
| 8 | **BIZ-002: Token limit** | Context truncation при превышении budget | Нет | Backend |
| 9 | **TEST-001: API тесты** | 50+ тестов для events/todos/admin | Нет | QA |
| 10 | **TEST-002: Security тесты** | 30+ тестов для HMAC/JWT/TOTP | Нет | QA |

### Порядок выполнения (рекомендуемый)

```
День 1: SEC-001 + INFRA-001 (параллельно, DevOps)
День 2: SEC-002 + BIZ-001 (параллельно, Backend)
День 3: SEC-003 (Frontend)
День 4: SEC-004 + SEC-005 (Backend)
День 5: BIZ-002 (Backend)
День 6-7: TEST-001 + TEST-002 (QA)
```

---

## 7. Блокеры и риски

### Активные блокеры

| ID | Блокер | Влияние | Владелец | Дедлайн |
|----|--------|---------|----------|---------|
| BLK-001 | Секреты в Git истории | Полная компрометация | DevOps | 2026-01-10 |
| BLK-002 | Нет автоматических бэкапов | Потеря данных | DevOps | 2026-01-10 |

### Топ-3 риска

| Риск | Вероятность | Влияние | Статус митигации |
|------|-------------|---------|------------------|
| SQL Injection breach | Высокая | Критическое | SEC-002 в Todo |
| Downtime без диагностики | Высокая | Высокое | INFRA-002 в Todo |
| Regression без тестов | Высокая | Среднее | TEST-001/002 в Todo |

### План снятия блокеров

1. **BLK-001 (секреты):**
   - Ротировать токены → BFG удалить историю → gitleaks в CI
   - Время: 2-3 часа
   - Владелец: DevOps

2. **BLK-002 (бэкапы):**
   - Добавить cron job → включить GPG → настроить cloud upload
   - Время: 1-2 часа
   - Владелец: DevOps

---

## Итоговая структура проектных файлов

```
ai-calendar-assistant/
├── PROJECT_STATUS.md           # Снимок состояния (создан)
├── BACKLOG.md                  # Kanban-доска (переписан)
├── RISKS_AND_BLOCKERS.md       # Риски и блокеры (создан)
├── DECISIONS_LOG.md            # Журнал решений (создан)
├── FULL_CODE_REVIEW_2026-01-09.md  # Аудит кода (создан ранее)
├── TPM_REPORT_2026-01-09.md    # Этот отчёт (создан)
├── CLAUDE.md                   # Инструкции AI (обновлён)
├── CHANGELOG.md                # История изменений
├── DEPLOY.md                   # Инструкции деплоя
├── README.md                   # Описание проекта
└── docs/                       # Детальная документация
```

---

## Следующий отчёт

**Дата:** 2026-01-12 (после закрытия Blockers)
**Ожидаемый прогресс:**
- SEC-001, SEC-002, INFRA-001 — Done
- BIZ-001, SEC-003 — Done или Review
- TEST-001 — In Progress

---

*Отчёт подготовлен в соответствии с TPM workflow*
