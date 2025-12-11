"""Forum Activity Logger - logs user interactions to Telegram forum topics.

Each user gets their own topic in a Telegram forum group.
All messages and bot responses are logged for monitoring and support.

Uses a SEPARATE bot to avoid load on the main calendar bot.
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
import structlog
from telegram import Bot
from telegram.error import TelegramError

from app.config import settings
from app.services.encrypted_storage import EncryptedStorage
from app.services.analytics_service import analytics_service

logger = structlog.get_logger()


class ForumActivityLogger:
    """Service for logging user activity to Telegram forum topics.

    Creates a topic per user and logs all interactions there.
    Uses async queue to avoid blocking main request flow.
    Uses SEPARATE bot instance (not the main calendar bot).
    """

    # Topic icon colors (Telegram requires specific values)
    ICON_COLORS = [
        0x6FB9F0,  # Blue
        0xFFD67E,  # Yellow
        0xCB86DB,  # Purple
        0x8EEE98,  # Green
        0xFF93B2,  # Pink
        0xFB6F5F,  # Red
    ]

    def __init__(self, data_dir: str = "/var/lib/calendar-bot"):
        """Initialize forum logger with its own bot instance.

        Args:
            data_dir: Directory for storing topic mappings
        """
        # Create separate bot instance for logging
        if settings.forum_logger_bot_token:
            self.bot = Bot(token=settings.forum_logger_bot_token)
        else:
            self.bot = None

        self.storage = EncryptedStorage(data_dir=data_dir)
        self.topics_file = "forum_topics.json"
        self.topics: Dict[str, int] = {}  # user_id -> thread_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

        # Load existing topic mappings
        self._load_topics()

    def _load_topics(self):
        """Load topic mappings from storage."""
        try:
            data = self.storage.load(self.topics_file, default={'topics': {}})
            self.topics = {str(k): int(v) for k, v in data.get('topics', {}).items()}
            logger.info("forum_topics_loaded", count=len(self.topics))
        except Exception as e:
            logger.error("forum_topics_load_error", error=str(e))
            self.topics = {}

    def _save_topics(self):
        """Save topic mappings to storage."""
        try:
            data = {'topics': self.topics}
            self.storage.save(data, self.topics_file, encrypt=True)
        except Exception as e:
            logger.error("forum_topics_save_error", error=str(e))

    @property
    def enabled(self) -> bool:
        """Check if forum logging is enabled."""
        return (
            settings.forum_logger_enabled and
            settings.forum_logger_bot_token is not None and
            settings.forum_logger_chat_id is not None and
            self.bot is not None
        )

    def start(self):
        """Start the background worker."""
        if not self.enabled:
            logger.info("forum_logger_disabled")
            return

        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("forum_logger_started", chat_id=settings.forum_logger_chat_id)

    def stop(self):
        """Stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            logger.info("forum_logger_stopped")

    async def _worker(self):
        """Background worker that processes the message queue."""
        while self._running:
            try:
                # Wait for message with timeout
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process message
                await self._send_to_forum(item)
                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("forum_logger_worker_error", error=str(e))
                await asyncio.sleep(1)

    async def _send_to_forum(self, item: dict):
        """Send a message to the appropriate forum topic.

        Args:
            item: Dict with keys: user_id, user_name, text, is_bot_response
        """
        if not self.enabled:
            return

        user_id = item['user_id']
        user_name = item.get('user_name', f'User {user_id}')
        text = item['text']
        is_bot = item.get('is_bot_response', False)

        try:
            # Get or create topic for user
            thread_id = await self._get_or_create_topic(user_id, user_name)
            if not thread_id:
                return

            # Format message
            timestamp = datetime.now().strftime("%H:%M:%S")
            if is_bot:
                formatted = f"🤖 *Бот* [{timestamp}]:\n{text}"
            else:
                formatted = f"📩 *Пользователь* [{timestamp}]:\n{text}"

            # Send to topic
            await self.bot.send_message(
                chat_id=settings.forum_logger_chat_id,
                message_thread_id=thread_id,
                text=formatted,
                parse_mode="Markdown"
            )

        except TelegramError as e:
            logger.warning("forum_logger_send_error",
                          user_id=user_id,
                          error=str(e))

    async def _get_or_create_topic(self, user_id: str, user_name: str) -> Optional[int]:
        """Get existing topic or create new one for user.

        Args:
            user_id: Telegram user ID
            user_name: User display name

        Returns:
            Thread ID or None if failed
        """
        # Check if topic exists
        if user_id in self.topics:
            return self.topics[user_id]

        try:
            # Create new topic
            # Color based on user_id hash for consistency
            color_index = hash(user_id) % len(self.ICON_COLORS)
            icon_color = self.ICON_COLORS[color_index]

            topic = await self.bot.create_forum_topic(
                chat_id=settings.forum_logger_chat_id,
                name=f"👤 {user_name} ({user_id})",
                icon_color=icon_color
            )

            thread_id = topic.message_thread_id
            self.topics[user_id] = thread_id
            self._save_topics()

            logger.info("forum_topic_created",
                       user_id=user_id,
                       thread_id=thread_id,
                       name=user_name)

            # Send welcome message to topic
            await self.bot.send_message(
                chat_id=settings.forum_logger_chat_id,
                message_thread_id=thread_id,
                text=f"📋 *Лог активности пользователя*\n\n"
                     f"ID: `{user_id}`\n"
                     f"Имя: {user_name}\n"
                     f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode="Markdown"
            )

            return thread_id

        except TelegramError as e:
            logger.error("forum_topic_create_error",
                        user_id=user_id,
                        error=str(e))
            return None

    def log_user_message(
        self,
        user_id: str,
        user_name: str,
        message_text: str,
        is_voice: bool = False
    ):
        """Queue a user message for logging.

        Args:
            user_id: Telegram user ID
            user_name: User display name (first_name + username)
            message_text: Message content
            is_voice: Whether this was a voice message
        """
        if not self.enabled:
            return

        text = message_text
        if is_voice:
            text = f"[🎤 Голосовое]\n{message_text}"

        self._queue.put_nowait({
            'user_id': user_id,
            'user_name': user_name,
            'text': text,
            'is_bot_response': False
        })

    def log_bot_response(self, user_id: str, response_text: str):
        """Queue a bot response for logging.

        Args:
            user_id: Telegram user ID
            response_text: Bot's response
        """
        if not self.enabled:
            return

        # Truncate very long responses
        text = response_text
        if len(text) > 2000:
            text = text[:2000] + "\n... (обрезано)"

        self._queue.put_nowait({
            'user_id': user_id,
            'user_name': '',  # Not needed for bot responses
            'text': text,
            'is_bot_response': True
        })

    def log_event(
        self,
        user_id: str,
        user_name: str,
        event_type: str,
        details: str
    ):
        """Queue an event for logging.

        Args:
            user_id: Telegram user ID
            user_name: User display name
            event_type: Type of event (e.g., "event_created", "callback")
            details: Event details
        """
        if not self.enabled:
            return

        emoji_map = {
            'event_created': '📅',
            'event_deleted': '🗑',
            'event_updated': '✏️',
            'callback': '🔘',
            'command': '⚡',
            'error': '❌',
            'consent': '✅',
        }
        emoji = emoji_map.get(event_type, '📌')

        self._queue.put_nowait({
            'user_id': user_id,
            'user_name': user_name,
            'text': f"{emoji} *{event_type}*\n{details}",
            'is_bot_response': False
        })

    async def send_admin_daily_report(self) -> bool:
        """Send daily statistics report to admin via this bot.

        Uses the same bot (@dogovorarenda_bot) to send stats to admin's personal chat.
        This keeps all admin notifications in one place (same as smoke_test.sh).

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.warning("admin_report_skipped", reason="bot_not_initialized")
            return False

        if not settings.admin_user_id:
            logger.warning("admin_report_skipped", reason="admin_user_id_not_set")
            return False

        try:
            # Gather statistics from analytics service
            llm_stats = analytics_service.get_llm_cost_stats(hours=24)
            dashboard_stats = analytics_service.get_dashboard_stats()
            error_stats = analytics_service.get_error_stats(hours=24)

            # Format report message
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            message = f"""📊 <b>Статистика бота</b>

💰 <b>Yandex GPT (24ч):</b>
├ Запросов: {llm_stats['total_requests']}
├ Токенов: {llm_stats['total_tokens']:,}
├ Стоимость: {llm_stats['total_cost_rub']:.2f}₽
└ Ср./польз.: {llm_stats['avg_cost_per_user']:.2f}₽

👥 <b>Пользователи:</b>
├ Всего: {dashboard_stats.total_users}
├ Активных сегодня: {dashboard_stats.active_users_today}
└ Сообщений сегодня: {dashboard_stats.messages_today}

📅 <b>События:</b>
├ Всего: {dashboard_stats.total_events}
└ Сегодня: {dashboard_stats.events_today}

❌ <b>Ошибки (24ч):</b> {error_stats['total']}

🕐 {timestamp}"""

            # Send to admin's personal chat
            await self.bot.send_message(
                chat_id=int(settings.admin_user_id),
                text=message,
                parse_mode="HTML"
            )

            logger.info("admin_daily_report_sent",
                       admin_id=settings.admin_user_id,
                       llm_requests=llm_stats['total_requests'],
                       llm_cost=llm_stats['total_cost_rub'])
            return True

        except TelegramError as e:
            logger.error("admin_daily_report_failed",
                        admin_id=settings.admin_user_id,
                        error=str(e))
            return False
        except Exception as e:
            logger.error("admin_daily_report_error",
                        error=str(e),
                        exc_info=True)
            return False


# Global instance (initialized in run_polling.py)
forum_logger: Optional[ForumActivityLogger] = None
