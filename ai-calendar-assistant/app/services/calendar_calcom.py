"""Cal.com integration service (open source calendar platform)."""

from typing import Optional, List
from datetime import datetime, timedelta
import httpx
import structlog

from app.config import settings
from app.schemas.events import EventDTO, CalendarEvent, FreeSlot

logger = structlog.get_logger()


class CalComService:
    """
    Service for interacting with Cal.com API.

    Cal.com - open source scheduling platform (https://cal.com)
    API Documentation: https://cal.com/docs/api-reference
    """

    def __init__(self):
        """Initialize Cal.com service."""
        self.api_url = settings.calcom_api_url
        self.api_key = settings.calcom_api_key
        self.username = settings.calcom_username

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_event(self, user_id: str, event: EventDTO) -> Optional[str]:
        """
        Create calendar booking via Cal.com.

        Args:
            user_id: User identifier (Telegram ID)
            event: Event details

        Returns:
            Booking URL or None if failed

        Note: Cal.com uses "bookings" terminology instead of "events"
        """
        try:
            async with httpx.AsyncClient() as client:
                # Calculate end time
                end_time = event.end_time or (
                    event.start_time + timedelta(minutes=event.duration_minutes or 60)
                )

                # Prepare booking data
                booking_data = {
                    "eventTypeId": 1,  # Default event type, should be configurable
                    "start": event.start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "responses": {
                        "name": event.title or "Событие",
                        "email": f"user_{user_id}@telegram.local",  # Placeholder
                        "notes": event.description or "",
                        "location": event.location or "Not specified"
                    },
                    "timeZone": settings.default_timezone,
                    "language": "ru",
                }

                # Create booking
                response = await client.post(
                    f"{self.api_url}/bookings",
                    json=booking_data,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code in [200, 201]:
                    result = response.json()
                    booking_id = result.get("id")
                    booking_url = result.get("url") or f"https://cal.com/booking/{booking_id}"

                    logger.info(
                        "calcom_booking_created",
                        user_id=user_id,
                        booking_id=booking_id,
                        title=event.title
                    )

                    return booking_url
                else:
                    logger.error(
                        "calcom_api_error",
                        status=response.status_code,
                        error=response.text
                    )
                    return None

        except Exception as e:
            logger.error("calcom_create_error", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def list_bookings(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime
    ) -> List[CalendarEvent]:
        """
        List Cal.com bookings in time range.

        Args:
            user_id: User identifier
            time_min: Start of time range
            time_max: End of time range

        Returns:
            List of calendar events
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get bookings
                params = {
                    "status": "accepted",
                    "afterStart": time_min.isoformat(),
                    "beforeEnd": time_max.isoformat()
                }

                response = await client.get(
                    f"{self.api_url}/bookings",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error("calcom_list_error", status=response.status_code)
                    return []

                data = response.json()
                bookings = data.get("bookings", [])

                calendar_events = []
                for booking in bookings:
                    start_str = booking.get("startTime")
                    end_str = booking.get("endTime")

                    if not start_str or not end_str:
                        continue

                    calendar_events.append(CalendarEvent(
                        id=str(booking.get("id")),
                        summary=booking.get("title", "Событие"),
                        description=booking.get("description"),
                        start=datetime.fromisoformat(start_str.replace('Z', '+00:00')),
                        end=datetime.fromisoformat(end_str.replace('Z', '+00:00')),
                        location=booking.get("location", {}).get("value"),
                        attendees=[a.get("email") for a in booking.get("attendees", [])],
                        html_link=booking.get("url", "")
                    ))

                logger.info("calcom_bookings_listed", user_id=user_id, count=len(calendar_events))
                return calendar_events

        except Exception as e:
            logger.error("calcom_list_error", user_id=user_id, error=str(e), exc_info=True)
            return []

    async def find_free_slots(
        self,
        user_id: str,
        date: datetime,
        work_hours_start: int = 9,
        work_hours_end: int = 18
    ) -> List[FreeSlot]:
        """
        Find free time slots on a given date.

        Args:
            user_id: User identifier
            date: Date to check
            work_hours_start: Start of work day (hour)
            work_hours_end: End of work day (hour)

        Returns:
            List of free time slots
        """
        try:
            async with httpx.AsyncClient() as client:
                # Get available slots from Cal.com
                params = {
                    "eventTypeId": 1,  # Default event type
                    "startTime": date.replace(hour=work_hours_start, minute=0).isoformat(),
                    "endTime": date.replace(hour=work_hours_end, minute=0).isoformat(),
                    "timeZone": settings.default_timezone
                }

                response = await client.get(
                    f"{self.api_url}/slots",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error("calcom_slots_error", status=response.status_code)
                    return []

                data = response.json()
                slots_data = data.get("slots", {})

                free_slots = []
                for date_str, times in slots_data.items():
                    for slot in times:
                        start = datetime.fromisoformat(slot.get("time"))
                        # Assume 30 min slots by default
                        end = start + timedelta(minutes=30)
                        duration = 30

                        free_slots.append(FreeSlot(
                            start=start,
                            end=end,
                            duration_minutes=duration
                        ))

                logger.info("calcom_slots_found", user_id=user_id, count=len(free_slots))
                return free_slots

        except Exception as e:
            logger.error("calcom_slots_error", user_id=user_id, error=str(e), exc_info=True)
            return []

    async def cancel_booking(self, user_id: str, booking_id: str) -> bool:
        """
        Cancel a booking.

        Args:
            user_id: User identifier
            booking_id: Cal.com booking ID

        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.api_url}/bookings/{booking_id}",
                    headers=self.headers,
                    timeout=30.0
                )

                if response.status_code in [200, 204]:
                    logger.info("calcom_booking_cancelled", user_id=user_id, booking_id=booking_id)
                    return True
                else:
                    logger.error("calcom_cancel_error", status=response.status_code)
                    return False

        except Exception as e:
            logger.error("calcom_cancel_error", user_id=user_id, error=str(e), exc_info=True)
            return False

    def has_api_key(self, user_id: str = None) -> bool:
        """
        Check if Cal.com API key is configured.

        Unlike Google Calendar, Cal.com uses API keys, not OAuth per user.
        The API key is shared for the application.
        """
        return bool(self.api_key and self.api_key != "your_calcom_api_key_here")


# Global instance
calendar_service = CalComService()
