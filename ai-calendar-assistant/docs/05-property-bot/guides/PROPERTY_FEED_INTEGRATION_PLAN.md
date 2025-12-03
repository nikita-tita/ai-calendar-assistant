# План интеграции фидов недвижимости для Property Bot

## Контекст

Property Bot - отдельный микросервис внутри календарного бота, полностью изолированный от календарной логики. Реализована базовая архитектура (модели, API, скоринг), но отсутствует интеграция с реальными фидами недвижимости.

## Источник данных

**Feed Provider:** nmarket.pro
**URL:** `https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=77`
**Регион:** Москва (77)
**Формат:** Предположительно XML/JSON с каталогом новостроек

## Текущее состояние проекта

### Что уже реализовано ✅

1. **Модели данных** ([app/models/property.py](app/models/property.py:1-252))
   - `PropertyClient` - профиль клиента с требованиями и вкусами
   - `PropertyListing` - объявление с полями для обогащенных данных
   - `PropertySelection` - подборка с share-токеном
   - `SelectionItem` - элемент подборки с Dream Score и объяснениями
   - `SelectionFeedback` - фидбек клиента (лайк/дизлайк/комментарий)
   - `UserBotMode` - переключение между режимами

2. **Система скоринга** ([app/services/property/property_scoring.py](app/services/property/property_scoring.py:1-432))
   - Dream Score (0-100) с 9 компонентами
   - Ранжирование листингов
   - Генерация объяснений "почему в топе"

3. **API endpoints** ([app/routers/property.py](app/routers/property.py:1-287))
   - CRUD для клиентов, листингов, подборок
   - Скоринг и ранжирование
   - Публичные share-ссылки

### Что отсутствует ❌

1. **Интеграция с фидами** - нет парсинга внешних источников
2. **Обогащение данных** - нет геокодирования, POI, маршрутов, ценового контекста
3. **AI-инструменты** - нет интеграции с Yandex AI Studio для function calling
4. **Дедупликация** - нет детекции дубликатов
5. **Клиентский интерфейс** - нет HTML-страницы для share-ссылок
6. **Онбординг вкусов** - нет парных сравнений и галереи

---

## Детальный план доработок

### 🔴 ФАЗА 1: Интеграция с фидами (Неделя 1-2)

#### 1.1. Feed Ingestion Service

**Файл:** `app/services/property/feed_ingestion.py`

**Задачи:**
- [ ] Создать сервис для загрузки фида от nmarket.pro
- [ ] Парсинг XML/JSON структуры фида
- [ ] Маппинг полей фида на модель `PropertyListing`
- [ ] Batch-обработка (по 100-500 объектов)
- [ ] Инкрементальное обновление (только новые/измененные)
- [ ] Логирование ошибок парсинга

**Поля фида → модель:**
```python
# Основные поля
external_id = feed_item.id  # ID из фида
title = feed_item.name
description = feed_item.description
price = feed_item.price
deal_type = DealType.BUY  # Новостройки = покупка
address_raw = feed_item.address
building_year = feed_item.completion_year
floors_total = feed_item.floors
area_total = feed_item.area
rooms = feed_item.rooms
photos = feed_item.images  # List[str]

# Застройщик
developer_id = feed_item.developer_id
source = "nmarket.pro"
```

**Cron task:**
- Запуск каждые 6 часов
- Хранение last_sync_timestamp

#### 1.2. Data Validation & Deduplication

**Файл:** `app/services/property/data_validator.py`

**Задачи:**
- [ ] Валидация обязательных полей (цена, адрес, площадь)
- [ ] Проверка диапазонов (цена > 0, комнаты <= 10, и т.д.)
- [ ] Детекция дубликатов по:
  - `external_id` (из фида)
  - Адрес + площадь + комнаты (фаззи-матчинг)
  - Perceptual hash фотографий (если совпадают 3+ из 5)
- [ ] Маркировка невалидных записей (`is_active = False`)
- [ ] Отчет о дубликатах и ошибках

**Алгоритм дедупликации:**
```python
def find_duplicates(listing: PropertyListing) -> List[str]:
    # 1. Exact match по external_id
    exact = db.query(PropertyListing).filter(
        PropertyListing.external_id == listing.external_id,
        PropertyListing.id != listing.id
    ).first()

    # 2. Fuzzy match по адресу + площади
    fuzzy = db.query(PropertyListing).filter(
        func.similarity(PropertyListing.address_raw, listing.address_raw) > 0.8,
        PropertyListing.area_total.between(listing.area_total * 0.95, listing.area_total * 1.05)
    ).all()

    # 3. Image hash match
    if listing.photos:
        similar_images = find_similar_images(listing.photos)

    return [d.id for d in exact + fuzzy + similar_images]
```

---

### 🟠 ФАЗА 2: Обогащение данных через Yandex AI Studio (Неделя 2-3)

#### 2.1. Yandex AI Integration Service

**Файл:** `app/services/property/yandex_ai_service.py`

**Конфигурация:**
```python
# app/config.py (уже есть)
yandex_gpt_api_key: str  # Используем существующую авторизацию
yandex_gpt_folder_id: str
```

**API endpoints Yandex AI Studio:**
- YandexGPT (function calling) - для извлечения параметров из текста
- Vision API - анализ фотографий
- Geocoder API - геокодирование адресов
- Maps API - матрица расстояний, POI-поиск

#### 2.2. Geocoding & Location Enrichment

**Функция:** `enrich_location(listing: PropertyListing)`

**Задачи:**
- [ ] Геокодирование `address_raw` → `(lat, lon)`
- [ ] Получение точного адреса (нормализация)
- [ ] Определение района (district)
- [ ] Поиск ближайшего метро + время пешком
- [ ] Кэширование результатов (по адресу)

**Function calling через YandexGPT:**
```python
tools = [
    {
        "name": "geocode",
        "description": "Геокодирование адреса в координаты",
        "parameters": {
            "query": "string"
        }
    }
]

response = yandex_ai.function_call(
    prompt=f"Геокодируй адрес: {listing.address_raw}",
    tools=tools
)

listing.lat = response.lat
listing.lon = response.lon
listing.district = response.district
listing.metro_station = response.nearest_metro.name
listing.metro_distance_minutes = response.nearest_metro.walk_time
```

#### 2.3. Route Matrix Calculation

**Функция:** `calculate_routes(listing: PropertyListing, client: PropertyClient)`

**Задачи:**
- [ ] Матрица времени от объекта до anchor_points клиента
- [ ] Режимы: auto, public_transport, walk
- [ ] Учет утренних пробок (8:00-10:00)
- [ ] Кэширование по (origin_coords, destination_coords, mode)

**Function calling:**
```python
tools = [
    {
        "name": "route_matrix",
        "description": "Расчет времени в пути между точками",
        "parameters": {
            "origins": "List[(lat, lon)]",
            "destinations": "List[(lat, lon)]",
            "mode": "auto|pt|walk",
            "departure_time": "timestamp"  # Утро понедельника
        }
    }
]

# Пример anchor_points клиента
anchor_points = [
    {"type": "work", "lat": 55.7558, "lon": 37.6173, "mode": "auto"},
    {"type": "kindergarten", "lat": 55.7500, "lon": 37.6000, "mode": "pt"}
]

routes = yandex_ai.function_call(
    prompt="Рассчитай время в пути от объекта до важных точек клиента",
    tools=tools,
    origins=[(listing.lat, listing.lon)],
    destinations=[(p["lat"], p["lon"]) for p in anchor_points]
)

# Сохраняем в routes_cache
listing.routes_cache = {
    client.id: {
        "to_work": {"auto": 35, "pt": 42},
        "to_kindergarten": {"auto": 20, "pt": 28}
    }
}
```

#### 2.4. POI (Points of Interest) Enrichment

**Функция:** `enrich_poi(listing: PropertyListing)`

**Задачи:**
- [ ] Поиск POI в радиусах 500м и 1км
- [ ] Категории: школы, детсады, парки, магазины, спортзалы, аптеки
- [ ] Подсчет количества в каждой категории
- [ ] Кэширование по координатам (тайлы 250×250м)

**Function calling:**
```python
tools = [
    {
        "name": "search_poi",
        "description": "Поиск объектов инфраструктуры рядом с точкой",
        "parameters": {
            "lat": "float",
            "lon": "float",
            "radius_meters": "int",
            "categories": "List[string]"
        }
    }
]

poi_data = yandex_ai.function_call(
    prompt="Найди объекты инфраструктуры рядом с объектом недвижимости",
    tools=tools,
    lat=listing.lat,
    lon=listing.lon,
    radius_meters=[500, 1000],
    categories=["school", "kindergarten", "park", "grocery", "pharmacy", "sport"]
)

listing.poi_data = {
    "school_1km": 3,
    "kindergarten_1km": 2,
    "park_1km": 1,
    "grocery_500m": 5,
    "pharmacy_500m": 2,
    "sport_1km": 1
}
```

#### 2.5. Vision Analysis (Photo Embeddings)

**Функция:** `analyze_photos(listing: PropertyListing)`

**Задачи:**
- [ ] Анализ фотографий (минимум 3 для достоверности)
- [ ] Определение светлости (light_score 0-1)
- [ ] Теги вида (park, quiet, street, courtyard, panoramic)
- [ ] Оценка состояния (condition_score 0-1)
- [ ] Детекция "двор/улица"

**Function calling через Yandex Vision:**
```python
tools = [
    {
        "name": "analyze_images",
        "description": "Анализ качества и особенностей фотографий недвижимости",
        "parameters": {
            "image_urls": "List[string]",
            "aspects": "List[string]"  # ["light", "view", "condition", "layout"]
        }
    }
]

if len(listing.photos) >= 3:
    vision_data = yandex_ai.function_call(
        prompt="Проанализируй фотографии квартиры и оцени освещенность, вид, состояние",
        tools=tools,
        image_urls=listing.photos[:5],  # Первые 5 фото
        aspects=["light", "view", "condition", "street_or_yard"]
    )

    listing.vision_data = {
        "light_score": 0.85,  # Светлая квартира
        "view_tags": ["park", "quiet", "courtyard"],
        "condition_score": 0.7,
        "confidence": 0.9
    }
else:
    listing.vision_data = {"confidence": 0.0}  # Недостаточно фото
```

#### 2.6. Price Context (Market Analysis)

**Функция:** `enrich_price_context(listing: PropertyListing)`

**Задачи:**
- [ ] Получение медианы цен для района/ЖК
- [ ] Расчет перцентиля текущей цены (p25, p50, p75)
- [ ] Определение позиции: ниже/на уровне/выше рынка
- [ ] Аргументы для торга

**Function calling:**
```python
tools = [
    {
        "name": "market_stats",
        "description": "Статистика цен по району и типу жилья",
        "parameters": {
            "district": "string",
            "rooms": "int",
            "area_range": "(float, float)"
        }
    }
]

market_data = yandex_ai.function_call(
    prompt="Получи статистику цен на аналогичные квартиры в этом районе",
    tools=tools,
    district=listing.district,
    rooms=listing.rooms,
    area_range=(listing.area_total * 0.9, listing.area_total * 1.1)
)

# Рассчитываем перцентиль
from scipy import stats
pct = stats.percentileofscore([market_data.prices], listing.price)

listing.market_data = {
    "median": 9000000,
    "p25": 8500000,
    "p75": 9500000,
    "pct": 55  # На уровне рынка
}
```

#### 2.7. Builder/Developer Risk Score

**Функция:** `enrich_builder_data(listing: PropertyListing)`

**Задачи:**
- [ ] Поиск застройщика по `developer_id` или названию ЖК
- [ ] Web-поиск новостей о застройщике (задержки, банкротства)
- [ ] Простой risk_score (0-1, где 0 = надежный)
- [ ] Флаг "проблемный застройщик"

**Function calling:**
```python
tools = [
    {
        "name": "builder_lookup",
        "description": "Поиск информации о застройщике и репутации",
        "parameters": {
            "developer_name": "string",
            "developer_id": "string"
        }
    }
]

builder_data = yandex_ai.function_call(
    prompt="Найди информацию о репутации застройщика",
    tools=tools,
    developer_id=listing.developer_id
)

listing.builder_data = {
    "name": "ГК ПИК",
    "risk_score": 0.15,  # Низкий риск
    "completion_rate": 0.98,
    "delays_count": 1,
    "facts": ["Крупный застройщик", "Сдано 150+ домов"]
}
```

---

### 🟡 ФАЗА 3: Pipeline обогащения и скоринга (Неделя 3)

#### 3.1. Enrichment Pipeline

**Файл:** `app/services/property/enrichment_pipeline.py`

**Задачи:**
- [ ] Orchestration всех этапов обогащения
- [ ] Параллельная обработка (геокодинг + POI + vision)
- [ ] Retry логика при ошибках API
- [ ] Progress tracking (X из Y объектов обработано)

**Пайплайн:**
```python
async def enrich_listing_full(listing: PropertyListing) -> PropertyListing:
    """Полное обогащение листинга."""

    # 1. Геокодирование (критично для дальнейшего)
    if not listing.lat or not listing.lon:
        await enrich_location(listing)

    # 2. Параллельные задачи (не зависят друг от друга)
    tasks = [
        enrich_poi(listing),
        analyze_photos(listing),
        enrich_price_context(listing),
        enrich_builder_data(listing)
    ]
    await asyncio.gather(*tasks)

    # 3. Маршруты (требуют client context, делаем при подборе)
    # calculate_routes вызывается в rank_for_client()

    return listing

async def enrich_batch(listings: List[PropertyListing], batch_size: int = 50):
    """Batch-обработка с rate limiting."""
    for i in range(0, len(listings), batch_size):
        batch = listings[i:i+batch_size]
        await asyncio.gather(*[enrich_listing_full(l) for l in batch])
        await asyncio.sleep(1)  # Rate limit для Yandex API
```

#### 3.2. Enhanced Scoring Service

**Обновить:** `app/services/property/property_scoring.py`

**Задачи:**
- [ ] Интеграция с обогащенными данными (routes_cache, poi_data, vision_data)
- [ ] Улучшить `_score_location()` - учесть реальные маршруты
- [ ] Улучшить `_score_light()` - использовать vision_data
- [ ] Улучшить `_score_infrastructure()` - использовать poi_data
- [ ] Диверсификация топ-N (разные районы/планировки)

**Диверсификация:**
```python
def diversify_top_listings(ranked: List[Dict], top_n: int = 12) -> List[Dict]:
    """Обеспечить разнообразие в топе."""

    result = []
    seen_districts = set()
    seen_room_counts = set()

    # Первый проход: берем топовые, следя за разнообразием
    for listing in ranked:
        district = listing.get("district")
        rooms = listing.get("rooms")

        # Ограничение: не больше 3 из одного района
        if seen_districts.count(district) >= 3:
            continue

        # Ограничение: минимум 2 разных типа по комнатам
        if len(result) >= 6 and len(seen_room_counts) < 2:
            if rooms not in seen_room_counts:
                pass  # Добавим для разнообразия
            else:
                continue

        result.append(listing)
        seen_districts.add(district)
        seen_room_counts.add(rooms)

        if len(result) >= top_n:
            break

    return result
```

---

### 🟢 ФАЗА 4: Клиентский интерфейс (Неделя 4)

#### 4.1. Onboarding Flow (Taste Capture)

**Файл:** `app/services/property/onboarding_service.py`

**Задачи:**
- [ ] Парные сравнения (A vs B) для быстрого профилирования
- [ ] Мини-галерея (10 фото, лайк/дизлайк)
- [ ] Извлечение весов вкусов из фидбека
- [ ] Интеграция в Telegram-флоу

**Telegram-флоу:**
```
1. "🔍 Начать поиск"
2. Must-have вопросы (бюджет, комнаты, район)
3. "Давайте узнаем ваши предпочтения! (2 мин)"
4. Показать 5 пар фото:
   - Светлая vs Темная → weight["light"]
   - Двор vs Улица → weight["noise"]
   - Высокий этаж vs Низкий → weight["view"]
5. Показать 10 фото, просьба лайкнуть любимые
6. "Ищем для вас лучшие варианты..."
```

**Алгоритм извлечения весов:**
```python
def extract_taste_weights(feedback: List[Dict]) -> Dict[str, float]:
    """Извлечь веса вкусов из парных сравнений."""

    weights = {
        "light": 0.10,
        "view": 0.05,
        "noise": 0.05,
        # ... defaults
    }

    for fb in feedback:
        if fb["comparison"] == "light_vs_dark" and fb["choice"] == "light":
            weights["light"] += 0.05
        if fb["comparison"] == "yard_vs_street" and fb["choice"] == "yard":
            weights["noise"] += 0.05
        # ...

    # Нормализация (сумма = 1.0)
    total = sum(weights.values())
    return {k: v/total for k, v in weights.items()}
```

#### 4.2. Share Page (Public Selection View)

**Файл:** `app/routers/property_public.py`

**Задачи:**
- [ ] HTML-страница для share-токена
- [ ] Карточки объектов с фото, объяснениями, ценой
- [ ] Интерактивные элементы (лайк/дизлайк/комментарий)
- [ ] Адаптивный дизайн (mobile-first)
- [ ] Автообновление при новых объектах

**Шаблон страницы:** `app/templates/property_selection.html`

```html
<!DOCTYPE html>
<html>
<head>
    <title>Ваша персональная подборка</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Mobile-first CSS */
        .listing-card {
            border: 1px solid #ddd;
            border-radius: 12px;
            margin: 16px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .dream-score {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }
        .explanation {
            margin-top: 12px;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Подобрано для вас: {{ selection.items|length }} вариантов</h1>

        {% for item in selection.items %}
        <div class="listing-card">
            <!-- Фото -->
            <div class="photos">
                <img src="{{ item.listing.photos[0] }}" alt="Фото квартиры">
            </div>

            <!-- Dream Score -->
            <div class="dream-score">⭐ {{ item.dream_score }}/100</div>

            <!-- Заголовок -->
            <h2>{{ item.listing.title }}</h2>
            <p>{{ item.listing.price|format_price }} ₽ | {{ item.listing.rooms }} комн. | {{ item.listing.area_total }} м²</p>

            <!-- Объяснение -->
            <div class="explanation">
                <h3>Почему в топе:</h3>
                <ul>
                    {% for reason in item.explanation.why_top %}
                    <li>{{ reason }}</li>
                    {% endfor %}
                </ul>

                {% if item.explanation.compromise %}
                <h3>Компромиссы:</h3>
                <ul>
                    {% for c in item.explanation.compromise %}
                    <li>{{ c }}</li>
                    {% endfor %}
                </ul>
                {% endif %}

                <p><strong>Цена:</strong> {{ item.explanation.price_context }}</p>

                {% if item.explanation.routes %}
                <h3>Маршруты:</h3>
                <ul>
                    {% for route, times in item.explanation.routes.items() %}
                    <li>{{ route }}: 🚗 {{ times.auto }} мин, 🚇 {{ times.pt }} мин</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>

            <!-- Заметка агента -->
            {% if item.agent_note %}
            <div class="agent-note">
                <strong>Комментарий агента:</strong> {{ item.agent_note }}
            </div>
            {% endif %}

            <!-- Действия -->
            <div class="actions">
                <button onclick="feedback('{{ item.listing_id }}', 'like')">👍 Нравится</button>
                <button onclick="feedback('{{ item.listing_id }}', 'dislike')">👎 Не нравится</button>
                <button onclick="showCommentBox('{{ item.listing_id }}')">💬 Комментировать</button>
            </div>
        </div>
        {% endfor %}
    </div>

    <script>
        async function feedback(listingId, type) {
            await fetch('/api/property/feedback', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    selection_id: '{{ selection.id }}',
                    listing_id: listingId,
                    feedback_type: type,
                    client_telegram_id: '{{ client_telegram_id }}'
                })
            });
            alert('Спасибо за отзыв!');
        }
    </script>
</body>
</html>
```

**Endpoint:**
```python
@router.get("/selection/{share_token}", response_class=HTMLResponse)
async def view_selection(share_token: str, request: Request):
    """Public selection view."""
    selection = await property_service.get_selection_by_token(share_token)
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")

    return templates.TemplateResponse("property_selection.html", {
        "request": request,
        "selection": selection
    })
```

#### 4.3. PDF Export

**Файл:** `app/services/property/pdf_export.py`

**Задачи:**
- [ ] Генерация PDF с топ-12 объектами
- [ ] Включить фото, объяснения, контакты
- [ ] Чек-лист для просмотра каждого объекта
- [ ] Кнопка "Скачать PDF" на share-странице

**Библиотека:** `reportlab` или `weasyprint`

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image

def generate_pdf(selection: Dict) -> bytes:
    """Generate PDF report for selection."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []

    # Заголовок
    story.append(Paragraph(f"Подборка недвижимости", style_title))
    story.append(Paragraph(f"Дата: {selection['created_at']}", style_normal))

    # Объекты
    for item in selection['items'][:12]:
        listing = item['listing']

        # Фото
        if listing['photos']:
            img = Image(listing['photos'][0], width=400, height=300)
            story.append(img)

        # Заголовок
        story.append(Paragraph(listing['title'], style_heading))
        story.append(Paragraph(f"{listing['price']:,} ₽", style_price))

        # Объяснение
        story.append(Paragraph("Почему рекомендуем:", style_bold))
        for reason in item['explanation']['why_top']:
            story.append(Paragraph(f"• {reason}", style_normal))

        # Чек-лист для просмотра
        story.append(Paragraph("Что проверить на просмотре:", style_bold))
        for check in item['explanation']['check_on_viewing']:
            story.append(Paragraph(f"☐ {check}", style_normal))

        story.append(PageBreak())

    doc.build(story)
    return buffer.getvalue()
```

---

### 🔵 ФАЗА 5: Online Learning & Персонализация (Неделя 4+)

#### 5.1. Feedback Learning

**Файл:** `app/services/property/learning_service.py`

**Задачи:**
- [ ] Обновление taste_weights клиента на основе лайков/дизлайков
- [ ] Reinforcement learning подход
- [ ] Пересчет подборки при достаточном фидбеке (>5 действий)

**Алгоритм:**
```python
def update_weights_from_feedback(
    client: PropertyClient,
    feedback_items: List[SelectionFeedback]
) -> Dict[str, float]:
    """Обновить веса на основе фидбека."""

    current_weights = client.taste_weights or {}

    for fb in feedback_items:
        listing = get_listing(fb.listing_id)

        if fb.feedback_type == "like":
            # Усилить веса по компонентам, где этот листинг был силен
            if listing.vision_data.get("light_score", 0) > 0.7:
                current_weights["light"] += 0.02
            if listing.metro_distance_minutes <= 10:
                current_weights["transport"] += 0.02
            # ...

        elif fb.feedback_type == "dislike":
            # Ослабить веса по компонентам, где был слабым
            if listing.floor == 1:
                # Клиент дизлайкнул первый этаж - усилить "plan" (нужен высокий этаж)
                current_weights["plan"] += 0.01
            # ...

    # Нормализация
    total = sum(current_weights.values())
    return {k: v/total for k, v in current_weights.items()}
```

---

### 🟣 ФАЗА 6: Дополнительные фичи (Опционально)

#### 6.1. Автоматические уведомления

**Задачи:**
- [ ] Мониторинг новых листингов из фида
- [ ] Матчинг с профилями активных клиентов
- [ ] Telegram-уведомление "Новый объект для вас!"

#### 6.2. История просмотров

**Задачи:**
- [ ] Трекинг просмотров (клиент открыл карточку)
- [ ] Статистика: "Просмотрено 3 раза, лайков 2"

#### 6.3. Сравнение объектов

**Задачи:**
- [ ] UI для сравнения 2-3 объектов side-by-side
- [ ] Таблица с критериями

---

## Технические детали

### Конфигурация (app/config.py)

Добавить в существующий файл:

```python
# Property Feed
nmarket_feed_url: str = "https://ecatalog-service.nmarket.pro/BasePro/"
nmarket_login: str = "titworking_mail_ru"
nmarket_password: str = "q3uCvV5Y6GB"
nmarket_region_group_id: str = "77"  # Москва

# Yandex AI Studio (уже есть yandex_gpt_api_key, yandex_gpt_folder_id)
yandex_maps_api_key: Optional[str] = None  # Для Maps/Geocoder
yandex_vision_api_key: Optional[str] = None  # Если отдельный
```

### Структура файлов

```
app/
├── services/
│   └── property/
│       ├── __init__.py
│       ├── property_service.py         # ✅ Уже есть
│       ├── property_scoring.py         # ✅ Уже есть
│       ├── property_handler.py         # ✅ Уже есть
│       ├── feed_ingestion.py           # 🆕 Парсинг фидов
│       ├── data_validator.py           # 🆕 Валидация и дедупликация
│       ├── yandex_ai_service.py        # 🆕 Интеграция с Yandex AI
│       ├── enrichment_pipeline.py      # 🆕 Пайплайн обогащения
│       ├── onboarding_service.py       # 🆕 Онбординг вкусов
│       ├── learning_service.py         # 🆕 Обучение по фидбеку
│       └── pdf_export.py               # 🆕 Экспорт в PDF
├── routers/
│   ├── property.py                     # ✅ Уже есть
│   └── property_public.py              # 🆕 Публичные share-страницы
├── templates/
│   └── property_selection.html         # 🆕 Шаблон страницы
└── tasks/
    └── property_cron.py                # 🆕 Cron-задачи (обновление фидов)
```

### Зависимости (requirements.txt)

Добавить:

```txt
# XML/HTML parsing
lxml>=4.9.0
beautifulsoup4>=4.12.0

# HTTP clients
httpx>=0.25.0  # async HTTP
aiohttp>=3.9.0

# Image processing
Pillow>=10.0.0
imagehash>=4.3.0  # Perceptual hashing для дедупликации

# PDF generation
reportlab>=4.0.0
# или weasyprint>=60.0

# Fuzzy matching
fuzzywuzzy>=0.18.0
python-Levenshtein>=0.21.0

# Async tasks
celery>=5.3.0  # Для фоновых задач (опционально)
redis>=5.0.0

# Jinja2 templates
jinja2>=3.1.0
```

---

## Приоритизация (MVP для 4 недель)

### Must-Have (Критично) 🔴

1. ✅ Feed Ingestion (парсинг nmarket.pro)
2. ✅ Геокодирование (адрес → координаты)
3. ✅ POI-поиск (инфраструктура)
4. ✅ Маршруты до anchor_points
5. ✅ Ценовой контекст (медиана)
6. ✅ Vision анализ (светлость, вид)
7. ✅ Обновленный скоринг (с реальными данными)
8. ✅ Share-страница (HTML с карточками)
9. ✅ Фидбек (лайк/дизлайк)

### Should-Have (Важно) 🟠

10. ✅ Дедупликация листингов
11. ✅ Онбординг вкусов (парные сравнения)
12. ✅ PDF-экспорт подборки
13. ✅ Обучение по фидбеку (обновление весов)

### Nice-to-Have (Опционально) 🟢

14. ⚪ Builder risk score (репутация застройщика)
15. ⚪ Автоуведомления о новых объектах
16. ⚪ История просмотров
17. ⚪ Сравнение объектов

---

## Метрики успеха

### Технические
- ✅ Обновление фида: каждые 6 часов, успешность >95%
- ✅ Обогащение: 90% объектов с полными данными (lat/lon/poi/vision)
- ✅ Скорость: TTFB первой подборки <8 сек
- ✅ Дедупликация: <5% дубликатов в базе

### Бизнес-метрики (из PRD)
- ✅ Релевантность: >40% лайков на топ-12 в первой итерации
- ✅ Конверсия: ≥1 просмотр из топ-5 в течение 72 часов
- ✅ Объяснимость: ≥90% карточек с полными объяснениями
- ✅ Скорость агента: время на подборку ≤10 мин (было ≥30 мин)

---

## Риски и митигации

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| Фид nmarket.pro недоступен | Средняя | Локальное кэширование последней версии, алерты |
| Yandex API rate limits | Высокая | Batch-обработка, кэширование, экспоненциальный backoff |
| Некорректные адреса | Высокая | Батч-геокод + ручная проверка, флаг "требует уточнения" |
| Дубликаты в фиде | Средняя | Агрессивная дедупликация (3 метода) |
| Перегрузка БД | Низкая | Индексы на lat/lon/district/external_id, партиционирование |

---

## Следующие шаги

1. **Получить доступ к фиду** - уточнить формат XML/JSON, тестовые данные
2. **Протестировать Yandex AI Studio** - проверить function calling с геокодером
3. **Запустить MVP Фазы 1** - парсинг и загрузка первых 100 объектов
4. **Итерировать по фидбеку** - показать первую подборку и собрать фидбек

---

## Контакты для вопросов

- Технический архитектор: [ваше имя]
- Product Owner: [ваше имя]
- Доступ к фиду: техподдержка nmarket.pro
