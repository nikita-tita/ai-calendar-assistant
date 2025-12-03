"""Events API router for web application."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
import structlog

from app.services.calendar_radicale import calendar_service
from app.services.analytics_service import analytics_service
from app.models.analytics import ActionType
from app.schemas.events import EventDTO, CalendarEvent

logger = structlog.get_logger()

router = APIRouter()


# Pydantic models for API
class EventCreateRequest(BaseModel):
    """Request model for creating an event."""
    title: str
    start: datetime
    end: datetime
    location: Optional[str] = ""
    description: Optional[str] = ""
    color: Optional[str] = "blue"


class EventUpdateRequest(BaseModel):
    """Request model for updating an event."""
    title: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class EventResponse(BaseModel):
    """Response model for event."""
    id: str
    title: str
    start: datetime
    end: datetime
    location: str
    description: str
    color: str


@router.get("/events/{user_id}", response_model=List[EventResponse])
async def get_user_events(
    request: Request,
    user_id: str,
    start: Optional[datetime] = Query(None, description="Start of time range"),
    end: Optional[datetime] = Query(None, description="End of time range")
):
    """
    Get all events for a user in specified time range.

    If no time range specified, returns events for next 30 days.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot access other user's events"
            )

        # Default time range: now to 30 days from now
        if not start:
            start = datetime.now()
        if not end:
            end = start + timedelta(days=30)

        logger.info("fetching_events", user_id=user_id, start=start, end=end)

        # Log WebApp open (first API call indicates WebApp usage)
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.WEBAPP_OPEN,
            details=f"WebApp: Fetched events {start} to {end}"
        )

        events = await calendar_service.list_events(user_id, start, end)

        # Convert to response format
        response_events = []
        for event in events:
            response_events.append(EventResponse(
                id=event.id,
                title=event.summary,
                start=event.start,
                end=event.end,
                location=event.location or "",
                description=event.description or "",
                color="blue"  # Default color
            ))

        logger.info("events_fetched", user_id=user_id, count=len(response_events))
        return response_events

    except Exception as e:
        logger.error("get_events_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch events: {str(e)}")


@router.post("/events/{user_id}", response_model=EventResponse)
async def create_event(request: Request, user_id: str, event: EventCreateRequest):
    """
    Create a new event for a user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot create events for other users"
            )

        logger.info("creating_event", user_id=user_id, title=event.title)

        # Calculate duration
        duration = int((event.end - event.start).total_seconds() / 60)

        # Create EventDTO
        from app.schemas.events import IntentType
        event_dto = EventDTO(
            intent=IntentType.CREATE,
            title=event.title,
            start_time=event.start,
            end_time=event.end,
            duration_minutes=duration,
            location=event.location,
            description=event.description
        )

        # Create event in calendar
        event_uid = await calendar_service.create_event(user_id, event_dto)

        if not event_uid:
            raise HTTPException(status_code=500, detail="Failed to create event")

        logger.info("event_created", user_id=user_id, uid=event_uid)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.EVENT_CREATE,
            details=f"API: Created {event.title}",
            event_id=event_uid
        )

        # Return created event
        return EventResponse(
            id=event_uid,
            title=event.title,
            start=event.start,
            end=event.end,
            location=event.location or "",
            description=event.description or "",
            color=event.color or "blue"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("create_event_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, event: EventUpdateRequest):
    """
    Update an existing event.

    Note: user_id should be extracted from event_id or passed separately
    For now, we'll need to search all calendars or pass user_id in query
    """
    try:
        # TODO: Extract user_id from event_id or require it as query param
        # For now, raise not implemented
        raise HTTPException(
            status_code=501,
            detail="Update event requires user_id. Use PUT /events/{user_id}/{event_id} instead"
        )

    except Exception as e:
        logger.error("update_event_error", event_id=event_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(e)}")


@router.put("/events/{user_id}/{event_id}", response_model=EventResponse)
async def update_event_with_user(request: Request, user_id: str, event_id: str, event: EventUpdateRequest):
    """
    Update an existing event for a specific user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot update other user's events"
            )

        logger.info("updating_event", user_id=user_id, event_id=event_id)

        # Create EventDTO with updated fields
        from app.schemas.events import IntentType
        event_dto = EventDTO(
            intent=IntentType.UPDATE,
            title=event.title or "",
            start_time=event.start,
            end_time=event.end,
            location=event.location,
            description=event.description,
            duration_minutes=int((event.end - event.start).total_seconds() / 60) if event.start and event.end else None
        )

        # Update event
        success = await calendar_service.update_event(user_id, event_id, event_dto)

        if not success:
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info("event_updated", user_id=user_id, event_id=event_id)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.EVENT_UPDATE,
            details=f"API: Updated {event_id}",
            event_id=event_id
        )

        # Return updated event
        return EventResponse(
            id=event_id,
            title=event.title or "",
            start=event.start or datetime.now(),
            end=event.end or datetime.now(),
            location=event.location or "",
            description=event.description or "",
            color=event.color or "blue"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_event_error", user_id=user_id, event_id=event_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update event: {str(e)}")


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """
    Delete an event.

    Note: Requires user_id to locate the calendar.
    Use DELETE /events/{user_id}/{event_id} instead.
    """
    raise HTTPException(
        status_code=501,
        detail="Delete event requires user_id. Use DELETE /events/{user_id}/{event_id} instead"
    )


@router.delete("/events/{user_id}/{event_id}")
async def delete_event_with_user(request: Request, user_id: str, event_id: str):
    """
    Delete an event for a specific user.

    Note: user_id is validated by TelegramAuthMiddleware via HMAC signature.
    """
    try:
        # Get validated user_id from middleware
        authenticated_user_id = request.state.telegram_user_id

        # Verify that path user_id matches authenticated user_id
        if user_id != authenticated_user_id:
            logger.warning(
                "user_id_mismatch",
                requested_user_id=user_id,
                authenticated_user_id=authenticated_user_id
            )
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Cannot delete other user's events"
            )

        logger.info("deleting_event", user_id=user_id, event_id=event_id)

        success = await calendar_service.delete_event(user_id, event_id)

        if not success:
            raise HTTPException(status_code=404, detail="Event not found")

        logger.info("event_deleted", user_id=user_id, event_id=event_id)

        # Log to analytics
        analytics_service.log_action(
            user_id=user_id,
            action_type=ActionType.EVENT_DELETE,
            details=f"API: Deleted {event_id}",
            event_id=event_id
        )

        return {"status": "deleted", "id": event_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_event_error", user_id=user_id, event_id=event_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete event: {str(e)}")


@router.get("/health")
async def events_health():
    """Health check for events API."""
    is_connected = calendar_service.is_connected()
    return {
        "status": "ok" if is_connected else "error",
        "radicale_connected": is_connected
    }
