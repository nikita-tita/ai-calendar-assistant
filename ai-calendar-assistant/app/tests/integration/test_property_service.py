"""Integration tests for Property Service."""

import pytest
from app.services.property.property_service import PropertyService
from app.schemas.property import PropertyClientCreate
from app.models.property import DealType
from typing import List


@pytest.fixture
def property_service():
    """Create PropertyService instance."""
    return PropertyService()


@pytest.fixture
def test_user_id():
    """Test user ID for property operations."""
    return "property_test_user_123"


@pytest.fixture
def sample_client_data(test_user_id):
    """Sample client data for testing."""
    return PropertyClientCreate(
        telegram_user_id=test_user_id,
        budget_min=5000000,
        budget_max=15000000,
        rooms_min=2,
        rooms_max=3,
        districts=["Центральный", "Северный"],
        metro_stations=["Краснопресненская", "Белорусская"],
        mortgage_required=True,
        preferred_building_types=["монолитный", "кирпичный"],
        preferred_renovations=["чистовая", "без отделки"]
    )


@pytest.mark.asyncio
class TestPropertyClientOperations:
    """Test Property Client CRUD operations."""

    async def test_create_client(self, property_service, sample_client_data):
        """Test creating a new property client."""
        client = await property_service.create_client(sample_client_data)
        
        # Assertions
        assert client is not None, "Client should be created"
        assert client.telegram_user_id == sample_client_data.telegram_user_id
        assert client.budget_min == sample_client_data.budget_min
        assert client.budget_max == sample_client_data.budget_max
        assert client.rooms_min == sample_client_data.rooms_min
        assert client.rooms_max == sample_client_data.rooms_max

    async def test_get_client_by_telegram_id(self, property_service, sample_client_data, test_user_id):
        """Test retrieving client by Telegram ID."""
        # First create a client
        created_client = await property_service.create_client(sample_client_data)
        
        # Then retrieve it
        client = await property_service.get_client_by_telegram_id(test_user_id)
        
        # Assertions
        assert client is not None, "Client should be found"
        assert client.id == created_client.id
        assert client.telegram_user_id == test_user_id

    async def test_update_client(self, property_service, sample_client_data, test_user_id):
        """Test updating client data."""
        from app.schemas.property import PropertyClientUpdate
        
        # Create client
        client = await property_service.create_client(sample_client_data)
        
        # Update client
        update_data = PropertyClientUpdate(
            budget_min=8000000,
            budget_max=20000000,
            rooms_min=3
        )
        
        updated = await property_service.update_client(client.id, update_data)
        
        # Assertions
        assert updated is not None
        assert updated.budget_min == 8000000
        assert updated.budget_max == 20000000
        assert updated.rooms_min == 3


@pytest.mark.asyncio
class TestPropertySearch:
    """Test property search functionality."""

    async def test_search_by_price_range(self, property_service):
        """Test searching properties by price range."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            price_min=5000000,
            price_max=15000000,
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        
        # Verify all results are within price range
        for listing in listings:
            assert listing.price >= 5000000, "Price should be >= min"
            assert listing.price <= 15000000, "Price should be <= max"

    async def test_search_by_rooms(self, property_service):
        """Test searching properties by number of rooms."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            rooms_min=2,
            rooms_max=3,
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        
        # Verify all results match room criteria
        for listing in listings:
            assert listing.rooms >= 2, "Should have at least 2 rooms"
            assert listing.rooms <= 3, "Should have at most 3 rooms"

    async def test_search_by_district(self, property_service):
        """Test searching properties by district."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            districts=["Центральный"],
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        
        # Verify all results are in specified district
        for listing in listings:
            assert listing.district == "Центральный", "Should be in Central district"

    async def test_search_with_multiple_filters(self, property_service):
        """Test searching with multiple filters combined."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            price_min=5000000,
            price_max=10000000,
            rooms_min=2,
            rooms_max=2,
            districts=["Центральный"],
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        
        # Verify all results match all criteria
        for listing in listings:
            assert 5000000 <= listing.price <= 10000000, "Price in range"
            assert listing.rooms == 2, "Should have 2 rooms"
            assert listing.district == "Центральный", "Should be in Central"

    async def test_search_empty_results(self, property_service):
        """Test search that returns no results."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            price_min=999999999,
            price_max=999999999,
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        assert len(listings) == 0, "Should return empty for impossible criteria"

    async def test_search_with_area_filter(self, property_service):
        """Test searching by area range."""
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            area_min=40.0,
            area_max=80.0,
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        
        # Verify area constraints
        for listing in listings:
            assert 40.0 <= listing.area_total <= 80.0, "Area should be in range"


@pytest.mark.asyncio
class TestPropertyScoring:
    """Test property scoring functionality."""

    async def test_dream_score_calculation(self, property_service, sample_client_data):
        """Test Dream Score calculation for listings."""
        from app.services.property.property_scoring import PropertyScoringService
        
        scoring_service = PropertyScoringService()
        
        # Create client
        client = await property_service.create_client(sample_client_data)
        
        # Get some listings
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            limit=5
        )
        
        if listings:
            # Calculate dream score for first listing
            listing_data = listings[0].dict()
            client_data = client.dict()
            
            dream_score = scoring_service.calculate_dream_score(
                listing_data,
                client_data
            )
            
            # Assertions
            assert dream_score is not None, "Dream score should be calculated"
            assert 0 <= dream_score <= 100, "Dream score should be 0-100"

    async def test_ranking_listings(self, property_service, sample_client_data):
        """Test ranking listings by Dream Score."""
        from app.services.property.property_scoring import PropertyScoringService
        
        scoring_service = PropertyScoringService()
        
        # Create client
        client = await property_service.create_client(sample_client_data)
        
        # Get listings
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            limit=10
        )
        
        if len(listings) > 1:
            # Rank listings
            listing_dicts = [l.dict() for l in listings]
            client_dict = client.dict()
            
            ranked = scoring_service.rank_listings(
                listing_dicts,
                client_dict,
                top_n=5
            )
            
            # Assertions
            assert isinstance(ranked, list), "Should return a list"
            assert len(ranked) <= 5, "Should return top 5"
            
            # Verify sorting (highest to lowest)
            if len(ranked) > 1:
                for i in range(len(ranked) - 1):
                    assert ranked[i]["dream_score"] >= ranked[i + 1]["dream_score"], \
                        "Should be sorted by dream score descending"
            
            # Verify rank field
            for i, listing in enumerate(ranked, 1):
                assert listing.get("rank") == i, "Should have rank field"


@pytest.mark.asyncio
class TestPropertyEdgeCases:
    """Test property service edge cases."""

    async def test_search_with_none_parameters(self, property_service):
        """Test search with all None parameters."""
        listings = await property_service.search_listings(limit=10)
        
        assert isinstance(listings, list), "Should return a list"

    async def test_search_with_invalid_price_range(self, property_service):
        """Test search with invalid price range (min > max)."""
        listings = await property_service.search_listings(
            price_min=15000000,
            price_max=5000000,  # min > max
            limit=10
        )
        
        assert isinstance(listings, list), "Should return a list"
        assert len(listings) == 0, "Should return empty for invalid range"

    async def test_search_with_zero_limit(self, property_service):
        """Test search with zero limit."""
        listings = await property_service.search_listings(limit=0)
        
        assert isinstance(listings, list), "Should return a list"
        assert len(listings) == 0, "Should return empty for zero limit"


@pytest.mark.skip(reason="Requires database with sample data")
class TestPropertyServiceIntegration:
    """Full integration tests with actual database."""

    async def test_full_search_and_scoring_workflow(self, property_service, sample_client_data):
        """Test complete workflow: create client -> search -> score -> rank."""
        # 1. Create client
        client = await property_service.create_client(sample_client_data)
        assert client is not None
        
        # 2. Search listings
        listings = await property_service.search_listings(
            deal_type=DealType.buy,
            price_min=client.budget_min,
            price_max=client.budget_max,
            rooms_min=client.rooms_min,
            rooms_max=client.rooms_max,
            limit=10
        )
        assert len(listings) > 0, "Should find listings"
        
        # 3. Score and rank
        from app.services.property.property_scoring import PropertyScoringService
        scoring_service = PropertyScoringService()
        
        ranked = scoring_service.rank_listings(
            [l.dict() for l in listings],
            client.dict(),
            top_n=5
        )
        
        assert len(ranked) > 0, "Should have ranked results"
        assert all("dream_score" in r for r in ranked), "All should have dream_score"
        assert all("rank" in r for r in ranked), "All should have rank"
