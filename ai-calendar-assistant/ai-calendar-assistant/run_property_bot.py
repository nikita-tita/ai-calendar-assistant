#!/usr/bin/env python3
"""Run property search bot in polling mode."""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog

from app.config import settings
from app.services.property.property_handler import PropertyHandler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = structlog.get_logger()

# Property bot token
PROPERTY_BOT_TOKEN = "7964619356:AAGXqaiVnsUfYpOSi45KP2LnSFCIrL-NIN8"

# Initialize property handler
property_handler = PropertyHandler()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command for property bot."""
    user = update.effective_user
    user_id = str(user.id)

    logger.info("property_bot_start", user_id=user_id, username=user.username)

    welcome_message = f"""👋 Привет, {user.first_name}!

Я помогу найти идеальную квартиру в новостройках.

🏗 <b>Что я умею:</b>
• Поиск квартир по вашим критериям
• Умный подбор с учетом бюджета и локации
• Показ фото, планировок и характеристик
• Сохранение избранных вариантов

💬 <b>Как искать:</b>
Просто напишите свой запрос, например:
• "Двушка до 18 млн на севере"
• "Квартиру на васке за 15 млн"
• "Однушку около метро, до 12 млн"

Я пойму ваш запрос и подберу подходящие варианты!

Начнем? Напишите, что ищете 👇"""

    keyboard = [
        [InlineKeyboardButton("🔍 Начать поиск", callback_data="property_start_search")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="property_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        welcome_message,
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command."""
    help_text = """🆘 <b>Помощь по поиску</b>

<b>Примеры запросов:</b>

📍 <b>По району:</b>
• "Квартира в Приморском районе"
• "На Васильевском острове"

💰 <b>По бюджету:</b>
• "До 15 миллионов"
• "От 10 до 18 млн"

🛏 <b>По комнатам:</b>
• "Однушка" или "1-комнатная"
• "Двухкомнатная квартира"
• "Студия"

📐 <b>По площади:</b>
• "От 60 квадратов"
• "Площадь около 70 метров"

🏦 <b>Ипотека:</b>
• "Подходит под ипотеку Сбербанка"
• "С рассрочкой"

<b>Комбинируйте критерии:</b>
"Двушка до 18 млн в Приморском, от 65 квадратов"

Я умный - пойму ваш запрос и подберу варианты! 🤖"""

    # Check if called from callback or direct message
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text, parse_mode="HTML")
    else:
        await update.message.reply_text(help_text, parse_mode="HTML")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages."""
    user_id = str(update.effective_user.id)
    text = update.message.text

    logger.info("property_message_received", user_id=user_id, text=text[:50])

    # Pass to property handler - use handle_property_message
    await property_handler.handle_property_message(update, user_id, text)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries."""
    query = update.callback_query
    user_id = str(query.from_user.id)
    callback_data = query.data

    logger.info("property_callback", user_id=user_id, data=callback_data)

    if callback_data == "property_start_search":
        await query.answer()
        await query.message.reply_text(
            "🔍 Отлично! Напишите, какую квартиру вы ищете.\n\n"
            "Например: \"Двушка до 18 млн на севере\" или \"Однушка на васке, до 15 млн\""
        )
    elif callback_data == "property_help":
        await query.answer()
        await help_command(update, context)
    else:
        # Pass to property handler - use handle_property_callback
        await property_handler.handle_property_callback(update, user_id, callback_data)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error("property_bot_error", error=str(context.error), exc_info=context.error)


def main():
    """Run the property bot."""
    logger.info("property_bot_starting", token=PROPERTY_BOT_TOKEN[:20] + "...")

    # Create application
    application = Application.builder().token(PROPERTY_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start bot
    logger.info("property_bot_running")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
