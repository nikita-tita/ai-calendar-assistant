"""Run Telegram bot in polling mode (for local testing without webhook)."""

import asyncio
import logging
import signal
from datetime import datetime, time
import pytz
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

# Global shutdown event for graceful termination
shutdown_event = asyncio.Event()

# Admin report schedule (Moscow timezone)
ADMIN_REPORT_HOUR = 21  # 21:00 MSK
ADMIN_REPORT_MINUTE = 0


async def run_admin_report_schedule(forum_logger: ForumActivityLogger):
    """Background task to send admin daily report at 21:00 MSK.

    Uses forum_logger bot (@dogovorarenda_bot) to send stats to admin.
    """
    moscow_tz = pytz.timezone('Europe/Moscow')
    last_sent_date = None

    logger.info("admin_report_schedule_started", time=f"{ADMIN_REPORT_HOUR:02d}:{ADMIN_REPORT_MINUTE:02d} MSK")

    while True:
        try:
            now_msk = datetime.now(moscow_tz)
            current_date = now_msk.date()
            current_time = now_msk.time()

            # Check if it's time to send (21:00 MSK) and not already sent today
            target_time = time(ADMIN_REPORT_HOUR, ADMIN_REPORT_MINUTE)
            if (current_time.hour == target_time.hour and
                current_time.minute == target_time.minute and
                last_sent_date != current_date):

                logger.info("admin_report_sending", time=now_msk.strftime("%H:%M"))
                success = await forum_logger.send_admin_daily_report()

                if success:
                    last_sent_date = current_date
                    logger.info("admin_report_sent_successfully", date=str(current_date))

            # Check every minute
            await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("admin_report_schedule_cancelled")
            break
        except Exception as e:
            logger.error("admin_report_schedule_error", error=str(e))
            await asyncio.sleep(60)


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

    # Initialize forum activity logger (uses separate bot)
    forum_logger = ForumActivityLogger()
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

    # Start admin report schedule (21:00 MSK via @dogovorarenda_bot)
    admin_report_task = asyncio.create_task(run_admin_report_schedule(forum_logger))
    logger.info("Admin report schedule started (21:00 MSK via @dogovorarenda_bot)")

    # Setup signal handlers for graceful shutdown (handles Docker SIGTERM)
    # Use get_running_loop() instead of deprecated get_event_loop() in async context
    loop = asyncio.get_running_loop()

    def signal_handler(sig):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Graceful shutdown
    logger.info("Stopping bot...")
    reminders.stop()
    reminders_task.cancel()
    event_reminders.stop()
    event_reminders_task.cancel()
    admin_report_task.cancel()
    forum_logger.stop()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Bot stopped gracefully")


if __name__ == "__main__":
    asyncio.run(main())
