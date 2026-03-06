"""Follow-up service for post-event feedback collection.

Schedules follow-up messages after domain events (showings, calls, etc.)
and tracks responses for analytics.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import structlog
import pytz
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

logger = structlog.get_logger()

# Follow-up timing rules per event type
FOLLOWUP_DELAYS = {
    "showing": timedelta(hours=1),       # 1 hour after showing ends
    "client_call": timedelta(minutes=30), # 30 min after call
    "doc_signing": timedelta(hours=12),   # Next morning
    # "generic" and "dev_meeting" — no auto follow-up
}

# Max hour for same-day follow-up (after this, push to next morning 9:00)
MAX_FOLLOWUP_HOUR = 21
MORNING_FOLLOWUP_HOUR = 9


class FollowUpService:
    """Manages follow-up messages after calendar events."""

    def __init__(self, bot: Bot, db_path: str = "/var/lib/calendar-bot/followups.db"):
        self.bot = bot
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for follow-ups."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS follow_ups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    event_uid TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_title TEXT,
                    event_end_time TIMESTAMP NOT NULL,
                    follow_up_time TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'pending',
                    sent_at TIMESTAMP,
                    response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(event_uid, user_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_followup_pending
                ON follow_ups(status, follow_up_time)
                WHERE status = 'pending'
            """)
            conn.commit()
            conn.close()
            logger.info("followup_db_initialized", path=str(self.db_path))
        except Exception as e:
            logger.error("followup_db_init_error", error=str(e))

    def schedule_follow_up(
        self,
        user_id: str,
        chat_id: int,
        event_uid: str,
        event_type: str,
        event_title: str,
        event_end_time: datetime,
        user_timezone: str = "Europe/Moscow"
    ) -> bool:
        """Schedule a follow-up for an event.

        Returns True if scheduled, False if not applicable or error.
        """
        if event_type not in FOLLOWUP_DELAYS:
            return False

        delay = FOLLOWUP_DELAYS[event_type]
        follow_up_time = event_end_time + delay

        # If follow-up would be too late, push to next morning
        try:
            tz = pytz.timezone(user_timezone)
            fu_local = follow_up_time
            if fu_local.tzinfo is None:
                fu_local = tz.localize(fu_local)
            else:
                fu_local = fu_local.astimezone(tz)

            if fu_local.hour >= MAX_FOLLOWUP_HOUR:
                # Push to next morning
                next_day = fu_local + timedelta(days=1)
                follow_up_time = next_day.replace(
                    hour=MORNING_FOLLOWUP_HOUR, minute=0, second=0, microsecond=0
                )
                if follow_up_time.tzinfo:
                    follow_up_time = follow_up_time.replace(tzinfo=None)
        except Exception as e:
            logger.warning("followup_timezone_error", error=str(e))

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO follow_ups
                (user_id, chat_id, event_uid, event_type, event_title, event_end_time, follow_up_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, chat_id, event_uid, event_type,
                event_title, event_end_time.isoformat(),
                follow_up_time.isoformat()
            ))
            conn.commit()
            inserted = cursor.rowcount > 0
            conn.close()

            if inserted:
                logger.info("followup_scheduled",
                           user_id=user_id,
                           event_type=event_type,
                           event_title=event_title[:30],
                           follow_up_time=follow_up_time.isoformat())
            return inserted
        except Exception as e:
            logger.error("followup_schedule_error", error=str(e))
            return False

    async def check_and_send_follow_ups(self):
        """Check for pending follow-ups and send them. Called every minute."""
        now = datetime.now()
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, chat_id, event_uid, event_type, event_title
                FROM follow_ups
                WHERE status = 'pending' AND follow_up_time <= ?
                LIMIT 10
            """, (now.isoformat(),))
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            logger.error("followup_check_error", error=str(e))
            return

        for row in rows:
            fu_id, user_id, chat_id, event_uid, event_type, event_title = row
            await self._send_follow_up(fu_id, user_id, chat_id, event_uid, event_type, event_title)

    async def _send_follow_up(
        self, fu_id: int, user_id: str, chat_id: int,
        event_uid: str, event_type: str, event_title: str
    ):
        """Send a single follow-up message."""
        _type_questions = {
            "showing": f'Как прошёл показ "{event_title}"?',
            "client_call": f'Как прошёл звонок "{event_title}"?',
            "doc_signing": f'Как прошло подписание "{event_title}"?',
        }
        question = _type_questions.get(event_type, f'Как прошло "{event_title}"?')

        # Build inline keyboard based on event type
        if event_type == "showing":
            buttons = [
                [
                    InlineKeyboardButton("✅ Заинтересован", callback_data=f"followup:positive:{fu_id}"),
                    InlineKeyboardButton("🔄 Повторный", callback_data=f"followup:reschedule:{fu_id}"),
                ],
                [
                    InlineKeyboardButton("❌ Отказ", callback_data=f"followup:negative:{fu_id}"),
                    InlineKeyboardButton("⏭ Пропустить", callback_data=f"followup:skip:{fu_id}"),
                ],
            ]
        elif event_type == "client_call":
            buttons = [
                [
                    InlineKeyboardButton("✅ Договорились", callback_data=f"followup:positive:{fu_id}"),
                    InlineKeyboardButton("📞 Перезвонить", callback_data=f"followup:reschedule:{fu_id}"),
                ],
                [
                    InlineKeyboardButton("❌ Не ответил", callback_data=f"followup:negative:{fu_id}"),
                    InlineKeyboardButton("⏭ Пропустить", callback_data=f"followup:skip:{fu_id}"),
                ],
            ]
        else:
            buttons = [
                [
                    InlineKeyboardButton("✅ Успешно", callback_data=f"followup:positive:{fu_id}"),
                    InlineKeyboardButton("❌ Проблемы", callback_data=f"followup:negative:{fu_id}"),
                ],
                [
                    InlineKeyboardButton("⏭ Пропустить", callback_data=f"followup:skip:{fu_id}"),
                ],
            ]

        keyboard = InlineKeyboardMarkup(buttons)

        try:
            await self.bot.send_message(chat_id=chat_id, text=question, reply_markup=keyboard)
            # Mark as sent
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE follow_ups SET status = 'sent', sent_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), fu_id))
            conn.commit()
            conn.close()
            logger.info("followup_sent", user_id=user_id, fu_id=fu_id, event_type=event_type)
        except TelegramError as e:
            logger.error("followup_send_error", user_id=user_id, error=str(e))
            # Mark as skipped if chat not found
            if "chat not found" in str(e).lower() or "bot was blocked" in str(e).lower():
                self._update_status(fu_id, "skipped")

    def record_response(self, fu_id: int, response: str) -> Optional[Dict]:
        """Record user's follow-up response. Returns follow-up data for post-actions."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE follow_ups SET status = 'responded', response = ? WHERE id = ?
            """, (response, fu_id))
            # Get the follow-up data for post-actions
            cursor.execute("""
                SELECT user_id, event_uid, event_type, event_title
                FROM follow_ups WHERE id = ?
            """, (fu_id,))
            row = cursor.fetchone()
            conn.commit()
            conn.close()

            if row:
                logger.info("followup_response_recorded",
                           fu_id=fu_id, response=response, event_type=row[2])
                return {
                    "user_id": row[0],
                    "event_uid": row[1],
                    "event_type": row[2],
                    "event_title": row[3],
                    "response": response,
                }
            return None
        except Exception as e:
            logger.error("followup_record_error", error=str(e))
            return None

    def _update_status(self, fu_id: int, status: str):
        """Update follow-up status."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("UPDATE follow_ups SET status = ? WHERE id = ?", (status, fu_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("followup_status_update_error", error=str(e))

    def cleanup_old(self, days: int = 30):
        """Remove follow-ups older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM follow_ups WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            if deleted > 0:
                logger.info("followup_cleanup", deleted=deleted)
        except Exception as e:
            logger.error("followup_cleanup_error", error=str(e))


# Global instance (initialized in run_polling.py)
followup_service: Optional[FollowUpService] = None
