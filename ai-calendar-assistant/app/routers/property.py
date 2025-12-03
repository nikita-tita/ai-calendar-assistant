"""Property search API router."""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import structlog

from app.schemas.property import (
    PropertyClientCreate,
    PropertyClientUpdate,
    PropertyClientResponse,
    PropertyListingCreate,
    PropertyListingResponse,
    PropertySelectionCreate,
    PropertySelectionResponse,
    SelectionItemCreate,
    SelectionFeedbackCreate,
    DealType,
)
from app.services.property.property_service import property_service
from app.services.property.property_scoring import property_scoring_service

logger = structlog.get_logger()

router = APIRouter(prefix="/property", tags=["property"])


# ==================== Client Endpoints ====================

@router.post("/clients", response_model=PropertyClientResponse)
async def create_client(client_data: PropertyClientCreate):
    """Create new property client."""
    try:
        client = await property_service.create_client(client_data)
        return client
    except Exception as e:
        logger.error("create_client_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/telegram/{telegram_user_id}", response_model=PropertyClientResponse)
async def get_client_by_telegram_id(telegram_user_id: str):
    """Get client by Telegram user ID."""
    client = await property_service.get_client_by_telegram_id(telegram_user_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get("/clients/{client_id}", response_model=PropertyClientResponse)
async def get_client(client_id: str):
    """Get client by ID."""
    client = await property_service.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.patch("/clients/{client_id}", response_model=PropertyClientResponse)
async def update_client(client_id: str, client_data: PropertyClientUpdate):
    """Update client data."""
    client = await property_service.update_client(client_id, client_data)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


# ==================== Listing Endpoints ====================

@router.post("/listings", response_model=PropertyListingResponse)
async def create_listing(listing_data: PropertyListingCreate):
    """Create new property listing."""
    try:
        listing = await property_service.create_listing(listing_data)
        return listing
    except Exception as e:
        logger.error("create_listing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}", response_model=PropertyListingResponse)
async def get_listing(listing_id: str):
    """Get listing by ID."""
    listing = await property_service.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.get("/listings", response_model=List[PropertyListingResponse])
async def search_listings(
    deal_type: Optional[DealType] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    rooms_min: Optional[int] = None,
    rooms_max: Optional[int] = None,
    area_min: Optional[float] = None,
    area_max: Optional[float] = None,
    districts: Optional[str] = Query(None, description="Comma-separated list of districts"),
    metro_stations: Optional[str] = Query(None, description="Comma-separated list of metro stations"),
    floor_min: Optional[int] = None,
    floor_max: Optional[int] = None,
    limit: int = Query(100, le=500)
):
    """Search listings with filters."""
    # Parse comma-separated lists
    districts_list = districts.split(",") if districts else None
    metro_stations_list = metro_stations.split(",") if metro_stations else None

    listings = await property_service.search_listings(
        deal_type=deal_type,
        price_min=price_min,
        price_max=price_max,
        rooms_min=rooms_min,
        rooms_max=rooms_max,
        area_min=area_min,
        area_max=area_max,
        districts=districts_list,
        metro_stations=metro_stations_list,
        floor_min=floor_min,
        floor_max=floor_max,
        limit=limit
    )
    return listings


# ==================== Selection Endpoints ====================

@router.post("/selections", response_model=dict)
async def create_selection(selection_data: PropertySelectionCreate):
    """Create new property selection."""
    try:
        selection_id = await property_service.create_selection(selection_data)
        return {"selection_id": selection_id, "status": "created"}
    except Exception as e:
        logger.error("create_selection_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/selections/{selection_id}/items", response_model=dict)
async def add_selection_item(selection_id: str, item_data: SelectionItemCreate):
    """Add item to selection."""
    try:
        item_id = await property_service.add_selection_item(selection_id, item_data)
        return {"item_id": item_id, "status": "added"}
    except Exception as e:
        logger.error("add_selection_item_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selections/{selection_id}")
async def get_selection(selection_id: str, include_items: bool = True):
    """Get selection by ID."""
    selection = await property_service.get_selection(selection_id, include_items=include_items)
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")
    return selection


@router.get("/selections/token/{share_token}")
async def get_selection_by_token(share_token: str):
    """Get selection by share token (public access)."""
    selection = await property_service.get_selection_by_token(share_token)
    if not selection:
        raise HTTPException(status_code=404, detail="Selection not found")
    return selection


# ==================== Feedback Endpoints ====================

@router.post("/feedback", response_model=dict)
async def add_feedback(feedback_data: SelectionFeedbackCreate):
    """Add feedback to selection item."""
    try:
        feedback_id = await property_service.add_feedback(feedback_data)
        return {"feedback_id": feedback_id, "status": "added"}
    except Exception as e:
        logger.error("add_feedback_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selections/{selection_id}/feedback")
async def get_selection_feedback(selection_id: str):
    """Get all feedback for a selection."""
    feedback = await property_service.get_selection_feedback(selection_id)
    return {"feedback": feedback}


# ==================== Scoring & Ranking Endpoints ====================

@router.post("/score")
async def score_listing(
    listing_id: str,
    client_id: str
):
    """Calculate Dream Score for a listing."""
    try:
        # Get listing and client
        listing = await property_service.get_listing(listing_id)
        if not listing:
            raise HTTPException(status_code=404, detail="Listing not found")

        client = await property_service.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Calculate score
        score = property_scoring_service.calculate_dream_score(
            listing.dict(),
            client.dict()
        )

        # Generate explanation
        explanation = property_scoring_service.generate_explanation(
            listing.dict(),
            client.dict(),
            score
        )

        return {
            "listing_id": listing_id,
            "client_id": client_id,
            "dream_score": score,
            "explanation": explanation
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("score_listing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank")
async def rank_listings(
    client_id: str,
    listing_ids: List[str],
    top_n: int = 20
):
    """Rank multiple listings for a client."""
    try:
        # Get client
        client = await property_service.get_client(client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Get all listings
        listings = []
        for listing_id in listing_ids:
            listing = await property_service.get_listing(listing_id)
            if listing:
                listings.append(listing.dict())

        if not listings:
            raise HTTPException(status_code=404, detail="No listings found")

        # Rank listings
        ranked = property_scoring_service.rank_listings(
            listings,
            client.dict(),
            top_n=top_n
        )

        return {
            "client_id": client_id,
            "total_listings": len(listings),
            "top_n": len(ranked),
            "ranked_listings": ranked
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("rank_listings_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Testing & Debugging Endpoints ====================

@router.get("/search-results/{user_id}")
async def get_user_search_results(user_id: int):
    """Get search results for a specific user (for testing)."""
    try:
        # Get client by telegram ID
        client = await property_service.get_client_by_telegram_id(str(user_id))

        if not client:
            return {
                "user_id": user_id,
                "results": [],
                "message": "No client found for this user"
            }

        # Get latest selection for this client
        # This is a simplified version - you may need to implement this
        return {
            "user_id": user_id,
            "client_id": client.id,
            "results": [],
            "message": "Results fetching not yet implemented"
        }

    except Exception as e:
        logger.error("get_search_results_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user-context/{user_id}")
async def get_user_context(user_id: int):
    """Get conversation context for a user (for testing)."""
    try:
        from app.services.property.search_service import PropertySearchService

        search_service = PropertySearchService()
        context = search_service.get_user_context(user_id)

        if not context:
            return {
                "user_id": user_id,
                "context": None,
                "message": "No context found for this user"
            }

        return {
            "user_id": user_id,
            "context": context
        }

    except Exception as e:
        logger.error("get_user_context_error", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Status Endpoint ====================

@router.get("/status")
async def get_status():
    """Get property service status."""
    return {
        "status": "ok",
        "service": "property_search",
        "version": "1.0.0"
    }
