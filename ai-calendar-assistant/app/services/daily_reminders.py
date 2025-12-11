"""Daily reminders service for morning and evening messages."""

import asyncio
import sqlite3
from datetime import datetime, time, timedelta
from typing import Dict
import json
from pathlib import Path
import structlog
import pytz
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from app.config import settings
from app.services.calendar_radicale import calendar_service
from app.services.user_preferences import user_preferences
from app.services.translations import get_translation
from app.utils.datetime_parser import format_datetime_human
from app.services.analytics_service import analytics_service
from app.services.todos_service import todos_service

logger = structlog.get_logger()

# Test mode configuration
# When TEST_MODE is True, only TEST_USER_IDS will receive reminders at test times
TEST_MODE = False  # Production mode - all users receive reminders at their configured times
TEST_USER_IDS = {"2296243"}  # @nikita_tita - test user IDs (only used when TEST_MODE=True)


def is_time_match(current: time, target: time) -> bool:
    """Check if current time matches target time (same hour and minute)."""
    return current.hour == target.hour and current.minute == target.minute


def is_in_quiet_hours(current_time: time, start: time, end: time) -> bool:
    """
    Check if current time is within quiet hours.

    Args:
        current_time: Time to check
        start: Quiet hours start (e.g., 22:00)
        end: Quiet hours end (e.g., 08:00)

    Returns:
        True if in quiet hours, False otherwise
    """
    if start < end:
        # Normal range within same day (e.g., 08:00-22:00)
        return start <= current_time < end
    else:
        # Range crosses midnight (e.g., 22:00-08:00)
        return current_time >= start or current_time < end


class DailyRemindersService:
    """Service for sending daily reminders to users."""

    def __init__(self, bot: Bot, users_file: str = "/var/lib/calendar-bot/daily_reminder_users.json",
                 db_path: str = "/var/lib/calendar-bot/reminders.db"):
        """Initialize reminders service."""
        self.bot = bot
        self.users_file = Path(users_file)  # Legacy, kept for migration
        self.db_path = Path(db_path)
        self.running = False

        # Load active users from analytics SQLite (single source of truth)
        self._load_users()

        # Migrate from JSON if needed (one-time)
        self._migrate_json_users()

        # Initialize SQLite for idempotency (sent_daily_reminders table)
        self._init_database()

    @property
    def active_users(self) -> Dict[str, int]:
        """Get active users from analytics service (live query)."""
        return analytics_service.get_active_users()

    def _load_users(self):
        """Load active users from analytics SQLite."""
        users = analytics_service.get_active_users()
        logger.info("daily_reminder_users_loaded", count=len(users), source="analytics_sqlite")

    def _migrate_json_users(self):
        """One-time migration from JSON to SQLite."""
        if not self.users_file.exists():
            return

        try:
            with open(self.users_file, 'r') as f:
                json_users = json.load(f)

            if not json_users:
                return

            # Check if migration needed (SQLite has fewer users)
            sqlite_users = analytics_service.get_active_users()
            if len(sqlite_users) >= len(json_users):
                logger.info("migration_skipped", reason="sqlite_has_users")
                return

            # Migrate each user
            migrated = 0
            for user_id, chat_id in json_users.items():
                analytics_service.ensure_user(str(user_id), int(chat_id))
                migrated += 1

            logger.info("json_users_migrated_to_sqlite", count=migrated)

            # Rename old file to backup
            backup_path = self.users_file.with_suffix('.json.migrated')
            self.users_file.rename(backup_path)
            logger.info("json_file_backed_up", path=str(backup_path))

        except Exception as e:
            logger.error("json_migration_error", error=str(e), exc_info=True)

    def _init_database(self):
        """Initialize SQLite database for tracking sent daily reminders."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sent_daily_reminders (
                    user_id TEXT NOT NULL,
                    reminder_date TEXT NOT NULL,
                    reminder_type TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, reminder_date, reminder_type)
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_sent_at
                ON sent_daily_reminders(sent_at)
            ''')
            conn.commit()
            conn.close()
            logger.info("daily_reminders_database_initialized", path=str(self.db_path))
        except Exception as e:
            logger.error("daily_reminders_database_init_error", error=str(e))

    def _is_daily_reminder_sent(self, user_id: str, date_str: str, reminder_type: str) -> bool:
        """
        Check if daily reminder was already sent.

        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            reminder_type: 'morning', 'motivation', or 'evening'

        Returns:
            True if already sent, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                'SELECT 1 FROM sent_daily_reminders WHERE user_id = ? AND reminder_date = ? AND reminder_type = ?',
                (user_id, date_str, reminder_type)
            )
            result = cursor.fetchone() is not None
            conn.close()
            return result
        except Exception as e:
            logger.error("check_daily_reminder_error", error=str(e))
            return False  # Allow sending if check fails

    def _record_daily_reminder(self, user_id: str, date_str: str, reminder_type: str):
        """
        Record that daily reminder was sent.

        Args:
            user_id: User ID
            date_str: Date in YYYY-MM-DD format
            reminder_type: 'morning', 'motivation', or 'evening'
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                '''INSERT OR REPLACE INTO sent_daily_reminders
                   (user_id, reminder_date, reminder_type, sent_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)''',
                (user_id, date_str, reminder_type)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("record_daily_reminder_error", error=str(e))

    def cleanup_old_daily_reminders(self, days: int = 7):
        """Remove daily reminder records older than specified days."""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.execute(
                'DELETE FROM sent_daily_reminders WHERE sent_at < ?',
                (cutoff.isoformat(),)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted_count > 0:
                logger.info("old_daily_reminders_cleaned", count=deleted_count, days=days)
        except Exception as e:
            logger.error("cleanup_daily_reminders_error", error=str(e))

    def register_user(self, user_id: str, chat_id: int):
        """Register user for daily reminders (writes to analytics SQLite)."""
        analytics_service.ensure_user(str(user_id), int(chat_id))
        logger.info("user_registered_for_reminders", user_id=user_id)

    def unregister_user(self, user_id: str):
        """Unregister user from daily reminders (e.g., when chat is not found)."""
        analytics_service.deactivate_user(str(user_id))
        logger.info("user_unregistered_from_reminders", user_id=user_id)

    async def _get_user_todos(self, user_id: str) -> tuple:
        """
        Get user's incomplete and today-completed todos.

        Returns:
            Tuple of (incomplete_todos, completed_today_todos)
        """
        try:
            all_todos = await todos_service.list_todos(user_id)
            incomplete = [t for t in all_todos if not t.completed]
            # Get todos completed today
            today = datetime.now().date()
            completed_today = [
                t for t in all_todos
                if t.completed and t.updated_at.date() == today
            ]
            return incomplete, completed_today
        except Exception as e:
            logger.error("get_user_todos_error", user_id=user_id, error=str(e))
            return [], []

    def _format_task_list(self, tasks: list, max_items: int = 5) -> str:
        """Format task list with truncation."""
        if not tasks:
            return ""

        lines = []
        for i, task in enumerate(tasks[:max_items]):
            title = task.title[:40] + "..." if len(task.title) > 40 else task.title
            lines.append(f"• {title}")

        if len(tasks) > max_items:
            remaining = len(tasks) - max_items
            lines.append(f"...и ещё {remaining}")

        return "\n".join(lines)

    async def send_morning_reminder(self, user_id: str, chat_id: int):
        """Send morning reminder with today's events and tasks."""
        try:
            # Get user's language and timezone
            lang = user_preferences.get_language(user_id)
            user_tz_str = user_preferences.get_timezone(user_id)
            user_tz = pytz.timezone(user_tz_str)

            # Get current date in user's timezone
            now_user_tz = datetime.now(user_tz)

            # Get today's events
            start_of_day = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            events = await calendar_service.list_events(user_id, start_of_day, end_of_day)

            # Format events list
            today_events = []
            for e in events:
                event_start = e.start
                if event_start.tzinfo is None:
                    event_start = pytz.UTC.localize(event_start)
                event_start_local = event_start.astimezone(user_tz)
                today_events.append({
                    'start': event_start_local,
                    'title': e.summary
                })
            today_events.sort(key=lambda x: x['start'])

            # Get user's incomplete tasks
            incomplete_todos, _ = await self._get_user_todos(user_id)

            events_count = len(today_events)
            tasks_count = len(incomplete_todos)

            # Build greeting
            greeting = get_translation("morning_greeting", lang)
            parts = [greeting, ""]

            # Determine scenario and build message
            if events_count == 0 and tasks_count == 0:
                # Scenario 1: Empty day
                parts.append(get_translation("morning_empty_day", lang))
                parts.append("")
                parts.append(get_translation("morning_empty_suggestions", lang))

            elif events_count == 0 and tasks_count > 0:
                # Scenario 2: Tasks only
                parts.append(get_translation("morning_no_meetings", lang))
                parts.append("")
                parts.append(get_translation("morning_tasks_header", lang, count=tasks_count))
                parts.append(self._format_task_list(incomplete_todos))
                parts.append("")
                parts.append(get_translation("morning_productive", lang))

            elif events_count > 0 and tasks_count == 0:
                # Scenario 3: Events only
                parts.append(get_translation("morning_meetings_header", lang, count=events_count))
                events_list = "\n".join([
                    f"• {e['start'].strftime('%H:%M')} - {e['title'][:40]}"
                    for e in today_events[:7]
                ])
                parts.append(events_list)
                parts.append("")
                parts.append(get_translation("morning_add_tasks", lang))
                parts.append("")
                parts.append(get_translation("morning_good_deals", lang))

            else:
                # Scenario 4: Full day (events + tasks)
                parts.append(get_translation("morning_meetings_header", lang, count=events_count))
                events_list = "\n".join([
                    f"• {e['start'].strftime('%H:%M')} - {e['title'][:40]}"
                    for e in today_events[:7]
                ])
                parts.append(events_list)
                parts.append("")
                parts.append(get_translation("morning_and_tasks", lang, count=tasks_count))
                parts.append(self._format_task_list(incomplete_todos))
                parts.append("")
                parts.append(get_translation("morning_full_day", lang))

            message = "\n".join(parts)
            await self.bot.send_message(chat_id=chat_id, text=message)
            logger.info("morning_reminder_sent", user_id=user_id,
                       events_count=events_count, tasks_count=tasks_count)

        except TelegramError as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning("chat_not_found_unregistering", user_id=user_id, error=str(e))
                self.unregister_user(user_id)
            else:
                logger.error("morning_reminder_failed", user_id=user_id, error=str(e))
        except Exception as e:
            logger.error("morning_reminder_error", user_id=user_id, error=str(e), exc_info=True)

    async def send_morning_motivation(self, user_id: str, chat_id: int):
        """Send morning motivational message at 10:00 AM."""
        try:
            # Get user's language and current motivation index
            lang = user_preferences.get_language(user_id)
            current_index = user_preferences.get_motivation_index(user_id)

            # Get motivational message
            message_key = f"morning_motivation_{current_index}"
            message = get_translation(message_key, lang)

            # Create inline keyboard with action button
            button_text = get_translation("motivation_btn_action", lang)
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text, callback_data=f"motivation_action:{user_id}")]
            ])

            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=keyboard
            )

            # Increment index for next day
            user_preferences.increment_motivation_index(user_id)

            logger.info("morning_motivation_sent", user_id=user_id, message_index=current_index)

        except TelegramError as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning("chat_not_found_unregistering", user_id=user_id, error=str(e))
                self.unregister_user(user_id)
            else:
                logger.error("morning_motivation_failed", user_id=user_id, error=str(e))
        except Exception as e:
            logger.error("morning_motivation_error", user_id=user_id, error=str(e))

    async def send_evening_reminder(self, user_id: str, chat_id: int):
        """Send evening summary with tasks status and optional admin stats."""
        try:
            # Get user's language and timezone
            lang = user_preferences.get_language(user_id)
            user_tz_str = user_preferences.get_timezone(user_id)
            user_tz = pytz.timezone(user_tz_str)

            # Get current date in user's timezone
            now_user_tz = datetime.now(user_tz)

            # Get today's events count
            start_of_day = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            events = await calendar_service.list_events(user_id, start_of_day, end_of_day)
            events_count = len(events)

            # Get tasks: incomplete and completed today
            incomplete_todos, completed_today = await self._get_user_todos(user_id)
            incomplete_count = len(incomplete_todos)
            completed_count = len(completed_today)
            total_tasks = incomplete_count + completed_count

            parts = []

            # Determine scenario
            has_activity = events_count > 0 or total_tasks > 0

            if not has_activity:
                # Scenario 3: Quiet day
                parts.append(get_translation("evening_quiet_day", lang))
                parts.append("")
                parts.append(get_translation("evening_plan_tomorrow", lang))

            elif incomplete_count > 0:
                # Scenario 1: Has remaining tasks
                parts.append(get_translation("evening_summary_header", lang))
                parts.append("")

                # Show stats based on what we have
                if events_count > 0 and total_tasks > 0:
                    parts.append(get_translation("evening_stats", lang,
                                                events=events_count,
                                                completed=completed_count,
                                                total=total_tasks))
                elif events_count > 0:
                    parts.append(get_translation("evening_stats_events_only", lang,
                                                events=events_count))
                else:
                    parts.append(get_translation("evening_stats_tasks_only", lang,
                                                completed=completed_count,
                                                total=total_tasks))

                parts.append("")
                parts.append(get_translation("evening_remaining_header", lang))
                parts.append(self._format_task_list(incomplete_todos))
                parts.append("")
                parts.append(get_translation("evening_rest_tomorrow", lang))

            else:
                # Scenario 2: All done
                parts.append(get_translation("evening_all_done_header", lang))
                parts.append("")

                if events_count > 0 or completed_count > 0:
                    parts.append(get_translation("evening_all_done_stats", lang,
                                                events=events_count,
                                                tasks=completed_count))
                    parts.append("")

                parts.append(get_translation("evening_keep_going", lang))

            message = "\n".join(parts)

            # Add LLM cost stats for admin user
            if settings.admin_user_id and user_id == settings.admin_user_id:
                llm_stats = analytics_service.get_llm_cost_stats(hours=24)
                dashboard_stats = analytics_service.get_dashboard_stats()
                error_stats = analytics_service.get_error_stats(hours=24)

                admin_section = f"""

━━━━━━━━━━━━━━━━━━
📊 *Статистика бота*

💰 *Yandex GPT (24ч):*
├ Запросов: {llm_stats['total_requests']}
├ Токенов: {llm_stats['total_tokens']:,}
├ Стоимость: {llm_stats['total_cost_rub']:.2f}₽
└ Ср./польз.: {llm_stats['avg_cost_per_user']:.2f}₽

👥 *Пользователи:*
├ Всего: {dashboard_stats.total_users}
├ Активных: {dashboard_stats.active_users_today}
└ Сообщений: {dashboard_stats.messages_today}

❌ Ошибок: {error_stats['total']}"""
                message += admin_section

            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            logger.info("evening_reminder_sent", user_id=user_id,
                       events_count=events_count, tasks_incomplete=incomplete_count,
                       tasks_completed=completed_count,
                       is_admin=(user_id == settings.admin_user_id))

        except TelegramError as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning("chat_not_found_unregistering", user_id=user_id, error=str(e))
                self.unregister_user(user_id)
            else:
                logger.error("evening_reminder_failed", user_id=user_id, error=str(e))
        except Exception as e:
            logger.error("evening_reminder_error", user_id=user_id, error=str(e), exc_info=True)

    async def run_daily_schedule(self):
        """Run daily reminder schedule."""
        self.running = True
        logger.info("daily_reminders_started",
                   test_mode=TEST_MODE,
                   active_users_count=len(self.active_users))

        # Log check counter (every 10 minutes)
        check_counter = 0

        while self.running:
            try:
                utc_now = datetime.now(pytz.UTC)
                check_counter += 1

                # Log status every 10 minutes (10 checks)
                if check_counter % 10 == 0:
                    logger.info("daily_reminders_check",
                               utc_time=utc_now.strftime('%H:%M'),
                               active_users=len(self.active_users),
                               checks_done=check_counter)

                # Cleanup old reminder records at 3:00 UTC
                if utc_now.hour == 3 and utc_now.minute == 0:
                    self.cleanup_old_daily_reminders(days=7)

                # Check each user's local time
                for user_id, chat_id in list(self.active_users.items()):
                    try:
                        # Get user's timezone and preferences
                        user_tz_str = user_preferences.get_timezone(user_id)
                        user_tz = pytz.timezone(user_tz_str)
                        user_local_time = utc_now.astimezone(user_tz)
                        user_time = user_local_time.time()

                        # Get user's reminder settings
                        morning_enabled = user_preferences.get_morning_summary_enabled(user_id)
                        morning_time_str = user_preferences.get_morning_summary_time(user_id)
                        evening_enabled = user_preferences.get_evening_digest_enabled(user_id)
                        evening_time_str = user_preferences.get_evening_digest_time(user_id)
                        quiet_start_str, quiet_end_str = user_preferences.get_quiet_hours(user_id)

                        # Parse time strings to time objects
                        morning_hour, morning_min = map(int, morning_time_str.split(':'))
                        morning_time = time(morning_hour, morning_min)
                        evening_hour, evening_min = map(int, evening_time_str.split(':'))
                        evening_time = time(evening_hour, evening_min)
                        quiet_start_hour, quiet_start_min = map(int, quiet_start_str.split(':'))
                        quiet_start = time(quiet_start_hour, quiet_start_min)
                        quiet_end_hour, quiet_end_min = map(int, quiet_end_str.split(':'))
                        quiet_end = time(quiet_end_hour, quiet_end_min)

                        # Check if current time is in quiet hours (using module-level function)
                        in_quiet_hours = is_in_quiet_hours(user_time, quiet_start, quiet_end)

                        # Get date string for idempotency check
                        user_date_str = user_local_time.strftime('%Y-%m-%d')

                        # Determine if this is a test user
                        is_test_user = user_id in TEST_USER_IDS

                        # Use different schedules for test and production users
                        if TEST_MODE and is_test_user:
                            # TEST SCHEDULE for test users only
                            # Morning reminder at 12:37 (normally user's configured time)
                            if time(12, 37) <= user_time < time(12, 38):
                                if morning_enabled and not in_quiet_hours:
                                    if not self._is_daily_reminder_sent(user_id, user_date_str, 'morning'):
                                        await self.send_morning_reminder(user_id, chat_id)
                                        self._record_daily_reminder(user_id, user_date_str, 'morning')
                                        await asyncio.sleep(1)  # Rate limiting

                            # Morning motivation at 12:39 (normally 10:00)
                            elif time(12, 39) <= user_time < time(12, 40):
                                if not in_quiet_hours:
                                    if not self._is_daily_reminder_sent(user_id, user_date_str, 'motivation'):
                                        await self.send_morning_motivation(user_id, chat_id)
                                        self._record_daily_reminder(user_id, user_date_str, 'motivation')
                                        await asyncio.sleep(1)  # Rate limiting

                            # Evening reminder at 21:00 (normally user's configured time)
                            elif time(21, 0) <= user_time < time(21, 1):
                                if evening_enabled and not in_quiet_hours:
                                    if not self._is_daily_reminder_sent(user_id, user_date_str, 'evening'):
                                        await self.send_evening_reminder(user_id, chat_id)
                                        self._record_daily_reminder(user_id, user_date_str, 'evening')
                                        await asyncio.sleep(1)  # Rate limiting

                        else:
                            # PRODUCTION SCHEDULE - uses user's configured times
                            current_minute_time = time(user_time.hour, user_time.minute)

                            # Morning reminder at user's configured time
                            if morning_enabled and not in_quiet_hours:
                                if is_time_match(current_minute_time, morning_time):
                                    if not self._is_daily_reminder_sent(user_id, user_date_str, 'morning'):
                                        await self.send_morning_reminder(user_id, chat_id)
                                        self._record_daily_reminder(user_id, user_date_str, 'morning')
                                        await asyncio.sleep(1)  # Rate limiting

                            # Morning motivation at 10:00 (only if morning reminders enabled)
                            if morning_enabled and not in_quiet_hours and is_time_match(current_minute_time, time(10, 0)):
                                if not self._is_daily_reminder_sent(user_id, user_date_str, 'motivation'):
                                    await self.send_morning_motivation(user_id, chat_id)
                                    self._record_daily_reminder(user_id, user_date_str, 'motivation')
                                    await asyncio.sleep(1)  # Rate limiting

                            # Evening reminder at user's configured time
                            if evening_enabled and not in_quiet_hours:
                                if is_time_match(current_minute_time, evening_time):
                                    if not self._is_daily_reminder_sent(user_id, user_date_str, 'evening'):
                                        await self.send_evening_reminder(user_id, chat_id)
                                        self._record_daily_reminder(user_id, user_date_str, 'evening')
                                        await asyncio.sleep(1)  # Rate limiting

                    except Exception as e:
                        logger.error("user_schedule_check_error", user_id=user_id, error=str(e))

                # Check every minute
                await asyncio.sleep(60)

            except Exception as e:
                logger.error("daily_schedule_error", error=str(e))
                await asyncio.sleep(60)

    def stop(self):
        """Stop daily reminders."""
        self.running = False
        logger.info("daily_reminders_stopped")


# Global instance (will be initialized in main app)
reminders_service: DailyRemindersService = None
