"""Telegram Bot Integration for Property Search.

This module provides integration between Property Search Bot and Telegram.
"""

import asyncio
from typing import Dict, Any, List, Optional
import structlog
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.services.property.llm_agent_property import PropertyLLMAgent
from app.services.property.property_service import PropertyService
from app.services.property.search_result_handler import SearchResultHandler
from app.services.property.dream_score import DreamScoreCalculator
from app.services.property.enrichment_orchestrator import EnrichmentOrchestrator
from app.schemas.property import PropertyListingResponse

logger = structlog.get_logger()


class PropertyTelegramIntegration:
    """
    Integration between Property Search Bot and Telegram.

    Handles:
    - Natural language search queries
    - Interactive result browsing
    - Detailed listing views with enrichment
    - Client profile management
    - Favorites and comparisons
    """

    def __init__(self):
        """Initialize property telegram integration."""
        self.llm_agent = PropertyLLMAgent()
        self.property_service = PropertyService()
        self.result_handler = SearchResultHandler()
        self.enrichment = EnrichmentOrchestrator()

        logger.info("property_telegram_integration_initialized")

    async def handle_search_query(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message: str
    ) -> None:
        """
        Handle property search query from user.

        Args:
            update: Telegram update object
            context: Telegram context
            message: User's search query in natural language
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        logger.info("property_search_initiated",
                   user_id=user_id,
                   query=message)

        # Send "searching" message
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="🔍 Ищу квартиры по вашим критериям..."
        )

        try:
            # 1. Extract search parameters from natural language
            params = await self.llm_agent.extract_search_params(message)

            logger.info("search_params_extracted",
                       user_id=user_id,
                       params_count=len(params))

            # 2. Get or create client profile
            client = await self.property_service.get_or_create_client(
                telegram_id=user_id,
                name=update.effective_user.full_name,
                preferences=params
            )

            # 3. Search listings
            listings = await self.property_service.search_listings(**params)

            # 4. Calculate Dream Scores
            for listing in listings:
                listing.dream_score = DreamScoreCalculator.calculate_score(
                    listing, client
                )

            # Sort by Dream Score (descending)
            listings.sort(key=lambda x: x.dream_score or 0, reverse=True)

            logger.info("search_completed",
                       user_id=user_id,
                       results_count=len(listings),
                       top_score=listings[0].dream_score if listings else None)

            # 5. Handle results based on count
            result = await self.result_handler.handle_results(
                listings, client, params
            )

            # 6. Format and send response
            await self._send_search_results(
                chat_id, status_msg.message_id, result, context
            )

        except Exception as e:
            logger.error("property_search_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"❌ Ошибка при поиске: {str(e)}\n\n"
                     f"Попробуйте переформулировать запрос."
            )

    async def _send_search_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send formatted search results to user."""
        scenario = result["scenario"]

        if scenario == "no_results":
            await self._send_no_results(chat_id, message_id, result, context)
        elif scenario == "few_results":
            await self._send_few_results(chat_id, message_id, result, context)
        elif scenario == "optimal_results":
            await self._send_optimal_results(chat_id, message_id, result, context)
        elif scenario == "clustered_results":
            await self._send_clustered_results(chat_id, message_id, result, context)
        else:  # too_many_results
            await self._send_too_many_results(chat_id, message_id, result, context)

    async def _send_no_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send no results message with suggestions."""
        lines = [
            "❌ К сожалению, ничего не найдено по вашим критериям.",
            "",
            "💡 Рекомендации:",
        ]

        for i, suggestion in enumerate(result.get("suggestions", []), 1):
            lines.append(f"{i}. {suggestion}")

        # Add filter relaxation options as buttons
        relaxations = result.get("filter_relaxations", [])
        keyboard = []

        for relaxation in relaxations[:3]:  # Top 3 relaxations
            callback_data = f"relax_{relaxation['filter']}"
            button_text = relaxation.get("suggestion", "Попробовать")
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=callback_data)
            ])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="\n".join(lines),
            reply_markup=reply_markup
        )

    async def _send_few_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send few results (1-20) - show all."""
        listings = result["listings"]

        text = f"✅ Найдено {len(listings)} {'квартира' if len(listings) == 1 else 'квартир(ы)'}:\n\n"

        # Delete status message
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

        # Send each listing as separate message with photo and buttons
        for i, listing in enumerate(listings, 1):
            await self._send_listing_card(chat_id, listing, i, context)

        # Send expansion suggestions
        if result.get("expansion_suggestion"):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"💡 {result['expansion_suggestion']}"
            )

    async def _send_optimal_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send optimal results (20-200) - show top 12."""
        total = result["total_count"]
        listings = result["listings"]

        lines = [
            f"✅ Найдено {total} квартир",
            f"Показываю топ-{len(listings)} по Dream Score:",
            ""
        ]

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="\n".join(lines)
        )

        # Send top listings as cards
        for i, listing in enumerate(listings, 1):
            await self._send_listing_card(chat_id, listing, i, context)

        # Send statistics
        stats = result.get("stats", {})
        stats_lines = [
            "📊 Статистика по всем результатам:",
            f"💰 Средняя цена: {stats.get('avg_price', 0)/1_000_000:.1f} млн ₽",
            f"📐 Средняя площадь: {stats.get('avg_area', 0):.1f} м²",
            f"📉 Диапазон цен: {stats.get('min_price', 0)/1_000_000:.1f}-{stats.get('max_price', 0)/1_000_000:.1f} млн ₽",
            f"🏢 Районов: {stats.get('districts_count', 0)}",
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(stats_lines)
        )

    async def _send_clustered_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send clustered results (100+ in one complex)."""
        total = result["total_count"]
        clusters = result["clusters"]

        lines = [
            f"🏢 Найдено {total} квартир в одном ЖК",
            f"Сгруппировал по планировке ({len(clusters)} групп):",
            ""
        ]

        for i, cluster in enumerate(clusters, 1):
            avg_price = cluster["avg_price"] / 1_000_000
            avg_area = cluster["avg_area"]
            count = cluster["count"]

            lines.append(
                f"{i}. {cluster['description']}: {count} шт, "
                f"~{avg_price:.1f}млн ₽, ~{avg_area:.1f}м²"
            )

        lines.append("")
        lines.append("Выберите интересную группу, чтобы посмотреть варианты:")

        # Create keyboard with cluster buttons
        keyboard = []
        for i, cluster in enumerate(clusters[:10], 1):  # Max 10 clusters
            callback_data = f"cluster_{i}"
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {cluster['description']} ({cluster['count']} шт)",
                    callback_data=callback_data
                )
            ])

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _send_too_many_results(
        self,
        chat_id: int,
        message_id: int,
        result: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send too many results message with narrowing suggestions."""
        total = result["total_count"]

        lines = [
            f"⚠️ Найдено слишком много квартир: {total}",
            "",
            "Уточните запрос для лучших результатов:",
        ]

        # Create keyboard with narrowing questions
        keyboard = []
        questions = result.get("narrowing_questions", [])

        for i, question in enumerate(questions[:5], 1):
            callback_data = f"narrow_{i}"
            keyboard.append([
                InlineKeyboardButton(
                    question.get("button_text", question["question"]),
                    callback_data=callback_data
                )
            ])

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _send_listing_card(
        self,
        chat_id: int,
        listing: PropertyListingResponse,
        index: int,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send single listing as a card with photo and details."""

        # Format listing text
        lines = [
            f"🏠 #{index} | Dream Score: {listing.dream_score}/100",
            "",
            f"💰 Цена: {listing.price/1_000_000:.1f} млн ₽",
            f"📐 Площадь: {listing.area_total} м² ({listing.rooms}-комн)",
            f"🏢 Этаж: {listing.floor}/{listing.floors_total}",
            f"📍 {listing.district}, м. {listing.metro_station or 'не указано'}",
        ]

        if listing.complex_name:
            lines.append(f"🏗️ ЖК: {listing.complex_name}")

        if listing.renovation:
            lines.append(f"🎨 Ремонт: {listing.renovation}")

        if listing.handover_date:
            lines.append(f"📅 Сдача: {listing.handover_date}")

        if listing.mortgage_available:
            lines.append("✅ Ипотека доступна")

        text = "\n".join(lines)

        # Create keyboard with action buttons
        keyboard = [
            [
                InlineKeyboardButton("📋 Детали", callback_data=f"details_{listing.id}"),
                InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_{listing.id}"),
            ],
            [
                InlineKeyboardButton("📞 Связаться", callback_data=f"contact_{listing.id}"),
                InlineKeyboardButton("🗺️ На карте", callback_data=f"map_{listing.id}"),
            ]
        ]

        # Send photo if available
        if listing.photo_urls and listing.photo_urls[0]:
            try:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=listing.photo_urls[0],
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except Exception as e:
                logger.warning("photo_send_error", listing_id=listing.id, error=str(e))
                # Send as text if photo fails
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            # Send as text
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_listing_details(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        listing_id: str
    ) -> None:
        """
        Show detailed listing information with full enrichment.

        Args:
            update: Telegram update object
            context: Telegram context
            listing_id: Listing ID to show details for
        """
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        logger.info("listing_details_requested",
                   user_id=user_id,
                   listing_id=listing_id)

        # Send "loading" message
        status_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="⏳ Загружаю детали и анализирую окружение..."
        )

        try:
            # Get listing
            listing = await self.property_service.get_listing(listing_id)
            if not listing:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text="❌ Квартира не найдена"
                )
                return

            # Get client profile
            client = await self.property_service.get_client_by_telegram_id(user_id)

            # Enrich with all external data (parallel execution)
            enrichment_data = await self.enrichment.enrich_listing_full(
                listing=listing,
                client=client,
                enable_poi=True,
                enable_routes=True,
                enable_vision=True,
                enable_price=True,
                enable_developer=True
            )

            logger.info("listing_enrichment_complete",
                       listing_id=listing_id,
                       enrichment_score=enrichment_data.get("enrichment_score", 0))

            # Delete loading message
            await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)

            # Send main photo
            if listing.photo_urls:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=listing.photo_urls[0],
                    caption=f"🏠 {listing.rooms}-комнатная квартира\n"
                            f"📍 {listing.district}, м. {listing.metro_station or 'не указано'}"
                )

            # Send detailed info
            await self._send_enriched_details(
                chat_id, listing, client, enrichment_data, context
            )

        except Exception as e:
            logger.error("listing_details_error",
                        user_id=user_id,
                        listing_id=listing_id,
                        error=str(e),
                        exc_info=True)

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"❌ Ошибка при загрузке: {str(e)}"
            )

    async def _send_enriched_details(
        self,
        chat_id: int,
        listing: PropertyListingResponse,
        client: Any,
        enrichment: Dict[str, Any],
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send enriched listing details in multiple messages."""

        # 1. Basic info
        basic_lines = [
            "📋 ОСНОВНАЯ ИНФОРМАЦИЯ",
            "",
            f"💰 Цена: {listing.price/1_000_000:.1f} млн ₽ ({listing.price_per_sqm:,.0f} ₽/м²)",
            f"📐 Площадь: {listing.area_total} м² (жилая {listing.area_living or 'н/д'} м², кухня {listing.area_kitchen or 'н/д'} м²)",
            f"🛏️ Комнат: {listing.rooms}",
            f"🏢 Этаж: {listing.floor}/{listing.floors_total}",
            f"🎨 Ремонт: {listing.renovation or 'не указано'}",
            f"📅 Срок сдачи: {listing.handover_date or 'не указано'}",
        ]

        if listing.complex_name:
            basic_lines.append(f"🏗️ ЖК: {listing.complex_name}")

        if listing.developer_name:
            basic_lines.append(f"👷 Застройщик: {listing.developer_name}")

        await context.bot.send_message(chat_id=chat_id, text="\n".join(basic_lines))

        # 2. Financial conditions
        financial_lines = ["💳 ФИНАНСОВЫЕ УСЛОВИЯ", ""]

        if listing.mortgage_available:
            financial_lines.append("✅ Ипотека доступна")
            if listing.initial_payment_pct:
                financial_lines.append(f"   Первый взнос от {listing.initial_payment_pct}%")

        if listing.payment_methods:
            financial_lines.append(f"💵 Способы оплаты: {', '.join(listing.payment_methods)}")

        if listing.installment_months:
            financial_lines.append(f"📆 Рассрочка: {listing.installment_months} мес")

        if len(financial_lines) > 2:
            await context.bot.send_message(chat_id=chat_id, text="\n".join(financial_lines))

        # 3. Price context
        price_data = enrichment.get("price_context")
        if price_data and price_data.get("comparable_count", 0) > 0:
            percentile = price_data.get("percentile", 50)
            value = price_data.get("value_assessment", "fair")
            avg_price = price_data.get("avg_price", 0)

            value_emoji = {
                "deal": "🎯",
                "good_value": "✅",
                "fair": "📊",
                "above_average": "⚠️",
                "expensive": "❌"
            }.get(value, "📊")

            price_lines = [
                "💹 РЫНОЧНЫЙ АНАЛИЗ",
                "",
                f"Перцентиль: {percentile}% (из 100%)",
                f"Средняя цена аналогов: {avg_price/1_000_000:.1f} млн ₽",
                f"{value_emoji} Оценка: {value}",
                f"Сравнивали с {price_data.get('comparable_count')} похожими квартирами",
            ]

            await context.bot.send_message(chat_id=chat_id, text="\n".join(price_lines))

        # 4. Infrastructure (POI)
        poi_data = enrichment.get("poi")
        if poi_data:
            poi_summary = self.enrichment.poi_service.get_poi_summary(poi_data)
            if "данные не найдены" not in poi_summary:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🗺️ ИНФРАСТРУКТУРА\n\n{poi_summary}"
                )

        # 5. Routes (if client has anchor points)
        routes_data = enrichment.get("routes")
        if routes_data and routes_data.get("routes"):
            routes_lines = ["🚗 МАРШРУТЫ", ""]
            for route in routes_data["routes"]:
                name = route.get("anchor_name", "Точка")
                duration = route.get("transit", {}).get("duration_minutes")
                if duration:
                    routes_lines.append(f"🚇 До {name}: {duration} мин")

            if len(routes_lines) > 2:
                await context.bot.send_message(chat_id=chat_id, text="\n".join(routes_lines))

        # 6. Developer reputation
        dev_data = enrichment.get("developer")
        if dev_data and dev_data.get("found"):
            score = dev_data.get("reputation_score", 0)
            tier = dev_data.get("tier", "unknown")

            tier_emoji = {
                "premium": "⭐⭐⭐",
                "reliable": "⭐⭐",
                "average": "⭐",
                "caution": "⚠️",
                "unknown": "❓"
            }.get(tier, "❓")

            dev_lines = [
                "👷 ЗАСТРОЙЩИК",
                "",
                f"{tier_emoji} Рейтинг: {score}/100",
                f"Уровень: {tier}",
            ]

            if dev_data.get("recommendation"):
                dev_lines.append(f"💡 {dev_data['recommendation']}")

            await context.bot.send_message(chat_id=chat_id, text="\n".join(dev_lines))

        # 7. Dream Score breakdown
        if listing.dream_score and client:
            score_breakdown = DreamScoreCalculator.explain_score(listing, client)

            score_lines = [
                f"⭐ DREAM SCORE: {listing.dream_score}/100",
                "",
                "Компоненты:",
            ]

            for component, details in score_breakdown.items():
                score_lines.append(f"• {component}: {details['score']}/100")
                if details.get("reason"):
                    score_lines.append(f"  {details['reason']}")

            await context.bot.send_message(chat_id=chat_id, text="\n".join(score_lines))

        # 8. Action buttons
        keyboard = [
            [
                InlineKeyboardButton("❤️ В избранное", callback_data=f"fav_{listing.id}"),
                InlineKeyboardButton("📞 Связаться", callback_data=f"contact_{listing.id}"),
            ],
            [
                InlineKeyboardButton("🗺️ Показать на карте", callback_data=f"map_{listing.id}"),
                InlineKeyboardButton("🔍 Похожие", callback_data=f"similar_{listing.id}"),
            ]
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text="Что дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# Global instance
property_telegram = PropertyTelegramIntegration()
