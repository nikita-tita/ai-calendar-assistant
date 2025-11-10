#!/usr/bin/env python3
"""Fix menu button in telegram handler."""

import re

# Read the file
with open("app/services/telegram_handler.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add command handlers after _handle_timezone
new_commands_handlers = '''
    async def _handle_calendar_command(self, update: Update, user_id: str) -> None:
        """Handle /calendar command - switch to calendar mode."""
        if PROPERTY_BOT_ENABLED:
            await property_handler.handle_mode_switch(update, user_id, BotMode.CALENDAR)
        else:
            await update.message.reply_text("📅 Вы уже в режиме календаря!")

    async def _handle_property_command(self, update: Update, user_id: str) -> None:
        """Handle /property command - switch to property search mode."""
        if PROPERTY_BOT_ENABLED:
            await property_handler.handle_mode_switch(update, user_id, BotMode.PROPERTY)
        else:
            await update.message.reply_text(
                "🏢 Режим поиска недвижимости скоро будет доступен!\\n"
                "Следите за обновлениями."
            )

    async def _handle_settings_command(self, update: Update, user_id: str) -> None:
        """Handle /settings command."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏰ Часовой пояс", callback_data="settings:timezone")],
            [InlineKeyboardButton("🔔 Напоминания", callback_data="settings:reminders")],
            [InlineKeyboardButton("🌍 Язык", callback_data="settings:language")],
        ])

        await update.message.reply_text(
            "⚙️ Настройки\\n\\n"
            "Выберите что хотите настроить:",
            reply_markup=keyboard
        )
'''

# Find position to insert (after _handle_timezone, before handle_callback_query)
insert_pattern = r"(            await update\.message\.reply_text\(\n                \"❌ Неверный часовой пояс\. Используйте /timezone для списка доступных\.\"\n            \)\n)"
match = re.search(insert_pattern, content)
if match:
    insert_pos = match.end()
    content = content[:insert_pos] + new_commands_handlers + content[insert_pos:]
    print("✅ Command handlers added")
else:
    print("⚠️  Could not find insertion point for command handlers")

# 2. Update _handle_start to set bot commands
old_menu_setup = '''        # Устанавливаем menu button с WebApp (кнопка слева от поля ввода)
        try:
            from telegram import MenuButtonWebApp
            menu_button = MenuButtonWebApp(
                text="🗓 Кабинет",
                web_app=WebAppInfo(url="https://этонесамыйдлинныйдомен.рф")
            )
            await self.bot.set_chat_menu_button(
                chat_id=update.effective_chat.id,
                menu_button=menu_button
            )
        except Exception as e:
            logger.warning("menu_button_set_failed", error=str(e))'''

new_menu_setup = '''        # Устанавливаем bot commands для меню
        try:
            from telegram import BotCommand, MenuButtonCommands
            commands = [
                BotCommand("start", "🏠 Главное меню"),
                BotCommand("calendar", "📅 Режим календаря"),
                BotCommand("property", "🏢 Поиск недвижимости"),
                BotCommand("timezone", "⏰ Установить часовой пояс"),
                BotCommand("settings", "⚙️ Настройки"),
            ]
            await self.bot.set_my_commands(commands)

            # Установить menu button как Commands
            menu_button = MenuButtonCommands()
            await self.bot.set_chat_menu_button(
                chat_id=update.effective_chat.id,
                menu_button=menu_button
            )
            logger.info("menu_commands_set", user_id=user_id)
        except Exception as e:
            logger.warning("menu_button_set_failed", error=str(e))'''

if old_menu_setup in content:
    content = content.replace(old_menu_setup, new_menu_setup)
    print("✅ Menu setup updated")
else:
    print("⚠️  Could not find menu setup section")

# 3. Add command handling in handle_update
old_command_check = '''            # Handle /start command
            if message.text and message.text.startswith('/start'):
                await self._handle_start(update, user_id)
                return

            # Handle /timezone command
            if message.text and message.text.startswith('/timezone'):
                await self._handle_timezone(update, user_id, message.text)
                return'''

new_command_check = '''            # Handle /start command
            if message.text and message.text.startswith('/start'):
                await self._handle_start(update, user_id)
                return

            # Handle /calendar command
            if message.text and message.text.startswith('/calendar'):
                await self._handle_calendar_command(update, user_id)
                return

            # Handle /property command
            if message.text and message.text.startswith('/property'):
                await self._handle_property_command(update, user_id)
                return

            # Handle /settings command
            if message.text and message.text.startswith('/settings'):
                await self._handle_settings_command(update, user_id)
                return

            # Handle /timezone command
            if message.text and message.text.startswith('/timezone'):
                await self._handle_timezone(update, user_id, message.text)
                return'''

if old_command_check in content:
    content = content.replace(old_command_check, new_command_check)
    print("✅ Command handling added to handle_update")
else:
    print("⚠️  Could not find command check section")

# 4. Update welcome message to mention menu
old_welcome = '''⏰ Команда /timezone - установить ваш часовой пояс

📅 Все события автоматически сохраняются в личном календаре.'''

new_welcome = '''⚙️ Нажмите кнопку МЕНЮ ☰ слева от поля ввода для переключения режимов и настроек.

📅 Все события автоматически сохраняются в личном календаре.'''

if old_welcome in content:
    content = content.replace(old_welcome, new_welcome)
    print("✅ Welcome message updated")
else:
    print("⚠️  Could not find welcome message")

# Write back
with open("app/services/telegram_handler.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ File updated successfully")
