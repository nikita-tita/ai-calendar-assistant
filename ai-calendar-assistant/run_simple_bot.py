#!/usr/bin/env python3
"""
Простая рабочая версия AI Calendar Bot
Без STT и сложных зависимостей
"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f'👋 Привет, {user.first_name}!\n\n'
        '🤖 Я AI Calendar Assistant!\n\n'
        '📋 Доступные команды:\n'
        '/start - Начало работы\n'
        '/help - Помощь\n'
        '/status - Статус бота\n\n'
        'Просто напишите мне событие, и я помогу его организовать!\n'
        'Например: "Встреча завтра в 15:00"'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        '📖 Справка:\n\n'
        '✅ Как использовать бота:\n'
        '• Отправьте описание события\n'
        '• Укажите дату и время\n'
        '• Я добавлю его в календарь\n\n'
        '📝 Примеры:\n'
        '• "Встреча с клиентом завтра в 14:00"\n'
        '• "Звонок родителям в пятницу вечером"\n'
        '• "Поход к врачу 15 октября в 10:30"\n\n'
        '💡 Команды:\n'
        '/start - Приветствие\n'
        '/help - Эта справка\n'
        '/status - Проверка работы'
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка статуса бота"""
    await update.message.reply_text(
        '✅ Бот работает нормально!\n\n'
        f'🤖 Версия: 1.0 (minimal)\n'
        f'📊 Статус: Online\n'
        f'🌍 Сервер: REG.RU VPS\n'
        f'⏰ Часовой пояс: Europe/Moscow'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_message = update.message.text
    logger.info(f"Получено сообщение от {update.effective_user.username}: {user_message}")
    
    # Простой ответ (позже добавим интеграцию с календарём)
    await update.message.reply_text(
        f'📝 Получено ваше сообщение:\n'
        f'"{user_message}"\n\n'
        f'🔄 Анализирую и добавляю в календарь...\n'
        f'(Интеграция с календарём будет добавлена в следующей версии)'
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            '❌ Произошла ошибка при обработке вашего запроса.\n'
            'Попробуйте ещё раз или обратитесь к администратору.'
        )

def main():
    """Основная функция запуска бота"""
    # Проверка токена
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        logger.error("Проверьте файл .env")
        return

    logger.info("🚀 Запуск AI Calendar Bot...")
    logger.info(f"📋 Токен: {TELEGRAM_BOT_TOKEN[:10]}...")

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)

    # Запуск бота в режиме polling
    logger.info("✅ Бот запущен в режиме polling")
    logger.info("⏳ Ожидание сообщений...")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
