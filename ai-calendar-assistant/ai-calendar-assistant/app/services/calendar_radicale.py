"""Radicale CalDAV integration service (local calendar server)."""

from typing import Optional, List
from datetime import datetime, timedelta
import caldav
from caldav.elements import dav
from icalendar import Calendar, Event as ICalEvent
import structlog
import hashlib
import uuid

from app.config import settings
from app.schemas.events import EventDTO, CalendarEvent, FreeSlot
from app.utils.pii_masking import safe_log_params

logger = structlog.get_logger()


class RadicaleService:
    """
    Service for interacting with Radicale CalDAV server.

    Radicale - lightweight open source CalDAV/CardDAV server
    Each user gets their own calendar automatically created by Telegram ID.
    No OAuth required - simple internal calendar management.

    Repository: https://github.com/Kozea/Radicale
    """

    def __init__(self):
        """Initialize Radicale service."""
        self.url = settings.radicale_url

    def _get_user_calendar_name(self, user_id: str) -> str:
        """Generate calendar name for user based on Telegram ID."""
        return f"telegram_{user_id}"

    def _get_user_client(self, user_id: str):
        """
        Create CalDAV client for specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            caldav.DAVClient configured for this user
        """
        # Use bot service account for authentication
        # Bot has access to all calendars via Radicale rights configuration
        if settings.radicale_bot_user and settings.radicale_bot_password:
            return caldav.DAVClient(
                url=self.url,
                username=settings.radicale_bot_user,
                password=settings.radicale_bot_password
            )
        else:
            # Fallback for development (no auth)
            logger.warning("radicale_auth_not_configured", message="Using unauthenticated access")
            return caldav.DAVClient(url=self.url, username=str(user_id))

    def _get_user_calendar(self, user_id: str):
        """
        Get or create calendar for user.

        Args:
            user_id: Telegram user ID

        Returns:
            caldav.Calendar object
        """
        try:
            client = self._get_user_client(user_id)
            principal = client.principal()
            calendar_name = self._get_user_calendar_name(user_id)

            # Try to find existing calendar by name
            calendars = principal.calendars()
            for cal in calendars:
                try:
                    # Check display name property
                    cal_props = cal.get_properties([dav.DisplayName()])
                    display_name = cal_props.get('{DAV:}displayname', '')

                    if display_name == calendar_name:
                        logger.info("calendar_found", user_id=user_id, calendar=calendar_name, url=str(cal.url))
                        return cal
                except Exception as e:
                    # If can't get properties, skip this calendar
                    logger.debug("calendar_props_error", calendar=str(cal.url), error=str(e))
                    continue

            # Create new calendar if doesn't exist
            new_calendar = principal.make_calendar(
                name=calendar_name,
                supported_calendar_component_set=['VEVENT']
            )

            logger.info("calendar_created", user_id=user_id, calendar=calendar_name)
            return new_calendar

        except Exception as e:
            logger.error("calendar_error", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def create_event(self, user_id: str, event: EventDTO) -> Optional[str]:
        """
        Create calendar event in user's personal calendar.

        Args:
            user_id: Telegram user ID
            event: Event details

        Returns:
            Event UID or None if failed
        """
        try:
            calendar = self._get_user_calendar(user_id)
            if not calendar:
                return None

            # Calculate end time
            end_time = event.end_time or (
                event.start_time + timedelta(minutes=event.duration_minutes or 60)
            )

            # Ensure times are timezone-aware (convert to UTC for CalDAV)
            import pytz
            start_time_utc = event.start_time
            logger.info("create_event_start_time_input",
                       start_time=event.start_time.isoformat() if event.start_time else None,
                       has_tzinfo=event.start_time.tzinfo is not None if event.start_time else None,
                       tzinfo_str=str(event.start_time.tzinfo) if event.start_time and event.start_time.tzinfo else None)

            if start_time_utc.tzinfo is None:
                # If naive, assume it's in user's timezone (Moscow by default)
                moscow_tz = pytz.timezone(settings.default_timezone)
                start_time_utc = moscow_tz.localize(start_time_utc)
            # Convert to UTC for CalDAV storage
            start_time_utc = start_time_utc.astimezone(pytz.UTC)

            logger.info("create_event_start_time_utc",
                       start_time_utc=start_time_utc.isoformat())

            end_time_utc = end_time
            if end_time_utc.tzinfo is None:
                moscow_tz = pytz.timezone(settings.default_timezone)
                end_time_utc = moscow_tz.localize(end_time_utc)
            end_time_utc = end_time_utc.astimezone(pytz.UTC)

            # Create iCalendar event
            cal = Calendar()
            cal.add('prodid', '-//AI Calendar Assistant//Telegram Bot//RU')
            cal.add('version', '2.0')

            ical_event = ICalEvent()

            # Generate cryptographically secure unique UID
            uid = str(uuid.uuid4())

            ical_event.add('uid', uid)
            ical_event.add('summary', event.title or "Событие")
            ical_event.add('dtstart', start_time_utc)
            ical_event.add('dtend', end_time_utc)
            ical_event.add('dtstamp', datetime.now(pytz.UTC))

            if event.description:
                ical_event.add('description', event.description)

            if event.location:
                ical_event.add('location', event.location)

            # Add attendees if any
            if event.attendees:
                for attendee in event.attendees:
                    ical_event.add('attendee', f'mailto:{attendee}')

            cal.add_component(ical_event)

            # Save to Radicale
            calendar.save_event(cal.to_ical().decode('utf-8'))

            logger.info(
                "event_created",
                **safe_log_params(user_id=user_id, title=event.title),
                uid=uid
            )

            return uid

        except Exception as e:
            logger.error("event_create_error", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def list_events(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime
    ) -> List[CalendarEvent]:
        """
        List events from user's calendar in time range.

        Args:
            user_id: Telegram user ID
            time_min: Start of time range
            time_max: End of time range

        Returns:
            List of calendar events
        """
        try:
            calendar = self._get_user_calendar(user_id)
            if not calendar:
                return []

            # Search events in time range
            events = calendar.date_search(start=time_min, end=time_max)

            calendar_events = []
            for event in events:
                ical = Calendar.from_ical(event.data)

                for component in ical.walk('VEVENT'):
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt

                    # Convert to datetime if date object
                    if not isinstance(start, datetime):
                        start = datetime.combine(start, datetime.min.time())
                    if not isinstance(end, datetime):
                        end = datetime.combine(end, datetime.min.time())

                    # Ensure timezone awareness
                    # Events in Radicale are stored in UTC, so if no timezone assume UTC
                    import pytz
                    if start.tzinfo is None:
                        start = pytz.UTC.localize(start)
                    if end.tzinfo is None:
                        end = pytz.UTC.localize(end)

                    # Convert UTC to user's timezone (Moscow by default)
                    # This ensures all times are in the same timezone for comparison
                    user_tz = pytz.timezone(settings.default_timezone)
                    start_local = start.astimezone(user_tz)
                    end_local = end.astimezone(user_tz)

                    logger.info("list_events_retrieved_event",
                               summary=str(component.get('summary', 'Событие')),
                               start_utc=start.isoformat(),
                               start_local=start_local.isoformat(),
                               has_tzinfo=start.tzinfo is not None,
                               tzinfo_str=str(start.tzinfo))

                    calendar_events.append(CalendarEvent(
                        id=str(component.get('uid')),
                        summary=str(component.get('summary', 'Событие')),
                        description=str(component.get('description', '')),
                        start=start_local,
                        end=end_local,
                        location=str(component.get('location', '')),
                        attendees=[
                            str(att).replace('mailto:', '')
                            for att in component.get('attendee', [])
                        ],
                        html_link=f"{self.url}/{self._get_user_calendar_name(user_id)}/{component.get('uid')}.ics"
                    ))

            logger.info("events_listed", user_id=user_id, count=len(calendar_events))
            return calendar_events

        except Exception as e:
            logger.error("events_list_error", user_id=user_id, error=str(e), exc_info=True)
            return []

    async def find_free_slots(
        self,
        user_id: str,
        date: datetime,
        work_hours_start: int = 9,
        work_hours_end: int = 18,
        slot_duration: int = 60
    ) -> List[FreeSlot]:
        """
        Find free time slots on a given date.

        Args:
            user_id: Telegram user ID
            date: Date to check
            work_hours_start: Start of work day (hour)
            work_hours_end: End of work day (hour)
            slot_duration: Slot duration in minutes

        Returns:
            List of free time slots
        """
        try:
            # Ensure date has timezone info
            import pytz
            if date.tzinfo is None:
                # Assume Moscow timezone if not specified
                tz = pytz.timezone(settings.default_timezone)
                date = tz.localize(date)

            # Get all events for the day
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            events = await self.list_events(user_id, day_start, day_end)

            # Log events found for debugging
            logger.info("free_slots_events_found",
                       user_id=user_id,
                       events_count=len(events),
                       date=day_start.strftime('%Y-%m-%d'))

            # Create list of busy time ranges
            busy_ranges = []
            for event in events:
                busy_ranges.append((event.start, event.end))
                logger.debug("busy_range_added",
                           event_title=event.summary,
                           start=event.start.strftime('%Y-%m-%d %H:%M'),
                           end=event.end.strftime('%Y-%m-%d %H:%M'))

            # Sort by start time
            busy_ranges.sort(key=lambda x: x[0])

            # Generate free slots using a simpler approach
            free_slots = []
            current_time = date.replace(hour=work_hours_start, minute=0, second=0, microsecond=0)
            end_of_day = date.replace(hour=work_hours_end, minute=0, second=0, microsecond=0)

            # Merge overlapping busy ranges to avoid duplicates
            merged_busy = []
            for start, end in busy_ranges:
                if merged_busy and start <= merged_busy[-1][1]:
                    # Overlaps with previous range, merge them
                    merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], end))
                else:
                    merged_busy.append((start, end))

            # Now find free slots between merged busy periods
            for i in range(len(merged_busy) + 1):
                # Determine the free period
                if i == 0:
                    # Before first event
                    free_start = current_time
                    free_end = merged_busy[0][0] if merged_busy else end_of_day
                elif i == len(merged_busy):
                    # After last event
                    free_start = merged_busy[-1][1]
                    free_end = end_of_day
                else:
                    # Between two events
                    free_start = merged_busy[i-1][1]
                    free_end = merged_busy[i][0]

                # Generate slots within this free period
                slot_time = free_start
                while slot_time + timedelta(minutes=slot_duration) <= free_end:
                    free_slots.append(FreeSlot(
                        start=slot_time,
                        end=slot_time + timedelta(minutes=slot_duration),
                        duration_minutes=slot_duration
                    ))
                    slot_time += timedelta(minutes=slot_duration)

            # Log free slots for debugging
            logger.info("free_slots_found",
                       user_id=user_id,
                       count=len(free_slots),
                       busy_ranges_count=len(merged_busy))
            for slot in free_slots[:5]:  # Log first 5 slots
                logger.debug("free_slot_generated",
                           start=slot.start.strftime('%Y-%m-%d %H:%M'),
                           end=slot.end.strftime('%Y-%m-%d %H:%M'))
            return free_slots

        except Exception as e:
            logger.error("free_slots_error", user_id=user_id, error=str(e), exc_info=True)
            return []

    async def update_event(self, user_id: str, event_uid: str, updated_event: EventDTO) -> bool:
        """
        Update existing event in user's calendar.

        Args:
            user_id: Telegram user ID
            event_uid: Event UID to update
            updated_event: New event details

        Returns:
            True if successful, False otherwise
        """
        try:
            calendar = self._get_user_calendar(user_id)
            if not calendar:
                return False

            # Find event to update
            events = calendar.events()
            for event in events:
                ical = Calendar.from_ical(event.data)
                for component in ical.walk('VEVENT'):
                    if str(component.get('uid')) == event_uid:
                        # Update fields if provided
                        if updated_event.title:
                            component['summary'] = updated_event.title
                        if updated_event.start_time:
                            component['dtstart'].dt = updated_event.start_time
                        if updated_event.end_time:
                            component['dtend'].dt = updated_event.end_time
                        elif updated_event.start_time and updated_event.duration_minutes:
                            component['dtend'].dt = updated_event.start_time + timedelta(minutes=updated_event.duration_minutes)
                        if updated_event.location:
                            component['location'] = updated_event.location
                        if updated_event.description:
                            component['description'] = updated_event.description

                        # Save updated event
                        event.data = ical.to_ical()
                        event.save()

                        logger.info("event_updated", user_id=user_id, uid=event_uid, title=updated_event.title)
                        return True

            logger.warning("event_not_found_for_update", user_id=user_id, uid=event_uid)
            return False

        except Exception as e:
            logger.error("event_update_error", user_id=user_id, error=str(e), exc_info=True)
            return False

    async def delete_event(self, user_id: str, event_uid: str) -> bool:
        """
        Delete event from user's calendar.

        Args:
            user_id: Telegram user ID
            event_uid: Event UID

        Returns:
            True if successful, False otherwise
        """
        try:
            calendar = self._get_user_calendar(user_id)
            if not calendar:
                return False

            # Find and delete event
            events = calendar.events()
            for event in events:
                ical = Calendar.from_ical(event.data)
                for component in ical.walk('VEVENT'):
                    if str(component.get('uid')) == event_uid:
                        event.delete()
                        logger.info("event_deleted", user_id=user_id, uid=event_uid)
                        return True

            logger.warning("event_not_found", user_id=user_id, uid=event_uid)
            return False

        except Exception as e:
            logger.error("event_delete_error", user_id=user_id, error=str(e), exc_info=True)
            return False

    def is_connected(self) -> bool:
        """Check if Radicale server is accessible."""
        try:
            # Test with a dummy user ID
            client = caldav.DAVClient(url=self.url, username="test")
            client.principal()
            return True
        except Exception as e:
            logger.error("radicale_connection_error", error=str(e))
            return False


# Global instance
calendar_service = RadicaleService()
