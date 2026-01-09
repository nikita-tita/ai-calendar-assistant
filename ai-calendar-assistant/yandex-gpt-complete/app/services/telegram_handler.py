"""Telegram bot message handler."""

from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application
import structlog

from app.config import settings
from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
from app.services.calendar_radicale import calendar_service
from app.services.stt import stt_service
from app.schemas.events import IntentType
from app.utils.datetime_parser import format_datetime_human

logger = structlog.get_logger()


class TelegramHandler:
    """Handler for Telegram bot messages."""

    def __init__(self, app: Application):
        """Initialize handler with Telegram application."""
        self.app = app
        self.bot = app.bot
        # Store conversation history per user (last 10 messages)
        self.conversation_history = {}
        # Store user timezone preferences (user_id -> timezone string)
        self.user_timezones = {}

    async def handle_update(self, update: Update) -> None:
        """
        Handle incoming Telegram update.

        Args:
            update: Telegram update object
        """
        if not update.message:
            return

        user_id = str(update.effective_user.id)
        message = update.message

        try:
            # Handle /start command
            if message.text and message.text.startswith('/start'):
                await self._handle_start(update, user_id)
                return

            # Handle /timezone command
            if message.text and message.text.startswith('/timezone'):
                await self._handle_timezone(update, user_id, message.text)
                return

            # Handle quick button "Дела на сегодня"
            if message.text and message.text in ['📋 Дела на сегодня', 'Дела на сегодня']:
                await self._handle_text(update, user_id, "Какие планы на сегодня?")
                return

            # Handle voice message
            if message.voice:
                await self._handle_voice(update, user_id)
                return

            # Handle text message
            if message.text:
                await self._handle_text(update, user_id, message.text)
                return

            # Unknown message type
            await message.reply_text(
                "Пожалуйста, отправьте текстовое или голосовое сообщение."
            )

        except Exception as e:
            logger.error(
                "handle_update_error",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            await message.reply_text(
                "Произошла ошибка при обработке сообщения. Попробуйте еще раз."
            )

    async def _handle_start(self, update: Update, user_id: str) -> None:
        """Handle /start command."""
        welcome_message = """🏢 Привет! Я ваш AI-ассистент для работы с недвижимостью.

Помогу организовать рабочий день и не пропустить важные встречи!

📝 Примеры команд:

📍 Создание событий:
• "Показ квартиры на Ленина для Андрея завтра в 14:00"
• "Встреча в офисе с Ивановым послезавтра в 11:00"
• "Звонок клиенту Петрову в пятницу в 10:00"
• "Сделка у нотариуса в понедельник в 15:00"
• "Встреча в банке по ипотеке во вторник в 12:00"

👀 Просмотр расписания:
• "Какие планы на сегодня?"
• "Что у меня завтра?"
• "Покажи события на неделю"

✏️ Изменение событий:
• "Перенеси встречу с Андреем на 17:00"
• "Отмени показ для Иванова"
• "Удали звонок Петрову"

🎤 Можете использовать голосовые сообщения - удобно за рулем!

⏰ Команда /timezone - установить ваш часовой пояс

📅 Все события автоматически сохраняются в личном календаре.
"""
        # Создаем клавиатуру только с быстрой командой
        keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📋 Дела на сегодня")]],
            resize_keyboard=True
        )

        await update.message.reply_text(welcome_message, reply_markup=keyboard)

        # Устанавливаем menu button с WebApp (кнопка слева от поля ввода)
        try:
            from telegram import MenuButtonWebApp
            menu_button = MenuButtonWebApp(
                text="🗓 Кабинет",
                web_app=WebAppInfo(url="https://calendar-webapp-beige.vercel.app")
            )
            await self.bot.set_chat_menu_button(
                chat_id=update.effective_chat.id,
                menu_button=menu_button
            )
        except Exception as e:
            logger.warning("menu_button_set_failed", error=str(e))

    async def _handle_voice(self, update: Update, user_id: str) -> None:
        """Handle voice message using OpenAI Whisper."""
        logger.info("voice_message_received", user_id=user_id)

        try:
            await update.message.reply_text("🎤 Распознаю голос...")

            # Download voice file
            voice = update.message.voice
            voice_file = await self.bot.get_file(voice.file_id)
            voice_bytes = await voice_file.download_as_bytearray()

            # Transcribe using OpenAI Whisper
            text = await stt_service.transcribe_audio(bytes(voice_bytes))

            if not text:
                await update.message.reply_text(
                    "Извините, не удалось распознать голос. Попробуйте еще раз или используйте текст."
                )
                return

            logger.info("voice_transcribed", user_id=user_id, text=text)

            # Show transcribed text
            await update.message.reply_text(f'Вы сказали: "{text}"')

            # Process as text
            await self._handle_text(update, user_id, text)

        except Exception as e:
            logger.error("voice_transcription_failed", user_id=user_id, error=str(e))
            await update.message.reply_text(
                "❌ Ошибка при распознавании голоса. Используйте текстовые сообщения."
            )

    async def _handle_timezone(self, update: Update, user_id: str, text: str) -> None:
        """Handle /timezone command to set user timezone."""
        parts = text.split()

        if len(parts) == 1:
            # Show current timezone and available options with inline buttons
            current_tz = self.user_timezones.get(user_id, 'Europe/Moscow')

            # Create inline keyboard with timezone buttons
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏛 Москва (UTC+3)", callback_data="tz:Europe/Moscow")],
                [InlineKeyboardButton("🏛 Самара (UTC+4)", callback_data="tz:Europe/Samara")],
                [InlineKeyboardButton("🏛 Екатеринбург (UTC+5)", callback_data="tz:Asia/Yekaterinburg")],
                [InlineKeyboardButton("🏛 Омск (UTC+6)", callback_data="tz:Asia/Omsk")],
                [InlineKeyboardButton("🏛 Красноярск (UTC+7)", callback_data="tz:Asia/Krasnoyarsk")],
                [InlineKeyboardButton("🏛 Иркутск (UTC+8)", callback_data="tz:Asia/Irkutsk")],
                [InlineKeyboardButton("🏛 Якутск (UTC+9)", callback_data="tz:Asia/Yakutsk")],
                [InlineKeyboardButton("🏛 Владивосток (UTC+10)", callback_data="tz:Asia/Vladivostok")],
                [InlineKeyboardButton("🏛 Магадан (UTC+11)", callback_data="tz:Asia/Magadan")],
                [InlineKeyboardButton("🏛 Камчатка (UTC+12)", callback_data="tz:Asia/Kamchatka")],
                [InlineKeyboardButton("🌍 Киев (UTC+2)", callback_data="tz:Europe/Kiev")],
                [InlineKeyboardButton("🌍 Алматы (UTC+6)", callback_data="tz:Asia/Almaty")],
                [InlineKeyboardButton("🌍 Ташкент (UTC+5)", callback_data="tz:Asia/Tashkent")],
                [InlineKeyboardButton("🌍 Минск (UTC+3)", callback_data="tz:Europe/Minsk")],
            ])

            await update.message.reply_text(
                f"⏰ Текущий часовой пояс: {current_tz}\n\nВыберите ваш часовой пояс:",
                reply_markup=keyboard
            )
            return

        # Set timezone
        timezone = parts[1]
        try:
            import pytz
            pytz.timezone(timezone)  # Validate timezone
            self.user_timezones[user_id] = timezone
            await update.message.reply_text(f"✅ Часовой пояс установлен: {timezone}")
        except:
            await update.message.reply_text(
                "❌ Неверный часовой пояс. Используйте /timezone для списка доступных."
            )

    async def handle_callback_query(self, update: Update) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        if not query:
            return

        await query.answer()

        user_id = str(update.effective_user.id)
        data = query.data

        # Handle timezone selection
        if data.startswith("tz:"):
            timezone = data[3:]  # Remove "tz:" prefix
            try:
                import pytz
                pytz.timezone(timezone)  # Validate timezone
                self.user_timezones[user_id] = timezone

                # Extract city name from timezone
                city = timezone.split('/')[-1].replace('_', ' ')
                await query.edit_message_text(f"✅ Часовой пояс установлен: {city} ({timezone})")

                logger.info("timezone_set", user_id=user_id, timezone=timezone)
            except Exception as e:
                logger.error("timezone_set_error", user_id=user_id, error=str(e))
                await query.edit_message_text("❌ Ошибка при установке часового пояса")

    def _get_user_timezone(self, update: Update) -> str:
        """Get user timezone from stored preferences or default to Moscow."""
        user_id = str(update.effective_user.id)
        return self.user_timezones.get(user_id, 'Europe/Moscow')

    async def _handle_text(self, update: Update, user_id: str, text: str) -> None:
        """Handle text message."""
        logger.info("text_message_received", user_id=user_id, text=text)

        # Check calendar service connection
        if not calendar_service.is_connected():
            await update.message.reply_text(
                "⚠️ Календарный сервер временно недоступен.\nПопробуйте позже."
            )
            return

        # Process with LLM
        await update.message.reply_text("⏳ Обрабатываю...")

        # Get or create conversation history for this user
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []

        # Get user timezone
        user_tz = self._get_user_timezone(update)

        # ALWAYS load events from calendar before processing request
        # This allows Claude to see what exists and make informed decisions
        from datetime import datetime, timedelta
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
        end = now + timedelta(days=60)
        existing_events = await calendar_service.list_events(user_id, start, end)

        logger.info("events_loaded_for_context", user_id=user_id, count=len(existing_events))

        # Pass conversation history ONLY if last message was a clarify question
        # Include both user request and assistant clarify question
        limited_history = []
        if len(self.conversation_history[user_id]) >= 2:
            # Check if last assistant message was clarify
            last_assistant = self.conversation_history[user_id][-1]
            prev_user = self.conversation_history[user_id][-2]

            if (last_assistant.get("role") == "assistant" and
                prev_user.get("role") == "user"):
                # Include both user request and clarify question for full context
                limited_history = [prev_user, last_assistant]

        event_dto = await llm_agent.extract_event(
            text,
            user_id,
            conversation_history=limited_history,
            timezone=user_tz,
            existing_events=existing_events
        )

        # Update conversation history based on intent
        if event_dto.intent == IntentType.CLARIFY:
            # Store user request and clarify question
            self.conversation_history[user_id] = [
                {"role": "user", "content": text},
                {"role": "assistant", "content": event_dto.clarify_question or "Уточните детали"}
            ]
        else:
            # Clear history after successful action
            self.conversation_history[user_id] = []

        # Handle different intents
        if event_dto.intent == IntentType.CLARIFY:
            await update.message.reply_text(
                event_dto.clarify_question or "Не могли бы вы уточнить детали?"
            )
            return

        if event_dto.intent == IntentType.CREATE:
            await self._handle_create(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.UPDATE:
            await self._handle_update(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.DELETE:
            await self._handle_delete(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.QUERY:
            await self._handle_query(update, user_id, event_dto)
            return

        if event_dto.intent == IntentType.FIND_FREE_SLOTS:
            await self._handle_free_slots(update, user_id, event_dto)
            return

        # Other intents not yet implemented
        await update.message.reply_text(
            "Эта функция пока в разработке. Скоро будет доступна!"
        )

    async def _handle_create(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event creation."""
        # Validate required fields
        if not event_dto.title or not event_dto.start_time:
            await update.message.reply_text(
                "Для создания события нужно указать название и время. Попробуйте еще раз."
            )
            return

        # Create event
        event_uid = await calendar_service.create_event(user_id, event_dto)

        if event_uid:
            time_str = format_datetime_human(event_dto.start_time)
            message = f"""✅ Событие создано!

📅 {event_dto.title}
🕐 {time_str}
{f"📍 {event_dto.location}" if event_dto.location else ""}"""
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "❌ Не удалось создать событие. Проверьте настройки доступа."
            )

    async def _handle_update(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event update."""
        if not event_dto.event_id or event_dto.event_id == "none":
            await update.message.reply_text(
                "Не удалось определить, какое событие нужно изменить. Попробуйте уточнить."
            )
            return

        # Get original event to show what changed
        from datetime import datetime, timedelta
        now = datetime.now()
        original_events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        original_event = next((e for e in original_events if e.id == event_dto.event_id), None)

        success = await calendar_service.update_event(user_id, event_dto.event_id, event_dto)

        if success:
            if original_event:
                # Show what was changed
                title = event_dto.title or original_event.summary
                new_time = event_dto.start_time if event_dto.start_time else original_event.start
                time_str = format_datetime_human(new_time)
                location = event_dto.location if event_dto.location else original_event.location

                message = f"""✅ Событие обновлено!

📅 {title}
🕐 {time_str}
{f"📍 {location}" if location else ""}"""
            else:
                # Fallback if couldn't find original
                time_str = format_datetime_human(event_dto.start_time) if event_dto.start_time else ""
                message = f"""✅ Событие обновлено!

📅 {event_dto.title if event_dto.title else 'Событие'}
{f"🕐 {time_str}" if time_str else ""}
{f"📍 {event_dto.location}" if event_dto.location else ""}"""

            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "❌ Не удалось обновить событие. Возможно, оно было удалено."
            )

    async def _handle_delete(self, update: Update, user_id: str, event_dto) -> None:
        """Handle event deletion."""
        if not event_dto.event_id or event_dto.event_id == "none":
            await update.message.reply_text(
                "Не удалось определить, какое событие нужно удалить. Попробуйте уточнить."
            )
            return

        # Get event details before deleting to show what was deleted
        from datetime import datetime, timedelta
        now = datetime.now()
        events = await calendar_service.list_events(user_id, now - timedelta(days=30), now + timedelta(days=90))
        event_to_delete = next((e for e in events if e.id == event_dto.event_id), None)

        success = await calendar_service.delete_event(user_id, event_dto.event_id)

        if success:
            if event_to_delete:
                time_str = format_datetime_human(event_to_delete.start)
                message = f"""✅ Событие удалено!

📅 {event_to_delete.summary}
🕐 {time_str}
{f"📍 {event_to_delete.location}" if event_to_delete.location else ""}"""
                await update.message.reply_text(message)
            else:
                await update.message.reply_text("✅ Событие удалено!")
        else:
            await update.message.reply_text(
                "❌ Не удалось удалить событие. Возможно, оно уже было удалено."
            )

    async def _handle_query(self, update: Update, user_id: str, event_dto) -> None:
        """Handle events query."""
        from datetime import datetime, timedelta

        # Default to today if no date specified
        start_date = event_dto.query_date_start or datetime.now()
        end_date = event_dto.query_date_end or (start_date + timedelta(days=1))

        events = await calendar_service.list_events(user_id, start_date, end_date)

        if not events:
            await update.message.reply_text("📅 На это время событий не запланировано.")
            return

        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e.start)

        # Format events list with more details
        message = f"📅 Ваши события:\n\n"
        for event in sorted_events:
            time_str = format_datetime_human(event.start)
            message += f"• {time_str} - {event.summary}\n"
            if event.location:
                message += f"  📍 {event.location}\n"

        await update.message.reply_text(message)

    async def _handle_free_slots(self, update: Update, user_id: str, event_dto) -> None:
        """Handle free slots query."""
        from datetime import datetime

        date = event_dto.query_date_start or datetime.now()

        free_slots = await calendar_service.find_free_slots(user_id, date)

        if not free_slots:
            await update.message.reply_text("📅 На этот день нет свободных промежутков.")
            return

        # Format free slots
        message = f"🆓 Свободные промежутки:\n\n"
        for slot in free_slots:
            start_str = slot.start.strftime("%H:%M")
            end_str = slot.end.strftime("%H:%M")
            message += f"• {start_str} - {end_str} ({slot.duration_minutes} мин)\n"

        await update.message.reply_text(message)


# Global instance (will be initialized in router)
telegram_handler: Optional[TelegramHandler] = None
