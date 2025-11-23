"""Todo-related schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TodoIntentType(str, Enum):
    """User intent types for todos."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    TOGGLE = "toggle"  # Toggle completion status
    CLARIFY = "clarify"


class TodoPriority(str, Enum):
    """Todo priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoDTO(BaseModel):
    """Data Transfer Object for todos."""

    # Intent and metadata
    intent: TodoIntentType = Field(default=TodoIntentType.CREATE, description="Type of operation")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score")

    # Todo details
    title: Optional[str] = Field(None, description="Todo title/description")
    completed: bool = Field(False, description="Whether todo is completed")
    priority: Optional[TodoPriority] = Field(TodoPriority.MEDIUM, description="Priority level")

    # Optional fields
    due_date: Optional[datetime] = Field(None, description="Due date (ISO 8601 with timezone)")
    notes: Optional[str] = Field(None, description="Additional notes")

    # For updates/deletes/toggles
    todo_id: Optional[str] = Field(None, description="Todo ID")

    # For clarifications
    clarify_question: Optional[str] = Field(None, description="Question to ask user for clarification")

    # Query parameters
    query_date_start: Optional[datetime] = Field(None, description="Start date for queries")
    query_date_end: Optional[datetime] = Field(None, description="End date for queries")
    query_completed: Optional[bool] = Field(None, description="Filter by completion status")

    # Original user input
    raw_text: Optional[str] = Field(None, description="Original user input")

    class Config:
        """Pydantic config."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Todo(BaseModel):
    """Todo item representation."""

    id: str = Field(..., description="Todo ID")
    title: str = Field(..., description="Todo title")
    completed: bool = Field(False, description="Completion status")
    priority: TodoPriority = Field(TodoPriority.MEDIUM, description="Priority level")
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
