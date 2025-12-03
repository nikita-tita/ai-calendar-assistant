"""Telegram bot message handler - Fixed version."""

from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application
import structlog

from app.config import settings
from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
from app.services.calendar_radicale import calendar_service
try:
    from app.services.stt_yandex import STTServiceYandex
    stt_service = STTServiceYandex()
except ImportError:
    from app.services.stt import stt_service
from app.schemas.events import IntentType
from app.utils.datetime_parser import format_datetime_human

# Try to import Property Bot modules (graceful fallback if not available)
try:
    from app.services.property.property_handler import property_handler
    from app.services.property.property_service import property_service
    from app.models.property import BotMode
    PROPERTY_BOT_ENABLED = True
except ImportError:
    property_handler = None
    property_service = None
    BotMode = None
    PROPERTY_BOT_ENABLED = False

logger = structlog.get_logger()


class TelegramHandler:
    """Handler for Telegram bot messages."""

    def __init__(self, app: Application):
        """Initialize handler with Telegram application."""
        self.app = app
        self.bot = app.bot
        self.conversation_history = {}
        self.user_timezones = {}
        self.user_context = {}  # Track user context (calendar/property)

    async def handle_update(self, update: Update) -> None:
        """Handle incoming Telegram update."""
        if not update.message:
            return

        user_id = str(update.effective_user.id)
        message = update.message

        try:
            # Handle commands
            if message.text and message.text.startswith('/start'):
                await self._handle_start(update, user_id)
                return

            # Handle menu navigation
            if message.text == "📋 Меню":
                await self._show_menu(update, user_id)
                return

            if message.text == "🏠 Поиск новостройки":
                self.user_context[user_id] = "property"
                await self._show_property_mode(update, user_id)
                return

            if message.text == "📅 Календарь":
                self.user_context[user_id] = "calendar"
                await self._show_calendar_mode(update, user_id)
                return

            if message.text == "⚙️ Настройки":
                await self._show_settings(update, user_id)
                return

            # Handle quick actions for calendar mode
            if message.text in ["📋 Сегодня", "📋 Планы на сегодня", "📋 Дела на сегодня"]:
                await self._handle_today(update, user_id)
                return

            if message.text in ["📋 Завтра", "📋 Планы на завтра", "📋 Дела на завтра"]:
                await self._handle_tomorrow(update, user_id)
                return

            if message.text in ["📋 Неделя", "📋 Планы на неделю", "📋 Дела на неделю"]:
                await self._handle_week(update, user_id)
                return

            # Handle voice messages
            if message.voice:
                await self._handle_voice(update, user_id)
                return

            # Handle text messages
            if message.text:
                await self._handle_text(update, user_id, message.text)
                return

        except Exception as e:
            logger.error("message_handling_error", user_id=user_id, error=str(e))
            await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")

    async def _handle_start(self, update: Update, user_id: str) -> None:
        """Handle /start command."""
        welcome_message = """👋 Привет! Я помогу не забыть о важных делах.

Просто скажите или напишите что нужно запланировать — я всё запомню и напомню вовремя!

📝 Примеры:
• "Встреча с клиентом завтра в 15:00"
• "Показ квартиры в пятницу в 10:00"
• "Звонок Ивану послезавтра"

🎤 Можно использовать голосовые сообщения!"""

        # Set default context to calendar
        self.user_context[user_id] = "calendar"  # Default to calendar

        # Show calendar keyboard
        keyboard = self._get_calendar_keyboard()
        await update.message.reply_text(welcome_message, reply_markup=keyboard)

    def _get_calendar_keyboard(self) -> ReplyKeyboardMarkup:
        """Get keyboard for calendar mode."""
        return ReplyKeyboardMarkup([
            [KeyboardButton("📋 Сегодня"), KeyboardButton("📋 Завтра"), KeyboardButton("📋 Неделя")],
            [KeyboardButton("📋 Меню")]
        ], resize_keyboard=True)

    def _get_property_keyboard(self) -> ReplyKeyboardMarkup:
        """Get keyboard for property mode."""
        return ReplyKeyboardMarkup([
            [KeyboardButton("📋 Меню")]
        ], resize_keyboard=True)

    def _get_menu_keyboard(self) -> ReplyKeyboardMarkup:
        """Get menu keyboard."""
        buttons = [
            [KeyboardButton("⚙️ Настройки")]
        ]

        if PROPERTY_BOT_ENABLED:
            context = self.user_context.get("current_user", "calendar")
            if context == "calendar":
                buttons.append([KeyboardButton("🏠 Поиск новостройки")])
            else:
                buttons.append([KeyboardButton("📅 Календарь")])

        return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    async def _show_menu(self, update: Update, user_id: str) -> None:
        """Show main menu."""
        context = self.user_context.get(user_id, "calendar")

        message = "📋 Выберите раздел:"
        keyboard = self._get_menu_keyboard()

        # Store current user for keyboard generation
        self.user_context["current_user"] = context

        await update.message.reply_text(message, reply_markup=keyboard)

    async def _show_property_mode(self, update: Update, user_id: str) -> None:
        """Show property search mode."""
        message = """🏠 **Поиск новостройки**

Опишите, что вы ищете голосом или текстом:
• Район, метро, локация
• Количество комнат
• Бюджет
• Срок сдачи

Я проанализирую предложения и подберу лучшие варианты!"""

        keyboard = self._get_property_keyboard()
        await update.message.reply_text(message, reply_markup=keyboard, parse_mode="Markdown")

    async def _show_calendar_mode(self, update: Update, user_id: str) -> None:
        """Show calendar mode."""
        message = "📅 Календарь\n\nОтправьте сообщение для создания события или используйте быстрые кнопки."
        keyboard = self._get_calendar_keyboard()
        await update.message.reply_text(message, reply_markup=keyboard)

    async def _show_settings(self, update: Update, user_id: str) -> None:
        """Show settings."""
        current_tz = self.user_timezones.get(user_id, 'Europe/Moscow')
        message = f"""⚙️ Настройки

Текущий часовой пояс: {current_tz}

Команды:
/timezone - изменить часовой пояс"""

        # Return to previous mode keyboard
        context = self.user_context.get(user_id, "calendar")
        if context == "property":
            keyboard = self._get_property_keyboard()
        else:
            keyboard = self._get_calendar_keyboard()

        await update.message.reply_text(message, reply_markup=keyboard)

    async def _handle_voice(self, update: Update, user_id: str) -> None:
        """Handle voice message."""
        logger.info("voice_message_received", user_id=user_id)

        try:
            await update.message.reply_text("🎤 Распознаю голос...")

            voice = update.message.voice
            voice_file = await self.bot.get_file(voice.file_id)
            voice_bytes = await voice_file.download_as_bytearray()

            text = await stt_service.transcribe_audio(bytes(voice_bytes))

            if not text:
                await update.message.reply_text(
                    "Извините, не удалось распознать голос. Попробуйте еще раз или используйте текст."
                )
                return

            logger.info("voice_transcribed", user_id=user_id, text=text)
            await update.message.reply_text(f'Вы сказали: "{text}"')

            # Route to appropriate handler based on context
            context = self.user_context.get(user_id, "calendar")
            if context == "property" and PROPERTY_BOT_ENABLED:
                await property_handler.handle_property_message(update, user_id, text)
            else:
                await self._handle_text(update, user_id, text)

        except Exception as e:
            logger.error("voice_error", user_id=user_id, error=str(e))
            await update.message.reply_text("❌ Ошибка при распознавании голоса.")

    async def _handle_text(self, update: Update, user_id: str, text: str) -> None:
        """Handle text message for calendar."""
        # Check if in property mode
        context = self.user_context.get(user_id, "calendar")
        if context == "property" and PROPERTY_BOT_ENABLED:
            await property_handler.handle_property_message(update, user_id, text)
            return

        # Calendar logic
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        self.conversation_history[user_id].append({"role": "user", "content": text})

        # Get user timezone
        user_tz = self.user_timezones.get(user_id, 'Europe/Moscow')

        # Process with LLM
        history = self.conversation_history[user_id][-10:]
        result = await llm_agent.process_message(text, user_id, history, user_tz)

        # Store assistant response
        if result.response:
            self.conversation_history[user_id].append({"role": "assistant", "content": result.response})

        # Handle based on intent
        if result.intent == IntentType.CREATE_EVENT:
            if result.actions:
                for action in result.actions:
                    try:
                        event = await calendar_service.create_event(
                            user_id=user_id,
                            title=action.get("title", ""),
                            start_time=action.get("start_time"),
                            end_time=action.get("end_time"),
                            description=action.get("description", ""),
                            location=action.get("location", ""),
                            timezone=user_tz
                        )
                        await update.message.reply_text(f"✅ Создано: {action.get('title')}")
                    except Exception as e:
                        logger.error("event_create_error", error=str(e))
                        await update.message.reply_text("❌ Не удалось создать событие")

        elif result.intent == IntentType.LIST_EVENTS:
            await self._send_events_list(update, user_id, result.response)

        else:
            if result.response:
                await update.message.reply_text(result.response)

    async def _handle_today(self, update: Update, user_id: str) -> None:
        """Handle 'today' quick button."""
        user_tz = self.user_timezones.get(user_id, 'Europe/Moscow')
        from datetime import datetime
        import pytz

        tz = pytz.timezone(user_tz)
        now = datetime.now(tz)

        try:
            events = await calendar_service.list_events(
                user_id=user_id,
                start_date=now,
                end_date=now.replace(hour=23, minute=59),
                timezone=user_tz
            )

            if not events:
                await update.message.reply_text("📅 На сегодня событий не запланировано.")
            else:
                response = f"📅 События на сегодня ({now.strftime('%d.%m.%Y')}):\n\n"
                for event in events:
                    response += f"• {event['summary']}\n"
                    if event.get('start'):
                        response += f"  🕐 {event['start'].strftime('%H:%M')}\n"
                await update.message.reply_text(response)
        except Exception as e:
            logger.error("today_events_error", error=str(e))
            await update.message.reply_text("❌ Ошибка при загрузке событий")

    async def _handle_tomorrow(self, update: Update, user_id: str) -> None:
        """Handle 'tomorrow' quick button."""
        user_tz = self.user_timezones.get(user_id, 'Europe/Moscow')
        from datetime import datetime, timedelta
        import pytz

        tz = pytz.timezone(user_tz)
        tomorrow = datetime.now(tz) + timedelta(days=1)

        try:
            events = await calendar_service.list_events(
                user_id=user_id,
                start_date=tomorrow.replace(hour=0, minute=0),
                end_date=tomorrow.replace(hour=23, minute=59),
                timezone=user_tz
            )

            if not events:
                await update.message.reply_text("📅 На завтра событий не запланировано.")
            else:
                response = f"📅 События на завтра ({tomorrow.strftime('%d.%m.%Y')}):\n\n"
                for event in events:
                    response += f"• {event['summary']}\n"
                    if event.get('start'):
                        response += f"  🕐 {event['start'].strftime('%H:%M')}\n"
                await update.message.reply_text(response)
        except Exception as e:
            logger.error("tomorrow_events_error", error=str(e))
            await update.message.reply_text("❌ Ошибка при загрузке событий")

    async def _handle_week(self, update: Update, user_id: str) -> None:
        """Handle 'week' quick button."""
        user_tz = self.user_timezones.get(user_id, 'Europe/Moscow')
        from datetime import datetime, timedelta
        import pytz

        tz = pytz.timezone(user_tz)
        now = datetime.now(tz)
        week_end = now + timedelta(days=7)

        try:
            events = await calendar_service.list_events(
                user_id=user_id,
                start_date=now,
                end_date=week_end,
                timezone=user_tz
            )

            if not events:
                await update.message.reply_text("📅 На неделю событий не запланировано.")
            else:
                response = "📅 События на неделю:\n\n"
                for event in events:
                    response += f"• {event['summary']}\n"
                    if event.get('start'):
                        response += f"  📅 {event['start'].strftime('%d.%m %H:%M')}\n"
                await update.message.reply_text(response)
        except Exception as e:
            logger.error("week_events_error", error=str(e))
            await update.message.reply_text("❌ Ошибка при загрузке событий")

    async def _send_events_list(self, update: Update, user_id: str, response: str) -> None:
        """Send events list."""
        await update.message.reply_text(response if response else "📅 Событий не найдено.")

    async def handle_callback_query(self, update: Update) -> None:
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        if not query:
            return

        await query.answer()

        user_id = str(update.effective_user.id)
        data = query.data

        # Route to property handler if in property mode or if callback starts with "property_"
        if PROPERTY_BOT_ENABLED and (data.startswith("property_") or self.user_context.get(user_id) == "property"):
            await property_handler.handle_property_callback(update, user_id, data)
        else:
            # Handle other callbacks (timezone, etc)
            pass
