"""Integration tests for Property Bot Stage 2 features."""

import pytest
from datetime import datetime
from typing import List, Dict, Any

# Mock imports for testing without dependencies
try:
    from app.services.property.property_service import PropertyService
    from app.services.property.search_result_handler import SearchResultHandler
    from app.services.property.llm_agent_property import PropertyLLMAgent
    from app.services.property.dream_score import DreamScoreCalculator
    from app.schemas.property import (
        PropertyListingCreate,
        PropertyListingResponse,
        PropertyClientCreate,
        PropertyClientResponse
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    pytest.skip("Property service modules not available", allow_module_level=True)


class TestEnhancedSearch:
    """Test enhanced search functionality with 20+ filters."""

    @pytest.mark.asyncio
    async def test_search_with_building_type_filter(self):
        """Test search with building type preference."""
        # This would require actual DB setup
        # For now, just test the API signature
        service = PropertyService(database_url="sqlite:///:memory:")

        # Test that new parameters are accepted
        results = await service.search_listings(
            budget_min=8000000,
            budget_max=12000000,
            rooms_min=2,
            rooms_max=3,
            building_types=["кирпично-монолитный", "монолитный"],
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_renovation_filter(self):
        """Test search with renovation preferences."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            renovations=["чистовая", "под ключ"],
            exclude_renovations=["без отделки"],
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_financial_filters(self):
        """Test search with financial conditions."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            mortgage_required=True,
            payment_methods=["ипотека", "рассрочка"],
            haggle_allowed=True,
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_layout_filters(self):
        """Test search with layout preferences."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            balcony_required=True,
            balcony_types=["лоджия"],
            bathroom_type="раздельный",
            bathroom_count_min=2,
            min_ceiling_height=2.8,
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_handover_date_filter(self):
        """Test search with handover date constraints."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            handover_quarter_min=1,
            handover_quarter_max=2,
            handover_year_min=2025,
            handover_year_max=2025,
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_infrastructure_filters(self):
        """Test search with POI filters."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            school_nearby=True,
            kindergarten_nearby=True,
            park_nearby=True,
            limit=10
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_all_new_filters_combined(self):
        """Test search with multiple new filter types combined."""
        service = PropertyService(database_url="sqlite:///:memory:")

        results = await service.search_listings(
            # Basic
            budget_min=8000000,
            budget_max=12000000,
            rooms_min=2,
            rooms_max=3,
            # Building
            building_types=["кирпично-монолитный"],
            building_name="ЖК Новый",
            # Renovation
            renovations=["чистовая"],
            # Layout
            balcony_required=True,
            bathroom_type="раздельный",
            min_ceiling_height=2.7,
            # Financial
            mortgage_required=True,
            payment_methods=["ипотека"],
            # Infrastructure
            school_nearby=True,
            kindergarten_nearby=True,
            # Amenities
            requires_elevator=True,
            has_parking=True,
            limit=50
        )

        assert isinstance(results, list)


class TestSearchResultHandler:
    """Test SearchResultHandler for different result scenarios."""

    @pytest.mark.asyncio
    async def test_handle_no_results(self):
        """Test handling of zero results scenario."""
        handler = SearchResultHandler()

        # Mock client and filters
        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            budget_min=8000000,
            budget_max=10000000,
            rooms_min=2,
            rooms_max=2,
            mortgage_required=True
        )

        filters_used = {
            "budget_min": 8000000,
            "budget_max": 10000000,
            "rooms_min": 2,
            "rooms_max": 2,
            "mortgage_required": True,
            "building_types": ["кирпичный"],
            "renovations": ["под ключ"]
        }

        result = await handler.handle_results([], client, filters_used)

        assert result["scenario"] == "no_results"
        assert len(result["listings"]) == 0
        assert len(result["suggestions"]) > 0
        assert "mortgage_required" in result["suggestions"][0]["filter"] or \
               "building_types" in result["suggestions"][0]["filter"] or \
               "renovations" in result["suggestions"][0]["filter"]

    @pytest.mark.asyncio
    async def test_handle_few_results(self):
        """Test handling of 1-20 results."""
        handler = SearchResultHandler()

        # Create mock listings
        listings = [
            PropertyListingResponse(
                id=f"listing-{i}",
                title=f"Квартира {i}",
                price=9000000 + i * 100000,
                rooms=2,
                area_total=60.0 + i,
                district="Бутово",
                deal_type="buy"
            )
            for i in range(5)
        ]

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            budget_max=10000000
        )

        result = await handler.handle_results(listings, client, {})

        assert result["scenario"] == "few_results"
        assert len(result["listings"]) == 5
        assert "stats" in result
        assert result["stats"]["total"] == 5

    @pytest.mark.asyncio
    async def test_handle_optimal_results(self):
        """Test handling of 20-200 results."""
        handler = SearchResultHandler()

        # Create 50 mock listings
        listings = [
            PropertyListingResponse(
                id=f"listing-{i}",
                title=f"Квартира {i}",
                price=8000000 + i * 50000,
                rooms=2,
                area_total=55.0 + i * 0.5,
                district="Бутово",
                deal_type="buy"
            )
            for i in range(50)
        ]

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345"
        )

        result = await handler.handle_results(listings, client, {})

        assert result["scenario"] == "optimal_results"
        assert len(result["listings"]) == 12  # Top 12
        assert result["stats"]["total"] == 50
        assert result["stats"]["showing"] == 12

    @pytest.mark.asyncio
    async def test_handle_too_many_results(self):
        """Test handling of 200+ results."""
        handler = SearchResultHandler()

        # Create 250 mock listings
        listings = [
            PropertyListingResponse(
                id=f"listing-{i}",
                title=f"Квартира {i}",
                price=7000000 + i * 10000,
                rooms=2,
                area_total=50.0 + i * 0.2,
                district="Бутово",
                deal_type="buy",
                renovation="чистовая" if i % 2 == 0 else "без отделки",
                building_type="кирпично-монолитный" if i % 3 == 0 else "панельный"
            )
            for i in range(250)
        ]

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345"
        )

        result = await handler.handle_results(listings, client, {})

        assert result["scenario"] == "too_many_results"
        assert len(result["listings"]) == 12  # Preview only
        assert len(result["suggestions"]) > 0
        # Should suggest narrowing
        assert any(s["type"] in ["select_renovation", "select_building_type", "select_handover_date"]
                  for s in result["suggestions"])

    @pytest.mark.asyncio
    async def test_handle_clustered_results(self):
        """Test handling of 100+ results in one complex."""
        handler = SearchResultHandler()

        # Create 150 listings in same building
        listings = [
            PropertyListingResponse(
                id=f"listing-{i}",
                title=f"Квартира {i}",
                price=8000000 + i * 50000,
                rooms=2 if i < 100 else 3,
                area_total=60.0 if i < 100 else 80.0,
                building_name="ЖК Тестовый",
                balcony_type="балкон" if i % 2 == 0 else "лоджия",
                bathroom_type="раздельный" if i % 3 == 0 else "совмещенный",
                deal_type="buy"
            )
            for i in range(150)
        ]

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345"
        )

        result = await handler.handle_results(listings, client, {})

        assert result["scenario"] == "clustered_results"
        assert "clusters" in result
        assert len(result["clusters"]) > 1  # Should group by layout
        assert result["stats"]["building"] == "ЖК Тестовый"


class TestEnhancedLLMAgent:
    """Test LLM agent with financial parameters extraction."""

    @pytest.mark.asyncio
    async def test_extract_financial_parameters_mortgage(self):
        """Test extraction of mortgage requirement."""
        agent = PropertyLLMAgent()

        # Test with fallback (no API)
        result = agent._fallback_extraction("Ищу 2-комнатную с ипотекой до 10 млн")

        assert result["intent"] == "search"
        assert result["criteria"]["mortgage_required"] is True
        assert "ипотека" in result["criteria"]["payment_methods"]

    @pytest.mark.asyncio
    async def test_extract_financial_parameters_installments(self):
        """Test extraction of installment payment."""
        agent = PropertyLLMAgent()

        result = agent._fallback_extraction("Нужна квартира в рассрочку")

        assert result["intent"] == "search"
        assert "payment_methods" in result["criteria"]
        assert "рассрочка" in result["criteria"]["payment_methods"]

    @pytest.mark.asyncio
    async def test_extract_financial_parameters_maternity_capital(self):
        """Test extraction of maternity capital."""
        agent = PropertyLLMAgent()

        result = agent._fallback_extraction("Квартира с материнским капиталом")

        assert result["intent"] == "search"
        assert "payment_methods" in result["criteria"]
        assert "материнский капитал" in result["criteria"]["payment_methods"]

    @pytest.mark.asyncio
    async def test_extract_building_preferences(self):
        """Test extraction of building type preferences."""
        agent = PropertyLLMAgent()

        result = agent._fallback_extraction("Хочу кирпичный дом с балконом")

        assert result["intent"] == "search"
        assert "building_types" in result["criteria"]
        assert any("кирпич" in bt for bt in result["criteria"]["building_types"])
        assert result["criteria"]["balcony_required"] is True

    @pytest.mark.asyncio
    async def test_extract_renovation_preferences(self):
        """Test extraction of renovation type."""
        agent = PropertyLLMAgent()

        result = agent._fallback_extraction("2к с чистовой отделкой")

        assert result["intent"] == "search"
        assert "renovations" in result["criteria"]
        assert "чистовая" in result["criteria"]["renovations"]

    @pytest.mark.asyncio
    async def test_extract_infrastructure_needs(self):
        """Test extraction of infrastructure requirements."""
        agent = PropertyLLMAgent()

        result = agent._fallback_extraction("Квартира рядом школа и детский сад")

        assert result["intent"] == "search"
        assert result["criteria"].get("school_nearby") is True
        assert result["criteria"].get("kindergarten_nearby") is True


class TestEnhancedDreamScore:
    """Test enhanced Dream Score with new components."""

    def test_dream_score_calculation_perfect_match(self):
        """Test Dream Score for perfect match listing."""
        calculator = DreamScoreCalculator()

        listing = PropertyListingResponse(
            id="test-listing",
            title="Perfect Apartment",
            price=9000000,
            rooms=2,
            area_total=65.0,
            living_area=45.0,
            kitchen_area=12.0,
            floor=5,
            total_floors=17,
            district="Бутово",
            metro_distance_minutes=7,
            building_type="кирпично-монолитный",
            building_year=2024,
            renovation="чистовая",
            balcony_type="лоджия",
            bathroom_type="раздельный",
            bathroom_count=2,
            ceiling_height=2.8,
            mortgage_available=True,
            payment_methods=["ипотека", "рассрочка"],
            haggle_allowed=True,
            has_elevator=True,
            has_parking=True,
            deal_type="buy"
        )

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            budget_min=8000000,
            budget_max=10000000,
            rooms_min=2,
            rooms_max=2,
            area_min=60.0,
            area_max=70.0,
            districts=["Бутово"],
            max_metro_distance_minutes=10,
            floor_min=3,
            floor_max=10,
            not_first_floor=True,
            not_last_floor=True,
            preferred_building_types=["кирпично-монолитный"],
            preferred_renovations=["чистовая"],
            balcony_required=True,
            bathroom_type_preference="раздельный",
            min_ceiling_height=2.7,
            mortgage_required=True,
            requires_elevator=True
        )

        result = calculator.calculate(listing, client)

        assert result["dream_score"] >= 80.0  # Should be high score
        assert "components" in result
        assert len(result["components"]) == 9
        assert result["components"]["price_match"] >= 80
        assert result["components"]["location"] >= 80
        assert result["components"]["building_quality"] >= 70
        assert result["components"]["financial"] >= 70

    def test_dream_score_calculation_poor_match(self):
        """Test Dream Score for poor match listing."""
        calculator = DreamScoreCalculator()

        listing = PropertyListingResponse(
            id="test-listing",
            title="Poor Match Apartment",
            price=15000000,  # Way over budget
            rooms=4,  # Wrong number of rooms
            area_total=120.0,
            floor=1,  # First floor
            district="Другой район",
            metro_distance_minutes=45,  # Too far
            building_type="панельный",
            renovation="без отделки",
            mortgage_available=False,  # No mortgage
            deal_type="buy"
        )

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            budget_min=8000000,
            budget_max=10000000,
            rooms_min=2,
            rooms_max=2,
            districts=["Бутово"],
            max_metro_distance_minutes=10,
            not_first_floor=True,
            mortgage_required=True,
            preferred_building_types=["кирпично-монолитный"],
            preferred_renovations=["чистовая"]
        )

        result = calculator.calculate(listing, client)

        assert result["dream_score"] < 40.0  # Should be low score
        assert result["components"]["price_match"] < 30
        assert result["components"]["location"] < 30
        assert result["components"]["floor"] < 10  # First floor dealbreaker

    def test_building_quality_component(self):
        """Test building quality scoring component."""
        calculator = DreamScoreCalculator()

        # High quality building
        listing_good = PropertyListingResponse(
            id="test-1",
            building_type="кирпично-монолитный",
            building_year=2024,
            renovation="под ключ",
            price=10000000,
            rooms=2,
            deal_type="buy"
        )

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            preferred_building_types=["кирпично-монолитный"],
            preferred_renovations=["под ключ"]
        )

        score_good = calculator._score_building_quality(listing_good, client)
        assert score_good >= 80.0

        # Low quality building
        listing_bad = PropertyListingResponse(
            id="test-2",
            building_type="панельный",
            building_year=2010,
            renovation="без отделки",
            price=10000000,
            rooms=2,
            deal_type="buy"
        )

        score_bad = calculator._score_building_quality(listing_bad, client)
        assert score_bad < 40.0

    def test_layout_component(self):
        """Test layout scoring component."""
        calculator = DreamScoreCalculator()

        # Perfect layout
        listing_perfect = PropertyListingResponse(
            id="test-1",
            balcony_type="лоджия",
            bathroom_type="раздельный",
            bathroom_count=2,
            ceiling_height=2.9,
            kitchen_area=12.0,
            price=10000000,
            rooms=2,
            deal_type="buy"
        )

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            balcony_required=True,
            preferred_balcony_types=["лоджия"],
            bathroom_type_preference="раздельный",
            min_bathroom_count=2,
            min_ceiling_height=2.7,
            kitchen_area_min=10.0
        )

        score_perfect = calculator._score_layout(listing_perfect, client)
        assert score_perfect >= 85.0

    def test_financial_component(self):
        """Test financial scoring component."""
        calculator = DreamScoreCalculator()

        # Perfect financial conditions
        listing_perfect = PropertyListingResponse(
            id="test-1",
            mortgage_available=True,
            payment_methods=["ипотека", "рассрочка", "материнский капитал"],
            haggle_allowed=True,
            price=10000000,
            rooms=2,
            deal_type="buy"
        )

        client = PropertyClientResponse(
            id="test-client",
            telegram_user_id="12345",
            mortgage_required=True,
            preferred_payment_methods=["ипотека", "рассрочка"]
        )

        score_perfect = calculator._score_financial(listing_perfect, client)
        assert score_perfect >= 90.0

        # No mortgage when required
        listing_bad = PropertyListingResponse(
            id="test-2",
            mortgage_available=False,
            payment_methods=[],
            haggle_allowed=False,
            price=10000000,
            rooms=2,
            deal_type="buy"
        )

        score_bad = calculator._score_financial(listing_bad, client)
        assert score_bad < 30.0  # Major penalty for missing mortgage


# Run tests with simple runner if pytest not available
if __name__ == "__main__":
    print("Running Property Stage 2 Integration Tests...")
    print("\nNote: These tests require pytest. Install with: pip install pytest pytest-asyncio")
    print("Run with: pytest tests/test_property_stage2_integration.py -v")
