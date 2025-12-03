"""
Google Calendar API integration service.
"""

import structlog
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import urlencode

from app.models.calendar_sync import CalendarConnection
from app.schemas.events import EventDTO

logger = structlog.get_logger()


class GoogleCalendarService:
    """Service for Google Calendar API integration."""

    OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://www.googleapis.com/calendar/v3"

    # OAuth scopes
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.events",  # Read/write events
        "https://www.googleapis.com/auth/calendar.readonly"  # Read calendar info
    ]

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Google Calendar service.

        Args:
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            redirect_uri: OAuth redirect URI (e.g., https://этонесамыйдлинныйдомен.рф/oauth/google/callback)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    # ==================== OAuth Flow ====================

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: Random state parameter for CSRF protection (should include user_id)

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent"  # Force consent to get refresh token
        }

        url = f"{self.OAUTH_URL}?{urlencode(params)}"
        logger.info("google_oauth_url_generated", state=state)
        return url

    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Dict with access_token, refresh_token, expires_in

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            tokens = response.json()

        logger.info("google_tokens_exchanged", expires_in=tokens.get("expires_in"))
        return tokens

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Dict with new access_token and expires_in

        Raises:
            httpx.HTTPError: If refresh fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            tokens = response.json()

        logger.info("google_token_refreshed")
        return tokens

    # ==================== Calendar API ====================

    async def _get_headers(self, connection: CalendarConnection) -> Dict[str, str]:
        """Get headers with valid access token (refreshes if needed)."""
        # Check if token needs refresh
        if connection.token_expires_at and connection.token_expires_at <= datetime.now():
            logger.info("google_token_expired", connection_id=connection.id)
            # Token refresh will be handled by caller (sync service)
            # For now, return current token
            pass

        return {
            "Authorization": f"Bearer {connection.access_token}",
            "Content-Type": "application/json"
        }

    async def list_events(
        self,
        connection: CalendarConnection,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        sync_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List events from Google Calendar.

        Args:
            connection: Calendar connection with access token
            time_min: Minimum time for events (default: 30 days ago)
            time_max: Maximum time for events (default: 90 days from now)
            sync_token: Token for incremental sync (if None, full sync)

        Returns:
            Dict with 'items' (events) and 'nextSyncToken'
        """
        if not time_min:
            time_min = datetime.now() - timedelta(days=30)
        if not time_max:
            time_max = datetime.now() + timedelta(days=90)

        headers = await self._get_headers(connection)
        params = {
            "maxResults": 2500,  # Max allowed by Google
            "singleEvents": True,  # Expand recurring events
            "orderBy": "updated"
        }

        if sync_token:
            # Incremental sync
            params["syncToken"] = sync_token
            logger.info("google_incremental_sync", connection_id=connection.id)
        else:
            # Full sync
            params["timeMin"] = time_min.isoformat() + "Z"
            params["timeMax"] = time_max.isoformat() + "Z"
            logger.info("google_full_sync", connection_id=connection.id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/calendars/{connection.calendar_id}/events",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()

        logger.info("google_events_listed",
                   connection_id=connection.id,
                   count=len(data.get("items", [])))
        return data

    async def get_event(self, connection: CalendarConnection, event_id: str) -> Dict[str, Any]:
        """Get single event by ID."""
        headers = await self._get_headers(connection)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.API_BASE}/calendars/{connection.calendar_id}/events/{event_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

    async def create_event(self, connection: CalendarConnection, event_dto: EventDTO) -> str:
        """
        Create event in Google Calendar.

        Args:
            connection: Calendar connection
            event_dto: Event data

        Returns:
            Event ID in Google Calendar
        """
        headers = await self._get_headers(connection)

        # Convert EventDTO to Google Calendar format
        event_data = self._event_dto_to_google(event_dto)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE}/calendars/{connection.calendar_id}/events",
                headers=headers,
                json=event_data
            )
            response.raise_for_status()
            created_event = response.json()

        event_id = created_event["id"]
        logger.info("google_event_created",
                   connection_id=connection.id,
                   event_id=event_id,
                   title=event_dto.title)
        return event_id

    async def update_event(
        self,
        connection: CalendarConnection,
        event_id: str,
        event_dto: EventDTO
    ) -> bool:
        """
        Update event in Google Calendar.

        Args:
            connection: Calendar connection
            event_id: Google Calendar event ID
            event_dto: Updated event data

        Returns:
            True if successful
        """
        headers = await self._get_headers(connection)
        event_data = self._event_dto_to_google(event_dto)

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.API_BASE}/calendars/{connection.calendar_id}/events/{event_id}",
                headers=headers,
                json=event_data
            )
            response.raise_for_status()

        logger.info("google_event_updated",
                   connection_id=connection.id,
                   event_id=event_id)
        return True

    async def delete_event(self, connection: CalendarConnection, event_id: str) -> bool:
        """
        Delete event from Google Calendar.

        Args:
            connection: Calendar connection
            event_id: Google Calendar event ID

        Returns:
            True if successful
        """
        headers = await self._get_headers(connection)

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.API_BASE}/calendars/{connection.calendar_id}/events/{event_id}",
                headers=headers
            )
            response.raise_for_status()

        logger.info("google_event_deleted",
                   connection_id=connection.id,
                   event_id=event_id)
        return True

    # ==================== Format Conversion ====================

    def _event_dto_to_google(self, event_dto: EventDTO) -> Dict[str, Any]:
        """Convert EventDTO to Google Calendar event format."""
        event_data = {
            "summary": event_dto.title,
            "start": {
                "dateTime": event_dto.start_time.isoformat(),
                "timeZone": str(event_dto.start_time.tzinfo) if event_dto.start_time.tzinfo else "UTC"
            },
            "end": {
                "dateTime": event_dto.end_time.isoformat(),
                "timeZone": str(event_dto.end_time.tzinfo) if event_dto.end_time.tzinfo else "UTC"
            }
        }

        if event_dto.description:
            event_data["description"] = event_dto.description

        if event_dto.location:
            event_data["location"] = event_dto.location

        return event_data

    def google_event_to_dto(self, google_event: Dict[str, Any]) -> EventDTO:
        """Convert Google Calendar event to EventDTO."""
        from app.schemas.events import IntentType
        import dateutil.parser

        # Parse times
        start = google_event.get("start", {})
        end = google_event.get("end", {})

        start_time = None
        end_time = None

        if "dateTime" in start:
            start_time = dateutil.parser.isoparse(start["dateTime"])
        elif "date" in start:
            # All-day event
            start_time = datetime.fromisoformat(start["date"] + "T00:00:00")

        if "dateTime" in end:
            end_time = dateutil.parser.isoparse(end["dateTime"])
        elif "date" in end:
            end_time = datetime.fromisoformat(end["date"] + "T23:59:59")

        # Calculate duration
        duration_minutes = None
        if start_time and end_time:
            duration_minutes = int((end_time - start_time).total_seconds() / 60)

        return EventDTO(
            intent=IntentType.CREATE,
            confidence=1.0,
            title=google_event.get("summary", "Untitled"),
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            description=google_event.get("description"),
            location=google_event.get("location"),
            event_id=google_event.get("id"),
            raw_text=""
        )
