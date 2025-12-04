"""Event reminders service with SQLite-based idempotency."""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import Dict
from pathlib import Path
import structlog
from telegram import Bot
from telegram.error import TelegramError
import pytz

from app.services.calendar_radicale import calendar_service
from app.services.user_preferences import user_preferences
from app.services.translations import get_translation, Language
from app.utils.datetime_parser import format_datetime_human

logger = structlog.get_logger()


class EventRemindersServiceIdempotent:
    """
    Service for sending pre-event reminders with idempotency.

    Features:
    - SQLite database for tracking sent reminders
    - Prevents duplicate reminders after restarts
    - Automatic cleanup of old reminder records
    - 28-32 minute window for reliability
    """

    def __init__(
        self,
        bot: Bot,
        db_path: str = "/var/lib/calendar-bot/reminders.db",
        users_file: str = "/var/lib/calendar-bot/event_reminder_users.json"
    ):
        """Initialize event reminders service."""
        self.bot = bot
        self.db_path = Path(db_path)
        self.running = False
        self.reminder_minutes = 30  # Remind 30 minutes before event
        self.reminder_window_min = 28  # Minimum minutes before
        self.reminder_window_max = 32  # Maximum minutes before

        # Initialize SQLite database
        self._init_database()

        logger.info("event_reminders_idempotent_initialized",
                   db_path=str(self.db_path),
                   reminder_minutes=self.reminder_minutes)

    def _init_database(self):
        """Initialize SQLite database for tracking sent reminders."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sent_reminders (
                event_uid TEXT NOT NULL,
                user_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                event_start TIMESTAMP NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (event_uid, user_id)
            )
        ''')

        # Create index for faster queries
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_sent_at ON sent_reminders(sent_at)
        ''')

        conn.commit()
        conn.close()

        logger.info("reminders_database_initialized", path=str(self.db_path))

    def _is_reminder_sent(self, event_uid: str, user_id: str) -> bool:
        """
        Check if reminder was already sent for this event and user.

        Args:
            event_uid: Event UID
            user_id: User ID

        Returns:
            True if reminder was already sent, False otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            'SELECT 1 FROM sent_reminders WHERE event_uid = ? AND user_id = ?',
            (event_uid, user_id)
        )
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def _record_sent_reminder(
        self,
        event_uid: str,
        user_id: str,
        chat_id: int,
        event_start: datetime
    ):
        """
        Record that reminder was sent.

        Args:
            event_uid: Event UID
            user_id: User ID
            chat_id: Telegram chat ID
            event_start: Event start time
        """
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                '''INSERT OR REPLACE INTO sent_reminders
                   (event_uid, user_id, chat_id, event_start, sent_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                (event_uid, user_id, chat_id, event_start.isoformat())
            )
            conn.commit()
        except Exception as e:
            logger.error("failed_to_record_reminder", error=str(e))
        finally:
            conn.close()

    def cleanup_old_reminders(self, days: int = 7):
        """
        Remove reminder records older than specified days.

        Args:
            days: Number of days to keep records
        """
        cutoff = datetime.now() - timedelta(days=days)
        conn = sqlite3.connect(str(self.db_path))

        cursor = conn.execute(
            'DELETE FROM sent_reminders WHERE sent_at < ?',
            (cutoff.isoformat(),)
        )
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted_count > 0:
            logger.info("old_reminders_cleaned", count=deleted_count, days=days)

    async def check_and_send_reminders(self):
        """Check for upcoming events and send reminders."""
        try:
            # Get all users who want event reminders
            # For now, we use daily_reminder_users as proxy
            from app.services.daily_reminders import daily_reminders_service

            if not hasattr(daily_reminders_service, 'active_users'):
                logger.warning("no_active_users_for_reminders")
                return

            for user_id, chat_id in daily_reminders_service.active_users.items():
                try:
                    await self._check_user_events(user_id, chat_id)
                except Exception as e:
                    logger.error("check_user_events_error",
                               user_id=user_id,
                               error=str(e))

        except Exception as e:
            logger.error("check_reminders_error", error=str(e), exc_info=True)

    async def _check_user_events(self, user_id: str, chat_id: int):
        """
        Check events for a specific user and send reminders.

        Args:
            user_id: User ID
            chat_id: Telegram chat ID
        """
        # Get user's timezone
        user_tz_str = user_preferences.get_timezone(user_id)
        user_tz = pytz.timezone(user_tz_str)
        now = datetime.now(user_tz)

        # Get events in the next hour
        time_min = now
        time_max = now + timedelta(hours=1)

        # Fetch events from calendar
        events = await calendar_service.list_events(user_id, time_min, time_max)

        for event in events:
            try:
                # Convert event time to user timezone
                event_start = event.start
                if event_start.tzinfo is None:
                    event_start = pytz.UTC.localize(event_start)
                event_start_local = event_start.astimezone(user_tz)

                # Calculate time until event
                time_until_event = event_start_local - now
                minutes_until = time_until_event.total_seconds() / 60

                # Check if within reminder window (28-32 minutes)
                if self.reminder_window_min <= minutes_until <= self.reminder_window_max:
                    # Check if reminder already sent
                    if self._is_reminder_sent(event.id, user_id):
                        logger.debug("reminder_already_sent",
                                   user_id=user_id,
                                   event_id=event.id)
                        continue

                    # Send reminder
                    await self._send_reminder(
                        user_id,
                        chat_id,
                        event,
                        event_start_local
                    )

                    # Record that reminder was sent
                    self._record_sent_reminder(
                        event.id,
                        user_id,
                        chat_id,
                        event_start_local
                    )

            except Exception as e:
                logger.error("process_event_reminder_error",
                           user_id=user_id,
                           event_id=getattr(event, 'id', 'unknown'),
                           error=str(e))

    async def _send_reminder(
        self,
        user_id: str,
        chat_id: int,
        event,
        event_start_local: datetime
    ):
        """
        Send reminder message to user.

        Args:
            user_id: User ID
            chat_id: Telegram chat ID
            event: Event object
            event_start_local: Event start time in user's timezone
        """
        try:
            # Get user's language
            lang = user_preferences.get_language(user_id)

            # Format time
            time_str = event_start_local.strftime('%H:%M')

            # Build reminder message
            reminder_text = get_translation("reminder_upcoming", lang) or "⏰ Напоминание!"
            event_name = get_translation("event_name", lang) or "Событие"
            time_label = get_translation("time_label", lang) or "Время"
            location_label = get_translation("location_label", lang) or "Место"
            minutes_30 = get_translation("in_30_minutes", lang) or "Через 30 минут"

            message = f"{reminder_text}\n\n"
            message += f"📅 {minutes_30}: {event.summary}\n"
            message += f"🕐 {time_label}: {time_str}\n"

            if event.location:
                message += f"📍 {location_label}: {event.location}\n"

            # Send message
            await self.bot.send_message(chat_id=chat_id, text=message)

            logger.info("reminder_sent",
                       user_id=user_id,
                       event_id=event.id,
                       event_title=event.summary[:50])

        except TelegramError as e:
            error_msg = str(e).lower()
            # Unregister user if chat not found (user blocked bot or deleted account)
            if "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning("chat_not_found_event_reminder", user_id=user_id, error=str(e))
                # Unregister from daily_reminders (source of truth)
                try:
                    from app.services.daily_reminders import daily_reminders_service
                    if daily_reminders_service:
                        daily_reminders_service.unregister_user(user_id)
                except Exception as unreg_error:
                    logger.error("unregister_user_failed", user_id=user_id, error=str(unreg_error))
            else:
                logger.error("telegram_send_reminder_error",
                            user_id=user_id,
                            error=str(e))
        except Exception as e:
            logger.error("send_reminder_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)

    async def run_reminder_loop(self):
        """Main loop for checking and sending reminders."""
        self.running = True
        logger.info("event_reminders_loop_started")

        while self.running:
            try:
                # Check for reminders every minute
                await self.check_and_send_reminders()

                # Cleanup old reminders once per day (at 3 AM)
                now = datetime.now()
                if now.hour == 3 and now.minute == 0:
                    self.cleanup_old_reminders(days=7)

                # Wait 1 minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error("reminder_loop_error", error=str(e), exc_info=True)
                await asyncio.sleep(60)

        logger.info("event_reminders_loop_stopped")

    def stop(self):
        """Stop the reminder loop."""
        self.running = False
        logger.info("event_reminders_stop_requested")


# Global instance - will be initialized by application
event_reminders_service: EventRemindersServiceIdempotent = None


def init_event_reminders(bot: Bot):
    """Initialize global event reminders service."""
    global event_reminders_service
    event_reminders_service = EventRemindersServiceIdempotent(bot)
    logger.info("event_reminders_global_initialized")


def get_event_reminders() -> EventRemindersServiceIdempotent:
    """Get event reminders service instance."""
    if event_reminders_service is None:
        raise RuntimeError("Event reminders not initialized")
    return event_reminders_service
