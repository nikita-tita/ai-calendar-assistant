"""Pydantic schemas for property search."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class BotMode(str, Enum):
    """Bot operation mode."""
    calendar = "calendar"
    property = "property"


class DealType(str, Enum):
    """Type of real estate deal."""
    rent = "rent"
    buy = "buy"


class TransportMode(str, Enum):
    """Transport mode for route calculation."""
    AUTO = "auto"
    PUBLIC_TRANSPORT = "pt"
    WALK = "walk"


class AnchorPointType(str, Enum):
    """Type of anchor point."""
    WORK = "work"
    KINDERGARTEN = "kindergarten"
    SCHOOL = "school"
    PARENTS = "parents"
    OTHER = "other"


class AnchorPointCreate(BaseModel):
    """Anchor point creation schema."""
    type: AnchorPointType
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    mode: TransportMode = TransportMode.AUTO
    description: Optional[str] = None


class PropertyClientCreate(BaseModel):
    """Schema for creating property client."""
    telegram_user_id: str
    name: Optional[str] = None
    contacts: Optional[Dict[str, str]] = None

    # Must-have filters - Price & Size
    budget_min: Optional[int] = Field(None, ge=0)
    budget_max: Optional[int] = Field(None, ge=0)
    rooms_min: Optional[int] = Field(None, ge=0)
    rooms_max: Optional[int] = Field(None, ge=0)
    area_min: Optional[float] = Field(None, ge=0)
    area_max: Optional[float] = Field(None, ge=0)
    deal_type: Optional[DealType] = None

    # Location preferences
    districts: Optional[List[str]] = None
    metro_stations: Optional[List[str]] = None
    max_metro_distance_minutes: Optional[int] = Field(None, ge=0, le=120)

    # Floor preferences
    floor_min: Optional[int] = Field(None, ge=1)
    floor_max: Optional[int] = Field(None, ge=1)
    requires_elevator: bool = False
    not_first_floor: bool = False
    not_last_floor: bool = False

    # Building preferences
    preferred_building_types: Optional[List[str]] = None  # ["кирпично-монолитный", "панельный"]
    exclude_building_types: Optional[List[str]] = None

    # Condition & Renovation
    preferred_renovations: Optional[List[str]] = None  # ["Без отделки", "Чистовая"]
    exclude_renovations: Optional[List[str]] = None

    # Layout preferences
    balcony_required: Optional[bool] = None
    preferred_balcony_types: Optional[List[str]] = None  # ["лоджия", "терраса"]
    bathroom_type_preference: Optional[str] = None  # "раздельный" или "совмещенный"
    min_ceiling_height: Optional[float] = None

    # Financial preferences
    mortgage_required: Optional[bool] = None
    preferred_payment_methods: Optional[List[str]] = None  # ["Ипотека", "Рассрочка"]

    # Lifestyle filters
    allows_pets: Optional[bool] = None
    allows_kids: Optional[bool] = None

    # For new construction
    handover_date_from: Optional[datetime] = None
    handover_date_to: Optional[datetime] = None
    handover_quarter_min: Optional[int] = Field(None, ge=1, le=4)
    handover_quarter_max: Optional[int] = Field(None, ge=1, le=4)
    handover_year_min: Optional[int] = None
    handover_year_max: Optional[int] = None

    # Developer preferences
    preferred_developers: Optional[List[str]] = None
    exclude_developers: Optional[List[str]] = None

    # Infrastructure priorities
    school_nearby_required: Optional[bool] = None  # Школа в радиусе 1км
    kindergarten_nearby_required: Optional[bool] = None  # Детский сад
    park_nearby_required: Optional[bool] = None  # Парк

    # Taste weights
    taste_weights: Optional[Dict[str, float]] = None

    # Anchor points
    anchor_points: Optional[List[AnchorPointCreate]] = None

    notes: Optional[str] = None

    @validator('budget_max')
    def validate_budget_max(cls, v, values):
        """Validate budget_max >= budget_min."""
        if v is not None and 'budget_min' in values and values['budget_min'] is not None:
            if v < values['budget_min']:
                raise ValueError('budget_max must be >= budget_min')
        return v


class PropertyClientUpdate(BaseModel):
    """Schema for updating property client."""
    name: Optional[str] = None
    contacts: Optional[Dict[str, str]] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    deal_type: Optional[DealType] = None
    districts: Optional[List[str]] = None
    metro_stations: Optional[List[str]] = None
    max_metro_distance_minutes: Optional[int] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    requires_elevator: Optional[bool] = None
    not_first_floor: Optional[bool] = None
    not_last_floor: Optional[bool] = None
    allows_pets: Optional[bool] = None
    allows_kids: Optional[bool] = None
    handover_date_from: Optional[datetime] = None
    handover_date_to: Optional[datetime] = None
    taste_weights: Optional[Dict[str, float]] = None
    anchor_points: Optional[List[AnchorPointCreate]] = None
    notes: Optional[str] = None


class PropertyClientResponse(BaseModel):
    """Schema for property client response."""
    id: str
    telegram_user_id: str
    name: Optional[str] = None
    contacts: Optional[Dict[str, str]] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    area_min: Optional[float] = None
    area_max: Optional[float] = None
    deal_type: Optional[DealType] = None
    districts: Optional[List[str]] = None
    metro_stations: Optional[List[str]] = None
    max_metro_distance_minutes: Optional[int] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    requires_elevator: bool = False
    not_first_floor: bool = False
    not_last_floor: bool = False
    allows_pets: Optional[bool] = None
    allows_kids: Optional[bool] = None
    handover_date_from: Optional[datetime] = None
    handover_date_to: Optional[datetime] = None
    taste_weights: Optional[Dict[str, float]] = None
    anchor_points: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PropertyListingCreate(BaseModel):
    """Schema for creating property listing."""
    title: str
    description: Optional[str] = None
    price: int = Field(..., ge=0)
    deal_type: DealType

    # Category & Type (from feed)
    category: Optional[str] = None  # "квартира", "гараж", "коммерческая"
    property_type: Optional[str] = None  # "жилая", "коммерческая"

    # Location
    address_raw: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    district: Optional[str] = None
    metro_station: Optional[str] = None
    metro_distance_minutes: Optional[int] = Field(None, ge=0)

    # Building Info
    building_name: Optional[str] = None  # Название ЖК
    building_type: Optional[str] = None  # "кирпично-монолитный", "панельный"
    building_state: Optional[str] = None  # "hand-over", "in-progress"
    building_phase: Optional[str] = None  # "Очередь 1"
    building_section: Optional[str] = None  # "Корпус А"
    building_year: Optional[int] = Field(None, ge=1800, le=2100)
    ready_quarter: Optional[int] = Field(None, ge=1, le=4)  # Квартал сдачи

    # Floors
    floor: Optional[int] = Field(None, ge=0)  # 0 для подземных паркингов
    floors_total: Optional[int] = Field(None, ge=1)

    # Areas (m²)
    area_total: Optional[float] = Field(None, ge=0)
    living_area: Optional[float] = Field(None, ge=0)  # Жилая площадь
    kitchen_area: Optional[float] = Field(None, ge=0)  # Площадь кухни

    # Rooms & Layout
    rooms: Optional[int] = Field(None, ge=0)
    balcony_type: Optional[str] = None  # "лоджия", "балкон", "терраса"
    bathroom_count: Optional[int] = Field(None, ge=0)
    bathroom_type: Optional[str] = None  # "раздельный", "совмещенный"

    # Condition & Amenities
    renovation: Optional[str] = None  # "Без отделки", "Черновая", "Чистовая"
    ceiling_height: Optional[float] = Field(None, ge=0)  # Высота потолков (м)
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None

    # Financial
    mortgage_available: Optional[bool] = None
    haggle_allowed: Optional[bool] = None  # Торг
    payment_methods: Optional[List[str]] = None  # ["Ипотека", "Рассрочка"]
    approved_banks: Optional[List[str]] = None

    # Developer
    developer_id: Optional[str] = None
    developer_name: Optional[str] = None
    builder_data: Optional[Dict[str, Any]] = None

    # Images (categorized)
    photos: Optional[List[str]] = None  # Основные фото
    plan_images: Optional[List[str]] = None  # Планировка
    floor_plan_images: Optional[List[str]] = None  # Поэтажный план
    complex_scheme_images: Optional[List[str]] = None  # Схема ЖК

    # Complex Info
    complex_advantages: Optional[List[str]] = None  # Преимущества ЖК
    complex_description: Optional[str] = None

    # Agent/Sales Info
    agent_data: Optional[Dict[str, Any]] = None  # phone, email, organization

    # Enriched Data
    amenities: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    poi_data: Optional[Dict[str, Any]] = None
    vision_data: Optional[Dict[str, Any]] = None

    # Feed Metadata
    source: Optional[str] = None
    external_id: Optional[str] = None
    is_new_flat: bool = True  # Признак новостройки


class PropertyListingResponse(BaseModel):
    """Schema for property listing response."""
    id: str
    title: str
    description: Optional[str] = None
    price: int
    deal_type: DealType

    # Category & Type
    category: Optional[str] = None
    property_type: Optional[str] = None

    # Location
    address_raw: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    district: Optional[str] = None
    metro_station: Optional[str] = None
    metro_distance_minutes: Optional[int] = None

    # Building Info
    building_name: Optional[str] = None
    building_type: Optional[str] = None
    building_state: Optional[str] = None
    building_phase: Optional[str] = None
    building_section: Optional[str] = None
    building_year: Optional[int] = None
    ready_quarter: Optional[int] = None

    # Floors
    floor: Optional[int] = None
    floors_total: Optional[int] = None

    # Areas
    area_total: Optional[float] = None
    living_area: Optional[float] = None
    kitchen_area: Optional[float] = None

    # Rooms & Layout
    rooms: Optional[int] = None
    balcony_type: Optional[str] = None
    bathroom_count: Optional[int] = None
    bathroom_type: Optional[str] = None

    # Condition & Amenities
    renovation: Optional[str] = None
    ceiling_height: Optional[float] = None
    has_elevator: Optional[bool] = None
    has_parking: Optional[bool] = None

    # Financial
    mortgage_available: Optional[bool] = None
    haggle_allowed: Optional[bool] = None
    payment_methods: Optional[List[str]] = None
    approved_banks: Optional[List[str]] = None

    # Developer
    developer_id: Optional[str] = None
    developer_name: Optional[str] = None
    builder_data: Optional[Dict[str, Any]] = None

    # Images (categorized)
    photos: Optional[List[str]] = None
    plan_images: Optional[List[str]] = None
    floor_plan_images: Optional[List[str]] = None
    complex_scheme_images: Optional[List[str]] = None

    # Complex Info
    complex_advantages: Optional[List[str]] = None
    complex_description: Optional[str] = None

    # Agent/Sales Info
    agent_data: Optional[Dict[str, Any]] = None

    # Enriched Data
    amenities: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    poi_data: Optional[Dict[str, Any]] = None
    vision_data: Optional[Dict[str, Any]] = None

    # System fields
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    source: Optional[str] = None
    external_id: Optional[str] = None
    is_new_flat: bool = True

    class Config:
        from_attributes = True


class PropertySelectionCreate(BaseModel):
    """Schema for creating property selection."""
    client_id: str
    agent_telegram_id: Optional[str] = None
    filters_snapshot: Optional[Dict[str, Any]] = None
    taste_weights_snapshot: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class SelectionItemCreate(BaseModel):
    """Schema for creating selection item."""
    listing_id: str
    dream_score: float = Field(..., ge=0, le=100)
    rank: Optional[int] = None
    explanation: Optional[Dict[str, Any]] = None
    agent_note: Optional[str] = None
    status: str = "new"


class SelectionItemResponse(BaseModel):
    """Schema for selection item response."""
    id: str
    selection_id: str
    listing_id: str
    dream_score: float
    rank: Optional[int] = None
    explanation: Optional[Dict[str, Any]] = None
    agent_note: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    listing: Optional[PropertyListingResponse] = None

    class Config:
        from_attributes = True


class PropertySelectionResponse(BaseModel):
    """Schema for property selection response."""
    id: str
    client_id: str
    agent_telegram_id: Optional[str] = None
    filters_snapshot: Optional[Dict[str, Any]] = None
    taste_weights_snapshot: Optional[Dict[str, Any]] = None
    share_token: Optional[str] = None
    share_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None
    items: Optional[List[SelectionItemResponse]] = None

    class Config:
        from_attributes = True


class SelectionFeedbackCreate(BaseModel):
    """Schema for creating selection feedback."""
    selection_id: str
    listing_id: str
    client_telegram_id: str
    feedback_type: str = Field(..., pattern="^(like|dislike|comment)$")
    comment: Optional[str] = None


class SelectionFeedbackResponse(BaseModel):
    """Schema for selection feedback response."""
    id: str
    selection_id: str
    listing_id: str
    client_telegram_id: str
    feedback_type: str
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserBotModeUpdate(BaseModel):
    """Schema for updating user bot mode."""
    current_mode: BotMode
    active_client_id: Optional[str] = None


class UserBotModeResponse(BaseModel):
    """Schema for user bot mode response."""
    telegram_user_id: str
    current_mode: BotMode
    active_client_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PropertySearchFilters(BaseModel):
    """Schema for property search filters (from user message)."""
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    rooms: Optional[int] = None
    area_min: Optional[float] = None
    deal_type: Optional[DealType] = None
    districts: Optional[List[str]] = None
    metro_stations: Optional[List[str]] = None
    max_metro_distance: Optional[int] = None
    raw_text: str  # Original user message


class PropertySearchIntent(BaseModel):
    """Schema for property search intent (extracted by LLM)."""
    intent_type: str  # start_search, refine_filters, show_selection, like, dislike, etc.
    filters: Optional[PropertySearchFilters] = None
    listing_id: Optional[str] = None
    feedback: Optional[str] = None
    clarify_question: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
