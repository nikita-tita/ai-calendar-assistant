"""
Hooks for exporting events to external calendars.

Called after event creation/update/deletion in bot.
"""

import structlog
import asyncio
from typing import Optional

from app.services.sync_database import sync_db
from app.services.calendar_sync_service import calendar_sync_service
from app.schemas.events import EventDTO

logger = structlog.get_logger()


async def export_created_event(user_id: str, local_event_id: str, event_dto: EventDTO):
    """
    Export newly created event to all connected external calendars.

    Args:
        user_id: User ID
        local_event_id: Local event UID in Radicale
        event_dto: Event data
    """
    if not calendar_sync_service:
        return

    try:
        # Get user's enabled connections
        connections = sync_db.get_user_connections(user_id, enabled_only=True)

        if not connections:
            return

        logger.info("exporting_created_event",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   connections_count=len(connections))

        # Export to all connections in parallel
        tasks = []
        for conn in connections:
            task = calendar_sync_service.export_event_to_google(
                user_id,
                conn,
                local_event_id,
                event_dto
            )
            tasks.append(task)

        # Wait for all exports
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log results
        success_count = sum(1 for r in results if r is True)
        logger.info("event_export_completed",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   success_count=success_count,
                   total_connections=len(connections))

    except Exception as e:
        logger.error("event_export_error",
                    user_id=user_id,
                    local_event_id=local_event_id,
                    error=str(e),
                    exc_info=True)


async def export_updated_event(user_id: str, local_event_id: str, event_dto: EventDTO):
    """
    Export updated event to all connected external calendars.

    Args:
        user_id: User ID
        local_event_id: Local event UID
        event_dto: Updated event data
    """
    if not calendar_sync_service:
        return

    try:
        connections = sync_db.get_user_connections(user_id, enabled_only=True)

        if not connections:
            return

        logger.info("exporting_updated_event",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   connections_count=len(connections))

        # Export to all connections in parallel
        tasks = []
        for conn in connections:
            task = calendar_sync_service.export_updated_event_to_google(
                user_id,
                conn,
                local_event_id,
                event_dto
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.info("event_update_export_completed",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   success_count=success_count)

    except Exception as e:
        logger.error("event_update_export_error",
                    user_id=user_id,
                    local_event_id=local_event_id,
                    error=str(e),
                    exc_info=True)


async def export_deleted_event(user_id: str, local_event_id: str):
    """
    Export event deletion to all connected external calendars.

    Args:
        user_id: User ID
        local_event_id: Local event UID
    """
    if not calendar_sync_service:
        return

    try:
        connections = sync_db.get_user_connections(user_id, enabled_only=True)

        if not connections:
            return

        logger.info("exporting_deleted_event",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   connections_count=len(connections))

        # Export to all connections in parallel
        tasks = []
        for conn in connections:
            task = calendar_sync_service.export_deleted_event_to_google(
                user_id,
                conn,
                local_event_id
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        logger.info("event_deletion_export_completed",
                   user_id=user_id,
                   local_event_id=local_event_id,
                   success_count=success_count)

    except Exception as e:
        logger.error("event_deletion_export_error",
                    user_id=user_id,
                    local_event_id=local_event_id,
                    error=str(e),
                    exc_info=True)


def trigger_export_created(user_id: str, local_event_id: str, event_dto: EventDTO):
    """Trigger export in background (non-blocking)."""
    asyncio.create_task(export_created_event(user_id, local_event_id, event_dto))


def trigger_export_updated(user_id: str, local_event_id: str, event_dto: EventDTO):
    """Trigger export in background (non-blocking)."""
    asyncio.create_task(export_updated_event(user_id, local_event_id, event_dto))


def trigger_export_deleted(user_id: str, local_event_id: str):
    """Trigger export in background (non-blocking)."""
    asyncio.create_task(export_deleted_event(user_id, local_event_id))
