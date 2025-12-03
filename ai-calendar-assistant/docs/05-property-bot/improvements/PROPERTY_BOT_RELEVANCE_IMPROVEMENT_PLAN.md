# План улучшения релевантности поиска недвижимости

## Дата создания: 2025-10-28

## Резюме выполненных работ

### ✅ Завершено
1. **Расширены схемы данных** ([app/schemas/property.py](app/schemas/property.py))
   - PropertyListingCreate: добавлено 30+ новых полей из фида База.Про
   - PropertyClientCreate: добавлено 15+ новых фильтров для точного подбора

2. **Обновлены модели БД** ([app/models/property.py](app/models/property.py))
   - PropertyListing: полная поддержка всех полей из XML-фида
   - PropertyClient: расширенные фильтры по всем параметрам

3. **Создан сервис маппинга фида** ([app/services/property/feed_mapper.py](app/services/property/feed_mapper.py))
   - Полный парсинг XML-формата База.Про
   - Категоризация изображений (планировка, фото ЖК, поэтажный план)
   - Извлечение финансовой информации (ипотека, банки, способы оплаты)
   - Обработка преимуществ ЖК и застройщика

---

## Карта маппинга: XML → Модель бота

### 🟢 Критически важные поля (Must-have)

| XML Тег | Поле модели | Статус | Примечание |
|---------|-------------|--------|------------|
| `<category>` | `category` | ✅ | Фильтруем только "квартира" |
| `<price><value>` | `price` | ✅ | Must-have фильтр |
| `<rooms>` | `rooms` | ✅ | Must-have фильтр |
| `<area><value>` | `area_total` | ✅ | Must-have фильтр |
| `<living-space><value>` | `living_area` | ✅ | Для детального сравнения |
| `<kitchen-space><value>` | `kitchen_area` | ✅ | Важно для семей |
| `<renovation>` | `renovation` | ✅ | **Критично!** Часто спрашивают |
| `<floor>` | `floor` | ✅ | С фильтром не первый/последний |
| `<floors-total>` | `floors_total` | ✅ | Для расчёта последнего этажа |
| `<lift>` | `has_elevator` | ✅ | Важно для высоких этажей |
| `<metro><name>` | `metro_station` | ✅ | Ключевой фактор локации |
| `<metro><time-on-foot>` | `metro_distance_minutes` | ✅ | Время до метро критично |

### 🟡 Важные поля (Should-have)

| XML Тег | Поле модели | Статус | Использование |
|---------|-------------|--------|---------------|
| `<building-name>` | `building_name` | ✅ | Для поиска по ЖК, SEO |
| `<building-type>` | `building_type` | ✅ | Предпочтения клиента |
| `<balcony>` | `balcony_type` | ✅ | Лоджия vs балкон |
| `<bathroom-unit>` | `bathroom_count`, `bathroom_type` | ✅ | Раздельный vs совмещённый |
| `<ceiling-height>` | `ceiling_height` | ✅ | Для любителей высоких потолков |
| `<ready-quarter>` | `ready_quarter` | ✅ | Дата сдачи для новостроек |
| `<mortgage>` | `mortgage_available` | ✅ | Доступность ипотеки |
| `<payment-methods>` | `payment_methods` | ✅ | Ипотека, рассрочка, мат.капитал |
| `<approved-banks>` | `approved_banks` | ✅ | Список аккредитованных банков |
| `<image tag="plan">` | `plan_images` | ✅ | **Критично для принятия решения** |
| `<image tag="floorplan">` | `floor_plan_images` | ✅ | Поэтажный план |

### 🔵 Дополнительные поля (Nice-to-have)

| XML Тег | Поле модели | Статус | Использование |
|---------|-------------|--------|---------------|
| `<advantages>` | `complex_advantages` | ✅ | Преимущества ЖК для описания |
| `<complex-description>` | `complex_description` | ✅ | Описание комплекса |
| `<developer-name>` | `developer_name` | ✅ | Репутация застройщика |
| `<developer-documents>` | `builder_data.documents` | ✅ | Документы застройщика |
| `<sales-agent>` | `agent_data` | ✅ | Контакты для связи |
| `<haggle>` | `haggle_allowed` | ✅ | Возможность торга |
| `<building-state>` | `building_state` | ✅ | Сдан vs строится |
| `<building-phase>` | `building_phase` | ✅ | Очередь строительства |

---

## Новые возможности фильтрации

### Для клиента (PropertyClient)

#### 1. **Базовые фильтры** (уже были)
- ✅ Бюджет (min/max)
- ✅ Количество комнат (min/max)
- ✅ Площадь (min/max)
- ✅ Тип сделки (покупка/аренда)

#### 2. **Локация** (расширено)
- ✅ Районы (список)
- ✅ Станции метро (список)
- ✅ Максимальное время до метро
- 🆕 **Поиск по названию ЖК**

#### 3. **Этажи** (расширено)
- ✅ Диапазон этажей
- ✅ Не первый этаж
- ✅ Не последний этаж
- ✅ Требуется лифт

#### 4. **🆕 Тип здания**
- `preferred_building_types`: ["кирпично-монолитный", "панельный", "монолитный"]
- `exclude_building_types`: ["панельный"] (исключить)

#### 5. **🆕 Ремонт**
- `preferred_renovations`: ["Без отделки", "Чистовая отделка"]
- `exclude_renovations`: ["Без отделки"] (только с отделкой)

#### 6. **🆕 Планировка**
- `balcony_required`: true (обязателен балкон/лоджия)
- `preferred_balcony_types`: ["лоджия", "терраса"]
- `bathroom_type_preference`: "раздельный"
- `min_ceiling_height`: 3.0 (минимум 3 метра)

#### 7. **🆕 Финансы**
- `mortgage_required`: true (только с ипотекой)
- `preferred_payment_methods`: ["Ипотека", "Рассрочка"]

#### 8. **🆕 Дата сдачи (для новостроек)**
- `handover_quarter_min`: 2 (со 2 квартала)
- `handover_quarter_max`: 4
- `handover_year_min`: 2025
- `handover_year_max`: 2026

#### 9. **🆕 Застройщик**
- `preferred_developers`: ["ГК ПИК", "ЛСР"]
- `exclude_developers`: ["Проблемный застройщик"]

#### 10. **🆕 Инфраструктура**
- `school_nearby_required`: true (школа в 1км)
- `kindergarten_nearby_required`: true (детский сад)
- `park_nearby_required`: true (парк рядом)

---

## Сценарии работы с пользователем

**Полный гайд:** [PROPERTY_BOT_USER_FLOW_GUIDE.md](PROPERTY_BOT_USER_FLOW_GUIDE.md)

### Ключевые сценарии

#### 1. **Нет результатов (0)** - Умное расслабление фильтров
- Предлагаем увеличить бюджет на 10%
- Расширить диапазон комнат (±1)
- Добавить соседние районы
- Убрать строгие фильтры (renovation, building_type)

#### 2. **Мало результатов (1-20)** - Показываем всё + расширение
- Ранжируем все варианты
- Показываем полный список
- Предлагаем расширить поиск для разнообразия

#### 3. **Много результатов (200+)** - Умное сужение
- Анализируем разброс (ЖК, ремонт, этажи, дата сдачи)
- Предлагаем уточнения по приоритету:
  1. Выбор ЖК (если > 15 ЖК)
  2. Тип ремонта (сильно влияет на цену)
  3. Дата сдачи (критично для планирования)
  4. Тип здания
  5. Этаж
  6. Финансовые условия

#### 4. **Один ЖК, много квартир (100+)** - Кластеризация по планировкам
- Группируем по типовым планировкам
- Показываем представителя каждого кластера
- Для выбранной планировки показываем все варианты

#### 5. **Несколько ЖК (5-15)** - Сравнение ЖК
- Показываем топ-3 квартиры из каждого ЖК
- Рассчитываем средний Dream Score для ЖК
- Даём информацию о застройщике и условиях

### Финансовые условия (из XML-фида)

**Что извлекаем:**
- ✅ `<mortgage>true</mortgage>` → `mortgage_available`
- ✅ `<approved-banks>` → список банков с аккредитацией
- ✅ `<payment-methods>` → ["Ипотека", "Рассрочка", "Материнский капитал"]
- ✅ `<haggle>true</haggle>` → возможность торга

**Как показываем:**
```
💳 Финансовые условия:
✓ Ипотека от 7 банков (Сбербанк, ВТБ, Газпромбанк и ещё 4)
✓ Рассрочка от застройщика
✓ Материнский капитал
✓ Возможен торг
```

**Фильтрация:**
- "только с ипотекой" → `mortgage_required=True`
- "с рассрочкой" → `payment_methods` contains "Рассрочка"
- "аккредитация в Сбербанке" → `approved_banks` contains "Сбербанк"

---

## Следующие шаги реализации

### 📋 **Задача 1: Обновить логику поиска (search_listings)**
**Файл:** [app/services/property/property_service.py](app/services/property/property_service.py:209-270)

**Что добавить:**

```python
async def search_listings(
    self,
    # Existing filters...

    # 🆕 Building filters
    building_types: Optional[List[str]] = None,
    exclude_building_types: Optional[List[str]] = None,
    building_name: Optional[str] = None,  # Поиск по ЖК

    # 🆕 Renovation
    renovations: Optional[List[str]] = None,
    exclude_renovations: Optional[List[str]] = None,

    # 🆕 Layout filters
    balcony_required: Optional[bool] = None,
    balcony_types: Optional[List[str]] = None,
    bathroom_type: Optional[str] = None,
    min_ceiling_height: Optional[float] = None,

    # 🆕 Elevator
    requires_elevator: Optional[bool] = None,

    # 🆕 Financial
    mortgage_required: Optional[bool] = None,

    # 🆕 Handover date
    handover_quarter_min: Optional[int] = None,
    handover_quarter_max: Optional[int] = None,
    handover_year_min: Optional[int] = None,
    handover_year_max: Optional[int] = None,

    # 🆕 Developer
    developers: Optional[List[str]] = None,
    exclude_developers: Optional[List[str]] = None,

    # 🆕 Infrastructure (POI)
    school_nearby: Optional[bool] = None,
    kindergarten_nearby: Optional[bool] = None,
    park_nearby: Optional[bool] = None,

    limit: int = 100
) -> List[PropertyListingResponse]:
    """Enhanced search with all new filters."""

    query = session.query(PropertyListing).filter(
        PropertyListing.is_active == True,
        PropertyListing.category == "квартира"  # 🆕 Only apartments
    )

    # 🆕 Building type filters
    if building_types:
        query = query.filter(PropertyListing.building_type.in_(building_types))
    if exclude_building_types:
        query = query.filter(~PropertyListing.building_type.in_(exclude_building_types))

    # 🆕 Building name search (fuzzy match)
    if building_name:
        query = query.filter(PropertyListing.building_name.ilike(f"%{building_name}%"))

    # 🆕 Renovation filters
    if renovations:
        query = query.filter(PropertyListing.renovation.in_(renovations))
    if exclude_renovations:
        query = query.filter(~PropertyListing.renovation.in_(exclude_renovations))

    # 🆕 Balcony
    if balcony_required:
        query = query.filter(PropertyListing.balcony_type.isnot(None))
    if balcony_types:
        query = query.filter(PropertyListing.balcony_type.in_(balcony_types))

    # 🆕 Bathroom type
    if bathroom_type:
        query = query.filter(PropertyListing.bathroom_type == bathroom_type)

    # 🆕 Ceiling height
    if min_ceiling_height:
        query = query.filter(PropertyListing.ceiling_height >= min_ceiling_height)

    # 🆕 Elevator
    if requires_elevator:
        query = query.filter(PropertyListing.has_elevator == True)

    # 🆕 Mortgage
    if mortgage_required:
        query = query.filter(PropertyListing.mortgage_available == True)

    # 🆕 Handover date (for new flats)
    if handover_year_min:
        query = query.filter(PropertyListing.building_year >= handover_year_min)
    if handover_year_max:
        query = query.filter(PropertyListing.building_year <= handover_year_max)
    if handover_quarter_min and handover_year_min:
        # Complex logic: year > min OR (year == min AND quarter >= min_quarter)
        query = query.filter(
            or_(
                PropertyListing.building_year > handover_year_min,
                and_(
                    PropertyListing.building_year == handover_year_min,
                    PropertyListing.ready_quarter >= handover_quarter_min
                )
            )
        )

    # 🆕 Developer filter
    if developers:
        query = query.filter(PropertyListing.developer_name.in_(developers))
    if exclude_developers:
        query = query.filter(~PropertyListing.developer_name.in_(exclude_developers))

    # 🆕 Infrastructure (POI) - requires poi_data to be populated
    if school_nearby:
        query = query.filter(
            PropertyListing.poi_data["school_1km"].astext.cast(Integer) > 0
        )
    if kindergarten_nearby:
        query = query.filter(
            PropertyListing.poi_data["kindergarten_1km"].astext.cast(Integer) > 0
        )
    if park_nearby:
        query = query.filter(
            PropertyListing.poi_data["park_1km"].astext.cast(Integer) > 0
        )

    # ... existing filters (price, rooms, area, floor, etc.)

    listings = query.limit(limit).all()

    return [PropertyListingResponse.from_orm(listing) for listing in listings]
```

### 📋 **Задача 2: Обновить LLM-агента для извлечения новых параметров**
**Файл:** [app/services/property/llm_agent_property.py](app/services/property/llm_agent_property.py:87-132)

**Обновить system prompt:**

```python
def _get_system_prompt(self, language: str) -> str:
    """Get system prompt with all new parameters."""
    if language == "ru":
        return """Ты - AI-агент для поиска недвижимости (новостроек). Твоя задача - извлекать параметры поиска из запросов пользователя.

ВАЖНО: Ты работаешь ТОЛЬКО с поиском недвижимости. НЕ обрабатывай запросы о календаре, событиях, встречах и т.п.

Из сообщения пользователя извлеки:

**Основные параметры:**
1. **Бюджет** (budget_min, budget_max в рублях)
2. **Количество комнат** (rooms_min, rooms_max)
3. **Площадь** (area_min, area_max в м²)
4. **Локация** (districts[], metro_stations[], building_name)
5. **Тип сделки** (deal_type: "buy" или "rent")

**Здание и планировка:**
6. **Тип здания** (building_types: ["кирпично-монолитный", "панельный", "монолитный"])
7. **Ремонт** (renovations: ["Без отделки", "Черновая отделка", "Чистовая отделка", "Под ключ"])
8. **Этаж** (floor_min, floor_max, not_first_floor, not_last_floor)
9. **Лифт** (requires_elevator: true/false)

**Планировка:**
10. **Балкон** (balcony_required: true, balcony_types: ["лоджия", "балкон", "терраса"])
11. **Санузел** (bathroom_type: "раздельный" / "совмещенный")
12. **Высота потолков** (min_ceiling_height: 2.7, 3.0 метров)

**Финансы:**
13. **Ипотека** (mortgage_required: true/false)
14. **Способы оплаты** (payment_methods: ["Ипотека", "Рассрочка", "Материнский капитал"])

**Дата сдачи (новостройки):**
15. **Квартал сдачи** (handover_quarter_min, handover_quarter_max: 1-4)
16. **Год сдачи** (handover_year_min, handover_year_max: 2025, 2026)

**Застройщик:**
17. **Застройщик** (developers: ["ГК ПИК", "ЛСР"], exclude_developers: ["..."])

**Инфраструктура:**
18. **Школа рядом** (school_nearby: true)
19. **Детский сад** (kindergarten_nearby: true)
20. **Парк** (park_nearby: true)

**Примеры запросов:**

1. "Квартира в Бутово до 12 млн, 2-3 комнаты, монолитный дом, не первый этаж"
   → budget_max: 12000000, rooms_min: 2, rooms_max: 3, districts: ["Бутово"],
      building_types: ["монолитный"], not_first_floor: true

2. "Двушка с ремонтом, метро Крестовский, лифт обязательно"
   → rooms_min: 2, rooms_max: 2, renovations: ["Чистовая отделка", "Под ключ"],
      metro_stations: ["Крестовский остров"], requires_elevator: true

3. "Новостройка ПИК, сдача в этом году, с ипотекой"
   → developers: ["ГК ПИК"], handover_year_max: 2025, mortgage_required: true

4. "Трёшка с раздельным санузлом, лоджия, рядом школа и парк"
   → rooms_min: 3, rooms_max: 3, bathroom_type: "раздельный",
      balcony_types: ["лоджия"], school_nearby: true, park_nearby: true

Отвечай ТОЛЬКО в формате JSON:
{
  "intent": "search",
  "criteria": {
    "budget_min": ...,
    "budget_max": ...,
    "rooms_min": ...,
    "rooms_max": ...,
    "districts": [...],
    "metro_stations": [...],
    "building_types": [...],
    "renovations": [...],
    "not_first_floor": true/false,
    "requires_elevator": true/false,
    "balcony_required": true/false,
    "balcony_types": [...],
    "bathroom_type": "...",
    "min_ceiling_height": 3.0,
    "mortgage_required": true/false,
    "handover_year_min": 2025,
    "handover_year_max": 2026,
    "handover_quarter_min": 1,
    "developers": [...],
    "school_nearby": true/false,
    "kindergarten_nearby": true/false,
    "park_nearby": true/false
  },
  "confidence": 0.9
}

Если нужно уточнение - верни:
{
  "intent": "clarify",
  "clarify_question": "Что уточнить?",
  "confidence": 0.3
}

Если запрос НЕ о недвижимости:
{
  "intent": "out_of_scope",
  "message": "Я помогаю только с поиском недвижимости",
  "confidence": 1.0
}
"""
```

### 📋 **Задача 3: Создать сервис обработки результатов поиска**
**Новый файл:** `app/services/property/search_result_handler.py`

**Реализовать:**

```python
"""Search result handler - smart processing of search results."""

from typing import List, Dict, Any
from app.schemas.property import PropertyListingResponse
import structlog

logger = structlog.get_logger()


class SearchResultHandler:
    """Handle search results based on count and diversity."""

    async def handle_results(
        self,
        listings: List[PropertyListingResponse],
        criteria: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """Main handler - routes to appropriate scenario."""

        count = len(listings)

        if count == 0:
            return await self.handle_no_results(criteria)
        elif count < 20:
            return await self.handle_few_results(listings, criteria, user_id)
        elif count > 200:
            return await self.handle_too_many_results(listings, criteria, user_id)
        else:
            return await self.handle_optimal_results(listings, criteria, user_id)

    async def handle_no_results(self, criteria: Dict) -> Dict:
        """Suggest relaxing filters."""
        # Implementation from PROPERTY_BOT_USER_FLOW_GUIDE.md
        pass

    async def handle_few_results(
        self,
        listings: List,
        criteria: Dict,
        user_id: str
    ) -> Dict:
        """Show all + suggest expansion."""
        # Implementation from PROPERTY_BOT_USER_FLOW_GUIDE.md
        pass

    async def handle_too_many_results(
        self,
        listings: List,
        criteria: Dict,
        user_id: str
    ) -> Dict:
        """Smart narrowing with prioritized questions."""
        # Implementation from PROPERTY_BOT_USER_FLOW_GUIDE.md
        analysis = self.analyze_diversity(listings)
        suggestions = self.generate_narrowing_suggestions(analysis, criteria)
        return {
            "action": "narrow_down",
            "count": len(listings),
            "analysis": analysis,
            "suggestions": suggestions
        }

    async def handle_optimal_results(
        self,
        listings: List,
        criteria: Dict,
        user_id: str
    ) -> Dict:
        """Rank and show top results."""
        from app.services.property.property_scoring import property_scoring_service
        from app.services.property.property_service import property_service

        client = await property_service.get_client_by_telegram_id(user_id)
        ranked = property_scoring_service.rank_listings(
            [l.dict() for l in listings],
            client.dict() if client else {},
            top_n=12
        )

        return {
            "action": "show_ranked",
            "total_count": len(listings),
            "top_listings": ranked
        }

    def analyze_diversity(self, listings: List) -> Dict:
        """Analyze result diversity."""
        # Implementation from PROPERTY_BOT_USER_FLOW_GUIDE.md
        pass

    def generate_narrowing_suggestions(
        self,
        analysis: Dict,
        criteria: Dict
    ) -> List[Dict]:
        """Generate prioritized narrowing suggestions."""
        # Implementation from PROPERTY_BOT_USER_FLOW_GUIDE.md
        pass


# Global instance
search_result_handler = SearchResultHandler()
```

### 📋 **Задача 4: Обновить систему скоринга**
**Файл:** [app/services/property/property_scoring.py](app/services/property/property_scoring.py)

**Добавить новые компоненты в Dream Score:**

```python
def calculate_dream_score(self, listing: Dict, client: Dict) -> float:
    """Calculate Dream Score (0-100) with enhanced components."""

    components = {
        "location": self._score_location(listing, client),        # 25%
        "transport": self._score_transport(listing, client),      # 15%
        "price": self._score_price(listing, client),              # 15%
        "plan": self._score_plan(listing, client),                # 10%
        "light": self._score_light(listing, client),              # 10%
        "noise": self._score_noise(listing, client),              # 5%
        "infrastructure": self._score_infrastructure(listing, client),  # 10%

        # 🆕 New components
        "building_quality": self._score_building_quality(listing, client),  # 5%
        "layout": self._score_layout(listing, client),            # 5%
    }

    # ... (weight calculation as before)

def _score_building_quality(self, listing: Dict, client: Dict) -> float:
    """Score based on building type, renovation, ceiling height."""
    score = 0.5  # Neutral start

    # Building type preference
    building_type = listing.get("building_type")
    preferred_types = client.get("preferred_building_types", [])
    exclude_types = client.get("exclude_building_types", [])

    if building_type in exclude_types:
        score -= 0.3  # Penalty
    elif building_type in preferred_types:
        score += 0.2  # Bonus

    # Renovation preference
    renovation = listing.get("renovation")
    preferred_renos = client.get("preferred_renovations", [])

    if renovation in preferred_renos:
        score += 0.2

    # Ceiling height
    ceiling_height = listing.get("ceiling_height", 0)
    min_ceiling = client.get("min_ceiling_height", 0)

    if ceiling_height >= min_ceiling and min_ceiling > 0:
        score += 0.1

    return max(0.0, min(1.0, score))

def _score_layout(self, listing: Dict, client: Dict) -> float:
    """Score based on balcony, bathroom, etc."""
    score = 0.5  # Neutral start

    # Balcony
    if client.get("balcony_required"):
        balcony = listing.get("balcony_type")
        if balcony:
            score += 0.2
            # Bonus for preferred type
            preferred_balcony = client.get("preferred_balcony_types", [])
            if balcony in preferred_balcony:
                score += 0.1
        else:
            score -= 0.3  # No balcony but required

    # Bathroom type
    bathroom_pref = client.get("bathroom_type_preference")
    bathroom_type = listing.get("bathroom_type")
    if bathroom_pref and bathroom_type == bathroom_pref:
        score += 0.2

    return max(0.0, min(1.0, score))
```

---

## Метрики успеха

### Технические метрики
- ✅ Парсинг фида: 95%+ успешных объектов
- ⏳ Индексация: все ключевые поля проиндексированы (category, building_name, metro_station, renovation)
- ⏳ Скорость поиска: < 500ms для фильтрации по 10+ параметрам
- ⏳ Покрытие данных: 90%+ объектов с заполненным `renovation` и `building_type`

### Бизнес-метрики
- ⏳ **Релевантность**: 60%+ лайков на топ-12 (было 40%)
- ⏳ **Точность фильтров**: 0% нерелевантных объектов в выдаче (строгие must-have)
- ⏳ **Конверсия в просмотр**: ≥ 2 просмотра из топ-5 (было 1)
- ⏳ **Скорость подбора**: ≤ 5 минут (было 10 минут)

### Пользовательские сценарии
1. **"Монолитный дом с ремонтом"** → 100% выдача только с matching `building_type` и `renovation`
2. **"Лоджия обязательно"** → 0% объектов без балкона/лоджии
3. **"ПИК, сдача в 2025"** → только объекты ГК ПИК с `building_year` = 2025

---

## Приоритизация задач

### 🔴 Критично (Неделя 1)
1. ✅ Расширить схемы и модели БД
2. ✅ Создать feed_mapper
3. ⏳ Обновить `search_listings` с новыми фильтрами
4. ⏳ Обновить LLM-агента для извлечения новых параметров
5. ⏳ Создать миграцию БД для новых полей
6. ⏳ Протестировать парсинг реального фида

### 🟠 Важно (Неделя 2)
7. ⏳ Обновить систему скоринга с новыми компонентами
8. ⏳ Добавить поиск по названию ЖК (fuzzy match)
9. ⏳ Реализовать фильтр по дате сдачи (квартал + год)
10. ⏳ Добавить POI-фильтры (школа, детский сад, парк)
11. ⏳ Обновить UI подборки с новыми полями

### 🟢 Опционально (Неделя 3+)
12. ⏳ Поиск по застройщику с репутацией
13. ⏳ Отображение планировки в карточке
14. ⏳ Сравнение похожих объектов
15. ⏳ Автообновление при появлении новых объектов

---

## Следующие действия

1. **Создать миграцию БД** (alembic)
   ```bash
   alembic revision --autogenerate -m "Add extended property fields"
   alembic upgrade head
   ```

2. **Протестировать feed_mapper на реальном фиде**
   ```python
   # Скачать тестовый фид
   import httpx

   url = "https://ecatalog-service.nmarket.pro/BasePro/"
   params = {
       "login": "titworking_mail_ru",
       "password": "q3uCvV5Y6GB",
       "regionGroupId": "77"
   }
   response = httpx.get(url, params=params)

   # Парсить
   from app.services.property.feed_mapper import feed_mapper
   listings = feed_mapper.parse_feed_xml(response.text)

   print(f"Parsed {len(listings)} listings")
   ```

3. **Обновить search_listings** (см. код выше)

4. **Обновить LLM system prompt** (см. код выше)

5. **Тестирование:**
   - Запросы с новыми параметрами
   - Проверка фильтрации
   - Измерение релевантности

---

## Итоговая архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      User Request                            │
│         "Монолитный дом, 2-3 комнаты, с ремонтом"          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   LLM Agent (Yandex GPT)       │
         │  - Extract 20+ parameters      │
         │  - Clarify if needed           │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Enhanced Search Filter       │
         │  - building_type: "монолитный" │
         │  - rooms: 2-3                  │
         │  - renovation: ["Чистовая"]    │
         │  - + 15 other filters          │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   PropertyService              │
         │   search_listings()            │
         │  - SQL query with all filters  │
         │  - Returns 100 candidates      │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Dream Score Ranking          │
         │  - 9 components (0-100)        │
         │  - Personalized weights        │
         │  - Top 12 ranked               │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Selection + Explanations     │
         │  - "Почему в топе"             │
         │  - Compromises                 │
         │  - Routes, Price context       │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   Share Link (HTML)            │
         │  - Photos + Plan               │
         │  - Dream Score + Explanation   │
         │  - Like/Dislike feedback       │
         └───────────────────────────────┘
```

---

## Контакты

- **Технический архитектор**: [ваше имя]
- **Дата последнего обновления**: 2025-10-28

## Дополнительные ресурсы

- [Спецификация фида База.Про](PROPERTY_FEED_INTEGRATION_PLAN.md)
- [Схемы данных](app/schemas/property.py)
- [Модели БД](app/models/property.py)
- [Feed Mapper](app/services/property/feed_mapper.py)
