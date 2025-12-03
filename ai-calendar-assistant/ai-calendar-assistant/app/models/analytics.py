"""Analytics models for admin dashboard."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel


class ActionType(str, Enum):
    """User action types for analytics."""
    USER_START = "user_start"
    USER_LOGIN = "user_login"  # New: track bot authorization
    EVENT_CREATE = "event_create"
    EVENT_UPDATE = "event_update"
    EVENT_DELETE = "event_delete"
    EVENT_QUERY = "event_query"
    TEXT_MESSAGE = "text_message"
    VOICE_MESSAGE = "voice_message"
    WEBAPP_OPEN = "webapp_open"
    ERROR = "error"


class UserAction(BaseModel):
    """Single user action log entry."""
    id: Optional[int] = None
    user_id: str
    action_type: ActionType
    timestamp: datetime
    details: Optional[str] = None
    event_id: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    is_test: bool = False  # Flag for test/mock data
    # Telegram user info
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserStats(BaseModel):
    """User statistics."""
    user_id: str
    first_seen: datetime
    last_seen: datetime
    total_events: int
    total_messages: int
    total_voice_messages: int
    total_webapp_opens: int
    total_errors: int
    # Telegram user info
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class DashboardStats(BaseModel):
    """Overall dashboard statistics."""
    total_users: int
    active_users_today: int
    active_users_week: int
    total_events: int
    events_today: int
    events_week: int
    total_messages: int
    messages_today: int
    total_errors: int
    errors_today: int


class TimeSeriesPoint(BaseModel):
    """Time series data point for charts."""
    timestamp: datetime
    value: int


class UserActivityTimeline(BaseModel):
    """User activity timeline for charts."""
    user_id: str
    username: Optional[str] = None
    actions: List[TimeSeriesPoint]


class EventTypeDistribution(BaseModel):
    """Distribution of event types."""
    action_type: ActionType
    count: int
    percentage: float


class UserDetail(BaseModel):
    """Detailed user information for admin."""
    user_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    telegram_link: Optional[str] = None

    # Activity metrics
    first_seen: datetime
    last_seen: datetime
    total_logins: int
    total_actions: int

    # Daily/Weekly/Monthly activity
    actions_today: int
    actions_week: int
    actions_month: int

    # Active days
    active_days_week: int  # How many days user was active this week
    active_days_month: int  # How many days user was active this month

    # Is user active by criteria
    is_active_today: bool
    is_active_week: bool  # 3+ days in week
    is_active_month: bool  # 3+ days per week throughout month


class UserDialogEntry(BaseModel):
    """Single dialog entry (message or action)."""
    timestamp: datetime
    action_type: ActionType
    details: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class AdminDashboardStats(BaseModel):
    """Extended statistics for admin dashboard."""
    total_logins: int
    active_users_today: int  # Made at least 1 action today
    active_users_week: int  # Made actions on 3+ days this week
    active_users_month: int  # Made actions on 3+ days/week throughout month

    total_users: int
    total_actions: int
    total_events_created: int
    total_messages: int
