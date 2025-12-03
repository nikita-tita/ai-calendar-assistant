# Property Bot - Проблемы и исправления

**Дата:** 30 октября 2025, 00:17
**Статус:** Частично исправлено

---

## ✅ ИСПРАВЛЕНО

### 1. Кнопка "Подтвердить" не работала
**Проблема:** `handle_callback_query()` был пустой (только `pass`)

**Решение:** Добавлен роутинг callback в property_handler:
```python
async def handle_callback_query(self, update: Update) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data

    # Route to property handler if in property mode or callback starts with "property_"
    if PROPERTY_BOT_ENABLED and (data.startswith("property_") or self.user_context.get(user_id) == "property"):
        await property_handler.handle_property_callback(update, user_id, data)
```

**Файл:** [telegram_handler_fixed.py](app/services/telegram_handler_fixed.py:383)
**Статус:** ✅ Развёрнуто на сервере

---

## ❌ ТРЕБУЕТ ИСПРАВЛЕНИЯ

### 2. Недостаточно параметров извлекается из запроса

**Пример запроса пользователя:**
```
"Найди квартиру до 18000000 в ипотеку двухкомнатную север города не дальше 20 минут от метро"
```

**Что извлёк бот:**
- ✅ Бюджет: 18 млн
- ✅ Комнат: 2
- ✅ Район: север города

**Что НЕ извлёк:**
- ❌ **Ипотека** - упоминание "в ипотеку"
- ❌ **Метро** - "не дальше 20 минут от метро"

---

## 🔧 ПЛАН ИСПРАВЛЕНИЯ

### Добавить новые параметры в LLM промпт

**Файл:** [app/services/property/llm_agent_property.py](app/services/property/llm_agent_property.py)

**Метод:** `_get_system_prompt()` или где строится промпт для парсинга

**Добавить в REQUIRED/ADDITIONAL PARAMETERS:**

```
10. **Mortgage and payment:**
   - mortgage: true/false - does user want mortgage option
   - mortgage_type: "family", "military", "preferential", "standard"
   - initial_payment: amount in rubles or percentage
   - monthly_payment_max: maximum monthly payment

11. **Metro proximity:**
   - metro_distance_min: minimum walking time to metro (minutes)
   - metro_distance_max: maximum walking time to metro (minutes)
   - metro_transport_type: "walk", "transport", "car"
   - metro_stations: ["Station1", "Station2"] - preferred stations

12. **Delivery date:**
   - delivery_quarter_min: "Q1" | "Q2" | "Q3" | "Q4"
   - delivery_year_min: 2025
   - delivery_quarter_max: "Q1" | "Q2" | "Q3" | "Q4"
   - delivery_year_max: 2026
   - is_already_built: true/false - только готовые объекты
```

### Примеры извлечения:

**Входной текст:** "Найди квартиру до 18000000 в ипотеку двухкомнатную север города не дальше 20 минут от метро"

**Ожидаемый JSON:**
```json
{
  "type": "search_criteria",
  "criteria": {
    "budget_max": 18000000,
    "rooms_min": 2,
    "rooms_max": 2,
    "districts": ["Северный"],
    "mortgage": true,
    "metro_distance_max": 20,
    "metro_transport_type": "walk"
  },
  "summary": "Ищу 2-комнатную квартиру до 18 млн руб в северных районах города, в ипотеку, в пешей доступности от метро (до 20 минут)",
  "confidence": 0.9
}
```

**Входной текст:** "Хочу однушку до 10 млн по семейной ипотеке что сдается в 25-26 году"

**Ожидаемый JSON:**
```json
{
  "type": "search_criteria",
  "criteria": {
    "budget_max": 10000000,
    "rooms_min": 1,
    "rooms_max": 1,
    "mortgage": true,
    "mortgage_type": "family",
    "delivery_year_min": 2025,
    "delivery_year_max": 2026
  },
  "summary": "Ищу 1-комнатную квартиру до 10 млн руб по семейной ипотеке, сдача в 2025-2026 году",
  "confidence": 0.95
}
```

---

## 📝 ДЕТАЛИ РЕАЛИЗАЦИИ

### Fallback extraction

В методе `_fallback_extraction()` тоже нужно добавить распознавание:

```python
# Extract mortgage mention
if any(word in text_lower for word in ['ипотек', 'кредит', 'ипотеч']):
    criteria['mortgage'] = True

    # Detect mortgage type
    if 'семейн' in text_lower:
        criteria['mortgage_type'] = 'family'
    elif 'военн' in text_lower:
        criteria['mortgage_type'] = 'military'
    elif 'льготн' in text_lower:
        criteria['mortgage_type'] = 'preferential'

# Extract metro distance
metro_patterns = [
    r'(\d+)\s*минут.*метро',
    r'метро.*(\d+)\s*минут',
    r'до\s*метро\s*(\d+)',
]
for pattern in metro_patterns:
    match = re.search(pattern, text_lower)
    if match:
        criteria['metro_distance_max'] = int(match.group(1))
        criteria['metro_transport_type'] = 'walk'  # assume walking by default
        break

# Extract delivery date
year_match = re.findall(r'(\d{2,4})\s*год', text_lower)
if year_match:
    years = [int(y) if len(y) == 4 else 2000 + int(y) for y in year_match]
    if len(years) == 1:
        criteria['delivery_year_min'] = years[0]
        criteria['delivery_year_max'] = years[0]
    elif len(years) >= 2:
        criteria['delivery_year_min'] = min(years)
        criteria['delivery_year_max'] = max(years)
```

---

## 🎯 ПРИОРИТЕТЫ

1. **HIGH:** Добавить mortgage и metro_distance в LLM промпт
2. **HIGH:** Добавить delivery_date (срок сдачи) в LLM промпт
3. **MEDIUM:** Обновить fallback extraction
4. **MEDIUM:** Добавить эти параметры в модель SearchCriteria (если еще нет)
5. **LOW:** Обновить подтверждающее сообщение для показа всех параметров

---

## 📊 ТЕКУЩАЯ СХЕМА ПАРАМЕТРОВ

### Базовые (работают):
- ✅ budget_min, budget_max
- ✅ rooms_min, rooms_max
- ✅ districts[]
- ✅ metro_stations[]

### Дополнительные (работают):
- ✅ area_min, area_max
- ✅ floor_min, floor_max
- ✅ category
- ✅ building_types[]
- ✅ renovations[]

### Недостающие (нужно добавить):
- ❌ mortgage (bool)
- ❌ mortgage_type (str)
- ❌ initial_payment (int)
- ❌ monthly_payment_max (int)
- ❌ metro_distance_max (int)
- ❌ metro_transport_type (str)
- ❌ delivery_year_min/max (int)
- ❌ delivery_quarter_min/max (str)

---

## 🚀 ДЕПЛОЙ

После внесения изменений:

```bash
# 1. Обновить llm_agent_property.py на сервере
scp app/services/property/llm_agent_property.py root@SERVER:/root/ai-calendar-assistant/app/services/property/

# 2. Перезапустить бота
docker restart telegram-bot-polling

# 3. Протестировать с запросом:
"Найди квартиру до 18 млн в ипотеку двухкомнатную север города не дальше 20 минут от метро"
```

**Ожидаемый результат:**
Все параметры должны быть извлечены и показаны в подтверждении.

---

## 📞 СЛЕДУЮЩИЕ ШАГИ

1. Исправить LLM промпт с новыми параметрами
2. Обновить fallback extraction
3. Протестировать с разными запросами
4. Обновить UI подтверждения для показа всех параметров
5. Добавить в документацию примеры запросов

**Ответственный:** AI Assistant
**Deadline:** Как можно скорее
