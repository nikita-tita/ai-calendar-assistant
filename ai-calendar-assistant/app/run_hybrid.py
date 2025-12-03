"""Run bot in polling mode + FastAPI web server for webapp."""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters
import uvicorn
from threading import Thread

from app.config import settings
from app.services.telegram_handler import TelegramHandler
from app.services.daily_reminders import DailyRemindersService
from app.services.event_reminders import EventRemindersService
from app.main import app as fastapi_app

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def run_fastapi():
    """Run FastAPI server in separate thread."""
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


async def main():
    """Run bot in polling mode + FastAPI web server."""

    # Start FastAPI in separate thread
    logger.info("Starting FastAPI web server on port 8000...")
    fastapi_thread = Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()

    # Create Telegram application
    app = Application.builder().token(settings.telegram_bot_token).build()

    # Initialize handler
    handler = TelegramHandler(app)

    # Initialize reminders services
    daily_reminders = DailyRemindersService(app.bot)
    event_reminders = EventRemindersService(app.bot)

    # Create wrapper for handle_update that accepts context
    async def handle_with_context(update: Update, context):
        # Register user for reminders on any interaction
        if update.effective_user and update.effective_chat:
            user_id = str(update.effective_user.id)
            chat_id = update.effective_chat.id

            # Register for both daily and event reminders
            if user_id not in daily_reminders.active_users:
                daily_reminders.register_user(user_id, chat_id)
            if user_id not in event_reminders.active_users:
                event_reminders.register_user(user_id, chat_id)

        await handler.handle_update(update)

    # Create wrapper for callback queries
    async def handle_callback(update: Update, context):
        # Register user for reminders on callback interactions too
        if update.effective_user and update.effective_chat:
            user_id = str(update.effective_user.id)
            chat_id = update.effective_chat.id

            # Register for both daily and event reminders
            if user_id not in daily_reminders.active_users:
                daily_reminders.register_user(user_id, chat_id)
            if user_id not in event_reminders.active_users:
                event_reminders.register_user(user_id, chat_id)

        await handler.handle_callback_query(update)

    # Add handlers
    app.add_handler(CommandHandler("start", handle_with_context))
    app.add_handler(CommandHandler("language", handle_with_context))
    app.add_handler(CommandHandler("timezone", handle_with_context))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.VOICE, handle_with_context))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_with_context))

    # Run polling
    logger.info("Starting Telegram bot in polling mode...")
    logger.info(f"Bot token: {settings.telegram_bot_token[:10]}...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Start reminders in background
    daily_reminders_task = asyncio.create_task(daily_reminders.run_daily_schedule())
    logger.info("Daily reminders started (9:00 morning, 20:00 evening)")

    event_reminders_task = asyncio.create_task(event_reminders.run_reminder_schedule())
    logger.info("Event reminders started (30 minutes before each event)")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        daily_reminders.stop()
        event_reminders.stop()
        daily_reminders_task.cancel()
        event_reminders_task.cancel()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
