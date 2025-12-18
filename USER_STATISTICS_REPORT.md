# 📊 Отчет по пользователям AI Calendar Assistant

**Дата:** 18 декабря 2025  
**Статус:** ⚠️ Требуется доступ к production БД

---

## ⚠️ ВАЖНО

База данных находится на production сервере:
```
Путь: /var/lib/calendar-bot/analytics.db
Сервер: 91.229.8.221
```

Для получения актуальной статистики нужно:
1. SSH доступ к серверу
2. Или использовать админ-панель: http://your-domain/static/admin.html

---

## 📋 КАК ПОЛУЧИТЬ СТАТИСТИКУ

### Вариант 1: Через админ-панель (РЕКОМЕНДУЕТСЯ)

```
1. Открыть: http://your-domain/static/admin.html
2. Войти с admin/password
3. Посмотреть дашборд:
   - Общее количество пользователей
   - Активные за день/неделю/месяц
   - График активности
   - Список пользователей с деталями
```

### Вариант 2: Через SSH на сервере

```bash
# Подключиться к серверу
ssh root@91.229.8.221

# Перейти в директорию
cd /var/lib/calendar-bot

# Общая статистика
sqlite3 analytics.db "
SELECT 
    COUNT(DISTINCT user_id) as total_users,
    COUNT(DISTINCT CASE WHEN DATE(last_seen) = DATE('now') THEN user_id END) as active_today,
    COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-7 days') THEN user_id END) as active_week,
    COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-30 days') THEN user_id END) as active_month
FROM actions
WHERE is_test = 0;
"

# Когорты по месяцам регистрации
sqlite3 analytics.db "
SELECT 
    strftime('%Y-%m', MIN(timestamp)) as cohort_month,
    COUNT(DISTINCT user_id) as users,
    COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-7 days') THEN user_id END) as active_last_7d,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-7 days') THEN user_id END) / COUNT(DISTINCT user_id), 1) as retention_pct
FROM (
    SELECT 
        user_id,
        MIN(timestamp) as first_seen,
        MAX(timestamp) as last_seen
    FROM actions
    WHERE is_test = 0
    GROUP BY user_id
)
GROUP BY cohort_month
ORDER BY cohort_month DESC;
"

# Когорты по неделям
sqlite3 analytics.db "
SELECT 
    strftime('%Y-W%W', MIN(timestamp)) as cohort_week,
    COUNT(DISTINCT user_id) as users,
    COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-7 days') THEN user_id END) as active_now,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN DATE(last_seen) >= DATE('now', '-7 days') THEN user_id END) / COUNT(DISTINCT user_id), 1) as retention_pct
FROM (
    SELECT 
        user_id,
        MIN(timestamp) as first_seen,
        MAX(timestamp) as last_seen
    FROM actions
    WHERE is_test = 0
    GROUP BY user_id
)
GROUP BY cohort_week
ORDER BY cohort_week DESC
LIMIT 12;
"
```

### Вариант 3: Через API (если сервер запущен)

```bash
# Получить токен (войти)
TOKEN=$(curl -X POST http://your-domain/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}' \
  | jq -r '.token')

# Получить статистику
curl http://your-domain/api/admin/stats \
  -H "Authorization: Bearer $TOKEN" \
  | jq .

# Получить список пользователей
curl http://your-domain/api/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

---

## 📊 ПРИМЕРНАЯ СТРУКТУРА ОТЧЕТА

Когда получишь доступ к БД, отчет будет выглядеть так:

### 1. Общая статистика

```
┌─────────────────────────┬─────────┐
│ Метрика                 │ Значение│
├─────────────────────────┼─────────┤
│ Всего пользователей     │   XXX   │
│ Активных сегодня        │   XXX   │
│ Активных за неделю      │   XXX   │
│ Активных за месяц       │   XXX   │
│ Retention (7 дней)      │   XX%   │
│ Retention (30 дней)     │   XX%   │
└─────────────────────────┴─────────┘
```

### 2. Когорты по месяцам

```
┌────────────┬──────────┬─────────────┬──────────────┬────────────┐
│ Месяц      │ Новых    │ Активных    │ Retention    │ Статус     │
│ регистрации│ юзеров   │ сейчас      │ (%)          │            │
├────────────┼──────────┼─────────────┼──────────────┼────────────┤
│ 2025-12    │   XX     │   XX        │   XX%        │ 🟢 Новая   │
│ 2025-11    │   XX     │   XX        │   XX%        │ 🟡 Средняя │
│ 2025-10    │   XX     │   XX        │   XX%        │ 🔴 Старая  │
│ ...        │   ...    │   ...       │   ...        │ ...        │
└────────────┴──────────┴─────────────┴──────────────┴────────────┘
```

### 3. Когорты по неделям (последние 12 недель)

```
┌─────────────┬──────────┬─────────────┬──────────────┐
│ Неделя      │ Новых    │ Активных    │ Retention    │
│             │ юзеров   │ сейчас      │ (%)          │
├─────────────┼──────────┼─────────────┼──────────────┤
│ 2025-W50    │   XX     │   XX        │   XX%        │
│ 2025-W49    │   XX     │   XX        │   XX%        │
│ 2025-W48    │   XX     │   XX        │   XX%        │
│ ...         │   ...    │   ...       │   ...        │
└─────────────┴──────────┴─────────────┴──────────────┘
```

### 4. Активность по дням недели

```
┌──────────────┬──────────┬──────────────┐
│ День недели  │ Действий │ Уникальных   │
│              │          │ пользователей│
├──────────────┼──────────┼──────────────┤
│ Понедельник  │   XXX    │   XX         │
│ Вторник      │   XXX    │   XX         │
│ Среда        │   XXX    │   XX         │
│ Четверг      │   XXX    │   XX         │
│ Пятница      │   XXX    │   XX         │
│ Суббота      │   XXX    │   XX         │
│ Воскресенье  │   XXX    │   XX         │
└──────────────┴──────────┴──────────────┘
```

### 5. Топ пользователей по активности

```
┌─────────────┬──────────┬──────────┬─────────────┬──────────────┐
│ User ID     │ Username │ Действий │ Событий     │ Последняя    │
│             │          │          │ создано     │ активность   │
├─────────────┼──────────┼──────────┼─────────────┼──────────────┤
│ 123456789   │ @user1   │   XXX    │   XX        │ 2025-12-18   │
│ 987654321   │ @user2   │   XXX    │   XX        │ 2025-12-17   │
│ ...         │ ...      │   ...    │   ...       │ ...          │
└─────────────┴──────────┴──────────┴─────────────┴──────────────┘
```

---

## 🔧 СКРИПТ ДЛЯ АВТОМАТИЧЕСКОГО ОТЧЕТА

Создай файл `scripts/generate_user_report.py`:

```python
#!/usr/bin/env python3
"""Generate user statistics report."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "/var/lib/calendar-bot/analytics.db"

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("📊 ОТЧЕТ ПО ПОЛЬЗОВАТЕЛЯМ AI CALENDAR ASSISTANT")
    print("=" * 70)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Общая статистика
    print("1️⃣ ОБЩАЯ СТАТИСТИКА")
    print("-" * 70)
    
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT user_id) as total_users,
            COUNT(DISTINCT CASE WHEN DATE(timestamp) = DATE('now') THEN user_id END) as active_today,
            COUNT(DISTINCT CASE WHEN DATE(timestamp) >= DATE('now', '-7 days') THEN user_id END) as active_week,
            COUNT(DISTINCT CASE WHEN DATE(timestamp) >= DATE('now', '-30 days') THEN user_id END) as active_month
        FROM actions
        WHERE is_test = 0
    """)
    
    row = cursor.fetchone()
    total, today, week, month = row
    
    print(f"Всего пользователей:     {total:>6}")
    print(f"Активных сегодня:        {today:>6}")
    print(f"Активных за неделю:      {week:>6}")
    print(f"Активных за месяц:       {month:>6}")
    print(f"Retention (7 дней):      {week/total*100:>5.1f}%")
    print(f"Retention (30 дней):     {month/total*100:>5.1f}%")
    print()
    
    # 2. Когорты по месяцам
    print("2️⃣ КОГОРТЫ ПО МЕСЯЦАМ")
    print("-" * 70)
    print(f"{'Месяц':<12} {'Новых':>8} {'Активных':>10} {'Retention':>10}")
    print("-" * 70)
    
    cursor.execute("""
        SELECT 
            strftime('%Y-%m', MIN(timestamp)) as cohort_month,
            COUNT(DISTINCT user_id) as users,
            COUNT(DISTINCT CASE WHEN DATE(MAX(timestamp)) >= DATE('now', '-7 days') THEN user_id END) as active,
            ROUND(100.0 * COUNT(DISTINCT CASE WHEN DATE(MAX(timestamp)) >= DATE('now', '-7 days') THEN user_id END) / COUNT(DISTINCT user_id), 1) as retention
        FROM actions
        WHERE is_test = 0
        GROUP BY user_id
        HAVING cohort_month IS NOT NULL
        GROUP BY cohort_month
        ORDER BY cohort_month DESC
        LIMIT 12
    """)
    
    for row in cursor.fetchall():
        month, users, active, retention = row
        print(f"{month:<12} {users:>8} {active:>10} {retention:>9.1f}%")
    
    print()
    
    # 3. Топ пользователей
    print("3️⃣ ТОП-10 АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ")
    print("-" * 70)
    print(f"{'User ID':<15} {'Username':<20} {'Действий':>10} {'Событий':>10}")
    print("-" * 70)
    
    cursor.execute("""
        SELECT 
            user_id,
            COALESCE(username, 'N/A') as username,
            COUNT(*) as actions,
            COUNT(CASE WHEN action_type LIKE 'event_%' THEN 1 END) as events
        FROM actions
        WHERE is_test = 0
        GROUP BY user_id
        ORDER BY actions DESC
        LIMIT 10
    """)
    
    for row in cursor.fetchall():
        user_id, username, actions, events = row
        print(f"{user_id:<15} {username:<20} {actions:>10} {events:>10}")
    
    print()
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    generate_report()
```

Запустить на сервере:
```bash
python3 scripts/generate_user_report.py
```

---

## 📞 ЧТО ДЕЛАТЬ ДАЛЬШЕ

1. **Получить доступ к серверу:**
   ```bash
   ssh root@91.229.8.221
   ```

2. **Или использовать админ-панель:**
   - Открыть http://your-domain/static/admin.html
   - Войти
   - Посмотреть статистику

3. **Или запустить скрипт на сервере:**
   ```bash
   cd /path/to/project
   python3 scripts/generate_user_report.py > user_report_$(date +%Y%m%d).txt
   ```

4. **Прислать мне результат** - я сделаю красивые таблицы!

---

**P.S.** Если нужна помощь с доступом к серверу или админ-панели - дай знать!

