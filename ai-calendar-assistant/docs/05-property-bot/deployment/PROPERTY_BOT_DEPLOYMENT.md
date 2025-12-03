# Property Bot Deployment Guide

**Руководство по развертыванию Property Search Bot**

## Status: Production Ready ✅

Все 3 этапа разработки завершены (100%):
- ✅ Stage 1: Database schema, feed parsing, basic tests
- ✅ Stage 2: Enhanced search, result handlers, scoring system
- ✅ Stage 3: External enrichment services (POI, routes, vision, prices, developers)

---

## Prerequisites

### 1. System Requirements

- Python 3.10+
- PostgreSQL 14+
- Docker & Docker Compose (optional, recommended)
- 2GB RAM minimum
- 10GB disk space

### 2. Required API Keys

**Обязательные:**
- `YANDEX_GPT_API_KEY` - Yandex GPT для обработки запросов
- `YANDEX_GPT_FOLDER_ID` - Folder ID для Yandex Cloud

**Опциональные (система работает без них):**
- `YANDEX_MAPS_API_KEY` - Для расчета маршрутов
- `YANDEX_VISION_API_KEY` - Для анализа фотографий

### 3. Environment Variables

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/property_bot

# Yandex APIs (required)
YANDEX_GPT_API_KEY=your_yandex_gpt_api_key
YANDEX_GPT_FOLDER_ID=your_folder_id

# Yandex APIs (optional - graceful degradation)
YANDEX_MAPS_API_KEY=your_yandex_maps_api_key
YANDEX_VISION_API_KEY=your_yandex_vision_api_key

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## Installation

### Option 1: Docker Compose (Recommended)

**1. Clone repository:**
```bash
git clone <repository>
cd ai-calendar-assistant
```

**2. Create environment file:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**3. Start services:**
```bash
docker-compose -f docker-compose.property.yml up -d
```

**4. Run migrations:**
```bash
docker-compose -f docker-compose.property.yml exec property-bot alembic upgrade head
```

**5. Load test data (optional):**
```bash
docker-compose -f docker-compose.property.yml exec property-bot python scripts/load_sample_properties.py
```

### Option 2: Manual Installation

**1. Install Python dependencies:**
```bash
pip install -r requirements-property.txt
```

**2. Setup PostgreSQL:**
```bash
createdb property_bot
```

**3. Run migrations:**
```bash
cd app
alembic upgrade head
```

**4. Start application:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Database Setup

### Create Tables

```sql
-- Run migrations automatically
alembic upgrade head

-- Or manually:
psql -U postgres -d property_bot -f migrations/property_bot_schema.sql
```

### Load Sample Data

```bash
python scripts/load_sample_properties.py --count 1000
```

This creates:
- 1000 sample property listings
- 50 sample complexes
- 10 sample clients with preferences

---

## Integration with Telegram Bot

### Update app/services/telegram_handler.py

```python
from app.services.property.llm_agent_property import PropertyLLMAgent
from app.services.property.property_service import PropertyService
from app.services.property.search_result_handler import SearchResultHandler
from app.services.property.dream_score import DreamScoreCalculator
from app.services.property.enrichment_orchestrator import EnrichmentOrchestrator

class TelegramHandler:
    def __init__(self):
        # Initialize property services
        self.property_llm = PropertyLLMAgent()
        self.property_service = PropertyService()
        self.result_handler = SearchResultHandler()
        self.enrichment = EnrichmentOrchestrator()

    async def handle_property_search(self, user_id: int, message: str):
        """Handle property search request."""

        # 1. Extract search parameters from natural language
        params = await self.property_llm.extract_search_params(message)

        # 2. Get or create client profile
        client = await self.property_service.get_or_create_client(
            telegram_id=user_id,
            preferences=params
        )

        # 3. Search listings
        listings = await self.property_service.search_listings(**params)

        # 4. Calculate Dream Scores
        for listing in listings:
            listing.dream_score = DreamScoreCalculator.calculate_score(
                listing, client
            )

        # Sort by Dream Score
        listings.sort(key=lambda x: x.dream_score, reverse=True)

        # 5. Handle results based on count
        result = await self.result_handler.handle_results(
            listings, client, params
        )

        # 6. Format response
        if result["scenario"] == "no_results":
            response = self._format_no_results(result)
        elif result["scenario"] == "few_results":
            response = self._format_few_results(result)
        elif result["scenario"] == "optimal_results":
            response = await self._format_optimal_results(result)
        elif result["scenario"] == "clustered_results":
            response = self._format_clustered_results(result)
        else:  # too_many_results
            response = self._format_too_many_results(result)

        return response

    async def handle_listing_details(self, user_id: int, listing_id: str):
        """Show detailed listing info with enrichment."""

        # Get listing
        listing = await self.property_service.get_listing(listing_id)
        if not listing:
            return "Квартира не найдена"

        # Get client
        client = await self.property_service.get_client_by_telegram_id(user_id)

        # Enrich with all external data
        enrichment = await self.enrichment.enrich_listing_full(
            listing=listing,
            client=client,
            enable_poi=True,
            enable_routes=True,
            enable_vision=True,
            enable_price=True,
            enable_developer=True
        )

        # Format detailed response
        response = self._format_listing_details(listing, client, enrichment)

        return response

    def _format_optimal_results(self, result: Dict) -> str:
        """Format optimal results (20-200 listings)."""
        lines = [
            f"🏠 Найдено {result['total_count']} квартир",
            f"Показываю топ-{len(result['listings'])} по Dream Score:",
            ""
        ]

        for i, listing in enumerate(result["listings"], 1):
            lines.append(
                f"{i}. {listing.rooms}-комн, {listing.area_total}м², "
                f"{listing.price/1_000_000:.1f}млн ₽, {listing.district}"
            )
            lines.append(f"   Dream Score: {listing.dream_score}/100")
            lines.append(f"   /details_{listing.id}")
            lines.append("")

        # Add stats
        stats = result.get("stats", {})
        lines.append("📊 Статистика по всем результатам:")
        lines.append(f"Средняя цена: {stats['avg_price']/1_000_000:.1f}млн ₽")
        lines.append(f"Средняя площадь: {stats['avg_area']:.1f}м²")
        lines.append(f"Диапазон цен: {stats['min_price']/1_000_000:.1f}-{stats['max_price']/1_000_000:.1f}млн ₽")

        return "\n".join(lines)
```

### Add Router Endpoints

```python
# app/routers/property_search.py
from fastapi import APIRouter, Depends
from app.services.telegram_handler import TelegramHandler

router = APIRouter(prefix="/property", tags=["property"])

@router.post("/search")
async def search_properties(
    user_id: int,
    message: str,
    handler: TelegramHandler = Depends()
):
    """Search properties via natural language."""
    result = await handler.handle_property_search(user_id, message)
    return result

@router.get("/listing/{listing_id}")
async def get_listing_details(
    listing_id: str,
    user_id: int,
    handler: TelegramHandler = Depends()
):
    """Get detailed listing info with enrichment."""
    result = await handler.handle_listing_details(user_id, listing_id)
    return result
```

---

## Testing

### Run Unit Tests

```bash
pytest tests/test_property_stage2_integration.py -v
```

### Run CLI Tests

```bash
# All tests
python test_property_bot_cli.py

# Individual test suites
python test_property_bot_cli.py llm
python test_property_bot_cli.py search
python test_property_bot_cli.py handler
python test_property_bot_cli.py score
python test_property_bot_cli.py enrichment
```

### Manual Testing

```bash
# Test search
curl -X POST http://localhost:8000/property/search \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123, "message": "Ищу 2-комнатную квартиру до 10 млн с ипотекой"}'

# Test listing details
curl http://localhost:8000/property/listing/prop_001?user_id=123
```

---

## Monitoring

### Health Check Endpoint

```python
@router.get("/health")
async def health_check():
    """Check property bot services health."""
    return {
        "status": "healthy",
        "database": await check_database(),
        "yandex_gpt": await check_yandex_gpt(),
        "enrichment_services": {
            "poi": "operational (no API key needed)",
            "routes": await check_yandex_maps(),
            "vision": await check_yandex_vision(),
            "price": "operational",
            "developer": "operational"
        }
    }
```

### Logging

All services use `structlog` for structured logging:

```python
logger.info("search_executed",
           user_id=user_id,
           filters_count=len(params),
           results_count=len(listings),
           scenario=result["scenario"],
           duration_ms=duration)
```

### Metrics to Monitor

- Search request rate
- Average search duration
- Dream Score distribution
- Enrichment success rate
- Cache hit rate
- API error rate

---

## Performance Optimization

### Database Indexes

All critical columns are indexed:
```sql
CREATE INDEX idx_listings_price ON property_listings(price);
CREATE INDEX idx_listings_rooms ON property_listings(rooms);
CREATE INDEX idx_listings_district ON property_listings(district);
CREATE INDEX idx_listings_metro_station ON property_listings(metro_station);
CREATE INDEX idx_listings_area_total ON property_listings(area_total);
```

### Caching Strategy

- **POI data**: 7 days (infrastructure doesn't change often)
- **Route matrix**: 30 days (routes stable)
- **Price context**: 24 hours (market prices update daily)
- **Vision analysis**: Permanent (photos don't change)
- **Developer reputation**: Permanent (built-in database)

### Batch Processing

For enriching multiple listings:

```python
# Enrich 50 listings in parallel (batches of 10)
enrichment_results = await enrichment.enrich_listings_batch(
    listings=listings,
    batch_size=10,
    enable_all=True
)
```

---

## Security

### Input Validation

- All user inputs validated via Pydantic schemas
- SQL injection protection via SQLAlchemy ORM
- Price range limits: 500k - 500M RUB
- Area range limits: 10 - 500 m²

### API Rate Limiting

```python
from app.services.rate_limiter import rate_limiter

@router.post("/search")
@rate_limiter.limit("10/minute")
async def search_properties(...):
    pass
```

### Data Privacy

- No PII in logs
- Client preferences encrypted at rest
- Telegram IDs hashed for analytics

---

## Troubleshooting

### Common Issues

**1. "No Yandex GPT API key"**
```bash
# Check environment variable
echo $YANDEX_GPT_API_KEY

# Verify in application
curl http://localhost:8000/property/health
```

**2. "Database connection error"**
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
psql $DATABASE_URL
```

**3. "Enrichment services failing"**
- Check logs for specific service errors
- System works with graceful degradation
- POI works without API keys (uses OpenStreetMap)
- Routes/Vision require Yandex API keys but are optional

**4. "No search results"**
- Check if database has listings: `SELECT COUNT(*) FROM property_listings;`
- Load sample data: `python scripts/load_sample_properties.py`
- Verify filters aren't too restrictive

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python -m uvicorn app.main:app --reload
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
services:
  property-bot:
    image: property-bot:latest
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/property_bot
```

### Database Optimization

```sql
-- Partition large tables
CREATE TABLE property_listings_2024 PARTITION OF property_listings
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- Add read replicas for search queries
```

### Caching Layer

```python
# Add Redis for distributed caching
from redis import asyncio as aioredis

cache = await aioredis.from_url("redis://localhost")
```

---

## Maintenance

### Daily Tasks

- Monitor error logs
- Check enrichment success rates
- Verify API quota usage

### Weekly Tasks

- Review search analytics
- Update developer database
- Clean old cache entries

### Monthly Tasks

- Update sample data
- Optimize database queries
- Review and update Dream Score weights based on user feedback

---

## Support

### Documentation

- [API Guide](PROPERTY_BOT_API_GUIDE.md) - Complete API reference
- [Stage 2 Completion](PROPERTY_BOT_STAGE2_COMPLETE.md) - Technical details
- [Full Project Summary](PROPERTY_BOT_COMPLETE.md) - Architecture overview

### Testing Utilities

- `test_property_bot_cli.py` - CLI testing tool
- `tests/test_property_stage2_integration.py` - Unit tests

### Contact

For technical issues or feature requests, please refer to the documentation above or check the implementation files in `app/services/property/`.

---

## Changelog

### v1.0.0 (Current)

✅ **Stage 1 (30%)**: Database schema, feed parsing
✅ **Stage 2 (50%)**: Enhanced search with 37 filters, 5 result scenarios, 9-component Dream Score
✅ **Stage 3 (20%)**: External enrichment (POI, routes, vision, prices, developer reputation)

**Total Features:**
- 37 search filters (price, location, rooms, area, building, financial, renovation, infrastructure)
- 5 result handling scenarios (0, 1-20, 20-200, 200+, 100+ clustered)
- 9-component Dream Score (price, location, space, floor, layout, building, financial, infrastructure, amenities)
- 5 enrichment services (POI, routes, vision, price context, developer reputation)
- Complete test coverage with CLI utility
- Production-ready with graceful degradation

---

**Status: Ready for Production Deployment** 🚀
