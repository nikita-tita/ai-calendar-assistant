"""Radicale CalDAV integration service (local calendar server)."""

from typing import Optional, List, Dict
from datetime import datetime, timedelta
import asyncio
import threading
import time
import caldav
from caldav.elements import dav
from icalendar import Calendar, Event as ICalEvent
import structlog
import hashlib
import uuid
from urllib3.exceptions import NameResolutionError, NewConnectionError

from app.config import settings
from app.schemas.events import EventDTO, CalendarEvent, FreeSlot
from app.utils.pii_masking import safe_log_params

logger = structlog.get_logger()

# Analytics imports (optional - graceful fallback if not available)
try:
    from app.services.analytics_service import analytics_service
    from app.models.analytics import ActionType
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False
    analytics_service = None


class CalendarServiceError(Exception):
    """Raised when calendar service is temporarily unavailable.
    Used to distinguish real errors from empty calendar."""
    pass


class CalendarErrorType:
    """Error classification for structured analytics."""
    DNS_RESOLUTION = "dns_resolution"
    CONNECTION_REFUSED = "connection_refused"
    TIMEOUT = "timeout"
    AUTH_FAILED = "auth_failed"
    CONNECTION_RESET = "connection_reset"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"

    @staticmethod
    def classify(error: Exception) -> str:
        """Classify an exception into error type."""
        error_str = str(error).lower()
        if isinstance(error, (NameResolutionError, NewConnectionError)) or 'nameresolutionerror' in error_str:
            return CalendarErrorType.DNS_RESOLUTION
        elif 'connectionrefused' in error_str or 'connection refused' in error_str:
            return CalendarErrorType.CONNECTION_REFUSED
        elif 'timed out' in error_str or 'timeout' in error_str:
            return CalendarErrorType.TIMEOUT
        elif 'authorization' in error_str or '401' in error_str or '403' in error_str:
            return CalendarErrorType.AUTH_FAILED
        elif 'remote end closed' in error_str or 'connectionreset' in error_str:
            return CalendarErrorType.CONNECTION_RESET
        elif 'parse' in error_str or 'ical' in error_str or 'decode' in error_str:
            return CalendarErrorType.PARSE_ERROR
        return CalendarErrorType.UNKNOWN


class RadicaleService:
    """
    Service for interacting with Radicale CalDAV server.

    Radicale - lightweight open source CalDAV/CardDAV server
    Each user gets their own calendar automatically created by Telegram ID.
    No OAuth required - simple internal calendar management.

    Repository: https://github.com/Kozea/Radicale
    """

    # Cache settings
    CACHE_TTL_SECONDS = 300  # 5 minutes
    MAX_CACHED_CALENDARS = 500  # Limit memory usage
    MAX_CLIENT_AGE_SECONDS = 300  # Recycle connection every 5 minutes
    MAX_RETRIES = 2  # Retry CalDAV operations up to 2 times
    RETRY_DELAY_SECONDS = 0.5  # Delay between retries

    def __init__(self):
        """Initialize Radicale service."""
        self.url = settings.radicale_url

        # Single reusable client (connection pooling)
        self._client: Optional[caldav.DAVClient] = None
        self._principal: Optional[caldav.Principal] = None
        self._client_created_at: float = 0  # Timestamp for connection recycling

        # Calendar cache: user_id -> (calendar, timestamp)
        self._calendar_cache: dict = {}
        self._cache_lock = threading.Lock()  # For thread-safe cache access (used in asyncio.to_thread)

    def _get_user_calendar_name(self, user_id: str) -> str:
        """Generate calendar name for user based on Telegram ID."""
        return f"telegram_{user_id}"

    def _reset_connection(self, reason: str = "manual"):
        """Reset CalDAV client and principal, forcing reconnection on next use."""
        self._client = None
        self._principal = None
        self._client_created_at = 0
        self.invalidate_cache()
        logger.info("caldav_connection_reset", reason=reason)

    def _get_shared_client(self) -> caldav.DAVClient:
        """
        Get shared CalDAV client with connection reuse and automatic recycling.

        Connection is recycled every MAX_CLIENT_AGE_SECONDS to prevent
        stale TCP connections after Radicale restarts (fixes DNS resolution errors).

        Returns:
            caldav.DAVClient - reused or freshly created instance
        """
        now = time.time()

        # Recycle old connections to prevent stale TCP issues
        if self._client is not None:
            age = now - self._client_created_at
            if age > self.MAX_CLIENT_AGE_SECONDS:
                logger.info("caldav_client_recycling", age_seconds=round(age, 1))
                self._client = None
                self._principal = None

        if self._client is None:
            if settings.radicale_bot_user and settings.radicale_bot_password:
                self._client = caldav.DAVClient(
                    url=self.url,
                    username=settings.radicale_bot_user,
                    password=settings.radicale_bot_password
                )
            else:
                # Fallback for development (no auth)
                logger.warning("radicale_auth_not_configured", message="Using unauthenticated access")
                self._client = caldav.DAVClient(url=self.url)
            self._client_created_at = now
        return self._client

    def _get_user_client(self, user_id: str):
        """
        Get CalDAV client (uses shared client for efficiency).

        Args:
            user_id: Telegram user ID (not used, kept for API compatibility)

        Returns:
            caldav.DAVClient - shared instance
        """
        return self._get_shared_client()

    def _get_user_calendar(self, user_id: str):
        """
        Get or create calendar for user with caching.

        Args:
            user_id: Telegram user ID

        Returns:
            caldav.Calendar object
        """
        now = time.time()

        # Check cache first (thread-safe)
        with self._cache_lock:
            if user_id in self._calendar_cache:
                cached_cal, cached_time = self._calendar_cache[user_id]
                if now - cached_time < self.CACHE_TTL_SECONDS:
                    logger.debug("calendar_cache_hit", user_id=user_id)
                    return cached_cal

        _cal_start = time.perf_counter()
        try:
            client = self._get_shared_client()

            # Reuse principal if available
            if self._principal is None:
                self._principal = client.principal()

            calendar_name = self._get_user_calendar_name(user_id)

            # Try to find existing calendar by name
            calendars = self._principal.calendars()
            for cal in calendars:
                try:
                    # Check display name property
                    cal_props = cal.get_properties([dav.DisplayName()])
                    display_name = cal_props.get('{DAV:}displayname', '')

                    if display_name == calendar_name:
                        _cal_duration_ms = (time.perf_counter() - _cal_start) * 1000
                        logger.info("calendar_found", user_id=user_id, calendar=calendar_name, url=str(cal.url), duration_ms=round(_cal_duration_ms, 1))

                        # Cache the result
                        self._cache_calendar(user_id, cal)
                        return cal
                except Exception as e:
                    # If can't get properties, skip this calendar
                    logger.debug("calendar_props_error", calendar=str(cal.url), error=str(e))
                    continue

            # Create new calendar if doesn't exist
            new_calendar = self._principal.make_calendar(
                name=calendar_name,
                supported_calendar_component_set=['VEVENT']
            )

            _cal_duration_ms = (time.perf_counter() - _cal_start) * 1000
            logger.info("calendar_created", user_id=user_id, calendar=calendar_name, duration_ms=round(_cal_duration_ms, 1))

            # Cache the result
            self._cache_calendar(user_id, new_calendar)
            return new_calendar

        except Exception as e:
            _cal_duration_ms = (time.perf_counter() - _cal_start) * 1000
            logger.error("calendar_error", user_id=user_id, error=str(e), duration_ms=round(_cal_duration_ms, 1), exc_info=True)

            # Reset client/principal on error (might be stale connection)
            self._client = None
            self._principal = None
            return None

    def _cache_calendar(self, user_id: str, calendar):
        """Cache calendar for user with LRU-like eviction (thread-safe)."""
        with self._cache_lock:
            # Evict old entries if at limit
            if len(self._calendar_cache) >= self.MAX_CACHED_CALENDARS:
                # Remove oldest 10% of entries
                entries = sorted(self._calendar_cache.items(), key=lambda x: x[1][1])
                to_remove = len(entries) // 10 or 1
                for key, _ in entries[:to_remove]:
                    del self._calendar_cache[key]
                logger.debug("calendar_cache_evicted", removed=to_remove)

            self._calendar_cache[user_id] = (calendar, time.time())

    def _get_user_calendar_with_retry(self, user_id: str):
        """Get user calendar with retry on connection failure."""
        for attempt in range(self.MAX_RETRIES + 1):
            calendar = self._get_user_calendar(user_id)
            if calendar is not None:
                return calendar
            if attempt < self.MAX_RETRIES:
                logger.warning("get_calendar_retry",
                             user_id=user_id,
                             attempt=attempt)
                self._reset_connection(reason=f"get_calendar_retry_{attempt}")
                time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
        return None

    def _retry_caldav_operation(self, operation_name: str, user_id: str, func, *args, **kwargs):
        """
        Execute a CalDAV operation with retry logic.

        Retries on connection errors with connection reset between attempts.

        Args:
            operation_name: Name for logging
            user_id: User ID for logging
            func: Callable to execute
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result of func call

        Raises:
            CalendarServiceError: If all retries exhausted
        """
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_type = CalendarErrorType.classify(e)
                logger.warning(f"caldav_{operation_name}_retry",
                             user_id=user_id,
                             attempt=attempt,
                             error_type=error_type,
                             error=str(e)[:200])
                self._reset_connection(reason=f"{operation_name}_{error_type}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
        raise CalendarServiceError(
            f"{operation_name} failed after {self.MAX_RETRIES + 1} attempts: {str(last_error)[:100]}"
        )

    def invalidate_cache(self, user_id: Optional[str] = None):
        """Invalidate calendar cache for user or all users (thread-safe)."""
        with self._cache_lock:
            if user_id:
                self._calendar_cache.pop(user_id, None)
            else:
                self._calendar_cache.clear()
                self._principal = None
            logger.debug("calendar_cache_invalidated", user_id=user_id)

    def _find_conflicts(
        self,
        user_id: str,
        start: datetime,
        end: datetime,
        exclude_uid: Optional[str] = None
    ) -> List[dict]:
        """
        Find events that overlap with the specified time range.

        BIZ-004: Event conflict detection.

        Args:
            user_id: Telegram user ID
            start: Start time of the new/updated event
            end: End time of the new/updated event
            exclude_uid: Event UID to exclude (for updates)

        Returns:
            List of conflicting events as dicts with uid, summary, start, end
        """
        import pytz

        calendar = self._get_user_calendar(user_id)
        if not calendar:
            return []

        # Search events in time range (with buffer for edge cases)
        try:
            events = calendar.date_search(start=start, end=end)
        except Exception as e:
            logger.error("conflict_search_error", user_id=user_id, error=str(e))
            return []

        conflicts = []
        for event in events:
            try:
                ical = Calendar.from_ical(event.data)
                for component in ical.walk('VEVENT'):
                    uid = str(component.get('uid'))

                    # Skip excluded event (for updates)
                    if exclude_uid and uid == exclude_uid:
                        continue

                    event_start = component.get('dtstart').dt
                    event_end = component.get('dtend').dt

                    # Convert date to datetime if needed
                    if not isinstance(event_start, datetime):
                        event_start = datetime.combine(event_start, datetime.min.time())
                    if not isinstance(event_end, datetime):
                        event_end = datetime.combine(event_end, datetime.min.time())

                    # Ensure timezone awareness
                    if event_start.tzinfo is None:
                        event_start = pytz.UTC.localize(event_start)
                    if event_end.tzinfo is None:
                        event_end = pytz.UTC.localize(event_end)

                    # Normalize times for comparison
                    check_start = start if start.tzinfo else pytz.UTC.localize(start)
                    check_end = end if end.tzinfo else pytz.UTC.localize(end)

                    # Check overlap: start1 < end2 AND start2 < end1
                    if event_start < check_end and check_start < event_end:
                        conflicts.append({
                            'uid': uid,
                            'summary': str(component.get('summary', 'Событие')),
                            'start': event_start,
                            'end': event_end
                        })
            except Exception as e:
                logger.debug("conflict_parse_error", error=str(e))
                continue

        if conflicts:
            logger.info(
                "conflicts_found",
                user_id=user_id,
                conflict_count=len(conflicts),
                time_range=f"{start.isoformat()} - {end.isoformat()}"
            )

        return conflicts

    def _create_event_sync(self, user_id: str, event: EventDTO) -> Optional[str]:
        """
        Synchronous implementation of create_event with retry logic.
        Called via asyncio.to_thread to avoid blocking event loop.
        """
        import pytz  # Import here for thread safety

        # Safety check: start_time must exist to prevent NoneType + timedelta crash
        if not event.start_time:
            logger.error("create_event_missing_start_time",
                        user_id=user_id,
                        title=event.title)
            return None

        calendar = self._get_user_calendar_with_retry(user_id)
        if not calendar:
            return None

        # Calculate end time
        end_time = event.end_time or (
            event.start_time + timedelta(minutes=event.duration_minutes or 60)
        )

        # Ensure times are timezone-aware (convert to UTC for CalDAV)
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

        # BIZ-004: Check for conflicts (warning only, does not block)
        conflicts = self._find_conflicts(user_id, start_time_utc, end_time_utc)
        if conflicts:
            conflict_summaries = [c['summary'] for c in conflicts[:3]]  # First 3
            logger.warning(
                "event_conflict_detected",
                user_id=user_id,
                new_event_title=event.title,
                conflicts_count=len(conflicts),
                conflict_summaries=conflict_summaries
            )

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

        # Save to Radicale with retry
        ical_data = cal.to_ical().decode('utf-8')
        self._retry_caldav_operation(
            "save_event", user_id,
            lambda: calendar.save_event(ical_data)
        )

        logger.info(
            "event_created",
            **safe_log_params(user_id=user_id, title=event.title),
            uid=uid
        )

        return uid

    async def create_event(self, user_id: str, event: EventDTO) -> Optional[str]:
        """
        Create calendar event in user's personal calendar.
        Runs blocking CalDAV operations in thread pool.

        Args:
            user_id: Telegram user ID
            event: Event details

        Returns:
            Event UID or None if failed
        """
        try:
            # Run blocking CalDAV operations in thread pool
            result = await asyncio.to_thread(
                self._create_event_sync,
                user_id,
                event
            )
            # Invalidate cache after successful create (BIZ-003)
            if result:
                self.invalidate_cache(user_id)
            return result
        except CalendarServiceError:
            logger.error("event_create_service_error", user_id=user_id)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event create failed (retries exhausted): {event.title[:50] if event.title else 'No title'}",
                    success=False,
                    error_message="CalendarServiceError after retries"
                )
            raise
        except Exception as e:
            error_type = CalendarErrorType.classify(e)
            logger.error("event_create_error", user_id=user_id, error=str(e), error_type=error_type, exc_info=True)
            # Log calendar error to analytics
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event create failed [{error_type}]: {event.title[:50] if event.title else 'No title'}",
                    success=False,
                    error_message=str(e)[:200]
                )
            return None

    def _list_events_sync(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime
    ) -> List[CalendarEvent]:
        """
        Synchronous implementation of list_events with retry logic.
        Called via asyncio.to_thread to avoid blocking event loop.

        Retries on connection errors (DNS, timeout, reset) with connection refresh.
        """
        import pytz  # Import here to avoid issues with thread safety

        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            calendar = self._get_user_calendar(user_id)
            if not calendar:
                if attempt < self.MAX_RETRIES:
                    # Calendar fetch failed, reset connection and retry
                    self._reset_connection(reason=f"get_calendar_failed_attempt_{attempt}")
                    time.sleep(self.RETRY_DELAY_SECONDS)
                    continue
                raise CalendarServiceError("Calendar service unavailable")

            try:
                # Search events in time range
                _search_start = time.perf_counter()
                events = calendar.date_search(start=time_min, end=time_max)
                _search_duration_ms = (time.perf_counter() - _search_start) * 1000
                logger.info("caldav_date_search_duration",
                           duration_ms=round(_search_duration_ms, 1),
                           user_id=user_id,
                           attempt=attempt)
                break  # Success — exit retry loop

            except Exception as e:
                last_error = e
                error_type = CalendarErrorType.classify(e)
                logger.warning("caldav_date_search_failed",
                             user_id=user_id,
                             attempt=attempt,
                             max_retries=self.MAX_RETRIES,
                             error_type=error_type,
                             error=str(e)[:200])

                # Reset connection for next attempt
                self._reset_connection(reason=f"date_search_error_{error_type}")

                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))  # Exponential-ish backoff
                    continue
                else:
                    # All retries exhausted
                    raise CalendarServiceError(f"Calendar unavailable after {self.MAX_RETRIES + 1} attempts: {error_type}")

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

    async def list_events(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime
    ) -> List[CalendarEvent]:
        """
        List events from user's calendar in time range.
        Runs blocking CalDAV operations in thread pool.

        Args:
            user_id: Telegram user ID
            time_min: Start of time range
            time_max: End of time range

        Returns:
            List of calendar events
        """
        try:
            # Run blocking CalDAV operations in thread pool
            return await asyncio.to_thread(
                self._list_events_sync,
                user_id,
                time_min,
                time_max
            )
        except CalendarServiceError:
            # Re-raise CalendarServiceError so telegram_handler can show user-friendly message
            logger.error("events_list_service_error", user_id=user_id)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Events list failed (retries exhausted): {time_min.strftime('%Y-%m-%d')} - {time_max.strftime('%Y-%m-%d')}",
                    success=False,
                    error_message="CalendarServiceError after retries"
                )
            raise
        except Exception as e:
            error_type = CalendarErrorType.classify(e)
            logger.error("events_list_error", user_id=user_id, error=str(e), error_type=error_type, exc_info=True)
            # Log calendar error to analytics with error type
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Events list failed [{error_type}]: {time_min.strftime('%Y-%m-%d')} - {time_max.strftime('%Y-%m-%d')}",
                    success=False,
                    error_message=str(e)[:200]
                )
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

    def _update_event_sync(self, user_id: str, event_uid: str, updated_event: EventDTO) -> bool:
        """
        Synchronous implementation of update_event with retry.
        Called via asyncio.to_thread to avoid blocking event loop.
        """
        import pytz  # Import here for thread safety

        calendar = self._get_user_calendar_with_retry(user_id)
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

                    # BIZ-004: Check for conflicts when time is updated
                    if updated_event.start_time:
                        new_start = updated_event.start_time
                        new_end = updated_event.end_time or (
                            updated_event.start_time + timedelta(minutes=updated_event.duration_minutes or 60)
                        )
                        # Ensure timezone awareness
                        if new_start.tzinfo is None:
                            moscow_tz = pytz.timezone(settings.default_timezone)
                            new_start = moscow_tz.localize(new_start)
                        if new_end.tzinfo is None:
                            moscow_tz = pytz.timezone(settings.default_timezone)
                            new_end = moscow_tz.localize(new_end)
                        new_start_utc = new_start.astimezone(pytz.UTC)
                        new_end_utc = new_end.astimezone(pytz.UTC)

                        conflicts = self._find_conflicts(
                            user_id, new_start_utc, new_end_utc, exclude_uid=event_uid
                        )
                        if conflicts:
                            conflict_summaries = [c['summary'] for c in conflicts[:3]]
                            logger.warning(
                                "event_conflict_detected",
                                user_id=user_id,
                                updated_event_uid=event_uid,
                                new_event_title=updated_event.title,
                                conflicts_count=len(conflicts),
                                conflict_summaries=conflict_summaries
                            )

                    # Save updated event
                    event.data = ical.to_ical()
                    event.save()

                    logger.info("event_updated", user_id=user_id, uid=event_uid, title=updated_event.title)
                    return True

        logger.warning("event_not_found_for_update", user_id=user_id, uid=event_uid)
        return False

    async def update_event(self, user_id: str, event_uid: str, updated_event: EventDTO) -> bool:
        """
        Update existing event in user's calendar.
        Runs blocking CalDAV operations in thread pool.

        Args:
            user_id: Telegram user ID
            event_uid: Event UID to update
            updated_event: New event details

        Returns:
            True if successful, False otherwise
        """
        try:
            # Run blocking CalDAV operations in thread pool
            result = await asyncio.to_thread(
                self._update_event_sync,
                user_id,
                event_uid,
                updated_event
            )
            # Invalidate cache after successful update (BIZ-003)
            if result:
                self.invalidate_cache(user_id)
            return result
        except CalendarServiceError:
            logger.error("event_update_service_error", user_id=user_id, uid=event_uid)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event update failed (retries exhausted): uid={event_uid[:20]}",
                    event_id=event_uid,
                    success=False,
                    error_message="CalendarServiceError after retries"
                )
            raise
        except Exception as e:
            error_type = CalendarErrorType.classify(e)
            logger.error("event_update_error", user_id=user_id, error=str(e), error_type=error_type, exc_info=True)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event update failed [{error_type}]: uid={event_uid[:20]}",
                    event_id=event_uid,
                    success=False,
                    error_message=str(e)[:200]
                )
            return False

    def _delete_event_sync(self, user_id: str, event_uid: str) -> bool:
        """
        Synchronous implementation of delete_event with retry.
        Called via asyncio.to_thread to avoid blocking event loop.
        """
        calendar = self._get_user_calendar_with_retry(user_id)
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

    async def delete_event(self, user_id: str, event_uid: str) -> bool:
        """
        Delete event from user's calendar.
        Runs blocking CalDAV operations in thread pool.

        Args:
            user_id: Telegram user ID
            event_uid: Event UID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Run blocking CalDAV operations in thread pool
            result = await asyncio.to_thread(
                self._delete_event_sync,
                user_id,
                event_uid
            )
            # Invalidate cache after successful delete (BIZ-003)
            if result:
                self.invalidate_cache(user_id)
            return result
        except CalendarServiceError:
            logger.error("event_delete_service_error", user_id=user_id, uid=event_uid)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event delete failed (retries exhausted): uid={event_uid[:20]}",
                    event_id=event_uid,
                    success=False,
                    error_message="CalendarServiceError after retries"
                )
            raise
        except Exception as e:
            error_type = CalendarErrorType.classify(e)
            logger.error("event_delete_error", user_id=user_id, error=str(e), error_type=error_type, exc_info=True)
            if ANALYTICS_ENABLED and analytics_service:
                analytics_service.log_action(
                    user_id=user_id,
                    action_type=ActionType.CALENDAR_ERROR,
                    details=f"Event delete failed [{error_type}]: uid={event_uid[:20]}",
                    event_id=event_uid,
                    success=False,
                    error_message=str(e)[:200]
                )
            return False

    def _is_connected_sync(self) -> bool:
        """Synchronous connectivity check for Radicale server."""
        try:
            # Use the shared client instead of creating a new one each time
            client = self._get_shared_client()
            if self._principal is None:
                self._principal = client.principal()
            _ = self._principal.calendars()
            return True
        except Exception as e:
            logger.debug("radicale_connection_check_failed", error=str(e))
            # Reset on failure so next real operation gets fresh connection
            self._reset_connection(reason="health_check_failed")
            return False

    def is_connected(self) -> bool:
        """Check if Radicale server is accessible (sync wrapper)."""
        return self._is_connected_sync()

    async def is_connected_async(self) -> bool:
        """Check if Radicale server is accessible (async, non-blocking)."""
        try:
            return await asyncio.to_thread(self._is_connected_sync)
        except Exception:
            return False


# Global instance
calendar_service = RadicaleService()
