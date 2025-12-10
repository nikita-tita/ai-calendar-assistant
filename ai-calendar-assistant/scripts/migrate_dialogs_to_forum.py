#!/usr/bin/env python3
"""Migrate historical dialogs from analytics to forum topics.

This script:
1. Reads all user dialogs from analytics
2. Creates a topic per user in the forum
3. Posts historical messages to each topic

Run inside docker container:
    docker exec telegram-bot python3 scripts/migrate_dialogs_to_forum.py
"""

import asyncio
import sys
from datetime import datetime
from typing import List, Dict

# Add app to path
sys.path.insert(0, "/app")

from telegram import Bot
from telegram.error import TelegramError, RetryAfter
from app.config import settings
from app.services.analytics_service import analytics_service
from app.services.encrypted_storage import EncryptedStorage
from app.models.analytics import ActionType

import structlog
logger = structlog.get_logger()


# Action types that represent user messages
USER_MESSAGE_TYPES = [
    ActionType.TEXT_MESSAGE,
    ActionType.VOICE_MESSAGE,
]

# Action types that represent bot responses
BOT_RESPONSE_TYPES = [
    ActionType.BOT_RESPONSE,
]

# Event types to log
EVENT_TYPES = [
    ActionType.EVENT_CREATE,
    ActionType.EVENT_UPDATE,
    ActionType.EVENT_DELETE,
]

# Topic icon colors
ICON_COLORS = [
    0x6FB9F0,  # Blue
    0xFFD67E,  # Yellow
    0xCB86DB,  # Purple
    0x8EEE98,  # Green
    0xFF93B2,  # Pink
    0xFB6F5F,  # Red
]


async def get_or_create_topic(bot: Bot, chat_id: int, user_id: str, user_name: str, storage: EncryptedStorage, topics: Dict[str, int]) -> int:
    """Get existing topic or create new one."""
    if user_id in topics:
        return topics[user_id]

    for attempt in range(5):
        try:
            color_index = hash(user_id) % len(ICON_COLORS)
            topic = await bot.create_forum_topic(
                chat_id=chat_id,
                name=f"👤 {user_name[:20]} ({user_id})",
                icon_color=ICON_COLORS[color_index]
            )
            thread_id = topic.message_thread_id
            topics[user_id] = thread_id

            # Save updated topics
            storage.save({'topics': topics}, "forum_topics.json", encrypt=True)

            logger.info("topic_created", user_id=user_id, thread_id=thread_id)
            return thread_id

        except RetryAfter as e:
            logger.warning("topic_create_rate_limit", user_id=user_id, retry_after=e.retry_after)
            await asyncio.sleep(e.retry_after + 1)
        except TelegramError as e:
            logger.error("topic_create_error", user_id=user_id, error=str(e))
            return None

    return None


async def send_message_safe(bot: Bot, chat_id: int, thread_id: int, text: str, retries: int = 3):
    """Send message with retry on rate limit."""
    for attempt in range(retries):
        try:
            await bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="Markdown"
            )
            return True
        except RetryAfter as e:
            logger.warning("rate_limit", retry_after=e.retry_after)
            await asyncio.sleep(e.retry_after + 1)
        except TelegramError as e:
            logger.error("send_error", error=str(e))
            return False
    return False


async def migrate_user_dialog(bot: Bot, chat_id: int, user_id: str, user_name: str, storage: EncryptedStorage, topics: Dict[str, int]):
    """Migrate one user's dialog history."""

    # Get or create topic
    thread_id = await get_or_create_topic(bot, chat_id, user_id, user_name, storage, topics)
    if not thread_id:
        return 0

    # Get user dialog
    dialog = analytics_service.get_user_dialog(user_id, limit=1000)
    if not dialog:
        return 0

    # Send header
    await send_message_safe(
        bot, chat_id, thread_id,
        f"📋 *История диалога*\n\n"
        f"Пользователь: {user_name}\n"
        f"ID: `{user_id}`\n"
        f"Сообщений: {len(dialog)}\n"
        f"---"
    )

    # Batch messages to avoid rate limits
    batch = []
    batch_size = 0
    messages_sent = 0

    for entry in dialog:
        # Format message based on type
        ts = entry.timestamp.strftime("%d.%m %H:%M")

        if entry.action_type in USER_MESSAGE_TYPES:
            emoji = "🎤" if entry.action_type == ActionType.VOICE_MESSAGE else "📩"
            text = f"{emoji} [{ts}] *Пользователь:*\n{entry.details or '[пусто]'}"
        elif entry.action_type in BOT_RESPONSE_TYPES:
            text = f"🤖 [{ts}] *Бот:*\n{entry.details or '[пусто]'}"
        elif entry.action_type in EVENT_TYPES:
            emoji_map = {
                ActionType.EVENT_CREATE: "📅",
                ActionType.EVENT_UPDATE: "✏️",
                ActionType.EVENT_DELETE: "🗑",
            }
            emoji = emoji_map.get(entry.action_type, "📌")
            text = f"{emoji} [{ts}] *{entry.action_type}*\n{entry.details or ''}"
        else:
            continue  # Skip other action types

        # Truncate long messages
        if len(text) > 500:
            text = text[:497] + "..."

        batch.append(text)
        batch_size += len(text)

        # Send batch when it gets large enough
        if batch_size > 3000 or len(batch) >= 10:
            combined = "\n\n".join(batch)
            if await send_message_safe(bot, chat_id, thread_id, combined):
                messages_sent += len(batch)
            batch = []
            batch_size = 0
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)

    # Send remaining batch
    if batch:
        combined = "\n\n".join(batch)
        if await send_message_safe(bot, chat_id, thread_id, combined):
            messages_sent += len(batch)

    return messages_sent


async def main():
    """Main migration function."""

    # Check config
    if not settings.forum_logger_bot_token:
        print("ERROR: FORUM_LOGGER_BOT_TOKEN not set")
        return

    if not settings.forum_logger_chat_id:
        print("ERROR: FORUM_LOGGER_CHAT_ID not set")
        return

    chat_id = settings.forum_logger_chat_id

    # Create bot instance
    bot = Bot(token=settings.forum_logger_bot_token)

    # Load existing topics
    storage = EncryptedStorage(data_dir="/var/lib/calendar-bot")
    data = storage.load("forum_topics.json", default={'topics': {}})
    topics = {str(k): int(v) for k, v in data.get('topics', {}).items()}

    print(f"Loaded {len(topics)} existing topics")

    # Get all users
    users = analytics_service.get_all_users_details()
    print(f"Found {len(users)} users to migrate")

    # Migrate each user
    total_messages = 0
    for i, user in enumerate(users):
        user_id = user.user_id
        user_name = user.first_name or user.username or f"User {user_id}"

        print(f"[{i+1}/{len(users)}] Migrating {user_name} ({user_id})...")

        try:
            count = await migrate_user_dialog(bot, chat_id, user_id, user_name, storage, topics)
            total_messages += count
            print(f"  -> {count} messages migrated")
        except Exception as e:
            print(f"  -> ERROR: {e}")

        # Delay between users to avoid rate limits
        await asyncio.sleep(3)

    print(f"\nDone! Migrated {total_messages} messages for {len(users)} users")


if __name__ == "__main__":
    asyncio.run(main())
