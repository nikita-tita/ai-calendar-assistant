"""Simple test bot to verify Telegram connectivity."""

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# Bot token
TOKEN = "***REMOVED***"

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    logger.info(f"Received /start from user {update.effective_user.id}")
    await update.message.reply_text(
        "🤖 Привет! Я AI Calendar Assistant!\n\n"
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/auth - проверить статус календаря\n\n"
        "Или просто напишите что-то вроде:\n"
        "• Создай встречу завтра в 10:00\n"
        "• Какие у меня планы на сегодня?"
    )


async def auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /auth command."""
    logger.info(f"Received /auth from user {update.effective_user.id}")
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"✅ Ваш персональный календарь готов!\n\n"
        f"ID пользователя: {user_id}\n"
        f"Календарь: telegram_{user_id}\n\n"
        f"Можете начинать создавать события!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages."""
    user_id = update.effective_user.id
    text = update.message.text
    logger.info(f"Received message from user {user_id}: {text}")

    await update.message.reply_text(
        f"📩 Получил ваше сообщение: '{text}'\n\n"
        f"⚠️ Полная обработка пока не подключена.\n"
        f"Это тестовая версия бота."
    )


async def main():
    """Run bot."""
    # Create application
    app = Application.builder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("auth", auth_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start bot
    logger.info("Starting test bot...")
    logger.info(f"Bot token: {TOKEN[:10]}...")

    await app.initialize()
    await app.start()

    # Get bot info
    me = await app.bot.get_me()
    logger.info(f"Bot started: @{me.username} (ID: {me.id})")

    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("✅ Bot is running! Send /start to @aibroker_bot")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
