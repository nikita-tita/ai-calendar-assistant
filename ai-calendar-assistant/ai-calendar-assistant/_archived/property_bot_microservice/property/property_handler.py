"""Property search bot handler."""

from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import structlog

from .property_service import property_service
from .property_scoring import property_scoring_service
from .llm_agent_property import llm_agent_property
from app.models.property import BotMode
from app.schemas.property import PropertyClientCreate, PropertySearchFilters, DealType
from app.services.translations import Language, get_translation
from app.services.user_preferences import user_preferences

logger = structlog.get_logger()


# District name normalization map
DISTRICT_NORMALIZATIONS = {
    "василеостровский": "Васильевский",
    "василеостровский район": "Васильевский",
    "васильевский": "Васильевский",
    "васька": "Васильевский",
    "ваське": "Васильевский",
    "выборгский": "Выборгский",
    "выборгский район": "Выборгский",
    "калининский": "Калининский",
    "калининский район": "Калининский",
    "приморский": "Приморский",
    "приморский район": "Приморский",
}


def normalize_districts(districts: list) -> list:
    """Normalize district names to match DB format."""
    if not districts:
        return districts

    normalized = []
    for district in districts:
        district_lower = district.lower().strip()
        if district_lower in DISTRICT_NORMALIZATIONS:
            normalized.append(DISTRICT_NORMALIZATIONS[district_lower])
        else:
            # Try partial match
            for key, value in DISTRICT_NORMALIZATIONS.items():
                if key in district_lower or district_lower in key:
                    normalized.append(value)
                    break
            else:
                # Keep original if no match found
                normalized.append(district)

    return list(set(normalized))  # Remove duplicates


def add_budget_tolerance(budget_min: Optional[int], budget_max: Optional[int], tolerance: float = 0.15) -> tuple:
    """Add tolerance to budget (e.g., 15 млн -> 13-17 млн).

    Args:
        budget_min: Minimum budget
        budget_max: Maximum budget
        tolerance: Tolerance as fraction (0.15 = 15%)

    Returns:
        (adjusted_min, adjusted_max) tuple
    """
    if budget_max and not budget_min:
        # Only max specified (e.g., "до 15 млн") -> add lower bound with tolerance
        budget_min = int(budget_max * (1 - tolerance))
        budget_max = int(budget_max * (1 + tolerance))
    elif budget_min and not budget_max:
        # Only min specified (e.g., "от 10 млн") -> add upper bound with tolerance
        budget_max = int(budget_min * (1 + tolerance))
        budget_min = int(budget_min * (1 - tolerance))
    elif budget_min and budget_max:
        # Both specified - keep as is but could add small tolerance
        pass

    return (budget_min, budget_max)


class PropertyHandler:
    """Handler for property search bot mode."""

    def __init__(self):
        """Initialize property handler."""
        # Store conversation state per user
        self.conversation_state = {}  # user_id -> {"step": "...", "data": {...}}

    def _get_user_language(self, user_id: str) -> Language:
        """Get user's preferred language."""
        return user_preferences.get_language(user_id)

    def _translate(self, key: str, user_id: str, **kwargs) -> str:
        """Get translation for user's language."""
        lang = self._get_user_language(user_id)
        return get_translation(key, lang, **kwargs)

    def _get_property_keyboard(self, user_id: str) -> ReplyKeyboardMarkup:
        """Get keyboard for property search mode - empty, user just types."""
        # Property mode: NO buttons on keyboard, only MenuButton
        # User types free-form queries like "2к до 18 млн на севере города"
        from telegram import ReplyKeyboardRemove
        return ReplyKeyboardRemove()

    def _get_calendar_keyboard(self, user_id: str) -> ReplyKeyboardMarkup:
        """Get keyboard for calendar mode (original)."""
        lang = self._get_user_language(user_id)
        return ReplyKeyboardMarkup(
            [
                [KeyboardButton("📋 Дела на сегодня")],
                [KeyboardButton("📅 Дела на завтра"), KeyboardButton("📆 Дела на неделю")],
                [KeyboardButton("🏢 Поиск новостроек"), KeyboardButton("⚙️ Настройки")]
            ],
            resize_keyboard=True
        )

    async def handle_mode_switch(self, update: Update, user_id: str, target_mode: BotMode) -> None:
        """Handle switching between calendar and property modes."""
        try:
            await property_service.set_user_mode(user_id, target_mode)

            if target_mode == BotMode.property:
                # Switch to property mode
                welcome_msg = """🏠 <b>Поиск новостройки в Санкт-Петербурге</b>

Я помогу найти идеальную квартиру под ваши требования!

Используя AI, я проанализирую:
• Локацию и время в пути
• Инфраструктуру района
• Качество планировки
• Соотношение цены и рынка

<b>Просто напишите, что ищете.</b> Например:
"Двухкомнатную до 18 млн на севере города, с ипотекой Сбербанка"
"3к от 10 до 15 млн в Приморском районе, не первый этаж"
"Студию до 8 млн рядом с метро, с парковкой"

База: <b>11,468 квартир</b> в новостройках Питера"""

                keyboard = self._get_property_keyboard(user_id)
                await update.message.reply_text(
                    welcome_msg,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )

                # Set MenuButton with mode switching
                try:
                    from telegram import MenuButtonCommands
                    from telegram.ext import Application

                    # Get bot from application
                    bot = update.get_bot()

                    # In PROPERTY mode: show "📅 Календарь" and "⚙️ Настройки" in menu
                    menu_button = MenuButtonCommands()
                    await bot.set_chat_menu_button(
                        chat_id=update.effective_chat.id,
                        menu_button=menu_button
                    )

                    # Set bot commands for this chat
                    from telegram import BotCommand
                    commands = [
                        BotCommand("calendar", "📅 Переключиться на календарь"),
                        BotCommand("settings", "⚙️ Настройки")
                    ]
                    await bot.set_my_commands(commands, scope={"type": "chat", "chat_id": update.effective_chat.id})

                except Exception as e:
                    logger.warning("menu_button_set_failed", error=str(e))

                logger.info("mode_switched_to_property", user_id=user_id)

            else:  # BotMode.calendar
                # Switch back to calendar mode
                welcome_msg = self._translate("welcome_back_calendar", user_id)
                if welcome_msg == "welcome_back_calendar":
                    welcome_msg = "📅 Возвращаемся к календарю!"

                keyboard = self._get_calendar_keyboard(user_id)
                await update.message.reply_text(
                    welcome_msg,
                    reply_markup=keyboard
                )

                # Set MenuButton for CALENDAR mode
                try:
                    from telegram import MenuButtonCommands, BotCommand
                    bot = update.get_bot()

                    # In CALENDAR mode: show "🏢 Поиск новостроек" and "⚙️ Настройки" in menu
                    menu_button = MenuButtonCommands()
                    await bot.set_chat_menu_button(
                        chat_id=update.effective_chat.id,
                        menu_button=menu_button
                    )

                    # Set bot commands for this chat
                    commands = [
                        BotCommand("property", "🏢 Поиск новостроек"),
                        BotCommand("settings", "⚙️ Настройки")
                    ]
                    await bot.set_my_commands(commands, scope={"type": "chat", "chat_id": update.effective_chat.id})

                except Exception as e:
                    logger.warning("menu_button_set_failed_calendar", error=str(e))

                logger.info("mode_switched_to_calendar", user_id=user_id)

        except Exception as e:
            logger.error("mode_switch_error", error=str(e), user_id=user_id)
            await update.message.reply_text("❌ Ошибка при переключении режима")

    async def handle_property_message(self, update: Update, user_id: str, text: str) -> None:
        """Handle message in property search mode."""
        try:
            # Handle MenuButton commands first
            if text.startswith('/'):
                if text == '/calendar':
                    await self.handle_mode_switch(update, user_id, BotMode.calendar)
                    return
                elif text == '/settings':
                    # Show settings (reuse from calendar bot)
                    await update.message.reply_text("⚙️ Настройки (будут добавлены)")
                    return

            # Check for quick buttons (legacy support)
            if text in ["🔍 Начать поиск", "Начать поиск"]:
                await self._start_search_flow(update, user_id)
                return

            if text in ["📊 Мои подборки", "Мои подборки"]:
                await self._show_my_selections(update, user_id)
                return

            if text in ["📅 Календарь", "Календарь", "🔙 Календарь"]:
                await self.handle_mode_switch(update, user_id, BotMode.calendar)
                return

            if text in ["⚙️ Настройки", "Настройки"]:
                # Show settings (reuse from calendar bot)
                await update.message.reply_text("⚙️ Настройки (будут добавлены)")
                return

            # Check conversation state
            if user_id in self.conversation_state and "step" in self.conversation_state.get(user_id, {}):
                await self._handle_conversation_step(update, user_id, text)
                return

            # Otherwise, treat as free-form search query
            await self._handle_free_form_query(update, user_id, text)

        except Exception as e:
            import traceback
            logger.error("property_message_error", error=str(e), traceback=traceback.format_exc(), user_id=user_id)
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")

    async def _start_search_flow(self, update: Update, user_id: str) -> None:
        """Start guided search flow."""
        # Initialize conversation state
        self.conversation_state[user_id] = {
            "step": "ask_budget",
            "data": {}
        }

        message = """💰 <b>Шаг 1/5: Бюджет</b>

Какой у вас бюджет на покупку квартиры?

Примеры:
• "до 10 миллионов"
• "от 8 до 12 млн"
• "около 15 миллионов"

Или напишите конкретную сумму."""

        await update.message.reply_text(message, parse_mode="HTML")

    async def _handle_conversation_step(self, update: Update, user_id: str, text: str) -> None:
        """Handle conversation step in guided flow."""
        state = self.conversation_state[user_id]
        step = state["step"]
        data = state["data"]

        if step == "ask_budget":
            # Parse budget from text
            budget = self._parse_budget(text)
            if budget:
                data["budget_min"] = budget.get("min")
                data["budget_max"] = budget.get("max")

                # Next step: rooms
                state["step"] = "ask_rooms"
                message = """🛏 <b>Шаг 2/5: Количество комнат</b>

Сколько комнат вам нужно?

Примеры:
• "2 комнаты"
• "3-комнатная"
• "от 2 до 3 комнат"
• "студия"""

                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text(
                    "❓ Не могу распознать бюджет. Попробуйте еще раз, например: 'от 8 до 12 миллионов'"
                )

        elif step == "ask_rooms":
            # Parse rooms
            rooms = self._parse_rooms(text)
            if rooms:
                data["rooms_min"] = rooms.get("min")
                data["rooms_max"] = rooms.get("max")

                # Next step: location
                state["step"] = "ask_location"
                message = """📍 <b>Шаг 3/5: Локация</b>

В каком районе или рядом с какой станцией метро?

Примеры:
• "Выборгский район"
• "Приморский"
• "рядом с метро Проспект Просвещения"
• "север города"

Или напишите "любой район"."""

                await update.message.reply_text(message, parse_mode="HTML")
            else:
                await update.message.reply_text(
                    "❓ Не могу распознать количество комнат. Попробуйте еще раз, например: '2 комнаты'"
                )

        elif step == "ask_location":
            # Parse location
            location = self._parse_location(text)
            data["districts"] = location.get("districts", [])
            data["metro_stations"] = location.get("metro_stations", [])

            # Next step: additional filters
            state["step"] = "ask_additional"
            message = """✨ <b>Шаг 4/5: Дополнительные требования</b>

Есть ли особые пожелания?

Примеры:
• "не первый этаж"
• "с лифтом"
• "с парковкой"
• "нужна ипотека"

Или напишите "нет" для пропуска."""

            await update.message.reply_text(message, parse_mode="HTML")

        elif step == "ask_additional":
            # Parse additional requirements
            additional = self._parse_additional(text)
            data.update(additional)

            # Next step: confirmation
            state["step"] = "confirm"

            # Build summary
            summary = self._build_search_summary(data)
            message = f"""📋 <b>Проверьте параметры поиска:</b>

{summary}

Все верно? Нажмите "✅ Подтвердить" или "✏️ Изменить"."""

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"property_confirm:{user_id}"),
                    InlineKeyboardButton("✏️ Изменить", callback_data=f"property_restart:{user_id}")
                ]
            ])

            await update.message.reply_text(message, parse_mode="HTML", reply_markup=keyboard)

    async def _handle_free_form_query(self, update: Update, user_id: str, text: str) -> None:
        """Handle free-form search query (using LLM to extract criteria)."""
        await update.message.reply_text("🔍 Анализирую ваш запрос...")

        try:
            # Get conversation history if exists
            conversation_history = []
            if user_id in self.conversation_state:
                # Get last 2 messages for context
                history = self.conversation_state[user_id].get("history", [])
                conversation_history = history[-2:] if len(history) > 2 else history

            # Extract criteria using LLM
            lang = self._get_user_language(user_id)
            result = await llm_agent_property.extract_search_criteria(
                user_message=text,
                user_id=user_id,
                conversation_history=conversation_history,
                language=lang.value
            )

            intent = result.get("intent")

            if intent == "out_of_scope":
                # Request is not about real estate
                await update.message.reply_text(
                    "Я помогаю только с поиском недвижимости. "
                    "Для работы с календарём вернитесь в режим календаря, нажав кнопку '🔙 Календарь'."
                )
                return

            elif intent == "clarify":
                # Need clarification
                question = result.get("clarify_question", "Не могли бы вы уточнить параметры поиска?")
                await update.message.reply_text(question)

                # Store conversation history
                if user_id not in self.conversation_state:
                    self.conversation_state[user_id] = {"history": []}
                self.conversation_state[user_id]["history"].append({
                    "role": "user",
                    "text": text
                })
                self.conversation_state[user_id]["history"].append({
                    "role": "assistant",
                    "text": question
                })
                return

            elif intent == "search":
                # Criteria extracted successfully
                criteria = result.get("criteria", {})

                # Log extracted criteria for debugging
                logger.info("search_criteria_extracted",
                           user_id=user_id,
                           criteria_keys=list(criteria.keys()),
                           districts=criteria.get("districts"),
                           metro_time_max=criteria.get("metro_time_max"),
                           budget_min=criteria.get("budget_min"),
                           budget_max=criteria.get("budget_max"))

                # Initialize conversation state with extracted data
                self.conversation_state[user_id] = {
                    "step": "confirm",
                    "data": criteria
                }

                # Build summary and show confirmation
                summary = self._build_search_summary(criteria)
                message = f"""📋 <b>Я понял ваш запрос:</b>

{summary}

Все верно? Нажмите "✅ Подтвердить" для поиска или "✏️ Изменить" для корректировки."""

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Подтвердить", callback_data=f"property_confirm:{user_id}"),
                        InlineKeyboardButton("✏️ Изменить", callback_data=f"property_restart:{user_id}")
                    ]
                ])

                await update.message.reply_text(message, parse_mode="HTML", reply_markup=keyboard)

            else:
                # Unknown intent - fallback to guided flow
                await self._start_search_flow(update, user_id)

        except Exception as e:
            logger.error("free_form_query_error", error=str(e), user_id=user_id)
            # Fallback to guided flow
            await update.message.reply_text(
                "Не удалось распознать запрос. Давайте пройдём пошаговый поиск."
            )
            await self._start_search_flow(update, user_id)

    async def _show_my_selections(self, update: Update, user_id: str) -> None:
        """Show user's saved selections."""
        # Get user's client profile
        client = await property_service.get_client_by_telegram_id(user_id)

        if not client:
            await update.message.reply_text(
                "У вас пока нет сохраненных подборок.\n\n"
                "Начните поиск, чтобы создать первую подборку!"
            )
            return

        # TODO: Get user's selections and display them
        await update.message.reply_text(
            "📊 <b>Ваши подборки:</b>\n\n"
            "(Функция в разработке)",
            parse_mode="HTML"
        )

    async def handle_property_callback(self, update: Update, user_id: str, callback_data: str) -> None:
        """Handle callback query in property mode."""
        query = update.callback_query
        await query.answer()

        if callback_data.startswith("property_confirm:"):
            await self._execute_search(update, user_id)

        elif callback_data.startswith("property_restart:"):
            # Restart search flow
            if user_id in self.conversation_state:
                del self.conversation_state[user_id]
            await self._start_search_flow(update, user_id)

        elif callback_data.startswith("property_like:"):
            listing_id = callback_data.split(":")[1]
            await self._handle_like(update, user_id, listing_id)

        elif callback_data.startswith("property_dislike:"):
            listing_id = callback_data.split(":")[1]
            await self._handle_dislike(update, user_id, listing_id)

        elif callback_data.startswith("property_unlike:"):
            listing_id = callback_data.split(":")[1]
            await self._handle_unlike(update, user_id, listing_id)

        elif callback_data.startswith("property_show_favorites:"):
            await self._show_favorites(update, user_id)

        elif callback_data.startswith("dislike_reason:"):
            parts = callback_data.split(":")
            listing_id = parts[1]
            reason = parts[2]
            await self._save_dislike_reason(update, user_id, listing_id, reason)

        elif callback_data.startswith("property_get_selection:"):
            await self._generate_selection(update, user_id)

    async def _execute_search(self, update: Update, user_id: str) -> None:
        """Execute property search with collected criteria."""
        if user_id not in self.conversation_state:
            await update.callback_query.message.reply_text("❌ Данные поиска не найдены")
            return

        data = self.conversation_state[user_id]["data"]

        try:
            # Normalize districts
            if data.get("districts"):
                data["districts"] = normalize_districts(data["districts"])
                logger.info("districts_normalized", original=self.conversation_state[user_id]["data"].get("districts"),
                           normalized=data["districts"])

            # Add budget tolerance (e.g., 15 млн -> 13-17 млн)
            budget_min, budget_max = add_budget_tolerance(
                data.get("budget_min"),
                data.get("budget_max"),
                tolerance=0.15
            )
            data["budget_min"] = budget_min
            data["budget_max"] = budget_max

            logger.info("search_params_prepared",
                       budget_min=budget_min,
                       budget_max=budget_max,
                       rooms_min=data.get("rooms_min"),
                       rooms_max=data.get("rooms_max"),
                       districts=data.get("districts"))

            # Create or update client profile
            client = await property_service.get_client_by_telegram_id(user_id)

            if not client:
                # Create new client
                client_data = PropertyClientCreate(
                    telegram_user_id=user_id,
                    budget_min=budget_min,
                    budget_max=budget_max,
                    rooms_min=data.get("rooms_min"),
                    rooms_max=data.get("rooms_max"),
                    deal_type=DealType.buy,  # Default to buy
                    districts=data.get("districts"),
                    metro_stations=data.get("metro_stations"),
                    not_first_floor=data.get("not_first_floor", False),
                    requires_elevator=data.get("requires_elevator", False),
                    allows_pets=data.get("allows_pets")
                )
                client = await property_service.create_client(client_data)

            # Search listings - try strict search first
            listings = await property_service.search_listings(
                deal_type=DealType.buy,
                price_min=budget_min,
                price_max=budget_max,
                rooms_min=data.get("rooms_min"),
                rooms_max=data.get("rooms_max"),
                districts=data.get("districts"),
                metro_stations=data.get("metro_stations"),
                mortgage_required=data.get("mortgage_required")
            )

            if not listings:
                # Try relaxed search - remove location constraints but keep price/rooms
                logger.info("exact_search_failed_trying_relaxed", user_id=user_id)
                listings = await property_service.search_listings(
                    deal_type=DealType.buy,
                    price_min=budget_min,
                    price_max=budget_max,
                    rooms_min=data.get("rooms_min"),
                    rooms_max=data.get("rooms_max"),
                    mortgage_required=data.get("mortgage_required")
                )

                if not listings:
                    # Still nothing - expand price range by 10% more
                    logger.info("relaxed_search_failed_expanding_price", user_id=user_id)
                    price_expansion = int(max(budget_max or 0, budget_min or 0) * 0.1)

                    listings = await property_service.search_listings(
                        deal_type=DealType.buy,
                        price_min=max(0, budget_min - price_expansion) if budget_min else None,
                        price_max=(budget_max + price_expansion) if budget_max else None,
                        rooms_min=data.get("rooms_min"),
                        rooms_max=data.get("rooms_max")
                    )

                if not listings:
                    # Show DB stats to help user understand what's available
                    stats = await property_service.get_db_stats(
                        deal_type=DealType.buy,
                        rooms_min=data.get("rooms_min"),
                        rooms_max=data.get("rooms_max")
                    )

                    stats_message = "😔 К сожалению, не нашли подходящих вариантов.\n\n"

                    if stats and stats.get("total_count", 0) > 0:
                        stats_message += f"📊 <b>В базе есть {stats['total_count']} квартир:</b>\n"
                        if stats.get("price_range"):
                            stats_message += f"💰 Цены: от {stats['price_range']['min']:,.0f} до {stats['price_range']['max']:,.0f} ₽\n"
                        if stats.get("area_range"):
                            stats_message += f"📐 Площадь: от {stats['area_range']['min']:.1f} до {stats['area_range']['max']:.1f} м²\n"
                        if stats.get("districts"):
                            districts_str = ", ".join(stats['districts'][:5])
                            stats_message += f"📍 Районы: {districts_str}\n"
                        stats_message += "\n💡 Попробуйте изменить параметры поиска или расширить бюджет."
                    else:
                        stats_message += "База объектов пока пуста. Попробуйте позже."

                    await update.callback_query.message.reply_text(stats_message, parse_mode="HTML")
                    return
                else:
                    # Show message that search was relaxed
                    await update.callback_query.message.reply_text(
                        "🔍 По точным параметрам ничего не нашлось, но вот похожие варианты:"
                    )

            # Rank listings
            client_profile = client.dict()
            ranked_listings = property_scoring_service.rank_listings(
                [listing.dict() for listing in listings],
                client_profile,
                top_n=10
            )

            # Show top results
            await self._show_search_results(update, user_id, ranked_listings)

            # Clear conversation state
            del self.conversation_state[user_id]

        except Exception as e:
            logger.error("search_execution_error", error=str(e), user_id=user_id, exc_info=True)
            await update.callback_query.message.reply_text("❌ Ошибка при выполнении поиска")

    async def _show_search_results(self, update: Update, user_id: str, listings: list) -> None:
        """Show search results to user."""
        if not listings:
            await update.callback_query.message.reply_text("❌ Объекты не найдены")
            return

        # Send header message
        header = f"✨ <b>Найдено {len(listings)} лучших вариантов:</b>\n\n"
        await update.callback_query.message.reply_text(header, parse_mode="HTML")

        # Send each property as separate message with details
        for i, listing in enumerate(listings[:5], 1):  # Show top 5
            await self._send_property_card(update, user_id, listing, i)

    async def _send_property_card(self, update: Update, user_id: str, listing: dict, index: int) -> None:
        """Send detailed property card to user."""
        from telegram import InputMediaPhoto

        # Basic info
        price_millions = listing["price"] / 1_000_000
        rooms = listing.get("rooms", "?")
        area = listing.get("area_total", "?")
        score = listing.get("dream_score", 0)

        # Location
        district = listing.get("district", "")
        metro = listing.get("metro_station", "")
        address = listing.get("address_raw", "Адрес не указан")

        # Building info
        residential_complex = listing.get("building_name", "ЖК не указан")
        ready_quarter = listing.get("ready_quarter")
        building_year = listing.get("building_year")
        floor = listing.get("floor")
        floor_total = listing.get("floors_total")

        # Build message
        message = f"<b>📍 Вариант {index}</b>\n\n"

        # Title and complex
        message += f"🏢 <b>{residential_complex}</b>\n"
        message += f"<i>{listing['title']}</i>\n\n"

        # Price and basic params
        message += f"💰 <b>{price_millions:.1f} млн ₽</b>\n"
        message += f"🏠 {rooms}-комн. • {area} м²\n"

        # Floor info
        if floor and floor_total:
            message += f"🔢 Этаж: {floor} из {floor_total}\n"
        elif floor:
            message += f"🔢 Этаж: {floor}\n"

        # Completion date
        if ready_quarter and building_year:
            quarters = {1: "I", 2: "II", 3: "III", 4: "IV"}
            quarter_str = quarters.get(ready_quarter, ready_quarter)
            message += f"📅 Срок сдачи: {quarter_str} квартал {building_year} г.\n"
        elif building_year:
            message += f"📅 Срок сдачи: {building_year} г.\n"

        message += "\n"

        # Location
        message += f"📍 <b>Расположение:</b>\n"
        message += f"   {address}\n"
        message += f"   {district}"
        if metro:
            message += f", м. {metro}"
        message += "\n\n"

        # Dream Score with explanation
        message += f"⭐️ <b>Dream Score: {score:.1f}/100</b>\n"

        # Generate explanation based on score components
        explanation = self._generate_score_explanation(listing, score)
        if explanation:
            message += f"<i>{explanation}</i>\n\n"

        # Add link if available
        if listing.get("external_url"):
            message += f"🔗 <a href=\"{listing['external_url']}\">Посмотреть на сайте застройщика</a>\n\n"

        # Collect photos and floor plans
        photos = listing.get("photos") or []
        floor_plans = listing.get("floor_plan_images") or []

        media_group = []

        # Add complex photos (max 2)
        if photos:
            for i, photo in enumerate(photos[:2]):
                if isinstance(photo, dict) and photo.get("url"):
                    caption = message if i == 0 else ""  # Add caption only to first photo
                    media_group.append(InputMediaPhoto(
                        media=photo["url"],
                        caption=caption,
                        parse_mode="HTML"
                    ))

        # Add floor plan (1)
        if floor_plans:
            plan = floor_plans[0]
            if isinstance(plan, dict) and plan.get("url"):
                plan_caption = f"📐 {plan.get('description', 'Планировка')}"
                media_group.append(InputMediaPhoto(
                    media=plan["url"],
                    caption=plan_caption,
                    parse_mode="HTML"
                ))

        # Send photos as media group if available
        if media_group:
            await update.callback_query.message.reply_media_group(media=media_group)
        else:
            # Fallback to text-only if no photos
            await update.callback_query.message.reply_text(
                message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )

        # Send buttons as separate message (media groups can't have buttons)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("❤️ Нравится", callback_data=f"property_like:{listing['id']}"),
                InlineKeyboardButton("👎 Не подходит", callback_data=f"property_dislike:{listing['id']}")
            ]
        ])

        await update.callback_query.message.reply_text(
            "Что думаете об этом варианте?",
            reply_markup=keyboard
        )

    def _generate_score_explanation(self, listing: dict, score: float) -> str:
        """Generate human-readable explanation of why property is interesting."""
        reasons = []

        # Price analysis
        price_millions = listing["price"] / 1_000_000
        if price_millions < 15:
            reasons.append("выгодная цена")

        # Location
        if listing.get("metro_station"):
            reasons.append("удобное расположение у метро")

        # Check amenities
        amenities = listing.get("amenities") or {}
        if amenities.get("has_parking"):
            reasons.append("есть паркинг")
        if amenities.get("has_playground"):
            reasons.append("детская площадка")

        # Builder reputation
        builder_data = listing.get("builder_data") or {}
        if builder_data.get("reputation_score", 0) > 80:
            reasons.append("надежный застройщик")

        # Completion date
        if listing.get("completion_date"):
            import re
            completion = listing.get("completion_date", "")
            # Check if ready or soon
            if "готов" in completion.lower() or "сдан" in completion.lower():
                reasons.append("дом сдан")
            elif "2025" in completion:
                reasons.append("скорая сдача")

        # Score interpretation
        if score >= 70:
            prefix = "Отличный вариант:"
        elif score >= 60:
            prefix = "Хороший вариант:"
        else:
            prefix = "Подходит по параметрам:"

        if reasons:
            return f"{prefix} {', '.join(reasons)}"
        else:
            return f"{prefix} соответствует вашим критериям"

    async def _handle_like(self, update: Update, user_id: str, listing_id: str) -> None:
        """Handle like feedback - save to favorites."""
        # Initialize favorites list for user if not exists
        if user_id not in self.conversation_state:
            self.conversation_state[user_id] = {}

        if "favorites" not in self.conversation_state[user_id]:
            self.conversation_state[user_id]["favorites"] = []

        # Add to favorites if not already there
        if listing_id not in self.conversation_state[user_id]["favorites"]:
            self.conversation_state[user_id]["favorites"].append(listing_id)

        favorites_count = len(self.conversation_state[user_id]["favorites"])

        # Update message with confirmation
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📋 Посмотреть избранное", callback_data=f"property_show_favorites:{user_id}"),
                InlineKeyboardButton("↩️ Убрать из избранного", callback_data=f"property_unlike:{listing_id}")
            ]
        ])

        await update.callback_query.edit_message_text(
            f"✅ <b>Добавлено в избранное!</b>\n\n"
            f"У вас {favorites_count} объект(ов) в избранном.\n"
            f"После просмотра всех вариантов вы сможете получить PDF-подборку для отправки клиенту.",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info("property_liked", user_id=user_id, listing_id=listing_id, favorites_count=favorites_count)

    async def _handle_dislike(self, update: Update, user_id: str, listing_id: str) -> None:
        """Handle dislike feedback - ask for reason."""
        # Store that user disliked this listing
        if user_id not in self.conversation_state:
            self.conversation_state[user_id] = {}

        if "dislikes" not in self.conversation_state[user_id]:
            self.conversation_state[user_id]["dislikes"] = {}

        # Ask for reason
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Дорого", callback_data=f"dislike_reason:{listing_id}:price_high")],
            [InlineKeyboardButton("📍 Не та локация", callback_data=f"dislike_reason:{listing_id}:location")],
            [InlineKeyboardButton("📐 Маленькая площадь", callback_data=f"dislike_reason:{listing_id}:area_small")],
            [InlineKeyboardButton("🏢 Не нравится ЖК", callback_data=f"dislike_reason:{listing_id}:complex")],
            [InlineKeyboardButton("📅 Поздняя сдача", callback_data=f"dislike_reason:{listing_id}:completion_late")],
            [InlineKeyboardButton("🤷 Другое", callback_data=f"dislike_reason:{listing_id}:other")]
        ])

        await update.callback_query.edit_message_text(
            "👎 <b>Почему не подходит?</b>\n\n"
            "Это поможет улучшить рекомендации:",
            parse_mode="HTML",
            reply_markup=keyboard
        )

        logger.info("property_disliked", user_id=user_id, listing_id=listing_id)

    async def _handle_unlike(self, update: Update, user_id: str, listing_id: str) -> None:
        """Remove from favorites."""
        if user_id in self.conversation_state and "favorites" in self.conversation_state[user_id]:
            if listing_id in self.conversation_state[user_id]["favorites"]:
                self.conversation_state[user_id]["favorites"].remove(listing_id)

        await update.callback_query.edit_message_text(
            "↩️ <b>Убрано из избранного</b>",
            parse_mode="HTML"
        )

        logger.info("property_unliked", user_id=user_id, listing_id=listing_id)

    async def _save_dislike_reason(self, update: Update, user_id: str, listing_id: str, reason: str) -> None:
        """Save dislike reason and update preferences."""
        if user_id in self.conversation_state:
            if "dislikes" not in self.conversation_state[user_id]:
                self.conversation_state[user_id]["dislikes"] = {}

            self.conversation_state[user_id]["dislikes"][listing_id] = reason

        reason_text = {
            "price_high": "Цена слишком высокая",
            "location": "Не подходит локация",
            "area_small": "Маленькая площадь",
            "complex": "Не нравится ЖК",
            "completion_late": "Слишком поздняя сдача",
            "other": "Другая причина"
        }.get(reason, "Не указана")

        await update.callback_query.edit_message_text(
            f"✅ <b>Учтено: {reason_text}</b>\n\n"
            f"Продолжайте просматривать варианты, я буду учитывать ваши предпочтения в следующих поисках.",
            parse_mode="HTML"
        )

        logger.info("dislike_reason_saved", user_id=user_id, listing_id=listing_id, reason=reason)

    async def _show_favorites(self, update: Update, user_id: str) -> None:
        """Show user's favorite listings."""
        if user_id not in self.conversation_state or "favorites" not in self.conversation_state[user_id]:
            await update.callback_query.message.reply_text(
                "У вас пока нет избранных объектов."
            )
            return

        favorites = self.conversation_state[user_id]["favorites"]

        if not favorites:
            await update.callback_query.message.reply_text(
                "У вас пока нет избранных объектов."
            )
            return

        # Get listings details from database
        listings = []
        for listing_id in favorites:
            # TODO: Fetch from DB
            listings.append({"id": listing_id, "title": f"Объект {listing_id[:8]}"})

        message = f"📋 <b>Ваши избранные объекты ({len(favorites)}):</b>\n\n"

        for i, listing in enumerate(listings, 1):
            message += f"{i}. {listing['title']}\n"

        message += "\n💡 Что дальше?"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Получить PDF-подборку", callback_data=f"property_get_selection:{user_id}")],
            [InlineKeyboardButton("🔗 Получить ссылку для клиента", callback_data=f"property_get_link:{user_id}")],
            [InlineKeyboardButton("🔍 Продолжить поиск", callback_data=f"property_restart:{user_id}")]
        ])

        await update.callback_query.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    async def _generate_selection(self, update: Update, user_id: str) -> None:
        """Generate PDF selection document."""
        if user_id not in self.conversation_state or "favorites" not in self.conversation_state[user_id]:
            await update.callback_query.message.reply_text(
                "❌ У вас нет избранных объектов"
            )
            return

        favorites = self.conversation_state[user_id]["favorites"]

        if not favorites:
            await update.callback_query.message.reply_text(
                "❌ У вас нет избранных объектов"
            )
            return

        await update.callback_query.message.reply_text(
            f"⏳ <b>Генерирую PDF-подборку...</b>\n\n"
            f"Объектов в подборке: {len(favorites)}\n\n"
            f"Это займет несколько секунд.",
            parse_mode="HTML"
        )

        # TODO: Generate PDF with property details, photos, floor plans
        # For now, send placeholder
        await update.callback_query.message.reply_text(
            f"📄 <b>PDF-подборка готова!</b>\n\n"
            f"Функция генерации PDF пока в разработке.\n\n"
            f"В финальной версии вы получите:\n"
            f"• Красиво оформленный PDF\n"
            f"• Все фото и планировки\n"
            f"• Описания объектов\n"
            f"• Контакты застройщиков\n"
            f"• Готовый файл для отправки клиенту\n\n"
            f"Избранные объекты: {len(favorites)} шт.",
            parse_mode="HTML"
        )

        logger.info("selection_generated", user_id=user_id, favorites_count=len(favorites))

    # ========== Helper methods for parsing ==========

    def _parse_budget(self, text: str) -> Optional[dict]:
        """Parse budget from text."""
        import re
        text_lower = text.lower()

        # Extract numbers (millions)
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)', text)
        if not numbers:
            return None

        numbers = [float(n.replace(',', '.')) for n in numbers]

        # Check for "million" keywords
        if "млн" in text_lower or "миллион" in text_lower:
            numbers = [n * 1_000_000 for n in numbers]
        elif all(n < 100 for n in numbers):  # Assume millions if small numbers
            numbers = [n * 1_000_000 for n in numbers]

        if len(numbers) == 1:
            # Single number - assume it's max
            if "до" in text_lower or "максимум" in text_lower:
                return {"min": 0, "max": int(numbers[0])}
            elif "от" in text_lower:
                return {"min": int(numbers[0]), "max": None}
            else:
                return {"min": 0, "max": int(numbers[0])}
        else:
            # Range
            return {"min": int(min(numbers)), "max": int(max(numbers))}

    def _parse_rooms(self, text: str) -> Optional[dict]:
        """Parse rooms from text."""
        import re
        text_lower = text.lower()

        if "студ" in text_lower:
            return {"min": 0, "max": 0}

        numbers = re.findall(r'(\d+)', text)
        if not numbers:
            return None

        numbers = [int(n) for n in numbers]

        if len(numbers) == 1:
            return {"min": numbers[0], "max": numbers[0]}
        else:
            return {"min": min(numbers), "max": max(numbers)}

    def _parse_location(self, text: str) -> dict:
        """Parse location from text."""
        text_lower = text.lower()

        # Simple extraction (can be improved with geocoding)
        result = {"districts": [], "metro_stations": []}

        if "любой" in text_lower or "неважно" in text_lower:
            return result

        # Extract metro stations
        if "метро" in text_lower:
            # Extract text after "метро"
            parts = text_lower.split("метро")
            if len(parts) > 1:
                station = parts[1].strip().split()[0] if parts[1].strip() else ""
                if station:
                    result["metro_stations"] = [station.capitalize()]

        # Otherwise treat as district
        if not result["metro_stations"]:
            # Extract district name (simple heuristic)
            result["districts"] = [text.strip()]

        return result

    def _parse_additional(self, text: str) -> dict:
        """Parse additional requirements from text."""
        text_lower = text.lower()
        result = {}

        if "не первый" in text_lower or "не 1" in text_lower:
            result["not_first_floor"] = True

        if "не последний" in text_lower:
            result["not_last_floor"] = True

        if "лифт" in text_lower:
            result["requires_elevator"] = True

        if "живот" in text_lower or "собак" in text_lower or "кош" in text_lower:
            result["allows_pets"] = True

        return result

    def _build_search_summary(self, data: dict) -> str:
        """Build human-readable summary of search criteria."""
        lines = []

        # Budget
        budget_min = data.get("budget_min", 0)
        budget_max = data.get("budget_max")
        if budget_max:
            lines.append(f"💰 Бюджет: {budget_min/1_000_000:.1f} - {budget_max/1_000_000:.1f} млн руб")
        elif budget_min:
            lines.append(f"💰 Бюджет: от {budget_min/1_000_000:.1f} млн руб")

        # Rooms
        rooms_min = data.get("rooms_min")
        rooms_max = data.get("rooms_max")
        if rooms_min == rooms_max:
            lines.append(f"🛏 Комнат: {rooms_min}")
        elif rooms_min and rooms_max:
            lines.append(f"🛏 Комнат: {rooms_min}-{rooms_max}")

        # Location
        districts = data.get("districts", [])
        metro_stations = data.get("metro_stations", [])
        metro_time_max = data.get("metro_time_max")

        if metro_stations:
            lines.append(f"📍 Метро: {', '.join(metro_stations)}")
        elif districts:
            lines.append(f"📍 Район: {', '.join(districts)}")

        if metro_time_max:
            lines.append(f"🚇 До метро: не более {metro_time_max} мин")

        # Mortgage and banks
        if data.get("mortgage_required"):
            banks = data.get("approved_banks", [])
            if banks:
                lines.append(f"🏦 Ипотека: {', '.join(banks)}")
            else:
                lines.append(f"🏦 С ипотекой")

        # Additional requirements
        additional = []
        if data.get("not_first_floor"):
            additional.append("не первый этаж")
        if data.get("requires_elevator"):
            additional.append("с лифтом")
        if data.get("has_parking"):
            additional.append("с парковкой")
        if data.get("balcony_required"):
            additional.append("с балконом")
        if data.get("allows_pets"):
            additional.append("с животными")

        if additional:
            lines.append(f"✨ Требования: {', '.join(additional)}")

        return "\n".join(lines)


# Global instance
property_handler = PropertyHandler()
