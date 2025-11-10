"""Google Calendar integration service."""

from typing import Optional, List
from datetime import datetime, timedelta
import os
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import structlog

from app.config import settings
from app.schemas.events import EventDTO, CalendarEvent, FreeSlot

logger = structlog.get_logger()


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    def __init__(self):
        """Initialize Google Calendar service."""
        self.credentials_dir = Path("./credentials")
        self.credentials_dir.mkdir(exist_ok=True)

        # OAuth client config
        self.client_config = {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def get_authorization_url(self, user_id: str) -> str:
        """
        Get Google OAuth authorization URL.

        Args:
            user_id: User identifier (Telegram ID)

        Returns:
            Authorization URL to redirect user to
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=settings.google_redirect_uri
        )

        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=user_id  # Store user_id in state
        )

        logger.info("authorization_url_generated", user_id=user_id)
        return auth_url

    async def handle_oauth_callback(self, code: str, user_id: str) -> None:
        """
        Handle OAuth callback and save credentials.

        Args:
            code: Authorization code from Google
            user_id: User identifier
        """
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES,
            redirect_uri=settings.google_redirect_uri
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Save credentials
        self._save_credentials(user_id, credentials)
        logger.info("credentials_saved", user_id=user_id)

    def _save_credentials(self, user_id: str, credentials: Credentials) -> None:
        """Save user credentials to file."""
        creds_file = self.credentials_dir / f"{user_id}.json"

        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }

        with open(creds_file, 'w') as f:
            json.dump(creds_data, f)

    def _load_credentials(self, user_id: str) -> Optional[Credentials]:
        """Load user credentials from file."""
        creds_file = self.credentials_dir / f"{user_id}.json"

        if not creds_file.exists():
            return None

        with open(creds_file, 'r') as f:
            creds_data = json.load(f)

        credentials = Credentials(
            token=creds_data.get('token'),
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data.get('token_uri'),
            client_id=creds_data.get('client_id'),
            client_secret=creds_data.get('client_secret'),
            scopes=creds_data.get('scopes')
        )

        return credentials

    def has_credentials(self, user_id: str) -> bool:
        """Check if user has saved credentials."""
        creds_file = self.credentials_dir / f"{user_id}.json"
        return creds_file.exists()

    async def create_event(self, user_id: str, event: EventDTO) -> Optional[str]:
        """
        Create calendar event.

        Args:
            user_id: User identifier
            event: Event details

        Returns:
            Event HTML link or None if failed
        """
        credentials = self._load_credentials(user_id)
        if not credentials:
            logger.warning("no_credentials", user_id=user_id)
            return None

        try:
            service = build('calendar', 'v3', credentials=credentials)

            # Build event body
            event_body = {
                'summary': event.title,
                'description': event.description or '',
                'start': {
                    'dateTime': event.start_time.isoformat(),
                    'timeZone': settings.default_timezone,
                },
                'end': {
                    'dateTime': (event.end_time or event.start_time + timedelta(minutes=event.duration_minutes or 60)).isoformat(),
                    'timeZone': settings.default_timezone,
                },
            }

            if event.location:
                event_body['location'] = event.location

            if event.attendees:
                event_body['attendees'] = [{'email': email} for email in event.attendees]

            # Create event
            created_event = service.events().insert(
                calendarId='primary',
                body=event_body
            ).execute()

            logger.info(
                "event_created",
                user_id=user_id,
                event_id=created_event.get('id'),
                title=event.title
            )

            return created_event.get('htmlLink')

        except HttpError as e:
            logger.error("calendar_api_error", user_id=user_id, error=str(e))
            return None
        except Exception as e:
            logger.error("event_creation_error", user_id=user_id, error=str(e), exc_info=True)
            return None

    async def list_events(
        self,
        user_id: str,
        time_min: datetime,
        time_max: datetime
    ) -> List[CalendarEvent]:
        """
        List calendar events in time range.

        Args:
            user_id: User identifier
            time_min: Start of time range
            time_max: End of time range

        Returns:
            List of calendar events
        """
        credentials = self._load_credentials(user_id)
        if not credentials:
            return []

        try:
            service = build('calendar', 'v3', credentials=credentials)

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat(),
                timeMax=time_max.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])

            calendar_events = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                calendar_events.append(CalendarEvent(
                    id=event['id'],
                    summary=event.get('summary', 'Без названия'),
                    description=event.get('description'),
                    start=datetime.fromisoformat(start.replace('Z', '+00:00')),
                    end=datetime.fromisoformat(end.replace('Z', '+00:00')),
                    location=event.get('location'),
                    attendees=[a.get('email') for a in event.get('attendees', [])],
                    html_link=event.get('htmlLink', '')
                ))

            logger.info("events_listed", user_id=user_id, count=len(calendar_events))
            return calendar_events

        except HttpError as e:
            logger.error("calendar_api_error", user_id=user_id, error=str(e))
            return []
        except Exception as e:
            logger.error("list_events_error", user_id=user_id, error=str(e), exc_info=True)
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
        # Get events for the day
        day_start = date.replace(hour=work_hours_start, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=work_hours_end, minute=0, second=0, microsecond=0)

        events = await self.list_events(user_id, day_start, day_end)

        # Calculate free slots
        free_slots = []
        current_time = day_start

        for event in events:
            if current_time < event.start:
                # Free slot before this event
                duration = int((event.start - current_time).total_seconds() / 60)
                if duration >= 30:  # Minimum 30 minutes
                    free_slots.append(FreeSlot(
                        start=current_time,
                        end=event.start,
                        duration_minutes=duration
                    ))
            current_time = max(current_time, event.end)

        # Check if there's time left at end of day
        if current_time < day_end:
            duration = int((day_end - current_time).total_seconds() / 60)
            if duration >= 30:
                free_slots.append(FreeSlot(
                    start=current_time,
                    end=day_end,
                    duration_minutes=duration
                ))

        logger.info("free_slots_found", user_id=user_id, count=len(free_slots))
        return free_slots


# Global instance
calendar_service = GoogleCalendarService()
