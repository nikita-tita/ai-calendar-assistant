# Гайд по взаимодействию с пользователем в Property Bot

## Дата: 2025-10-28

## Содержание
1. [Воронка диалога](#воронка-диалога)
2. [Сценарии обработки запросов](#сценарии-обработки-запросов)
3. [Работа с большим количеством результатов](#работа-с-большим-количеством-результатов)
4. [Финансовые программы и условия](#финансовые-программы-и-условия)
5. [Умное сужение выборки](#умное-сужение-выборки)

---

## Воронка диалога

### Этап 1: Онбординг (первый контакт)

**Цель:** Собрать минимальные must-have параметры для начала поиска

```
Бот: 👋 Привет! Я помогу найти идеальную квартиру в новостройке.

Давайте начнём с главного:

1️⃣ **Бюджет** - сколько готовы потратить?
   Пример: "до 10 млн" или "от 8 до 12 млн"

2️⃣ **Комнаты** - сколько нужно?
   Пример: "2 комнаты" или "двушка"

3️⃣ **Район** - где хотите жить?
   Пример: "Бутово" или "метро Крестовский"

Можете написать всё в одном сообщении или по очереди!
```

**Минимальные must-have для старта:**
- ✅ `budget_max` (хотя бы верхняя граница)
- ✅ `rooms_min` / `rooms_max`
- ✅ `districts` ИЛИ `metro_stations` (хотя бы один)

**Примеры валидных первых запросов:**
- ✅ "Двушка в Бутово до 12 млн"
- ✅ "3 комнаты, метро Крестовский, бюджет 15 миллионов"
- ✅ "Квартира до 10 млн, 2-3 комнаты, Южное Бутово"

**Примеры НЕвалидных запросов:**
- ❌ "Квартира в Москве" (нет бюджета и комнат)
- ❌ "Двушка недорого" (бюджет неконкретный)
- ❌ "Хочу квартиру" (ничего конкретного)

**Логика обработки:**

```python
# В llm_agent_property.py
async def extract_search_criteria(user_message: str, conversation_history: List) -> Dict:
    """Extract criteria with validation."""

    result = await self._call_yandex_gpt(messages)

    # Проверяем must-have поля
    criteria = result.get("criteria", {})
    missing_fields = []

    if not criteria.get("budget_max"):
        missing_fields.append("бюджет")

    if not (criteria.get("rooms_min") or criteria.get("rooms_max")):
        missing_fields.append("количество комнат")

    if not (criteria.get("districts") or criteria.get("metro_stations")):
        missing_fields.append("район или метро")

    # Если чего-то не хватает - запрашиваем
    if missing_fields:
        return {
            "intent": "clarify",
            "missing_fields": missing_fields,
            "clarify_question": self._generate_clarification_question(missing_fields, criteria),
            "confidence": 0.3
        }

    # Всё есть - можно искать
    return {
        "intent": "search",
        "criteria": criteria,
        "confidence": 0.9
    }

def _generate_clarification_question(self, missing_fields: List[str], partial_criteria: Dict) -> str:
    """Генерируем вопрос для уточнения."""

    if len(missing_fields) == 1:
        if "бюджет" in missing_fields:
            return "Отлично! Уточните, пожалуйста, ваш бюджет. Например: 'до 10 млн' или 'от 8 до 12 млн'"
        elif "количество комнат" in missing_fields:
            return "Супер! Сколько комнат вам нужно? Например: '2 комнаты' или '2-3 комнаты'"
        elif "район или метро" in missing_fields:
            return "Понятно! В каком районе или рядом с каким метро хотите жить?"

    # Если не хватает нескольких - спрашиваем по порядку
    return f"Уточните, пожалуйста: {' и '.join(missing_fields)}"
```

---

### Этап 2: Первичный поиск и анализ результатов

После получения must-have параметров бот делает поиск:

```python
# В property_handler.py или telegram_handler.py

async def handle_search_request(user_id: str, criteria: Dict) -> Dict:
    """Handle search with smart result analysis."""

    # 1. Выполняем поиск
    listings = await property_service.search_listings(
        budget_max=criteria.get("budget_max"),
        rooms_min=criteria.get("rooms_min"),
        rooms_max=criteria.get("rooms_max"),
        districts=criteria.get("districts"),
        metro_stations=criteria.get("metro_stations"),
        limit=500  # Берём больше для анализа
    )

    # 2. Анализируем результаты
    analysis = analyze_search_results(listings, criteria)

    # 3. Решаем, что делать дальше
    if analysis["total_count"] == 0:
        return handle_no_results(criteria, analysis)

    elif analysis["total_count"] < 20:
        # Мало результатов - можно сразу ранжировать
        return handle_few_results(listings, criteria, user_id)

    elif analysis["total_count"] > 200:
        # Слишком много - предлагаем уточнить
        return handle_too_many_results(listings, criteria, analysis)

    else:
        # Нормальное количество - ранжируем и показываем топ
        return handle_optimal_results(listings, criteria, user_id)
```

---

## Сценарии обработки запросов

### Сценарий 1: Нет результатов (0)

**Проблема:** Слишком строгие фильтры, ничего не подходит

**Решение:** Умное расслабление фильтров

```python
def handle_no_results(criteria: Dict, analysis: Dict) -> Dict:
    """Handle zero results - suggest relaxing filters."""

    # Анализируем, какие фильтры можно расслабить
    suggestions = []

    # 1. Бюджет (расширить на 10%)
    if criteria.get("budget_max"):
        new_budget = int(criteria["budget_max"] * 1.1)
        suggestions.append({
            "type": "budget",
            "message": f"Увеличить бюджет до {format_price(new_budget)}?",
            "new_value": new_budget
        })

    # 2. Комнаты (добавить соседние)
    if criteria.get("rooms_min") == criteria.get("rooms_max"):
        rooms = criteria["rooms_min"]
        suggestions.append({
            "type": "rooms",
            "message": f"Рассмотреть также {rooms-1} или {rooms+1} комнатные?",
            "new_value": {"rooms_min": rooms-1, "rooms_max": rooms+1}
        })

    # 3. Районы (расширить соседними)
    if criteria.get("districts"):
        nearby = get_nearby_districts(criteria["districts"])
        suggestions.append({
            "type": "districts",
            "message": f"Рассмотреть соседние районы: {', '.join(nearby)}?",
            "new_value": criteria["districts"] + nearby
        })

    # 4. Ремонт (если был фильтр - убрать)
    if criteria.get("preferred_renovations"):
        suggestions.append({
            "type": "renovation",
            "message": "Убрать фильтр по ремонту?",
            "new_value": None
        })

    return {
        "message": "😔 К сожалению, по вашим критериям ничего не нашлось.\n\n"
                   "Попробуем расширить поиск?",
        "suggestions": suggestions,
        "action": "relax_filters"
    }
```

**Сообщение пользователю:**
```
😔 К сожалению, по вашим критериям ничего не нашлось.

Попробуем расширить поиск?

1. Увеличить бюджет до 13.2 млн? (было 12 млн)
2. Рассмотреть также 1 или 3 комнатные? (было только 2)
3. Рассмотреть соседние районы: Зюзино, Черёмушки?
4. Убрать фильтр "только монолитные дома"?

Выберите вариант или напишите свой
```

---

### Сценарий 2: Мало результатов (1-20)

**Проблема:** Мало вариантов, но они есть

**Решение:** Показываем всё что есть + предлагаем расширить

```python
async def handle_few_results(listings: List, criteria: Dict, user_id: str) -> Dict:
    """Handle few results - show all + suggest expansion."""

    # Ранжируем всё что есть
    client = await property_service.get_client_by_telegram_id(user_id)
    ranked = property_scoring_service.rank_listings(
        [l.dict() for l in listings],
        client.dict() if client else {},
        top_n=len(listings)  # Берём все
    )

    return {
        "message": f"🔍 Нашёл {len(listings)} вариантов по вашим критериям.\n\n"
                   f"Показываю все что есть:",
        "listings": ranked,
        "action": "show_all",
        "suggestion": "Хотите расширить поиск, чтобы увидеть больше вариантов?"
    }
```

**Сообщение пользователю:**
```
🔍 Нашёл 8 вариантов по вашим критериям.

Показываю все что есть:

⭐ 1. [Карточка квартиры]
⭐ 2. [Карточка квартиры]
...
⭐ 8. [Карточка квартиры]

💡 Хотите расширить поиск, чтобы увидеть больше вариантов?
Могу убрать некоторые фильтры или расширить районы.
```

---

### Сценарий 3: Много результатов (200-1000+)

**Проблема:** Слишком много вариантов - сложно выбрать

**Решение:** Умное сужение через приоритизацию

```python
async def handle_too_many_results(listings: List, criteria: Dict, analysis: Dict) -> Dict:
    """Handle too many results - smart narrowing."""

    # Анализируем, по каким параметрам больше всего разброс
    diversity = analyze_diversity(listings)

    # Предлагаем уточнения по порядку важности
    suggestions = []

    # 1. Если много ЖК - предлагаем выбрать топовые
    if diversity["unique_buildings"] > 20:
        top_buildings = get_top_buildings_by_popularity(listings, top_n=5)
        suggestions.append({
            "type": "building",
            "message": "📊 Нашлось более 20 ЖК. Показать топ-5 самых популярных?",
            "options": [b["name"] for b in top_buildings],
            "data": top_buildings
        })

    # 2. Если большой разброс по ремонту - уточняем
    if diversity["renovations"] > 2:
        suggestions.append({
            "type": "renovation",
            "message": "🎨 Квартиры с разным ремонтом. Что предпочитаете?",
            "options": ["Без отделки (дешевле)", "С чистовой отделкой", "Под ключ"],
            "field": "preferred_renovations"
        })

    # 3. Если разброс по типу здания
    if diversity["building_types"] > 2:
        suggestions.append({
            "type": "building_type",
            "message": "🏗 Тип дома имеет значение?",
            "options": ["Монолитный", "Кирпично-монолитный", "Панельный", "Любой"],
            "field": "preferred_building_types"
        })

    # 4. Если разброс по этажам
    if diversity["floor_spread"] > 10:
        suggestions.append({
            "type": "floor",
            "message": "🏢 Предпочтения по этажу?",
            "options": [
                "Не первый и не последний",
                "Низкие этажи (2-5)",
                "Средние этажи (6-12)",
                "Высокие этажи (13+)",
                "Любой"
            ],
            "field": "floor_preferences"
        })

    # 5. Дата сдачи (если новостройки)
    if diversity["handover_dates_spread"] > 12:  # > 1 года
        suggestions.append({
            "type": "handover",
            "message": "📅 Когда нужна квартира?",
            "options": [
                "Уже сдан / ближайшие месяцы",
                "В этом году (2025)",
                "Следующий год (2026)",
                "Не важно"
            ],
            "field": "handover_date"
        })

    return {
        "message": f"🔥 Нашёл {len(listings)} вариантов - это очень много!\n\n"
                   f"Давайте уточним параметры, чтобы выбрать лучшее:",
        "total_count": len(listings),
        "diversity": diversity,
        "suggestions": suggestions,
        "action": "narrow_down"
    }


def analyze_diversity(listings: List) -> Dict:
    """Analyze diversity of results to suggest narrowing."""

    unique_buildings = len(set(l.building_name for l in listings if l.building_name))
    renovations = len(set(l.renovation for l in listings if l.renovation))
    building_types = len(set(l.building_type for l in listings if l.building_type))

    floors = [l.floor for l in listings if l.floor]
    floor_spread = max(floors) - min(floors) if floors else 0

    handover_dates = []
    for l in listings:
        if l.building_year and l.ready_quarter:
            handover_dates.append(l.building_year * 10 + l.ready_quarter)

    handover_dates_spread = max(handover_dates) - min(handover_dates) if handover_dates else 0

    return {
        "unique_buildings": unique_buildings,
        "renovations": renovations,
        "building_types": building_types,
        "floor_spread": floor_spread,
        "handover_dates_spread": handover_dates_spread
    }
```

**Сообщение пользователю (много результатов):**
```
🔥 Нашёл 347 вариантов - это очень много!

Давайте уточним параметры, чтобы выбрать лучшее:

📊 1. Нашлось более 20 ЖК. Показать топ-5 самых популярных?
   • ЖК "Привилегия" (87 квартир)
   • ЖК "NEXT" (64 квартиры)
   • ЖК "Неоклассика" (52 квартиры)
   • ЖК "Достояние" (41 квартира)
   • ЖК "Символ" (38 квартир)

🎨 2. Квартиры с разным ремонтом. Что предпочитаете?
   [ Без отделки ]  [ С чистовой ]  [ Под ключ ]

🏗 3. Тип дома имеет значение?
   [ Монолитный ]  [ Кирпично-монолитный ]  [ Любой ]

📅 4. Когда нужна квартира?
   [ Уже сдан ]  [ В 2025 ]  [ В 2026 ]  [ Не важно ]

Ответьте на вопросы или выберите кнопки
```

---

### Сценарий 4: Один ЖК, много квартир (100+ в одном ЖК)

**Проблема:** Подходит один ЖК, но в нём 100+ типовых планировок

**Решение:** Умная кластеризация по планировкам

```python
async def handle_single_building_many_flats(listings: List, building_name: str, criteria: Dict) -> Dict:
    """Handle case when one building has many matching flats."""

    # Группируем по типовым планировкам
    clusters = cluster_by_layout(listings)

    # Для каждого кластера выбираем лучший вариант
    representatives = []
    for cluster in clusters:
        # Берём самый дешёвый в кластере
        best = min(cluster["flats"], key=lambda x: x.price)
        representatives.append({
            "representative": best,
            "cluster_size": len(cluster["flats"]),
            "price_range": {
                "min": min(f.price for f in cluster["flats"]),
                "max": max(f.price for f in cluster["flats"])
            },
            "floor_range": {
                "min": min(f.floor for f in cluster["flats"] if f.floor),
                "max": max(f.floor for f in cluster["flats"] if f.floor)
            },
            "layout_key": cluster["layout_key"]
        })

    return {
        "message": f"🏢 В ЖК '{building_name}' нашёл {len(listings)} квартир!\n\n"
                   f"Сгруппировал по планировкам - вот {len(representatives)} типовых вариантов:",
        "building_name": building_name,
        "total_flats": len(listings),
        "layout_clusters": representatives,
        "action": "show_clusters"
    }


def cluster_by_layout(listings: List) -> List[Dict]:
    """Cluster flats by similar layout."""

    clusters = {}

    for listing in listings:
        # Создаём ключ планировки
        layout_key = (
            listing.rooms,
            round(listing.area_total / 5) * 5,  # Округляем площадь до 5м²
            listing.balcony_type,
            listing.bathroom_type
        )

        if layout_key not in clusters:
            clusters[layout_key] = {
                "layout_key": layout_key,
                "flats": []
            }

        clusters[layout_key]["flats"].append(listing)

    return list(clusters.values())
```

**Сообщение пользователю (один ЖК, много квартир):**
```
🏢 В ЖК "Привилегия" нашёл 127 квартир!

Сгруппировал по планировкам - вот 8 типовых вариантов:

📐 Планировка 1 (47 квартир)
   • 2 комнаты, 65 м², лоджия, раздельный с/у
   • Этажи: с 3 по 18
   • Цена: от 9.2 до 11.8 млн
   [ Посмотреть варианты ]

📐 Планировка 2 (38 квартир)
   • 2 комнаты, 70 м², лоджия + балкон, раздельный с/у
   • Этажи: с 2 по 16
   • Цена: от 10.1 до 12.5 млн
   [ Посмотреть варианты ]

📐 Планировка 3 (22 квартиры)
   • 2 комнаты, 60 м², лоджия, совмещённый с/у
   • Этажи: с 4 по 19
   • Цена: от 8.7 до 10.9 млн
   [ Посмотреть варианты ]

...

💡 Выберите понравившуюся планировку, покажу все доступные варианты
```

---

### Сценарий 5: Несколько подходящих ЖК (5-15 ЖК)

**Проблема:** Подходит 5+ ЖК, в каждом по 20-50 квартир

**Решение:** Показываем сравнение ЖК с лучшим вариантом из каждого

```python
async def handle_multiple_buildings(listings: List, criteria: Dict, user_id: str) -> Dict:
    """Handle case with multiple suitable buildings."""

    # Группируем по ЖК
    by_building = {}
    for listing in listings:
        building = listing.building_name or "Без названия"
        if building not in by_building:
            by_building[building] = []
        by_building[building].append(listing)

    # Для каждого ЖК берём топ-3 квартиры
    building_summaries = []
    client = await property_service.get_client_by_telegram_id(user_id)

    for building_name, flats in by_building.items():
        # Ранжируем квартиры в этом ЖК
        ranked = property_scoring_service.rank_listings(
            [f.dict() for f in flats],
            client.dict() if client else {},
            top_n=3
        )

        # Собираем статистику по ЖК
        prices = [f.price for f in flats]
        building_summaries.append({
            "building_name": building_name,
            "total_flats": len(flats),
            "price_range": {"min": min(prices), "max": max(prices)},
            "top_3": ranked[:3],
            "avg_dream_score": sum(r["dream_score"] for r in ranked[:3]) / 3,

            # Дополнительная инфо о ЖК
            "developer": flats[0].developer_name,
            "building_type": flats[0].building_type,
            "metro_distance": flats[0].metro_distance_minutes,
            "handover_date": f"{flats[0].ready_quarter}Q {flats[0].building_year}" if flats[0].ready_quarter else None,
            "advantages": flats[0].complex_advantages or [],
        })

    # Сортируем ЖК по среднему Dream Score
    building_summaries.sort(key=lambda x: x["avg_dream_score"], reverse=True)

    return {
        "message": f"🏘 Нашёл {len(by_building)} подходящих ЖК!\n\n"
                   f"Сравниваю лучшие варианты из каждого:",
        "total_buildings": len(by_building),
        "building_summaries": building_summaries,
        "action": "compare_buildings"
    }
```

**Сообщение пользователю (несколько ЖК):**
```
🏘 Нашёл 7 подходящих ЖК!

Сравниваю лучшие варианты из каждого:

━━━━━━━━━━━━━━━━━━━━━━

⭐ 1. ЖК "Привилегия" (87 квартир)
Dream Score: 78/100

Топ вариант: 2 комн, 65 м², 9.2 млн
✓ Кирпично-монолитный, сдан
✓ Метро Крестовский - 10 мин пешком
✓ Чистовая отделка
✓ Ипотека от 7 банков, рассрочка

Преимущества ЖК:
• Благоустроенная территория
• Подземный паркинг
• Детский сад на территории

[ Показать все 87 квартир ]  [ Сравнить ]

━━━━━━━━━━━━━━━━━━━━━━

⭐ 2. ЖК "NEXT" (64 квартиры)
Dream Score: 75/100

Топ вариант: 2 комн, 70 м², 10.5 млн
✓ Монолитный, сдан
✓ Метро Василеостровская - 10 мин транспортом
✓ Без отделки (дешевле!)
✓ Ипотека, рассрочка, мат.капитал

Преимущества ЖК:
• Закрытая территория
• Видовые квартиры
• Парк рядом

[ Показать все 64 квартиры ]  [ Сравнить ]

━━━━━━━━━━━━━━━━━━━━━━

...

💡 Выберите ЖК для детального просмотра или сравните несколько
```

---

## Финансовые программы и условия

### Откуда берём данные о финансовых программах

Все данные **есть в XML-фиде**! В нашем feed_mapper уже реализован парсинг:

#### 1. Ипотека и банки

**Из фида:**
```xml
<mortgage>true</mortgage>
<approved-banks>
  <bank>Сбербанк</bank>
  <bank>ВТБ</bank>
  <bank>Газпромбанк</bank>
  <bank>Санкт-Петербург</bank>
  ...
</approved-banks>
```

**Маппинг:**
```python
listing.mortgage_available = True  # <mortgage>
listing.approved_banks = ["Сбербанк", "ВТБ", "Газпромбанк", ...]
```

#### 2. Способы оплаты (рассрочка, мат.капитал)

**Из фида:**
```xml
<payment-methods>
  <payment-method>Ипотека</payment-method>
  <payment-method>Материнский капитал</payment-method>
  <payment-method>Рассрочка</payment-method>
</payment-methods>
```

**Маппинг:**
```python
listing.payment_methods = ["Ипотека", "Материнский капитал", "Рассрочка"]
```

#### 3. Торг

**Из фида:**
```xml
<haggle>true</haggle>
```

**Маппинг:**
```python
listing.haggle_allowed = True
```

### Как показываем финансовые условия

#### В карточке квартиры:

```python
def format_listing_card(listing: PropertyListingResponse) -> str:
    """Format listing card with financial info."""

    card = f"""
🏠 {listing.title}
💰 {format_price(listing.price)} руб.

📊 Площадь: {listing.area_total} м²
🏢 Этаж: {listing.floor} из {listing.floors_total}
📍 {listing.district}, {listing.metro_station} ({listing.metro_distance_minutes} мин)

💳 Финансовые условия:
"""

    # Ипотека
    if listing.mortgage_available:
        if listing.approved_banks:
            banks_str = ", ".join(listing.approved_banks[:3])
            if len(listing.approved_banks) > 3:
                banks_str += f" и ещё {len(listing.approved_banks) - 3}"
            card += f"✓ Ипотека от {len(listing.approved_banks)} банков ({banks_str})\n"
        else:
            card += "✓ Ипотека доступна\n"

    # Способы оплаты
    if listing.payment_methods:
        for method in listing.payment_methods:
            if method == "Рассрочка":
                card += "✓ Рассрочка от застройщика\n"
            elif method == "Материнский капитал":
                card += "✓ Материнский капитал\n"

    # Торг
    if listing.haggle_allowed:
        card += "✓ Возможен торг\n"

    # Застройщик
    if listing.developer_name:
        card += f"\n🏗 Застройщик: {listing.developer_name}\n"

    return card
```

**Пример карточки:**
```
🏠 2-комн. квартира, 65 м² в ЖК "Привилегия"
💰 9 200 000 руб.

📊 Площадь: 65 м²
🏢 Этаж: 5 из 18
📍 Петроградский, Крестовский остров (10 мин пешком)

💳 Финансовые условия:
✓ Ипотека от 7 банков (Сбербанк, ВТБ, Газпромбанк и ещё 4)
✓ Рассрочка от застройщика
✓ Материнский капитал
✓ Возможен торг

🏗 Застройщик: ГК ПИК
```

### Фильтрация по финансовым условиям

```python
# Пользователь может явно запросить
"Только с ипотекой"          → mortgage_required=True
"С рассрочкой от застройщика" → payment_methods contains "Рассрочка"
"Материнский капитал"        → payment_methods contains "Материнский капитал"
"Аккредитация в Сбербанке"   → approved_banks contains "Сбербанк"
```

**Пример запроса:**
```
User: "Двушка до 10 млн в Бутово, обязательно с рассрочкой"

Бот извлекает:
{
  "budget_max": 10000000,
  "rooms_min": 2,
  "rooms_max": 2,
  "districts": ["Бутово"],
  "payment_methods": ["Рассрочка"]  ← новый фильтр
}

Поиск:
SELECT * FROM property_listings
WHERE price <= 10000000
  AND rooms = 2
  AND district LIKE '%Бутово%'
  AND payment_methods @> '["Рассрочка"]'  ← PostgreSQL JSONB contains
```

---

## Умное сужение выборки

### Стратегия приоритизации вопросов

Когда результатов много (200+), задаём вопросы в таком порядке:

```python
NARROWING_PRIORITY = [
    # 1. Самое важное - ЖК (если их много)
    {
        "condition": lambda analysis: analysis["unique_buildings"] > 15,
        "question_type": "building_selection",
        "impact": "high",  # Сразу сократит выборку в 5-10 раз
    },

    # 2. Ремонт (сильно влияет на цену)
    {
        "condition": lambda analysis: analysis["renovations"] > 2,
        "question_type": "renovation",
        "impact": "high",  # Разница в цене 15-20%
    },

    # 3. Дата сдачи (критично для планирования)
    {
        "condition": lambda analysis: analysis["handover_dates_spread"] > 8,
        "question_type": "handover_date",
        "impact": "medium",  # Сократит на 30-50%
    },

    # 4. Тип здания (влияет на качество)
    {
        "condition": lambda analysis: analysis["building_types"] > 2,
        "question_type": "building_type",
        "impact": "medium",
    },

    # 5. Этаж (личные предпочтения)
    {
        "condition": lambda analysis: analysis["floor_spread"] > 10,
        "question_type": "floor_preference",
        "impact": "low",  # Сократит на 20-30%
    },

    # 6. Финансы (если не указано ранее)
    {
        "condition": lambda criteria: not criteria.get("mortgage_required"),
        "question_type": "financial",
        "impact": "medium",
    },
]
```

### Интерактивные кнопки для быстрого выбора

```python
# В telegram_handler.py

def create_narrowing_keyboard(question_type: str, options: List) -> InlineKeyboardMarkup:
    """Create interactive keyboard for narrowing."""

    keyboard = []

    if question_type == "building_selection":
        # Показываем топ-5 ЖК
        for building in options[:5]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🏢 {building['name']} ({building['count']} квартир)",
                    callback_data=f"building:{building['id']}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("📋 Показать все ЖК", callback_data="buildings:all")
        ])

    elif question_type == "renovation":
        keyboard.append([
            InlineKeyboardButton("Без отделки", callback_data="reno:none"),
            InlineKeyboardButton("Черновая", callback_data="reno:rough"),
        ])
        keyboard.append([
            InlineKeyboardButton("Чистовая", callback_data="reno:clean"),
            InlineKeyboardButton("Под ключ", callback_data="reno:turnkey"),
        ])
        keyboard.append([
            InlineKeyboardButton("Любая", callback_data="reno:any"),
        ])

    elif question_type == "handover_date":
        keyboard.append([
            InlineKeyboardButton("Уже сдан", callback_data="date:ready"),
            InlineKeyboardButton("2025", callback_data="date:2025"),
        ])
        keyboard.append([
            InlineKeyboardButton("2026", callback_data="date:2026"),
            InlineKeyboardButton("Не важно", callback_data="date:any"),
        ])

    return InlineKeyboardMarkup(keyboard)
```

### Прогрессивное уточнение

```python
class NarrowingSession:
    """Track narrowing session state."""

    def __init__(self, user_id: str, initial_criteria: Dict, initial_count: int):
        self.user_id = user_id
        self.criteria = initial_criteria.copy()
        self.history = [{
            "step": 0,
            "criteria": initial_criteria,
            "count": initial_count
        }]
        self.current_step = 0

    async def apply_filter(self, filter_type: str, value: Any) -> Dict:
        """Apply filter and recalculate results."""

        # Обновляем критерии
        if filter_type == "building":
            self.criteria["building_name"] = value
        elif filter_type == "renovation":
            if value != "any":
                self.criteria["preferred_renovations"] = [value]
        elif filter_type == "handover_date":
            if value == "ready":
                self.criteria["building_state"] = "hand-over"
            elif value != "any":
                self.criteria["handover_year_max"] = int(value)

        # Пересчитываем результаты
        new_results = await property_service.search_listings(**self.criteria, limit=500)

        # Сохраняем в историю
        self.current_step += 1
        self.history.append({
            "step": self.current_step,
            "filter_applied": {filter_type: value},
            "criteria": self.criteria.copy(),
            "count": len(new_results)
        })

        return {
            "new_count": len(new_results),
            "previous_count": self.history[-2]["count"],
            "reduction": self.history[-2]["count"] - len(new_results),
            "listings": new_results
        }

    async def undo_last_filter(self) -> Dict:
        """Undo last applied filter."""
        if self.current_step == 0:
            return {"error": "Nothing to undo"}

        # Откатываемся на шаг назад
        self.history.pop()
        self.current_step -= 1
        self.criteria = self.history[-1]["criteria"].copy()

        # Пересчитываем
        results = await property_service.search_listings(**self.criteria, limit=500)

        return {
            "reverted_to_step": self.current_step,
            "count": len(results),
            "listings": results
        }
```

**Пример прогрессивного уточнения:**
```
Шаг 0: 347 квартир (много)
  ↓ Выбрал ЖК "Привилегия"
Шаг 1: 87 квартир (всё ещё много)
  ↓ Выбрал "Чистовая отделка"
Шаг 2: 34 квартиры (норм)
  ↓ Выбрал "Не первый этаж"
Шаг 3: 28 квартир (отлично!)
  → Ранжируем и показываем топ-12
```

---

## Обновление system prompt для LLM-агента

Добавляем в [app/services/property/llm_agent_property.py](app/services/property/llm_agent_property.py):

```python
def _get_enhanced_system_prompt(self, language: str) -> str:
    """Enhanced system prompt with financial and narrowing context."""

    if language == "ru":
        return """Ты - AI-агент для поиска недвижимости (новостроек).

Твоя задача - извлекать параметры поиска и помогать пользователю сузить выбор.

**ФИНАНСОВЫЕ УСЛОВИЯ** (извлекаем из запросов):
- "с ипотекой" → mortgage_required: true
- "рассрочка от застройщика" → payment_methods: ["Рассрочка"]
- "материнский капитал" → payment_methods: ["Материнский капитал"]
- "аккредитация в Сбербанке" → approved_banks: ["Сбербанк"]
- "возможен торг" → haggle_required: true

**УМНОЕ УТОЧНЕНИЕ при большом количестве результатов:**

Если пользователь говорит общее ("квартира в Москве до 15 млн") - это нормально!
НЕ требуй сразу все детали. Начни поиск с must-have, потом уточни.

Must-have для старта:
1. Бюджет (хотя бы budget_max)
2. Комнаты (rooms_min/max)
3. Локация (districts ИЛИ metro_stations)

Nice-to-have (спрашиваем ПОСЛЕ первого поиска, если много результатов):
- Тип здания (building_types)
- Ремонт (renovations)
- Дата сдачи (handover_year)
- Этаж (floor preferences)
- Лифт, балкон и т.д.

**ПРИМЕРЫ правильного извлечения:**

1. "Двушка до 12 млн в Бутово"
   → {criteria: {budget_max: 12000000, rooms: 2, districts: ["Бутово"]}}
   → ХВАТИТ для начала поиска! Не спрашивай больше ничего.

2. "Квартира с ипотекой, рассрочка обязательно"
   → {criteria: {mortgage_required: true, payment_methods: ["Рассрочка"]}}

3. "Только ПИК, сдача в этом году"
   → {criteria: {developers: ["ГК ПИК"], handover_year_max: 2025}}

**СЦЕНАРИЙ УТОЧНЕНИЯ (если нашлось > 100 вариантов):**

Bot: "Нашёл 200+ квартир! Давайте уточним:"
User: "Хочу монолитный дом"
→ {intent: "refine", add_filter: {building_types: ["монолитный"]}}

User: "Без отделки, дешевле"
→ {intent: "refine", add_filter: {renovations: ["Без отделки"]}}

User: "Покажи что есть"
→ {intent: "show_results"}  # Хватит уточнять, показываем топ

Отвечай в формате JSON.
"""
```

---

## Итоговая архитектура диалога

```
User: "Двушка до 12 млн в Бутово"
  ↓
LLM: Extract {budget_max: 12M, rooms: 2, district: "Бутово"}
  ↓
Search: 347 results (TOO MANY)
  ↓
Bot: "Нашёл 347 квартир! Уточним:"
     1. Показать топ-5 ЖК?
     2. Какой ремонт?
     3. Когда сдача?
  ↓
User: [Clicks "ЖК Привилегия"]
  ↓
Narrow: building_name = "Привилегия"
  ↓
Search: 87 results (STILL MANY)
  ↓
Bot: "87 квартир в ЖК Привилегия. Уточним:"
     1. Тип отделки?
     2. Этаж?
  ↓
User: "Чистовая отделка"
  ↓
Narrow: renovation = "Чистовая"
  ↓
Search: 34 results (GOOD!)
  ↓
Bot: "Отлично! Нашёл 34 варианта."
     [Shows top 12 ranked by Dream Score]
  ↓
User: [Views, likes, comments]
  ↓
Bot: [Updates taste_weights, re-ranks]
```

---

## Метрики успеха диалога

### Эффективность уточнений
- **Среднее количество уточнений до показа**: ≤ 3
- **Процент отказов от уточнений**: < 10%
- **Время до первого просмотра**: ≤ 2 минуты

### Качество фильтрации
- **Точность must-have фильтров**: 100% (строгие)
- **Релевантность топ-12**: ≥ 60% лайков
- **Разнообразие в топе**: минимум 3 разных ЖК (если есть)

### Финансовая прозрачность
- **Показ условий ипотеки**: 100% карточек с mortgage_available
- **Видимость банков**: топ-3 из approved_banks
- **Информация о рассрочке**: явно в карточке

---

Готово! Теперь у нас есть полная логика работы с пользователем от первого запроса до показа релевантных результатов. 🎯
