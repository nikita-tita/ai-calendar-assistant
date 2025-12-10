"""Run Telegram bot in polling mode (for local testing without webhook)."""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from app.config import settings
from app.services.telegram_handler import TelegramHandler
from app.services.daily_reminders import DailyRemindersService
from app.services.event_reminders_idempotent import EventRemindersServiceIdempotent
from app.services.forum_logger import ForumActivityLogger
import app.services.forum_logger as forum_logger_module

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    """Run bot in polling mode."""
    # Create application
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Initialize handler
    handler = TelegramHandler(app)

    # Initialize daily reminders service
    reminders = DailyRemindersService(app.bot)

    # Initialize event reminders service (30 minutes before events)
    # Uses SQLite for idempotency - survives restarts without duplicate reminders
    # Uses dependency injection for user list (no circular imports)
    event_reminders = EventRemindersServiceIdempotent(
        bot=app.bot,
        user_provider=lambda: reminders.active_users
    )

    # Set global reference for legacy compatibility
    import app.services.daily_reminders as dr_module
    dr_module.daily_reminders_service = reminders

    # Initialize forum activity logger
    forum_logger = ForumActivityLogger(app.bot)
    forum_logger_module.forum_logger = forum_logger
    forum_logger.start()

    # Create wrapper for handle_update that accepts context
    async def handle_with_context(update: Update, context):
        # Register user for daily reminders on ANY message (idempotent - won't duplicate)
        # Event reminders use daily_reminders.active_users as source of truth
        if update.effective_user and update.effective_chat:
            user_id = str(update.effective_user.id)
            chat_id = update.effective_chat.id
            # Only register if not already in active_users (avoid unnecessary file writes)
            if user_id not in reminders.active_users:
                reminders.register_user(user_id, chat_id)

        await handler.handle_update(update)

    # Create wrapper for callback queries
    async def handle_callback(update: Update, context):
        await handler.handle_callback_query(update)

    # Add handlers
    app.add_handler(CommandHandler("start", handle_with_context))
    app.add_handler(CommandHandler("timezone", handle_with_context))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_with_context))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_with_context))

    # Run polling
    logger.info("Starting bot in polling mode...")
    logger.info(f"Bot token: {settings.telegram_bot_token[:10]}...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Start daily reminders in background
    reminders_task = asyncio.create_task(reminders.run_daily_schedule())
    logger.info("Daily reminders started (9:00 morning, 20:00 evening)")

    # Start event reminders in background (idempotent - uses SQLite)
    event_reminders_task = asyncio.create_task(event_reminders.run_reminder_loop())
    logger.info("Event reminders started (30 minutes before events, idempotent)")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        reminders.stop()
        reminders_task.cancel()
        event_reminders.stop()
        event_reminders_task.cancel()
        forum_logger.stop()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
