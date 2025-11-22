"""Property search service for real estate bot."""

import uuid
import secrets
from urllib.parse import quote_plus
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, and_, or_, cast, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import structlog

from app.config import settings
from app.models.property import (
    Base,
    PropertyClient,
    PropertyListing,
    PropertySelection,
    SelectionItem,
    SelectionFeedback,
    UserBotMode,
    BotMode,
    DealType
)
from app.schemas.property import (
    PropertyClientCreate,
    PropertyClientUpdate,
    PropertyClientResponse,
    PropertyListingCreate,
    PropertyListingResponse,
    PropertySelectionCreate,
    SelectionItemCreate,
    SelectionFeedbackCreate,
    UserBotModeUpdate,
)

logger = structlog.get_logger()


class PropertyService:
    """Service for property search operations."""
    
    def __init__(self):
        """Initialize property service with database connection."""
        # Получаем компоненты базы данных из настроек
        db_user = settings.db_user
        db_password = settings.db_password
        db_host = settings.db_host
        db_port = settings.db_port
        db_name = settings.db_name
        
        # Проверяем, что все компоненты заданы
        if not all([db_user, db_password, db_host, db_port, db_name]):
            missing = []
            if not db_user: missing.append("DB_USER")
            if not db_password: missing.append("DB_PASSWORD") 
            if not db_host: missing.append("DB_HOST")
            if not db_port: missing.append("DB_PORT")
            if not db_name: missing.append("DB_NAME")
            raise ValueError(f"Missing database configuration: {', '.join(missing)}")
        
        # Создаем URL для подключения
        encoded_password = quote_plus(db_password)
        self.database_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
        
        # Отладочный вывод
        logger.info("database_connection_details",
                   db_user=db_user,
                   db_host=db_host,
                   db_port=db_port,
                   db_name=db_name,
                   password_length=len(db_password))
        
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Создаем таблицы
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("property_service_initialized", 
                       database_url=f"postgresql://{db_user}:****@{db_host}:{db_port}/{db_name}")
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    # ==================== Client Operations ====================

    async def create_client(self, client_data: PropertyClientCreate) -> PropertyClientResponse:
        """Create new property client with all preferences."""
        session = self.get_session()
        try:
            # Prepare client data dict
            client_dict = client_data.dict(exclude_unset=True)

            # Handle anchor_points conversion
            if "anchor_points" in client_dict and client_dict["anchor_points"]:
                client_dict["anchor_points"] = [point.dict() for point in client_data.anchor_points]

            client = PropertyClient(
                id=str(uuid.uuid4()),
                **client_dict
            )

            session.add(client)
            session.commit()
            session.refresh(client)

            logger.info("client_created",
                       client_id=client.id,
                       telegram_user_id=client.telegram_user_id,
                       has_building_prefs=bool(client_dict.get("preferred_building_types")),
                       has_renovation_prefs=bool(client_dict.get("preferred_renovations")),
                       mortgage_required=client_dict.get("mortgage_required"))

            return PropertyClientResponse.from_orm(client)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("client_creation_error", error=str(e))
            raise
        finally:
            session.close()

    async def get_client_by_telegram_id(self, telegram_user_id: str) -> Optional[PropertyClientResponse]:
        """Get client by Telegram user ID."""
        session = self.get_session()
        try:
            client = session.query(PropertyClient).filter(
                PropertyClient.telegram_user_id == telegram_user_id
            ).first()

            if not client:
                return None

            return PropertyClientResponse.from_orm(client)

        finally:
            session.close()

    async def get_client(self, client_id: str) -> Optional[PropertyClientResponse]:
        """Get client by ID."""
        session = self.get_session()
        try:
            client = session.query(PropertyClient).filter(PropertyClient.id == client_id).first()

            if not client:
                return None

            return PropertyClientResponse.from_orm(client)

        finally:
            session.close()

    async def update_client(self, client_id: str, client_data: PropertyClientUpdate) -> Optional[PropertyClientResponse]:
        """Update client data."""
        session = self.get_session()
        try:
            client = session.query(PropertyClient).filter(PropertyClient.id == client_id).first()

            if not client:
                return None

            # Update fields
            update_data = client_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == "anchor_points" and value is not None:
                    value = [point.dict() for point in value]
                setattr(client, field, value)

            client.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(client)

            logger.info("client_updated", client_id=client_id)

            return PropertyClientResponse.from_orm(client)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("client_update_error", error=str(e), client_id=client_id)
            raise
        finally:
            session.close()

    # ==================== Listing Operations ====================

    async def create_listing(self, listing_data: PropertyListingCreate) -> PropertyListingResponse:
        """Create new property listing."""
        session = self.get_session()
        try:
            listing = PropertyListing(
                id=str(uuid.uuid4()),
                **listing_data.dict()
            )

            session.add(listing)
            session.commit()
            session.refresh(listing)

            logger.info("listing_created", listing_id=listing.id, title=listing.title)

            return PropertyListingResponse.from_orm(listing)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("listing_creation_error", error=str(e))
            raise
        finally:
            session.close()

    async def get_listing(self, listing_id: str) -> Optional[PropertyListingResponse]:
        """Get listing by ID."""
        session = self.get_session()
        try:
            listing = session.query(PropertyListing).filter(PropertyListing.id == listing_id).first()

            if not listing:
                return None

            return PropertyListingResponse.from_orm(listing)

        finally:
            session.close()

    async def get_listing_by_external_id(self, external_id: str) -> Optional[PropertyListingResponse]:
        """Get listing by external ID (from feed)."""
        session = self.get_session()
        try:
            listing = session.query(PropertyListing).filter(
                PropertyListing.external_id == external_id
            ).first()

            if not listing:
                return None

            return PropertyListingResponse.from_orm(listing)

        finally:
            session.close()

    async def update_listing(self, listing_id: str, listing_data: PropertyListingCreate) -> Optional[PropertyListingResponse]:
        """Update existing listing."""
        session = self.get_session()
        try:
            listing = session.query(PropertyListing).filter(PropertyListing.id == listing_id).first()

            if not listing:
                return None

            # Update fields
            update_data = listing_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(listing, field, value)

            listing.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(listing)

            logger.info("listing_updated", listing_id=listing_id, external_id=listing.external_id)

            return PropertyListingResponse.from_orm(listing)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("listing_update_error", error=str(e), listing_id=listing_id)
            raise
        finally:
            session.close()

    async def search_listings(
        self,
        # Basic filters (existing)
        deal_type: Optional[DealType] = None,
        price_min: Optional[int] = None,
        price_max: Optional[int] = None,
        rooms_min: Optional[int] = None,
        rooms_max: Optional[int] = None,
        area_min: Optional[float] = None,
        area_max: Optional[float] = None,
        districts: Optional[List[str]] = None,
        metro_stations: Optional[List[str]] = None,
        floor_min: Optional[int] = None,
        floor_max: Optional[int] = None,

        # NEW: Category and type filters
        category: Optional[str] = "квартира",
        property_type: Optional[str] = None,

        # NEW: Building filters
        building_types: Optional[List[str]] = None,
        exclude_building_types: Optional[List[str]] = None,
        building_name: Optional[str] = None,

        # NEW: Renovation filters
        renovations: Optional[List[str]] = None,
        exclude_renovations: Optional[List[str]] = None,

        # NEW: Layout filters
        balcony_required: Optional[bool] = None,
        balcony_types: Optional[List[str]] = None,
        bathroom_type: Optional[str] = None,
        bathroom_count_min: Optional[int] = None,
        min_ceiling_height: Optional[float] = None,

        # NEW: Amenity filters
        requires_elevator: Optional[bool] = None,
        has_parking: Optional[bool] = None,

        # NEW: Financial filters
        mortgage_required: Optional[bool] = None,
        payment_methods: Optional[List[str]] = None,
        haggle_allowed: Optional[bool] = None,

        # NEW: Handover date filters
        handover_quarter_min: Optional[int] = None,
        handover_quarter_max: Optional[int] = None,
        handover_year_min: Optional[int] = None,
        handover_year_max: Optional[int] = None,

        # NEW: Developer filters
        developers: Optional[List[str]] = None,
        exclude_developers: Optional[List[str]] = None,

        # NEW: Area detail filters
        living_area_min: Optional[float] = None,
        living_area_max: Optional[float] = None,
        kitchen_area_min: Optional[float] = None,
        kitchen_area_max: Optional[float] = None,

        # NEW: POI filters (requires poi_data populated)
        school_nearby: Optional[bool] = None,
        kindergarten_nearby: Optional[bool] = None,
        park_nearby: Optional[bool] = None,

        limit: int = 100
    ) -> List[PropertyListingResponse]:
        """
        Search listings with comprehensive filters.
        """
        session = self.get_session()
        try:
            query = session.query(PropertyListing).filter(PropertyListing.is_active == True)

            # Basic filters (existing)
            if deal_type:
                query = query.filter(PropertyListing.deal_type == deal_type)

            if price_min is not None:
                query = query.filter(PropertyListing.price >= price_min)

            if price_max is not None:
                query = query.filter(PropertyListing.price <= price_max)

            if rooms_min is not None:
                query = query.filter(PropertyListing.rooms >= rooms_min)

            if rooms_max is not None:
                query = query.filter(PropertyListing.rooms <= rooms_max)

            if area_min is not None:
                query = query.filter(PropertyListing.area_total >= area_min)

            if area_max is not None:
                query = query.filter(PropertyListing.area_total <= area_max)

            if districts:
                query = query.filter(PropertyListing.district.in_(districts))

            if metro_stations:
                query = query.filter(PropertyListing.metro_station.in_(metro_stations))

            if floor_min is not None:
                query = query.filter(PropertyListing.floor >= floor_min)

            if floor_max is not None:
                query = query.filter(PropertyListing.floor <= floor_max)

            # NEW: Category filters
            if category:
                query = query.filter(PropertyListing.category == category)

            if property_type:
                query = query.filter(PropertyListing.property_type == property_type)

            # NEW: Building filters
            if building_types:
                query = query.filter(PropertyListing.building_type.in_(building_types))

            if exclude_building_types:
                query = query.filter(~PropertyListing.building_type.in_(exclude_building_types))

            if building_name:
                # Fuzzy search with ILIKE (case-insensitive)
                query = query.filter(PropertyListing.building_name.ilike(f"%{building_name}%"))

            # NEW: Renovation filters
            if renovations:
                query = query.filter(PropertyListing.renovation.in_(renovations))

            if exclude_renovations:
                query = query.filter(~PropertyListing.renovation.in_(exclude_renovations))

            # NEW: Layout filters
            if balcony_required is not None:
                if balcony_required:
                    query = query.filter(PropertyListing.balcony_type.isnot(None))
                else:
                    query = query.filter(PropertyListing.balcony_type.is_(None))

            if balcony_types:
                query = query.filter(PropertyListing.balcony_type.in_(balcony_types))

            if bathroom_type:
                query = query.filter(PropertyListing.bathroom_type == bathroom_type)

            if bathroom_count_min is not None:
                query = query.filter(PropertyListing.bathroom_count >= bathroom_count_min)

            if min_ceiling_height is not None:
                query = query.filter(PropertyListing.ceiling_height >= min_ceiling_height)

            # NEW: Amenity filters
            if requires_elevator is not None:
                query = query.filter(PropertyListing.has_elevator == requires_elevator)

            if has_parking is not None:
                query = query.filter(PropertyListing.has_parking == has_parking)

            # NEW: Financial filters
            if mortgage_required is not None:
                query = query.filter(PropertyListing.mortgage_available == mortgage_required)

            if payment_methods:
                # JSONB contains check for any of the specified payment methods
                for method in payment_methods:
                    query = query.filter(
                        cast(PropertyListing.payment_methods, JSONB).contains([method])
                    )

            if haggle_allowed is not None:
                query = query.filter(PropertyListing.haggle_allowed == haggle_allowed)

            # NEW: Handover date filters
            if handover_quarter_min is not None:
                query = query.filter(PropertyListing.ready_quarter >= handover_quarter_min)

            if handover_quarter_max is not None:
                query = query.filter(PropertyListing.ready_quarter <= handover_quarter_max)

            if handover_year_min is not None:
                query = query.filter(PropertyListing.building_year >= handover_year_min)

            if handover_year_max is not None:
                query = query.filter(PropertyListing.building_year <= handover_year_max)

            # NEW: Developer filters
            if developers:
                query = query.filter(PropertyListing.developer_name.in_(developers))

            if exclude_developers:
                query = query.filter(~PropertyListing.developer_name.in_(exclude_developers))

            # NEW: Area detail filters
            if living_area_min is not None:
                query = query.filter(PropertyListing.living_area >= living_area_min)

            if living_area_max is not None:
                query = query.filter(PropertyListing.living_area <= living_area_max)

            if kitchen_area_min is not None:
                query = query.filter(PropertyListing.kitchen_area >= kitchen_area_min)

            if kitchen_area_max is not None:
                query = query.filter(PropertyListing.kitchen_area <= kitchen_area_max)

            # NEW: POI filters (requires poi_data to be populated)
            if school_nearby is not None:
                # Assumes poi_data JSONB field with structure: {"school": {"nearby": true}}
                if school_nearby:
                    query = query.filter(
                        cast(PropertyListing.poi_data, JSONB)['school']['nearby'].astext.cast(Boolean) == True
                    )

            if kindergarten_nearby is not None:
                if kindergarten_nearby:
                    query = query.filter(
                        cast(PropertyListing.poi_data, JSONB)['kindergarten']['nearby'].astext.cast(Boolean) == True
                    )

            if park_nearby is not None:
                if park_nearby:
                    query = query.filter(
                        cast(PropertyListing.poi_data, JSONB)['park']['nearby'].astext.cast(Boolean) == True
                    )

            listings = query.limit(limit).all()

            logger.info("listings_searched",
                       count=len(listings),
                       filters_applied={
                           "category": category,
                           "building_types": building_types,
                           "renovations": renovations,
                           "mortgage_required": mortgage_required,
                           "price_range": f"{price_min}-{price_max}" if price_min or price_max else None
                       })

            return [PropertyListingResponse.from_orm(listing) for listing in listings]

        finally:
            session.close()

    async def get_db_stats(
        self,
        deal_type: Optional[DealType] = None,
        rooms_min: Optional[int] = None,
        rooms_max: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get database statistics to show user what's available."""
        session = self.get_session()
        try:
            from sqlalchemy import func

            query = session.query(PropertyListing).filter(PropertyListing.is_active == True)

            if deal_type:
                query = query.filter(PropertyListing.deal_type == deal_type)

            if rooms_min is not None:
                query = query.filter(PropertyListing.rooms >= rooms_min)

            if rooms_max is not None:
                query = query.filter(PropertyListing.rooms <= rooms_max)

            # Get total count
            total_count = query.count()

            if total_count == 0:
                return {"total_count": 0}

            # Get price range
            price_stats = session.query(
                func.min(PropertyListing.price).label('min_price'),
                func.max(PropertyListing.price).label('max_price')
            ).filter(PropertyListing.is_active == True)

            if deal_type:
                price_stats = price_stats.filter(PropertyListing.deal_type == deal_type)

            if rooms_min is not None:
                price_stats = price_stats.filter(PropertyListing.rooms >= rooms_min)

            if rooms_max is not None:
                price_stats = price_stats.filter(PropertyListing.rooms <= rooms_max)

            price_result = price_stats.first()

            # Get area range
            area_stats = session.query(
                func.min(PropertyListing.area_total).label('min_area'),
                func.max(PropertyListing.area_total).label('max_area')
            ).filter(PropertyListing.is_active == True)

            if deal_type:
                area_stats = area_stats.filter(PropertyListing.deal_type == deal_type)

            if rooms_min is not None:
                area_stats = area_stats.filter(PropertyListing.rooms >= rooms_min)

            if rooms_max is not None:
                area_stats = area_stats.filter(PropertyListing.rooms <= rooms_max)

            area_result = area_stats.first()

            # Get distinct districts
            districts_query = session.query(PropertyListing.district).filter(
                PropertyListing.is_active == True,
                PropertyListing.district.isnot(None)
            ).distinct()

            if deal_type:
                districts_query = districts_query.filter(PropertyListing.deal_type == deal_type)

            if rooms_min is not None:
                districts_query = districts_query.filter(PropertyListing.rooms >= rooms_min)

            if rooms_max is not None:
                districts_query = districts_query.filter(PropertyListing.rooms <= rooms_max)

            districts = [d[0] for d in districts_query.all() if d[0]]

            return {
                "total_count": total_count,
                "price_range": {
                    "min": price_result.min_price if price_result else None,
                    "max": price_result.max_price if price_result else None
                },
                "area_range": {
                    "min": area_result.min_area if area_result else None,
                    "max": area_result.max_area if area_result else None
                },
                "districts": districts
            }

        finally:
            session.close()

    # ==================== Selection Operations ====================

    async def create_selection(
        self,
        selection_data: PropertySelectionCreate
    ) -> str:
        """Create new property selection."""
        session = self.get_session()
        try:
            # Generate share token
            share_token = secrets.token_urlsafe(32)
            share_url = f"https://этонесамыйдлинныйдомен.рф/property/selection/{share_token}"

            selection = PropertySelection(
                id=str(uuid.uuid4()),
                client_id=selection_data.client_id,
                agent_telegram_id=selection_data.agent_telegram_id,
                filters_snapshot=selection_data.filters_snapshot,
                taste_weights_snapshot=selection_data.taste_weights_snapshot,
                share_token=share_token,
                share_url=share_url,
                notes=selection_data.notes
            )

            session.add(selection)
            session.commit()
            session.refresh(selection)

            logger.info("selection_created", selection_id=selection.id, client_id=selection.client_id)

            return selection.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("selection_creation_error", error=str(e))
            raise
        finally:
            session.close()

    async def add_selection_item(
        self,
        selection_id: str,
        item_data: SelectionItemCreate
    ) -> str:
        """Add item to selection."""
        session = self.get_session()
        try:
            item = SelectionItem(
                id=str(uuid.uuid4()),
                selection_id=selection_id,
                listing_id=item_data.listing_id,
                dream_score=item_data.dream_score,
                rank=item_data.rank,
                explanation=item_data.explanation,
                agent_note=item_data.agent_note,
                status=item_data.status
            )

            session.add(item)
            session.commit()
            session.refresh(item)

            logger.info("selection_item_added", item_id=item.id, selection_id=selection_id)

            return item.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("selection_item_add_error", error=str(e))
            raise
        finally:
            session.close()

    async def get_selection(self, selection_id: str, include_items: bool = True) -> Optional[Dict[str, Any]]:
        """Get selection by ID with optional items."""
        session = self.get_session()
        try:
            selection = session.query(PropertySelection).filter(
                PropertySelection.id == selection_id
            ).first()

            if not selection:
                return None

            result = {
                "id": selection.id,
                "client_id": selection.client_id,
                "agent_telegram_id": selection.agent_telegram_id,
                "filters_snapshot": selection.filters_snapshot,
                "taste_weights_snapshot": selection.taste_weights_snapshot,
                "share_token": selection.share_token,
                "share_url": selection.share_url,
                "created_at": selection.created_at,
                "updated_at": selection.updated_at,
                "notes": selection.notes,
                "items": []
            }

            if include_items:
                items = session.query(SelectionItem).filter(
                    SelectionItem.selection_id == selection_id
                ).order_by(SelectionItem.rank).all()

                for item in items:
                    listing = session.query(PropertyListing).filter(
                        PropertyListing.id == item.listing_id
                    ).first()

                    result["items"].append({
                        "id": item.id,
                        "listing_id": item.listing_id,
                        "dream_score": item.dream_score,
                        "rank": item.rank,
                        "explanation": item.explanation,
                        "agent_note": item.agent_note,
                        "status": item.status,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                        "listing": PropertyListingResponse.from_orm(listing).dict() if listing else None
                    })

            return result

        finally:
            session.close()

    async def get_selection_by_token(self, share_token: str) -> Optional[Dict[str, Any]]:
        """Get selection by share token."""
        session = self.get_session()
        try:
            selection = session.query(PropertySelection).filter(
                PropertySelection.share_token == share_token
            ).first()

            if not selection:
                return None

            return await self.get_selection(selection.id, include_items=True)

        finally:
            session.close()

    # ==================== Feedback Operations ====================

    async def add_feedback(self, feedback_data: SelectionFeedbackCreate) -> str:
        """Add feedback to selection item."""
        session = self.get_session()
        try:
            feedback = SelectionFeedback(
                id=str(uuid.uuid4()),
                selection_id=feedback_data.selection_id,
                listing_id=feedback_data.listing_id,
                client_telegram_id=feedback_data.client_telegram_id,
                feedback_type=feedback_data.feedback_type,
                comment=feedback_data.comment
            )

            session.add(feedback)
            session.commit()
            session.refresh(feedback)

            logger.info("feedback_added",
                       feedback_id=feedback.id,
                       selection_id=feedback.selection_id,
                       feedback_type=feedback.feedback_type)

            return feedback.id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("feedback_add_error", error=str(e))
            raise
        finally:
            session.close()

    async def get_selection_feedback(self, selection_id: str) -> List[Dict[str, Any]]:
        """Get all feedback for a selection."""
        session = self.get_session()
        try:
            feedback_items = session.query(SelectionFeedback).filter(
                SelectionFeedback.selection_id == selection_id
            ).order_by(SelectionFeedback.created_at.desc()).all()

            return [
                {
                    "id": f.id,
                    "listing_id": f.listing_id,
                    "client_telegram_id": f.client_telegram_id,
                    "feedback_type": f.feedback_type,
                    "comment": f.comment,
                    "created_at": f.created_at
                }
                for f in feedback_items
            ]

        finally:
            session.close()

    # ==================== Bot Mode Operations ====================

    async def get_user_mode(self, telegram_user_id: str) -> BotMode:
        """Get user's current bot mode."""
        session = self.get_session()
        try:
            user_mode = session.query(UserBotMode).filter(
                UserBotMode.telegram_user_id == telegram_user_id
            ).first()

            if not user_mode:
                # Default to calendar mode
                return BotMode.calendar

            return user_mode.current_mode

        finally:
            session.close()

    async def set_user_mode(self, telegram_user_id: str, mode: BotMode, client_id: Optional[str] = None) -> None:
        """Set user's bot mode."""
        session = self.get_session()
        try:
            user_mode = session.query(UserBotMode).filter(
                UserBotMode.telegram_user_id == telegram_user_id
            ).first()

            if user_mode:
                user_mode.current_mode = mode
                user_mode.active_client_id = client_id
                user_mode.updated_at = datetime.utcnow()
            else:
                user_mode = UserBotMode(
                    telegram_user_id=telegram_user_id,
                    current_mode=mode,
                    active_client_id=client_id
                )
                session.add(user_mode)

            session.commit()

            logger.info("user_mode_set",
                       telegram_user_id=telegram_user_id,
                       mode=mode.value,
                       client_id=client_id)

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("user_mode_set_error", error=str(e), telegram_user_id=telegram_user_id)
            raise
        finally:
            session.close()

    async def get_active_client_id(self, telegram_user_id: str) -> Optional[str]:
        """Get user's active client ID."""
        session = self.get_session()
        try:
            user_mode = session.query(UserBotMode).filter(
                UserBotMode.telegram_user_id == telegram_user_id
            ).first()

            if not user_mode:
                return None

            return user_mode.active_client_id

        finally:
            session.close()


property_service = PropertyService()