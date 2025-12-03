"""LLM Agent for Property Search Bot - Yandex GPT implementation."""

import json
from typing import Optional, List, Dict, Any
import structlog
from datetime import datetime

from app.config import settings

logger = structlog.get_logger()


class PropertyLLMAgent:
    """LLM Agent specifically for property search interactions."""

    def __init__(self):
        """Initialize Property LLM Agent."""
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id

        if not self.api_key or not self.folder_id:
            logger.warning("yandex_gpt_not_configured",
                          message="Property bot AI disabled. Set YANDEX_GPT_API_KEY and YANDEX_GPT_FOLDER_ID")

    async def extract_search_criteria(
        self,
        user_message: str,
        user_id: str,
        conversation_history: Optional[List[Dict]] = None,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """
        Extract property search criteria from user message.

        Args:
            user_message: User's message
            user_id: Telegram user ID
            conversation_history: Previous conversation context
            language: User's language

        Returns:
            Dictionary with extracted criteria
        """
        logger.info("extract_search_criteria_called",
                   user_id=user_id,
                   message_length=len(user_message))

        # System prompt for property search
        system_prompt = self._get_system_prompt(language)

        # Build messages
        messages = [
            {"role": "system", "text": system_prompt}
        ]

        # Add conversation history if exists
        if conversation_history:
            messages.extend(conversation_history)

        # Add current user message
        messages.append({
            "role": "user",
            "text": user_message
        })

        try:
            # Call Yandex GPT
            if not self.api_key:
                # Fallback to simple parsing
                return self._fallback_extraction(user_message)

            result = await self._call_yandex_gpt(messages)

            logger.info("search_criteria_extracted",
                       user_id=user_id,
                       result_keys=list(result.keys()))

            return result

        except Exception as e:
            logger.error("extraction_error",
                        error=str(e),
                        user_id=user_id)
            # Fallback to simple parsing
            return self._fallback_extraction(user_message)

    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt for property search agent."""
        if language == "ru":
            return """Ты - AI-агент для поиска недвижимости (новостроек) в Санкт-Петербурге. Твоя задача - извлекать параметры поиска из запросов пользователя.

ВАЖНО: Ты работаешь ТОЛЬКО с поиском недвижимости. НЕ обрабатывай запросы о календаре, событиях, встречах и т.п.

Из сообщения пользователя извлеки ВСЕ упомянутые параметры:

**ОБЯЗАТЕЛЬНЫЕ БАЗОВЫЕ ПАРАМЕТРЫ:**
1. **Бюджет** (budget_min, budget_max в рублях)
2. **Количество комнат** (rooms_min, rooms_max)
3. **Локация** (districts[], metro_stations[], metro_time_max в минутах до метро)

**ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ:**
4. **Площадь** (area_min, area_max в м², living_area_min, living_area_max, kitchen_area_min, kitchen_area_max)
5. **Этаж** (floor_min, floor_max, not_first_floor, not_last_floor)
6. **Тип сделки** (deal_type: "buy" или "rent")

**НОВЫЕ РАСШИРЕННЫЕ ПАРАМЕТРЫ:**

7. **Тип и категория:**
   - category: "квартира" (по умолчанию), "гараж", "коммерческая"
   - property_type: "жилая", "коммерческая"

8. **Характеристики дома:**
   - building_types: ["кирпично-монолитный", "панельный", "монолитный", "кирпичный"] - предпочтительные типы
   - exclude_building_types: [] - исключить типы домов
   - building_name: "название ЖК" - если упомянут конкретный комплекс

9. **Ремонт и отделка:**
   - renovations: ["чистовая", "предчистовая", "под ключ", "без отделки"] - какая отделка подходит
   - exclude_renovations: [] - какая отделка НЕ подходит

10. **Планировка:**
   - balcony_required: true/false - нужен ли балкон
   - balcony_types: ["балкон", "лоджия"] - тип балкона
   - bathroom_type: "раздельный" или "совмещенный"
   - bathroom_count_min: минимальное количество санузлов
   - min_ceiling_height: минимальная высота потолков в метрах

11. **Удобства:**
   - requires_elevator: true/false - нужен лифт
   - has_parking: true/false - нужна парковка
   - allows_pets: true/false
   - allows_kids: true/false

12. **ФИНАНСОВЫЕ УСЛОВИЯ (ВАЖНО!):**
   - mortgage_required: true/false - нужна ли ипотека
   - payment_methods: ["ипотека", "рассрочка", "материнский капитал", "жилищный сертификат", "субсидия"] - способы оплаты
   - approved_banks: ["Сбербанк", "ВТБ", "Газпромбанк", ...] - конкретные банки для ипотеки
   - haggle_allowed: true/false - возможен ли торг

13. **Срок сдачи:**
   - handover_quarter_min, handover_quarter_max: квартал (1-4)
   - handover_year_min, handover_year_max: год

14. **Застройщик:**
   - developers: ["ПИК", "ЛСР", ...] - предпочтительные застройщики
   - exclude_developers: [] - исключить застройщиков

15. **Инфраструктура рядом:**
   - school_nearby: true/false - школа в пешей доступности
   - kindergarten_nearby: true/false - детский сад рядом
   - park_nearby: true/false - парк рядом

**ВАЖНО: ГЕОГРАФИЧЕСКИЕ ЗОНЫ САНКТ-ПЕТЕРБУРГА**

Когда пользователь говорит "север города", "юг", "центр" и т.п., переводи в конкретные районы:

- **СЕВЕР ГОРОДА**: ["Выборгский", "Приморский", "Калининский"]
- **ЮГ ГОРОДА**: ["Кировский", "Красносельский", "Московский"]
- **ЦЕНТР ГОРОДА**: ["Адмиралтейский", "Василеостровский", "Петроградский", "Центральный"]
- **ВОСТОК ГОРОДА**: ["Невский", "Красногвардейский", "Фрунзенский"]

**Время до центра/метро:**
- "20 минут от центра" → metro_time_max: 20
- "в шаговой доступности от метро" → metro_time_max: 10
- "рядом с метро" → metro_time_max: 5

**ПРИМЕРЫ ИЗВЛЕЧЕНИЯ ФИНАНСОВЫХ ПАРАМЕТРОВ:**

Запрос: "Ищу квартиру с ипотекой, желательно в рассрочку"
→ mortgage_required: true, payment_methods: ["ипотека", "рассрочка"]

Запрос: "Нужна квартира с материнским капиталом, торг возможен"
→ payment_methods: ["материнский капитал"], haggle_allowed: true

Запрос: "Только ипотека Сбербанка"
→ mortgage_required: true, payment_methods: ["ипотека"], approved_banks: ["Сбербанк"]

Запрос: "Без ипотеки, готов платить сразу"
→ mortgage_required: false

**ПРИМЕРЫ ИЗВЛЕЧЕНИЯ ГЕОГРАФИИ:**

Запрос: "Ищу двушку на севере города"
→ rooms_min: 2, rooms_max: 2, districts: ["Выборгский", "Приморский", "Калининский"]

Запрос: "Квартира в 20 минутах от центра"
→ metro_time_max: 20

Запрос: "Хочу на юге, в районе Московской"
→ districts: ["Кировский", "Красносельский", "Московский"], metro_stations: ["Московская"]

**ПРИМЕРЫ ИЗВЛЕЧЕНИЯ ВСЕХ ПАРАМЕТРОВ:**

Запрос: "Хочу 2-комнатную до 10 млн в Бутово, не первый этаж, с ипотекой"
Ответ:
{
  "intent": "search",
  "criteria": {
    "budget_max": 10000000,
    "rooms_min": 2,
    "rooms_max": 2,
    "districts": ["Бутово"],
    "not_first_floor": true,
    "mortgage_required": true,
    "deal_type": "buy"
  },
  "confidence": 0.9
}

Запрос: "Нужна квартира с чистовой отделкой, кирпичный дом, с балконом, парковка обязательна"
Ответ:
{
  "intent": "search",
  "criteria": {
    "renovations": ["чистовая"],
    "building_types": ["кирпичный", "кирпично-монолитный"],
    "balcony_required": true,
    "has_parking": true,
    "deal_type": "buy"
  },
  "confidence": 0.8
}

Запрос: "3к от 8 до 12 млн, сдача в 2025, ипотека Сбербанка, детский сад рядом"
Ответ:
{
  "intent": "search",
  "criteria": {
    "budget_min": 8000000,
    "budget_max": 12000000,
    "rooms_min": 3,
    "rooms_max": 3,
    "handover_year_min": 2025,
    "handover_year_max": 2025,
    "mortgage_required": true,
    "approved_banks": ["Сбербанк"],
    "kindergarten_nearby": true,
    "deal_type": "buy"
  },
  "confidence": 0.9
}

Запрос: "Найди мне квартиру за 18000000 двухкомнатную на севере города в 20 минутах от центра Подходящую под ипотеку сбербанка"
Ответ:
{
  "intent": "search",
  "criteria": {
    "budget_max": 18000000,
    "rooms_min": 2,
    "rooms_max": 2,
    "districts": ["Выборгский", "Приморский", "Калининский"],
    "metro_time_max": 20,
    "mortgage_required": true,
    "approved_banks": ["Сбербанк"],
    "deal_type": "buy"
  },
  "confidence": 0.95
}

**ЕСЛИ ПАРАМЕТРОВ МАЛО:**
Если упомянуто менее 3 обязательных параметров (бюджет, комнаты, локация) - запроси уточнение:
{
  "intent": "clarify",
  "clarify_question": "Уточните, пожалуйста: какой у вас бюджет, сколько комнат и в каком районе ищете?",
  "confidence": 0.3
}

**ЕСЛИ ЗАПРОС НЕ О НЕДВИЖИМОСТИ:**
{
  "intent": "out_of_scope",
  "message": "Я помогаю только с поиском недвижимости",
  "confidence": 1.0
}

Отвечай ТОЛЬКО в формате JSON."""
        else:
            return """You are an AI agent for real estate search (new construction). Your task is to extract search parameters from user requests.

IMPORTANT: You work ONLY with real estate search. DO NOT process queries about calendar, events, meetings, etc.

Extract ALL mentioned parameters from user message:

**REQUIRED BASIC PARAMETERS:**
1. **Budget** (budget_min, budget_max in rubles)
2. **Rooms** (rooms_min, rooms_max)
3. **Location** (districts[], metro_stations[])

**ADDITIONAL PARAMETERS:**
4. **Area** (area_min, area_max in m², living_area_min, living_area_max, kitchen_area_min, kitchen_area_max)
5. **Floor** (floor_min, floor_max, not_first_floor, not_last_floor)
6. **Deal type** (deal_type: "buy" or "rent")

**NEW EXTENDED PARAMETERS:**

7. **Type and category:**
   - category: "квартира" (default), "гараж", "коммерческая"
   - property_type: "жилая", "коммерческая"

8. **Building characteristics:**
   - building_types: ["brick-monolithic", "panel", "monolithic", "brick"] - preferred types
   - exclude_building_types: [] - types to exclude
   - building_name: "complex name" - if specific complex mentioned

9. **Renovation:**
   - renovations: ["finished", "pre-finished", "turnkey", "without"] - suitable renovation types
   - exclude_renovations: [] - unsuitable types

10. **Layout:**
   - balcony_required: true/false - balcony needed
   - balcony_types: ["balcony", "loggia"] - balcony type
   - bathroom_type: "separate" or "combined"
   - bathroom_count_min: minimum number of bathrooms
   - min_ceiling_height: minimum ceiling height in meters

11. **Amenities:**
   - requires_elevator: true/false - elevator needed
   - has_parking: true/false - parking needed
   - allows_pets: true/false
   - allows_kids: true/false

12. **FINANCIAL CONDITIONS (IMPORTANT!):**
   - mortgage_required: true/false - mortgage needed
   - payment_methods: ["mortgage", "installments", "maternity capital", "housing certificate", "subsidy"] - payment methods
   - haggle_allowed: true/false - negotiation possible

13. **Handover date:**
   - handover_quarter_min, handover_quarter_max: quarter (1-4)
   - handover_year_min, handover_year_max: year

14. **Developer:**
   - developers: ["PIK", "LSR", ...] - preferred developers
   - exclude_developers: [] - developers to exclude

15. **Nearby infrastructure:**
   - school_nearby: true/false - school within walking distance
   - kindergarten_nearby: true/false - kindergarten nearby
   - park_nearby: true/false - park nearby

**FINANCIAL PARAMETERS EXTRACTION EXAMPLES:**

Request: "Looking for apartment with mortgage, preferably installments"
→ mortgage_required: true, payment_methods: ["mortgage", "installments"]

Request: "Need apartment with maternity capital, negotiation possible"
→ payment_methods: ["maternity capital"], haggle_allowed: true

**IF TOO FEW PARAMETERS:**
If less than 3 required parameters mentioned (budget, rooms, location) - ask for clarification:
{
  "intent": "clarify",
  "clarify_question": "Please specify: what is your budget, how many rooms, and which area?",
  "confidence": 0.3
}

**IF REQUEST NOT ABOUT REAL ESTATE:**
{
  "intent": "out_of_scope",
  "message": "I only help with real estate search",
  "confidence": 1.0
}

Respond ONLY in JSON format."""

    async def _call_yandex_gpt(self, messages: List[Dict]) -> Dict[str, Any]:
        """Call Yandex GPT API."""
        import aiohttp

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        # Convert messages to Yandex format
        yandex_messages = []
        for msg in messages:
            yandex_messages.append({
                "role": msg["role"],
                "text": msg["text"]
            })

        payload = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": 2000
            },
            "messages": yandex_messages
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("yandex_gpt_error",
                               status=response.status,
                               error=error_text)
                    raise Exception(f"Yandex GPT API error: {response.status}")

                result = await response.json()
                text = result["result"]["alternatives"][0]["message"]["text"]

                # Parse JSON from response
                try:
                    # Try to extract JSON from markdown code blocks
                    if "```json" in text:
                        json_text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        json_text = text.split("```")[1].split("```")[0].strip()
                    else:
                        json_text = text.strip()

                    return json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error("json_parse_error",
                               error=str(e),
                               text=text[:200])
                    # Return fallback
                    return {
                        "intent": "clarify",
                        "clarify_question": "Извините, не совсем понял. Не могли бы вы уточнить параметры поиска?",
                        "confidence": 0.1
                    }

    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Simple fallback extraction without LLM with extended parameters support."""
        import re

        text_lower = text.lower()
        criteria = {}

        # Extract budget
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)', text)
        if numbers:
            numbers = [float(n.replace(',', '.')) for n in numbers]

            # Check for "million" keywords
            if "млн" in text_lower or "миллион" in text_lower:
                numbers = [n * 1_000_000 for n in numbers]
            elif all(n < 100 for n in numbers):
                numbers = [n * 1_000_000 for n in numbers]

            if len(numbers) >= 1:
                if "до" in text_lower:
                    criteria["budget_max"] = int(numbers[0])
                elif "от" in text_lower and len(numbers) >= 2:
                    criteria["budget_min"] = int(numbers[0])
                    criteria["budget_max"] = int(numbers[1])
                elif len(numbers) == 1:
                    criteria["budget_max"] = int(numbers[0])
                else:
                    criteria["budget_min"] = int(min(numbers))
                    criteria["budget_max"] = int(max(numbers))

        # Extract rooms
        rooms_match = re.search(r'(\d+)\s*(?:комн|к\s|room)', text_lower)
        if rooms_match:
            rooms = int(rooms_match.group(1))
            criteria["rooms_min"] = rooms
            criteria["rooms_max"] = rooms
        elif "студ" in text_lower:
            criteria["rooms_min"] = 0
            criteria["rooms_max"] = 0

        # Extract districts/metro
        if "метро" in text_lower:
            parts = text_lower.split("метро")
            if len(parts) > 1:
                station = parts[1].strip().split()[0] if parts[1].strip() else ""
                if station:
                    criteria["metro_stations"] = [station.capitalize()]

        # Floor preferences
        if "не первый" in text_lower or "не 1" in text_lower:
            criteria["not_first_floor"] = True
        if "не последний" in text_lower:
            criteria["not_last_floor"] = True
        if "лифт" in text_lower:
            criteria["requires_elevator"] = True

        # Pets
        if any(word in text_lower for word in ["живот", "собак", "кош", "питом"]):
            criteria["allows_pets"] = True

        # NEW: Renovation
        if any(word in text_lower for word in ["чистов", "ремонт"]):
            criteria["renovations"] = ["чистовая"]
        elif "без отделк" in text_lower:
            criteria["renovations"] = ["без отделки"]

        # NEW: Building type
        if "кирпич" in text_lower:
            criteria["building_types"] = ["кирпичный", "кирпично-монолитный"]
        elif "панел" in text_lower:
            criteria["building_types"] = ["панельный"]
        elif "монолит" in text_lower:
            criteria["building_types"] = ["монолитный", "кирпично-монолитный"]

        # NEW: Balcony
        if "балкон" in text_lower or "лоджи" in text_lower:
            criteria["balcony_required"] = True
            if "лоджи" in text_lower:
                criteria["balcony_types"] = ["лоджия"]

        # NEW: Bathroom
        if "раздельн" in text_lower:
            criteria["bathroom_type"] = "раздельный"
        elif "совмещ" in text_lower:
            criteria["bathroom_type"] = "совмещенный"

        # NEW: Parking
        if "парков" in text_lower or "машиномест" in text_lower:
            criteria["has_parking"] = True

        # NEW: Financial conditions (IMPORTANT!)
        if any(word in text_lower for word in ["ипотек", "mortgage"]):
            criteria["mortgage_required"] = True
            criteria["payment_methods"] = ["ипотека"]

        if any(word in text_lower for word in ["рассрочк", "installment"]):
            if "payment_methods" not in criteria:
                criteria["payment_methods"] = []
            if "рассрочка" not in criteria["payment_methods"]:
                criteria["payment_methods"].append("рассрочка")

        if "материнск" in text_lower:
            if "payment_methods" not in criteria:
                criteria["payment_methods"] = []
            criteria["payment_methods"].append("материнский капитал")

        if any(word in text_lower for word in ["торг", "сторг", "bargain"]):
            criteria["haggle_allowed"] = True

        # NEW: Infrastructure
        if any(word in text_lower for word in ["школ", "school"]):
            criteria["school_nearby"] = True

        if "детск" in text_lower and ("сад" in text_lower or "садик" in text_lower):
            criteria["kindergarten_nearby"] = True

        if "парк" in text_lower and "парков" not in text_lower:  # "парк" но не "парковка"
            criteria["park_nearby"] = True

        # NEW: Handover year
        year_match = re.search(r'сдача.*?(\d{4})', text_lower)
        if year_match:
            year = int(year_match.group(1))
            criteria["handover_year_min"] = year
            criteria["handover_year_max"] = year

        # Deal type
        if "арен" in text_lower or "снять" in text_lower:
            criteria["deal_type"] = "rent"
        else:
            criteria["deal_type"] = "buy"

        if criteria:
            return {
                "intent": "search",
                "criteria": criteria,
                "confidence": 0.6
            }
        else:
            return {
                "intent": "clarify",
                "clarify_question": "Расскажите, пожалуйста, что вы ищете? Например: бюджет, количество комнат, район.",
                "confidence": 0.3
            }

    async def generate_listing_explanation(
        self,
        listing: Dict[str, Any],
        client_profile: Dict[str, Any],
        dream_score: float,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for listing.

        Args:
            listing: Property listing data
            client_profile: Client profile
            dream_score: Calculated Dream Score
            language: User's language

        Returns:
            Explanation dictionary
        """
        # For now, use simple template-based generation
        # Can be enhanced with LLM in the future

        explanation = {
            "why_top": [],
            "compromise": [],
            "price_context": "",
            "routes": {},
            "check_on_viewing": []
        }

        # Why in top
        if listing.get("metro_distance_minutes", 100) <= 10:
            explanation["why_top"].append(
                f"Близко к метро ({listing['metro_distance_minutes']} мин)" if language == "ru"
                else f"Close to metro ({listing['metro_distance_minutes']} min)"
            )

        vision_data = listing.get("vision_data", {})
        if vision_data.get("light_score", 0) > 0.7:
            explanation["why_top"].append(
                "Светлая квартира с хорошим освещением" if language == "ru"
                else "Bright apartment with good lighting"
            )

        # Compromises
        floor = listing.get("floor", 1)
        if floor == 1 and client_profile.get("not_first_floor"):
            explanation["compromise"].append(
                "Первый этаж" if language == "ru" else "First floor"
            )

        # Price context
        market_data = listing.get("market_data", {})
        pct = market_data.get("pct", 50)
        if pct < 40:
            explanation["price_context"] = (
                f"Цена ниже рынка на {50-pct}%. Хороший вариант для торга." if language == "ru"
                else f"Price below market by {50-pct}%. Good bargaining option."
            )
        elif pct > 60:
            explanation["price_context"] = (
                f"Цена выше рынка на {pct-50}%. Есть пространство для переговоров." if language == "ru"
                else f"Price above market by {pct-50}%. Room for negotiation."
            )
        else:
            explanation["price_context"] = (
                "Цена соответствует рынку." if language == "ru"
                else "Price matches market."
            )

        return explanation


# Global instance
llm_agent_property = PropertyLLMAgent()
