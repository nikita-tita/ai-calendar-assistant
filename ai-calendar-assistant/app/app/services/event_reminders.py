"""Event reminders service for pre-event notifications."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set
import json
from pathlib import Path
import structlog
from telegram import Bot
from telegram.error import TelegramError

from app.services.calendar_radicale import calendar_service
from app.services.user_preferences import user_preferences
from app.services.translations import get_translation, Language
from app.utils.datetime_parser import format_datetime_human

logger = structlog.get_logger()


class EventRemindersService:
    """Service for sending pre-event reminders to users."""

    def __init__(self, bot: Bot, users_file: str = "/var/lib/calendar-bot/event_reminder_users.json"):
        """Initialize event reminders service."""
        self.bot = bot
        self.users_file = Path(users_file)
        self.active_users: Dict[str, int] = {}  # user_id -> chat_id mapping
        self.running = False
        self.sent_reminders: Set[str] = set()  # Track sent reminders (event_id + user_id)
        self.reminder_minutes = 30  # Remind 30 minutes before event

        # Load active users from file
        self._load_users()

    def _load_users(self):
        """Load active users from file."""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys back to proper types
                    self.active_users = {str(k): int(v) for k, v in data.items()}
                logger.info("event_reminder_users_loaded", count=len(self.active_users))
            else:
                logger.info("event_reminder_users_file_not_found", creating_new=True)
        except Exception as e:
            logger.error("event_reminder_users_load_error", error=str(e), exc_info=True)

    def _save_users(self):
        """Save active users to file."""
        try:
            self.users_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump(self.active_users, f)
        except Exception as e:
            logger.error("event_reminder_users_save_error", error=str(e), exc_info=True)

    def register_user(self, user_id: str, chat_id: int):
        """Register user for event reminders."""
        self.active_users[user_id] = chat_id
        self._save_users()
        logger.info("user_registered_for_event_reminders", user_id=user_id)

    async def send_event_reminder(self, user_id: str, chat_id: int, event: dict):
        """Send reminder for upcoming event."""
        try:
            # Get user language and timezone
            lang = user_preferences.get_language(user_id)
            user_tz = user_preferences.get_timezone(user_id)

            # Convert event time to user's timezone and format
            import pytz
            tz = pytz.timezone(user_tz)
            event_start_local = event['start'].astimezone(tz)
            event_time_str = format_datetime_human(event_start_local, locale=lang.value)

            # Get translation
            reminder_text = get_translation("event_reminder_30min", lang,
                                          title=event['title'],
                                          time=event_time_str)

            await self.bot.send_message(chat_id=chat_id, text=reminder_text)
            logger.info("event_reminder_sent",
                       user_id=user_id,
                       event_title=event['title'],
                       event_time=event['start'])

        except TelegramError as e:
            logger.error("event_reminder_telegram_error",
                        user_id=user_id,
                        error=str(e))
        except Exception as e:
            logger.error("event_reminder_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)

    async def check_upcoming_events(self):
        """Check for upcoming events and send reminders."""
        import pytz

        logger.info("checking_upcoming_events", active_users=len(self.active_users))

        for user_id, chat_id in list(self.active_users.items()):
            try:
                # Get user's timezone
                user_tz = user_preferences.get_timezone(user_id)
                tz = pytz.timezone(user_tz)
                now = datetime.now(tz)

                # Reminder window: 28-32 minutes from now (allows for check frequency variance)
                reminder_window_start = now + timedelta(minutes=self.reminder_minutes - 2)
                reminder_window_end = now + timedelta(minutes=self.reminder_minutes + 2)

                # Get events for the next hour
                start_time = now
                end_time = now + timedelta(hours=1)

                events = await calendar_service.list_events(
                    user_id,
                    start_time,
                    end_time
                )

                logger.info("events_fetched_for_reminders",
                           user_id=user_id,
                           events_count=len(events),
                           user_tz=user_tz,
                           now=now.isoformat())

                for event in events:
                    # Events come from calendar_service in UTC, convert to user timezone
                    event_start = event.start.astimezone(tz)

                    # Check if event is in reminder window (28-32 minutes from now)
                    if reminder_window_start <= event_start <= reminder_window_end:
                        # Create unique reminder ID
                        event_id = event.id if hasattr(event, 'id') else event.summary
                        reminder_id = f"{user_id}_{event_id}_{event_start.isoformat()}"

                        # Only send if not already sent
                        if reminder_id not in self.sent_reminders:
                            # Convert CalendarEvent to dict format for reminder
                            event_dict = {
                                'id': event.id,
                                'title': event.summary,
                                'start': event.start,
                                'end': event.end,
                                'description': event.description if hasattr(event, 'description') else None
                            }
                            await self.send_event_reminder(user_id, chat_id, event_dict)
                            self.sent_reminders.add(reminder_id)

                            # Clean up old reminders (older than 2 hours)
                            self._cleanup_old_reminders()

            except Exception as e:
                logger.error("check_upcoming_events_error",
                            user_id=user_id,
                            error=str(e))

    def _cleanup_old_reminders(self):
        """Clean up reminder IDs older than 2 hours to prevent memory buildup."""
        # Keep last 1000 reminders max
        if len(self.sent_reminders) > 1000:
            # Convert to list, keep last 500
            recent = list(self.sent_reminders)[-500:]
            self.sent_reminders = set(recent)

    async def run_reminder_schedule(self):
        """Run event reminder schedule - check every minute."""
        self.running = True
        logger.info("event_reminders_started",
                   reminder_minutes=self.reminder_minutes)

        while self.running:
            try:
                await self.check_upcoming_events()

                # Check every minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error("reminder_schedule_error", error=str(e))
                await asyncio.sleep(60)

    def stop(self):
        """Stop event reminders."""
        self.running = False
        logger.info("event_reminders_stopped")


# Global instance (will be initialized in main app)
event_reminders_service: EventRemindersService = None
