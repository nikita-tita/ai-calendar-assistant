"""Event-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """User intent types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    FIND_FREE_SLOTS = "find_free_slots"
    CLARIFY = "clarify"
    BATCH_CONFIRM = "batch_confirm"
    CREATE_RECURRING = "create_recurring"
    DELETE_BY_CRITERIA = "delete_by_criteria"
    DELETE_DUPLICATES = "delete_duplicates"


class EventDTO(BaseModel):
    """Data Transfer Object for calendar events."""

    # Intent and metadata
    intent: IntentType = Field(default=IntentType.CREATE, description="Type of operation")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")

    # Event details
    title: Optional[str] = Field(None, description="Event title/summary")
    description: Optional[str] = Field(None, description="Event description/notes")

    # Time fields
    start_time: Optional[datetime] = Field(None, description="Event start time (ISO 8601 with timezone)")
    end_time: Optional[datetime] = Field(None, description="Event end time (ISO 8601 with timezone)")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes")

    # Location and participants
    location: Optional[str] = Field(None, description="Event location")
    attendees: Optional[List[str]] = Field(default_factory=list, description="List of attendee emails")

    # For updates/deletes
    event_id: Optional[str] = Field(None, description="Google Calendar event ID")

    # For clarifications
    clarify_question: Optional[str] = Field(None, description="Question to ask user for clarification")

    # Query parameters
    query_date_start: Optional[datetime] = Field(None, description="Start date for queries")
    query_date_end: Optional[datetime] = Field(None, description="End date for queries")

    # Original user input
    raw_text: Optional[str] = Field(None, description="Original user input")

    # Batch operations
    batch_actions: Optional[List[dict]] = Field(None, description="List of actions for batch confirmation")
    batch_summary: Optional[str] = Field(None, description="Human-readable summary of batch operations")

    # Recurring events
    recurrence_type: Optional[str] = Field(None, description="Recurrence pattern: daily, weekly, monthly")
    recurrence_end_date: Optional[datetime] = Field(None, description="End date for recurring events")
    recurrence_days: Optional[List[str]] = Field(None, description="Days of week for weekly recurrence (e.g., ['mon', 'wed', 'fri'])")

    # Delete by criteria (for mass delete without token limits)
    delete_criteria_title: Optional[str] = Field(None, description="Title pattern to match for deletion")
    delete_criteria_title_contains: Optional[str] = Field(None, description="Substring to search in title for deletion")

    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CalendarEvent(BaseModel):
    """Google Calendar event representation."""

    id: str = Field(..., description="Event ID")
    summary: str = Field(..., description="Event summary/title")
    description: Optional[str] = None
    start: datetime
    end: datetime
    location: Optional[str] = None
    attendees: List[str] = Field(default_factory=list)
    html_link: str = Field(..., description="Link to event in Google Calendar")

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FreeSlot(BaseModel):
    """Free time slot."""

    start: datetime
    end: datetime
    duration_minutes: int

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
