# 📋 План поэтапных доработок с автотестами

**Дата создания:** 2025-01-28  
**Статус:** В процессе

---

## 🎯 Общая цель

Довести проект AI Calendar Assistant до уровня **production-ready** с комплексным покрытием автотестами всего функционала.

---

## 📊 Этапы разработки

### **ЭТАП 1: Критическая безопасность** 🔴
**Приоритет:** КРИТИЧЕСКИЙ  
**Оценка времени:** 2 часа  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ Закрыть публичный доступ к Radicale
2. ✅ Исправить права на .env файл
3. ✅ Добавить проверку конфигурации при старте
4. ✅ Удалить хардкод из config.py
5. ✅ Создать security tests

#### Тесты:
```python
tests/integration/test_security.py
- test_radicale_not_publicly_accessible()
- test_env_file_permissions()
- test_no_hardcoded_secrets()
- test_webhook_authentication()
```

---

### **ЭТАП 2: Базовые интеграционные тесты** 🟡
**Приоритет:** ВЫСОКИЙ  
**Оценка времени:** 4 часа  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ Тесты Calendar Service (CRUD операции)
2. ✅ Тесты Property Service (поиск, scoring)
3. ✅ Тесты Telegram handler (сообщения, команды)
4. ✅ Тесты API endpoints

#### Тесты:
```python
tests/integration/test_calendar_service.py
- test_create_event()
- test_update_event()
- test_delete_event()
- test_get_events()
- test_find_free_slots()

tests/integration/test_property_service.py
- test_search_listings()
- test_dream_score_calculation()
- test_enrichment_orchestrator()

tests/integration/test_telegram_api.py
- test_webhook_receive()
- test_message_processing()
- test_voice_to_text()
```

---

### **ЭТАП 3: Тесты AI агентов** 🟡
**Приоритет:** ВЫСОКИЙ  
**Оценка времени:** 6 часов  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ Тесты Calendar LLM Agent (intent detection)
2. ✅ Тесты Property LLM Agent (criteria extraction)
3. ✅ Тесты обработки разных языков
4. ✅ Тесты edge cases

#### Тесты:
```python
tests/integration/test_llm_calendar_agent.py
- test_create_event_intent()
- test_update_event_intent()
- test_delete_event_intent()
- test_query_intent()
- test_find_free_slots_intent()
- test_recurring_events()
- test_multilingual_support()

tests/integration/test_llm_property_agent.py
- test_extract_search_criteria()
- test_budget_extraction()
- test_location_extraction()
- test_must_have_filters()
```

---

### **ЭТАП 4: Тесты интеграции** 🟢
**Приоритет:** СРЕДНИЙ  
**Оценка времени:** 4 часа  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ Тесты Webhook обработки
2. ✅ Тесты OAuth flow
3. ✅ Тесты Background tasks
4. ✅ Тесты Reminders

#### Тесты:
```python
tests/integration/test_webhooks.py
- test_telegram_webhook_validation()
- test_webhook_secret_check()
- test_callback_query_processing()

tests/integration/test_oauth.py
- test_google_oauth_flow()
- test_token_refresh()
- test_encrypted_token_storage()

tests/integration/test_background_tasks.py
- test_daily_reminders()
- test_event_reminders()
- test_sync_tasks()
```

---

### **ЭТАП 5: Performance тесты** 🟢
**Приоритет:** СРЕДНИЙ  
**Оценка времени:** 3 часа  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ Тесты Rate limiting
2. ✅ Нагрузочные тесты API
3. ✅ Тесты concurrent requests
4. ✅ Тесты Redis cache

#### Тесты:
```python
tests/performance/test_rate_limiting.py
- test_rate_limit_enforcement()
- test_redis_rate_limiter()
- test_burst_detection()
- test_user_blocking()

tests/performance/test_load.py
- test_concurrent_requests()
- test_api_response_time()
- test_llm_agent_performance()
```

---

### **ЭТАП 6: Security тесты** 🟢
**Приоритет:** НИЗКИЙ  
**Оценка времени:** 2 часа  
**Статус:** ⏳ Ожидает

#### Задачи:
1. ✅ SQL Injection protection
2. ✅ XSS protection
3. ✅ Authentication bypass attempts
4. ✅ Data validation

#### Тесты:
```python
tests/security/test_injection.py
- test_sql_injection_protection()
- test_xss_protection()
- test_script_injection()

tests/security/test_authentication.py
- test_unauthorized_access()
- test_token_expiration()
- test_session_hijacking_prevention()
```

---

## 📈 Метрики успеха

### Coverage цели:
- **Текущий:** ~15-20%
- **Целевой:** 80%+
- **Breakdown:**
  - Unit tests: 90%
  - Integration tests: 75%
  - E2E tests: 60%

### Критерии готовности каждого этапа:
1. ✅ Все тесты проходят
2. ✅ Coverage >= 70% для модуля
3. ✅ Нет критических багов
4. ✅ Код ревью пройден
5. ✅ CI/CD pipeline green

---

## 🚀 Порядок выполнения

1. **Сегодня:** ЭТАП 1 (безопасность) + начало ЭТАП 2
2. **Завтра:** ЭТАП 2 завершение + ЭТАП 3 начало
3. **День 3:** ЭТАП 3 завершение + ЭТАП 4
4. **День 4:** ЭТАП 5 + ЭТАП 6
5. **День 5:** Финальная проверка + документация

---

## 🎯 Quick Start Commands

### Запуск всех тестов:
```bash
# Все тесты
pytest

# С coverage
pytest --cov=app --cov-report=html

# Только integration
pytest tests/integration/

# Только определенный этап
pytest tests/integration/test_security.py -v
```

### CI/CD проверка:
```bash
# Линтинг
flake8 app tests

# Форматирование
black --check app tests

# Типы
mypy app

# Тесты
pytest tests/ -v
```

---

**Последнее обновление:** 2025-01-28  
**Версия плана:** 1.0
