"""Property search models for real estate bot."""

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

Base = declarative_base()


class BotMode(str, Enum):
    """Bot operation mode."""
    calendar = "calendar"
    property = "property"


class DealType(str, Enum):
    """Type of real estate deal."""
    rent = "rent"
    buy = "buy"


class RecurrenceType(str, Enum):
    """Type of recurrence for events."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class PropertyClient(Base):
    """Property search client profile."""

    __tablename__ = "property_clients"

    id = Column(String, primary_key=True)  # UUID
    telegram_user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    contacts = Column(JSON, nullable=True)  # {"phone": "", "email": ""}

    # Must-have filters - Price & Size
    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)
    rooms_min = Column(Integer, nullable=True)
    rooms_max = Column(Integer, nullable=True)
    area_min = Column(Float, nullable=True)
    area_max = Column(Float, nullable=True)
    deal_type = Column(SQLEnum(DealType), nullable=True)

    # Location preferences
    districts = Column(JSON, nullable=True)  # List of districts
    metro_stations = Column(JSON, nullable=True)  # List of metro stations
    max_metro_distance_minutes = Column(Integer, nullable=True)

    # Floor preferences
    floor_min = Column(Integer, nullable=True)
    floor_max = Column(Integer, nullable=True)
    requires_elevator = Column(Boolean, default=False)
    not_first_floor = Column(Boolean, default=False)
    not_last_floor = Column(Boolean, default=False)

    # Building preferences
    preferred_building_types = Column(JSON, nullable=True)  # ["кирпично-монолитный", "панельный"]
    exclude_building_types = Column(JSON, nullable=True)

    # Condition & Renovation
    preferred_renovations = Column(JSON, nullable=True)  # ["Без отделки", "Чистовая"]
    exclude_renovations = Column(JSON, nullable=True)

    # Layout preferences
    balcony_required = Column(Boolean, nullable=True)
    preferred_balcony_types = Column(JSON, nullable=True)  # ["лоджия", "терраса"]
    bathroom_type_preference = Column(String, nullable=True)  # "раздельный" или "совмещенный"
    min_ceiling_height = Column(Float, nullable=True)

    # Financial preferences
    mortgage_required = Column(Boolean, nullable=True)
    preferred_payment_methods = Column(JSON, nullable=True)  # ["Ипотека", "Рассрочка"]

    # Lifestyle filters
    allows_pets = Column(Boolean, nullable=True)
    allows_kids = Column(Boolean, nullable=True)

    # For new construction
    handover_date_from = Column(DateTime, nullable=True)
    handover_date_to = Column(DateTime, nullable=True)
    handover_quarter_min = Column(Integer, nullable=True)  # 1-4
    handover_quarter_max = Column(Integer, nullable=True)  # 1-4
    handover_year_min = Column(Integer, nullable=True)
    handover_year_max = Column(Integer, nullable=True)

    # Developer preferences
    preferred_developers = Column(JSON, nullable=True)
    exclude_developers = Column(JSON, nullable=True)

    # Infrastructure priorities
    school_nearby_required = Column(Boolean, nullable=True)
    kindergarten_nearby_required = Column(Boolean, nullable=True)
    park_nearby_required = Column(Boolean, nullable=True)

    # Taste weights (вкусовые предпочтения) - JSON object with weights
    taste_weights = Column(JSON, nullable=True)
    # Example: {"location": 0.35, "transport": 0.15, "light": 0.10, ...}

    # Anchor points (важные места)
    anchor_points = Column(JSON, nullable=True)
    # Example: [{"type": "work", "lat": 55.75, "lon": 37.62, "mode": "auto"}]

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    selections = relationship("PropertySelection", back_populates="client", cascade="all, delete-orphan")


class PropertyListing(Base):
    """Property listing (квартира/объект)."""

    __tablename__ = "property_listings"

    id = Column(String, primary_key=True)  # UUID or external ID

    # Basic info
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)
    deal_type = Column(SQLEnum(DealType), nullable=False)

    # Category & Type (from feed)
    category = Column(String, nullable=True, index=True)  # "квартира", "гараж", "коммерческая"
    property_type = Column(String, nullable=True)  # "жилая", "коммерческая"

    # Location
    address_raw = Column(String, nullable=True)
    lat = Column(Float, nullable=True, index=True)
    lon = Column(Float, nullable=True, index=True)
    district = Column(String, nullable=True, index=True)
    metro_station = Column(String, nullable=True, index=True)
    metro_distance_minutes = Column(Integer, nullable=True)

    # Building Info
    building_name = Column(String, nullable=True, index=True)  # Название ЖК
    building_type = Column(String, nullable=True)  # "кирпично-монолитный", "панельный"
    building_state = Column(String, nullable=True)  # "hand-over", "in-progress"
    building_phase = Column(String, nullable=True)  # "Очередь 1"
    building_section = Column(String, nullable=True)  # "Корпус А"
    building_year = Column(Integer, nullable=True)
    ready_quarter = Column(Integer, nullable=True)  # 1-4

    # Floors
    floor = Column(Integer, nullable=True)
    floors_total = Column(Integer, nullable=True)

    # Areas (m²)
    area_total = Column(Float, nullable=True, index=True)
    living_area = Column(Float, nullable=True)  # Жилая площадь
    kitchen_area = Column(Float, nullable=True)  # Площадь кухни

    # Rooms & Layout
    rooms = Column(Integer, nullable=True, index=True)
    balcony_type = Column(String, nullable=True)  # "лоджия", "балкон", "терраса"
    bathroom_count = Column(Integer, nullable=True)
    bathroom_type = Column(String, nullable=True)  # "раздельный", "совмещенный"

    # Condition & Amenities
    renovation = Column(String, nullable=True, index=True)  # "Без отделки", "Черновая", "Чистовая"
    ceiling_height = Column(Float, nullable=True)  # Высота потолков (м)
    has_elevator = Column(Boolean, nullable=True)
    has_parking = Column(Boolean, nullable=True)

    # Financial
    mortgage_available = Column(Boolean, nullable=True)
    haggle_allowed = Column(Boolean, nullable=True)  # Торг
    payment_methods = Column(JSON, nullable=True)  # ["Ипотека", "Рассрочка"]
    approved_banks = Column(JSON, nullable=True)  # ["Сбербанк", "ВТБ"]

    # Developer
    developer_id = Column(String, nullable=True, index=True)
    developer_name = Column(String, nullable=True)
    builder_data = Column(JSON, nullable=True)
    # {"risk_score": 0.2, "completion_rate": 0.95, ...}

    # Images (categorized)
    photos = Column(JSON, nullable=True)  # Основные фото
    plan_images = Column(JSON, nullable=True)  # Планировка
    floor_plan_images = Column(JSON, nullable=True)  # Поэтажный план
    complex_scheme_images = Column(JSON, nullable=True)  # Схема ЖК

    # Complex Info
    complex_advantages = Column(JSON, nullable=True)  # ["Благоустроенная территория", ...]
    complex_description = Column(Text, nullable=True)

    # Agent/Sales Info
    agent_data = Column(JSON, nullable=True)
    # {"phone": "+7...", "email": "...", "organization": "..."}

    # Enriched Data
    amenities = Column(JSON, nullable=True)
    market_data = Column(JSON, nullable=True)
    # {"median": 5000000, "p25": 4500000, "p75": 5500000, "pct": 55}
    poi_data = Column(JSON, nullable=True)
    # {"school_1km": 3, "park_1km": 1, "grocery_500m": 5, ...}
    routes_cache = Column(JSON, nullable=True)
    # {"client_id": {"to_work": {"auto": 35, "pt": 42}, ...}}
    vision_data = Column(JSON, nullable=True)
    # {"light_score": 0.85, "view_tags": ["park", "quiet"], "condition_score": 0.7, ...}

    # System fields
    is_active = Column(Boolean, default=True, index=True)
    is_new_flat = Column(Boolean, default=True)  # Признак новостройки

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String, nullable=True)  # Where listing came from
    external_id = Column(String, nullable=True, unique=True, index=True)  # ID from external source

    # Relationships
    selection_items = relationship("SelectionItem", back_populates="listing")


class PropertySelection(Base):
    """Property selection/подборка for a client."""

    __tablename__ = "property_selections"

    id = Column(String, primary_key=True)  # UUID
    client_id = Column(String, ForeignKey("property_clients.id"), nullable=False, index=True)
    agent_telegram_id = Column(String, nullable=True)  # Who created the selection

    # Snapshot of filters and weights at time of creation
    filters_snapshot = Column(JSON, nullable=True)
    taste_weights_snapshot = Column(JSON, nullable=True)

    # Share link
    share_token = Column(String, unique=True, nullable=True, index=True)
    share_url = Column(String, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    client = relationship("PropertyClient", back_populates="selections")
    items = relationship("SelectionItem", back_populates="selection", cascade="all, delete-orphan")
    feedback = relationship("SelectionFeedback", back_populates="selection", cascade="all, delete-orphan")


class SelectionItem(Base):
    """Item in a property selection."""

    __tablename__ = "selection_items"

    id = Column(String, primary_key=True)  # UUID
    selection_id = Column(String, ForeignKey("property_selections.id"), nullable=False, index=True)
    listing_id = Column(String, ForeignKey("property_listings.id"), nullable=False, index=True)

    # Ranking
    dream_score = Column(Float, nullable=False)  # 0-100
    rank = Column(Integer, nullable=True)  # Position in top-N

    # Explanation (AI-generated)
    explanation = Column(JSON, nullable=True)
    # {"why_top": [...], "compromise": [...], "price_context": "", "routes": {...}, "check_on_viewing": [...]}

    # Agent notes
    agent_note = Column(Text, nullable=True)

    # Status
    status = Column(String, default="new")  # new, sent, liked, hidden, viewed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    selection = relationship("PropertySelection", back_populates="items")
    listing = relationship("PropertyListing", back_populates="selection_items")


class SelectionFeedback(Base):
    """Feedback from client on selection items."""

    __tablename__ = "selection_feedback"

    id = Column(String, primary_key=True)  # UUID
    selection_id = Column(String, ForeignKey("property_selections.id"), nullable=False, index=True)
    listing_id = Column(String, nullable=False, index=True)
    client_telegram_id = Column(String, nullable=False)

    # Feedback
    feedback_type = Column(String, nullable=False)  # like, dislike, comment
    comment = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    selection = relationship("PropertySelection", back_populates="feedback")


class UserBotMode(Base):
    """Tracks which mode user is in (calendar vs property search)."""

    __tablename__ = "user_bot_modes"

    telegram_user_id = Column(String, primary_key=True)
    current_mode = Column(SQLEnum(BotMode), default=BotMode.calendar, nullable=False)

    # Active client ID when in property mode
    active_client_id = Column(String, ForeignKey("property_clients.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
