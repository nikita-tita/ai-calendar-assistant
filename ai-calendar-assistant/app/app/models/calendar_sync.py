"""
Database models for external calendar synchronization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class CalendarProvider(str, Enum):
    """Supported external calendar providers."""
    GOOGLE = "google"
    YANDEX = "yandex"
    APPLE = "apple"


class SyncDirection(str, Enum):
    """Sync direction for events."""
    IMPORT = "import"  # External -> Radicale
    EXPORT = "export"  # Radicale -> External
    BIDIRECTIONAL = "bidirectional"


class CalendarConnection(BaseModel):
    """External calendar connection for a user."""
    id: Optional[int] = None
    user_id: str
    provider: CalendarProvider
    calendar_id: str  # External calendar ID (e.g., "primary" for Google)
    calendar_name: str  # Display name

    # OAuth tokens (encrypted)
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    # Sync settings
    sync_enabled: bool = True
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    last_sync_at: Optional[datetime] = None
    last_sync_token: Optional[str] = None  # For incremental sync

    # Metadata
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True


class SyncEvent(BaseModel):
    """Mapping between local and external events."""
    id: Optional[int] = None
    user_id: str
    connection_id: int  # FK to CalendarConnection

    # Event identifiers
    local_event_id: str  # Radicale event UID
    external_event_id: str  # External calendar event ID

    # Sync metadata
    last_synced_at: datetime
    local_updated_at: datetime  # Last modification time in Radicale
    external_updated_at: datetime  # Last modification time in external calendar
    sync_status: str  # "synced", "conflict", "error"

    # Conflict resolution
    conflict_data: Optional[str] = None  # JSON with conflict details

    class Config:
        use_enum_values = True


class SyncLog(BaseModel):
    """Log of sync operations for debugging."""
    id: Optional[int] = None
    user_id: str
    connection_id: int

    sync_type: str  # "import", "export", "full_sync"
    events_imported: int = 0
    events_exported: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    conflicts: int = 0
    errors: int = 0

    error_message: Optional[str] = None
    duration_seconds: float = 0

    created_at: datetime

    class Config:
        use_enum_values = True
