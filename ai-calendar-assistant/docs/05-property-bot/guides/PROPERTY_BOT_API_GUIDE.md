```python
# Property Bot API Reference & Usage Guide

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Core Services](#core-services)
3. [Complete Workflows](#complete-workflows)
4. [API Reference](#api-reference)
5. [Configuration](#configuration)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

---

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Apply database migrations
psql -U postgres -d calendar_bot -f migrations/001_add_extended_property_fields.sql

# Set environment variables
export YANDEX_GPT_API_KEY="your_key"
export YANDEX_GPT_FOLDER_ID="your_folder_id"
export DATABASE_URL="postgresql://user:pass@localhost/calendar_bot"
```

### Minimal Example

```python
from app.services.property.llm_agent_property import llm_agent_property
from app.services.property.property_service import property_service

# Extract search criteria
result = await llm_agent_property.extract_search_criteria(
    user_message="Хочу 2к до 10 млн в Бутово с ипотекой",
    user_id="12345",
    language="ru"
)

# Search listings
listings = await property_service.search_listings(
    **result["criteria"],
    limit=50
)

print(f"Found {len(listings)} listings")
```

---

## 🔧 Core Services

### 1. LLM Agent (Natural Language Understanding)

**Purpose:** Extract structured search criteria from user messages

```python
from app.services.property.llm_agent_property import llm_agent_property

# Extract parameters
result = await llm_agent_property.extract_search_criteria(
    user_message="3к от 8 до 12 млн, кирпичный дом, чистовая отделка",
    user_id="user_123",
    conversation_history=None,  # Optional
    language="ru"  # ru/en
)

# Result structure:
{
    "intent": "search",  # search/clarify/out_of_scope
    "criteria": {
        "budget_min": 8000000,
        "budget_max": 12000000,
        "rooms_min": 3,
        "rooms_max": 3,
        "building_types": ["кирпичный", "кирпично-монолитный"],
        "renovations": ["чистовая"],
        "deal_type": "buy"
    },
    "confidence": 0.9
}
```

**Supported Parameters (37 total):**
- Basic: budget, rooms, area, district, metro, floor
- Building: building_types, exclude_building_types, building_name
- Renovation: renovations, exclude_renovations
- Layout: balcony_required, balcony_types, bathroom_type, min_ceiling_height
- Financial: mortgage_required, payment_methods, haggle_allowed
- Timing: handover_quarter, handover_year
- Developer: developers, exclude_developers
- Infrastructure: school_nearby, kindergarten_nearby, park_nearby

---

### 2. Property Service (Database Operations)

**Purpose:** Search, create, update listings and clients

#### Search with Filters

```python
from app.services.property.property_service import property_service

listings = await property_service.search_listings(
    # Basic filters
    deal_type="buy",
    price_min=8000000,
    price_max=12000000,
    rooms_min=2,
    rooms_max=3,
    area_min=60.0,
    area_max=80.0,
    districts=["Бутово", "Ясенево"],
    metro_stations=["Бульвар Дмитрия Донского"],
    floor_min=3,
    floor_max=15,

    # NEW: Building filters
    building_types=["кирпично-монолитный", "монолитный"],
    exclude_building_types=["панельный"],
    building_name="ЖК Новый",  # Fuzzy search

    # NEW: Renovation filters
    renovations=["чистовая", "под ключ"],
    exclude_renovations=["без отделки"],

    # NEW: Layout filters
    balcony_required=True,
    balcony_types=["лоджия"],
    bathroom_type="раздельный",
    bathroom_count_min=2,
    min_ceiling_height=2.8,

    # NEW: Financial filters (IMPORTANT!)
    mortgage_required=True,
    payment_methods=["ипотека", "рассрочка"],
    haggle_allowed=True,

    # NEW: Timing filters
    handover_quarter_min=1,
    handover_quarter_max=2,
    handover_year_min=2025,
    handover_year_max=2025,

    # NEW: Developer filters
    developers=["ПИК", "ЛСР"],
    exclude_developers=["А101"],

    # NEW: Area details
    living_area_min=40.0,
    kitchen_area_min=10.0,

    # NEW: Infrastructure
    school_nearby=True,
    kindergarten_nearby=True,
    park_nearby=True,

    limit=100
)
```

#### Create Client

```python
from app.schemas.property import PropertyClientCreate

client_data = PropertyClientCreate(
    telegram_user_id="123456",
    name="Иван Иванов",
    budget_min=8000000,
    budget_max=12000000,
    rooms_min=2,
    rooms_max=3,
    districts=["Бутово"],
    deal_type="buy",

    # NEW: Extended preferences
    preferred_building_types=["кирпично-монолитный"],
    preferred_renovations=["чистовая"],
    mortgage_required=True,
    balcony_required=True,
    bathroom_type_preference="раздельный",
    min_ceiling_height=2.7,
    kindergarten_nearby_required=True
)

client = await property_service.create_client(client_data)
```

---

### 3. Search Result Handler (Smart Result Management)

**Purpose:** Handle different result scenarios intelligently

```python
from app.services.property.search_result_handler import search_result_handler

result = await search_result_handler.handle_results(
    listings=listings,
    client=client,
    filters_used={
        "budget_max": 12000000,
        "mortgage_required": True,
        "building_types": ["кирпично-монолитный"]
    }
)

# Result structure:
{
    "scenario": "optimal_results",  # no_results/few_results/optimal_results/too_many_results/clustered_results
    "listings": [...],  # Top listings to show
    "message": "Нашёл 50 вариантов. Показываю топ-12 по цене.",
    "suggestions": [
        {
            "type": "add_renovation",
            "message": "Уточните тип отделки для сужения выбора"
        }
    ],
    "stats": {
        "total": 50,
        "showing": 12,
        "price_avg": 9500000
    }
}
```

**Scenarios:**
1. **no_results (0)** - Smart relaxation suggestions
2. **few_results (1-20)** - Show all + expansion suggestions
3. **optimal_results (20-200)** - Top 12 + statistics
4. **too_many_results (200+)** - Preview + narrowing questions
5. **clustered_results (100+ in one complex)** - Group by layout

---

### 4. Dream Score Calculator (Ranking System)

**Purpose:** Calculate match score (0-100) with detailed breakdown

```python
from app.services.property.dream_score import dream_score_calculator

score_data = dream_score_calculator.calculate(
    listing=listing,
    client=client
)

# Result structure:
{
    "dream_score": 87.5,  # 0-100
    "components": {
        "price_match": 95.0,      # 20% weight
        "location": 90.0,         # 15% weight
        "space": 85.0,            # 10% weight
        "floor": 80.0,            # 5% weight
        "layout": 92.0,           # 15% weight (NEW)
        "building_quality": 88.0, # 15% weight (NEW)
        "financial": 100.0,       # 10% weight (NEW)
        "infrastructure": 75.0,   # 5% weight (NEW)
        "amenities": 70.0         # 5% weight
    },
    "explanation": "Отличный вариант! Сильные стороны: финансовые условия (100%), цена (95%), планировка (92%)"
}
```

**Component Details:**
- **price_match**: Budget fit, value for money
- **location**: Metro distance, district match
- **space**: Rooms and area match
- **floor**: Floor preferences
- **layout** (NEW): Balcony, bathroom, ceiling, kitchen
- **building_quality** (NEW): Building type, renovation, year
- **financial** (NEW): Mortgage, payment methods, haggle
- **infrastructure** (NEW): School, kindergarten, park
- **amenities**: Elevator, parking, pets

---

### 5. Enrichment Services

#### POI Enrichment (OpenStreetMap)

```python
from app.services.property.poi_enrichment import poi_enrichment_service

poi_data = await poi_enrichment_service.enrich_listing(
    listing_id="listing-123",
    latitude=55.751244,
    longitude=37.618423
)

# Result:
{
    "school": {
        "nearby": True,
        "count": 3,
        "closest_distance": 350.5,
        "closest_name": "ГБОУ Школа №1234",
        "all": [...]  # Top 5
    },
    "kindergarten": {...},
    "park": {...},
    "supermarket": {...},
    "pharmacy": {...},
    "public_transport": {...}
}

# Human-readable summary
summary = poi_enrichment_service.get_poi_summary(poi_data)
# "🏫 Школа (350м): ГБОУ Школа №1234
#  👶 Детский сад (450м): Детский сад №567"
```

#### Route Matrix (Yandex.Maps)

```python
from app.services.property.route_matrix import route_matrix_service

route_data = await route_matrix_service.calculate_routes(
    listing_id="listing-123",
    from_latitude=55.751244,
    from_longitude=37.618423,
    anchor_points=[
        {
            "name": "Work Office",
            "latitude": 55.753215,
            "longitude": 37.622504,
            "priority": 1
        },
        {
            "name": "Parents",
            "latitude": 55.749215,
            "longitude": 37.614504,
            "priority": 2
        }
    ]
)

# Result:
{
    "routes": {
        "Work Office": {
            "transit": {
                "duration_minutes": 35,
                "distance_km": 12.5,
                "steps": ["Метро M1", "Автобус 123"]
            },
            "driving": {...},
            "walking": {...}
        }
    },
    "summary": {
        "avg_transit_time": 40.5,
        "max_transit_time": 55,
        "closest_anchor": "Work Office"
    }
}
```

#### Vision Analysis (Yandex Vision)

```python
from app.services.property.vision_analysis import vision_analysis_service

vision_data = await vision_analysis_service.analyze_listing_images(
    listing_id="listing-123",
    image_urls=[
        "https://example.com/photo1.jpg",
        "https://example.com/photo2.jpg"
    ],
    max_images=10
)

# Result:
{
    "light_score": 0.85,  # 0-1 (очень светлая)
    "quality_score": 0.9,  # 0-1 (отличные фото)
    "renovation_detected": "good",  # good/average/poor
    "room_types": ["kitchen", "bedroom", "living_room"],
    "amenities_detected": ["furniture", "kitchen_appliances"],
    "images_analyzed": 8
}
```

#### Price Context

```python
from app.services.property.price_context import price_context_service

price_data = await price_context_service.analyze_listing_price(
    listing_id="listing-123",
    price=10000000,
    area_total=65.0,
    rooms=2,
    district="Бутово",
    building_type="кирпично-монолитный",
    renovation="чистовая",
    all_listings=all_active_listings
)

# Result:
{
    "price_per_sqm": 153846,
    "price_percentile": 35.5,  # Lower = better deal
    "district_avg_price": 11000000,
    "value_assessment": "good_value",  # deal/good_value/fair/above_average/expensive
    "comparable_count": 47,
    "price_vs_avg": -9.1,  # 9.1% below average
    "context": "💰 Отличная цена! В нижних 25% рынка..."
}
```

#### Developer Reputation

```python
from app.services.property.developer_reputation import developer_reputation_service

dev_data = await developer_reputation_service.get_developer_reputation(
    developer_name="ПИК"
)

# Result:
{
    "developer_name": "ПИК",
    "full_name": "ПАО «Группа компаний ПИК»",
    "tier": "reliable",  # premium/reliable/average/caution/unknown
    "reputation_score": 85.5,  # 0-100
    "founded_year": 1994,
    "years_in_business": 31,
    "completed_projects": 250,
    "on_time_delivery_pct": 85,
    "quality_score": 7.5,  # 0-10
    "strengths": [
        "Многолетний опыт (31 год на рынке)",
        "Большое портфолио (250 проектов)"
    ],
    "concerns": [],
    "recommendation": "✅ Надежный застройщик..."
}
```

---

### 6. Enrichment Orchestrator (All-in-One)

**Purpose:** Coordinate all enrichment services with parallel execution

```python
from app.services.property.enrichment_orchestrator import enrichment_orchestrator

# Enrich single listing
enrichment_data = await enrichment_orchestrator.enrich_listing_full(
    listing=listing,
    client=client,
    all_listings=all_listings,
    enable_poi=True,
    enable_routes=True,
    enable_vision=True,
    enable_price=True,
    enable_developer=True
)

# Result:
{
    "listing_id": "listing-123",
    "poi_data": {...},
    "route_data": {...},
    "vision_data": {...},
    "price_context": {...},
    "developer_reputation": {...},
    "enrichment_score": 85.0,  # Completeness 0-100
    "enrichment_summary": "🏫 Школа (350м)...",
    "errors": []
}

# Get detailed report
report = enrichment_orchestrator.get_enrichment_report(
    enrichment_data,
    detailed=True
)
print(report)
```

---

## 🔄 Complete Workflows

### Workflow 1: End-to-End Search

```python
async def complete_search_workflow(user_message: str, user_id: str):
    """Complete search workflow from message to ranked results."""

    # Step 1: Extract criteria from natural language
    criteria_result = await llm_agent_property.extract_search_criteria(
        user_message=user_message,
        user_id=user_id,
        language="ru"
    )

    if criteria_result["intent"] == "clarify":
        return {
            "status": "need_clarification",
            "question": criteria_result["clarify_question"]
        }

    # Step 2: Get or create client profile
    client = await property_service.get_client_by_telegram_id(user_id)
    if not client:
        # Create client with extracted criteria
        client = await property_service.create_client(
            PropertyClientCreate(
                telegram_user_id=user_id,
                **criteria_result["criteria"]
            )
        )

    # Step 3: Search listings
    listings = await property_service.search_listings(
        **criteria_result["criteria"],
        limit=200
    )

    # Step 4: Handle results based on count
    result = await search_result_handler.handle_results(
        listings=listings,
        client=client,
        filters_used=criteria_result["criteria"]
    )

    # Step 5: Calculate Dream Scores for top results
    for listing in result["listings"][:10]:
        score_data = dream_score_calculator.calculate(listing, client)
        listing.dream_score = score_data["dream_score"]
        listing.score_explanation = score_data["explanation"]

    # Step 6: Sort by Dream Score
    result["listings"].sort(key=lambda x: x.dream_score, reverse=True)

    return {
        "status": "success",
        "scenario": result["scenario"],
        "listings": result["listings"][:5],  # Top 5
        "message": result["message"],
        "suggestions": result["suggestions"],
        "stats": result["stats"]
    }
```

### Workflow 2: Full Enrichment Pipeline

```python
async def enrich_top_listings(listings, client, all_listings):
    """Enrich top listings with all available data."""

    # Enrich top 3 in parallel
    enrichment_tasks = [
        enrichment_orchestrator.enrich_listing_full(
            listing=listing,
            client=client,
            all_listings=all_listings,
            enable_poi=True,
            enable_routes=True,
            enable_vision=True,
            enable_price=True,
            enable_developer=True
        )
        for listing in listings[:3]
    ]

    enrichment_results = await asyncio.gather(*enrichment_tasks)

    # Attach enrichment data to listings
    for listing, enrichment in zip(listings[:3], enrichment_results):
        listing.poi_data = enrichment["poi_data"]
        listing.route_data = enrichment["route_data"]
        listing.vision_data = enrichment["vision_data"]
        listing.price_context = enrichment["price_context"]
        listing.developer_reputation = enrichment["developer_reputation"]
        listing.enrichment_score = enrichment["enrichment_score"]

    return listings
```

### Workflow 3: Batch Processing

```python
async def batch_process_listings(listing_ids: List[str]):
    """Process multiple listings in batches."""

    # Fetch listings
    listings = []
    for listing_id in listing_ids:
        listing = await property_service.get_listing(listing_id)
        if listing:
            listings.append(listing)

    # Batch enrichment
    enrichment_results = await enrichment_orchestrator.enrich_listings_batch(
        listings=listings,
        client=None,  # No routes without client
        all_listings=listings,  # For price context
        batch_size=5,
        enable_poi=True,
        enable_routes=False,
        enable_vision=True,
        enable_price=True,
        enable_developer=True
    )

    return enrichment_results
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost/calendar_bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Yandex GPT (for LLM agent)
YANDEX_GPT_API_KEY=your_yandex_gpt_key
YANDEX_GPT_FOLDER_ID=your_folder_id

# Optional - External enrichment
YANDEX_MAPS_API_KEY=your_maps_key  # For routes
YANDEX_VISION_API_KEY=your_vision_key  # For photo analysis (can reuse GPT key)
```

### Service Configuration

```python
# Custom configuration
from app.services.property.poi_enrichment import POIEnrichmentService

poi_service = POIEnrichmentService()
poi_service.WALKING_DISTANCE_METERS = 1000  # Increase radius
poi_service.CACHE_TTL_DAYS = 14  # Longer cache

# Route service
from app.services.property.route_matrix import RouteMatrixService

route_service = RouteMatrixService()
route_service.CACHE_TTL_DAYS = 60  # Longer cache for routes
```

---

## 🛡️ Error Handling

### Graceful Degradation

All services support graceful degradation:

```python
# POI enrichment without API
poi_data = await poi_enrichment_service.enrich_listing(...)
# Returns empty data if Overpass API fails

# Routes without API key
route_data = await route_matrix_service.calculate_routes(...)
# Returns empty data if YANDEX_MAPS_API_KEY not set

# Vision without API
vision_data = await vision_analysis_service.analyze_listing_images(...)
# Returns empty data if YANDEX_VISION_API_KEY not set

# LLM without API
result = await llm_agent_property.extract_search_criteria(...)
# Falls back to regex parsing if YANDEX_GPT_API_KEY not set
```

### Error Recovery

```python
try:
    enrichment_data = await enrichment_orchestrator.enrich_listing_full(
        listing=listing,
        client=client
    )

    # Check for errors
    if enrichment_data.get("errors"):
        logger.warning("Enrichment had errors",
                      errors=enrichment_data["errors"])

    # Check completeness score
    if enrichment_data["enrichment_score"] < 50:
        logger.warning("Low enrichment score",
                      score=enrichment_data["enrichment_score"])

except Exception as e:
    logger.error("Enrichment failed completely", error=str(e))
    # Continue without enrichment
```

---

## 💡 Best Practices

### 1. Always Use Search Result Handler

```python
# ✅ Good
result = await search_result_handler.handle_results(listings, client, filters)
message = result["message"]
suggestions = result["suggestions"]

# ❌ Bad
if len(listings) == 0:
    message = "Nothing found"  # No smart suggestions
elif len(listings) > 200:
    message = "Too many"  # No narrowing questions
```

### 2. Cache Enrichment Data

```python
# Enrichment is expensive - cache results
if listing.poi_data and listing.poi_data_age < 7_days:
    poi_data = listing.poi_data
else:
    poi_data = await poi_enrichment_service.enrich_listing(...)
    listing.poi_data = poi_data
    await property_service.update_listing(listing)
```

### 3. Batch Operations

```python
# ✅ Good - batch enrichment
enrichment_results = await enrichment_orchestrator.enrich_listings_batch(
    listings=listings[:10],
    batch_size=5
)

# ❌ Bad - sequential enrichment
for listing in listings[:10]:
    await enrichment_orchestrator.enrich_listing_full(listing)
```

### 4. Progressive Enhancement

```python
# Show results immediately, enrich in background
async def progressive_search(query, user_id):
    # 1. Quick search
    listings = await property_service.search_listings(**query)
    result = await search_result_handler.handle_results(listings)

    # Show basic results to user immediately
    await send_to_user(result["listings"][:3])

    # 2. Calculate scores in background
    for listing in result["listings"][:10]:
        score = dream_score_calculator.calculate(listing, client)
        listing.dream_score = score["dream_score"]

    # Update user with scored results
    await update_user_results(result["listings"][:3])

    # 3. Enrich top results in background
    enrichment_data = await enrichment_orchestrator.enrich_listing_full(
        result["listings"][0]  # Top result only
    )

    # Show enrichment when ready
    await send_enrichment_to_user(enrichment_data)
```

### 5. Rate Limiting

```python
# Respect API rate limits
import asyncio

# POI - 2 req/sec max
for batch in chunks(listings, 2):
    await enrich_poi_batch(batch)
    await asyncio.sleep(0.5)

# Yandex APIs - built-in delays in services
```

---

## 📞 Support & Docs

- Main docs: [PROPERTY_BOT_COMPLETE.md](PROPERTY_BOT_COMPLETE.md)
- Implementation: [PROPERTY_BOT_IMPLEMENTATION.md](PROPERTY_BOT_IMPLEMENTATION.md)
- Tests: Run `python test_property_bot_cli.py`

**Happy coding! 🏡✨**
```
