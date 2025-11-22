"""
Сервис поиска недвижимости с поддержкой контекстных диалогов
"""

import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.property.property_service import property_service
from app.services.property.llm_agent_property import PropertyLLMAgent
from app.services.property.feed_loader import PropertyFeedLoader

logger = structlog.get_logger()


class PropertySearchService:
    """
    Сервис для интеллектуального поиска недвижимости
    с поддержкой многошагового диалога и уточнений
    """

    def __init__(self):
        self.llm_agent = PropertyLLMAgent()
        self.feed_loader = PropertyFeedLoader()
        self.property_service = property_service

        # Кэш контекстов пользователей
        self.user_contexts: Dict[int, Dict[str, Any]] = {}

    async def search_properties(
        self,
        user_id: int,
        query: str,
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск недвижимости с учетом контекста диалога

        Args:
            user_id: ID пользователя Telegram
            query: Текстовый запрос пользователя
            previous_results: Предыдущие результаты поиска для уточнения

        Returns:
            Список объектов недвижимости, отсортированных по релевантности
        """

        logger.info("property_search_started",
                   user_id=user_id,
                   query=query,
                   has_previous_results=bool(previous_results))

        # Получаем или создаем контекст пользователя
        context = self._get_or_create_context(user_id)

        # Добавляем текущий запрос в историю
        context["conversation_history"].append({
            "role": "user",
            "content": query,
            "timestamp": datetime.now().isoformat()
        })

        try:
            # Анализируем запрос (упрощенная версия без LLM для тестирования)
            parsed_criteria = self._parse_query_simple(query)

            logger.info("search_criteria_parsed",
                       user_id=user_id,
                       criteria=parsed_criteria)

            # Обновляем накопленные критерии
            context["accumulated_criteria"] = self._merge_criteria(
                context["accumulated_criteria"],
                parsed_criteria
            )

            # Получаем клиента из БД или создаем нового
            client = await self.property_service.get_client_by_telegram_id(str(user_id))

            if not client:
                # Создаем временного клиента для поиска
                from app.schemas.property import PropertyClientCreate
                client_data = PropertyClientCreate(
                    telegram_user_id=str(user_id),
                    deal_type=context["accumulated_criteria"].get("deal_type", "sale"),
                    min_price=context["accumulated_criteria"].get("min_price"),
                    max_price=context["accumulated_criteria"].get("max_price"),
                    min_rooms=context["accumulated_criteria"].get("min_rooms"),
                    max_rooms=context["accumulated_criteria"].get("max_rooms"),
                )
                client = await self.property_service.create_client(client_data)

            # Загружаем объекты из фида
            all_properties = await self.feed_loader.get_cached_properties()

            if not all_properties:
                logger.warning("no_properties_in_feed", user_id=user_id)
                return []

            # Фильтруем по базовым критериям
            filtered_properties = self._filter_properties(
                all_properties,
                context["accumulated_criteria"]
            )

            logger.info("properties_filtered",
                       user_id=user_id,
                       total=len(all_properties),
                       filtered=len(filtered_properties))

            # Скорим и сортируем результаты
            scored_properties = await self._score_and_rank(
                filtered_properties,
                context["accumulated_criteria"],
                user_id
            )

            # Сохраняем результаты в контекст
            context["last_results"] = scored_properties
            context["last_search_time"] = datetime.now().isoformat()

            # Добавляем ответ бота в историю
            context["conversation_history"].append({
                "role": "assistant",
                "content": f"Найдено {len(scored_properties)} объектов",
                "timestamp": datetime.now().isoformat(),
                "results_count": len(scored_properties)
            })

            return scored_properties

        except Exception as e:
            logger.error("property_search_error",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)
            raise

    def _get_or_create_context(self, user_id: int) -> Dict[str, Any]:
        """Получить или создать контекст пользователя"""

        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = {
                "user_id": user_id,
                "conversation_history": [],
                "accumulated_criteria": {},
                "last_results": [],
                "last_search_time": None,
                "created_at": datetime.now().isoformat()
            }

        return self.user_contexts[user_id]

    def _merge_criteria(
        self,
        existing: Dict[str, Any],
        new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Объединение критериев поиска
        Новые критерии дополняют или уточняют существующие
        """

        merged = existing.copy()

        for key, value in new.items():
            if value is not None:
                if key in ["requirements", "preferences"]:
                    # Для списков требований - добавляем новые
                    if key not in merged:
                        merged[key] = []
                    if isinstance(value, list):
                        merged[key].extend(value)
                    else:
                        merged[key].append(value)
                else:
                    # Для остальных - перезаписываем
                    merged[key] = value

        return merged

    def _filter_properties(
        self,
        properties: List[Dict[str, Any]],
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Фильтрация объектов по критериям
        """

        filtered = properties

        # Фильтр по цене
        if criteria.get("min_price"):
            filtered = [
                p for p in filtered
                if self._extract_price(p) >= criteria["min_price"]
            ]

        if criteria.get("max_price"):
            filtered = [
                p for p in filtered
                if self._extract_price(p) <= criteria["max_price"]
            ]

        # Фильтр по количеству комнат
        if criteria.get("rooms") is not None:
            filtered = [
                p for p in filtered
                if str(p.get("rooms", "")).strip() == str(criteria["rooms"])
            ]
        elif criteria.get("min_rooms") is not None:
            filtered = [
                p for p in filtered
                if self._safe_int(p.get("rooms", 0)) >= criteria["min_rooms"]
            ]

        # Фильтр по площади
        if criteria.get("min_area"):
            filtered = [
                p for p in filtered
                if self._extract_area(p) >= criteria["min_area"]
            ]

        if criteria.get("max_area"):
            filtered = [
                p for p in filtered
                if self._extract_area(p) <= criteria["max_area"]
            ]

        # Фильтр по этажу
        if criteria.get("min_floor"):
            filtered = [
                p for p in filtered
                if self._safe_int(p.get("floor", 0)) >= criteria["min_floor"]
            ]

        if criteria.get("avoid_first_floor"):
            filtered = [
                p for p in filtered
                if self._safe_int(p.get("floor", 0)) != 1
            ]

        if criteria.get("avoid_last_floor"):
            filtered = [
                p for p in filtered
                if p.get("floor") != p.get("floors_total")
            ]

        # Фильтр по району/локации
        if criteria.get("districts"):
            districts_lower = [d.lower() for d in criteria["districts"]]
            filtered = [
                p for p in filtered
                if any(d in str(p.get("location", {}.get("address", ""))).lower()
                      for d in districts_lower)
            ]

        # Фильтр по времени до метро
        if criteria.get("max_metro_time"):
            filtered = [
                p for p in filtered
                if self._check_metro_time(p, criteria["max_metro_time"])
            ]

        return filtered

    async def _score_and_rank(
        self,
        properties: List[Dict[str, Any]],
        criteria: Dict[str, Any],
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Скоринг и ранжирование объектов по релевантности
        """

        scored_properties = []

        for prop in properties:
            score = 0.0

            # Базовый скор за соответствие основным критериям
            if criteria.get("rooms") is not None:
                if str(prop.get("rooms")) == str(criteria["rooms"]):
                    score += 10.0

            # Скор за цену (чем ближе к максимуму бюджета, тем лучше)
            if criteria.get("max_price"):
                price = self._extract_price(prop)
                if price > 0:
                    price_ratio = price / criteria["max_price"]
                    if 0.7 <= price_ratio <= 1.0:
                        score += 8.0
                    elif 0.5 <= price_ratio < 0.7:
                        score += 5.0

            # Скор за площадь
            if criteria.get("min_area"):
                area = self._extract_area(prop)
                if area >= criteria["min_area"]:
                    score += 5.0
                    # Бонус за дополнительную площадь
                    extra_area = area - criteria["min_area"]
                    score += min(extra_area / 10, 3.0)

            # Скор за этаж
            floor = self._safe_int(prop.get("floor", 0))
            if criteria.get("min_floor") and floor >= criteria["min_floor"]:
                score += 5.0

            # Скор за близость к метро
            if criteria.get("max_metro_time"):
                if self._check_metro_time(prop, criteria["max_metro_time"]):
                    score += 7.0

            # Скор за дополнительные требования
            requirements = criteria.get("requirements", [])
            for req in requirements:
                if self._check_requirement(prop, req):
                    score += 3.0

            # Добавляем скор к объекту
            prop_with_score = prop.copy()
            prop_with_score["relevance_score"] = score
            scored_properties.append(prop_with_score)

        # Сортируем по убыванию релевантности
        scored_properties.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        return scored_properties

    # ============ Вспомогательные методы ============

    def _parse_query_simple(self, query: str) -> Dict[str, Any]:
        """
        Простой парсинг запроса без LLM (для тестирования)
        Ищет ключевые слова и числа в запросе
        """

        criteria = {}
        query_lower = query.lower()

        # Парсинг количества комнат
        import re

        # 1-комнатная, 2-комнатная, трешка и т.д.
        if "1" in query or "одн" in query_lower or "однушк" in query_lower or "1к" in query_lower:
            criteria["rooms"] = 1
        elif "2" in query or "дв" in query_lower or "двушк" in query_lower or "2к" in query_lower:
            criteria["rooms"] = 2
        elif "3" in query or "тр" in query_lower and "комн" in query_lower or "трешк" in query_lower or "3к" in query_lower:
            criteria["rooms"] = 3
        elif "студ" in query_lower:
            criteria["rooms"] = 0

        # Парсинг цены
        price_patterns = [
            r'(\d+)\s*(?:млн|миллион)',
            r'(\d+)\s*(?:тыс|тысяч)',
            r'до\s*(\d+)',
            r'за\s*(\d+)',
        ]

        for pattern in price_patterns:
            match = re.search(pattern, query_lower)
            if match:
                value = int(match.group(1))
                if "млн" in query_lower or "миллион" in query_lower:
                    criteria["max_price"] = value * 1000000
                elif "тыс" in query_lower or "тысяч" in query_lower:
                    criteria["max_price"] = value * 1000
                else:
                    # Предполагаем миллионы, если просто число
                    if value < 100:
                        criteria["max_price"] = value * 1000000
                break

        # Парсинг площади
        area_match = re.search(r'(\d+)\s*(?:квадрат|кв|м)', query_lower)
        if area_match:
            criteria["min_area"] = float(area_match.group(1))

        # Парсинг этажа
        if "высок" in query_lower and "этаж" in query_lower:
            criteria["min_floor"] = 10
        floor_match = re.search(r'(\d+)(?:-?го|\s+)?\s*этаж', query_lower)
        if floor_match:
            criteria["min_floor"] = int(floor_match.group(1))

        # Парсинг времени до метро
        metro_match = re.search(r'(\d+)\s*минут.*метро', query_lower)
        if metro_match:
            criteria["max_metro_time"] = int(metro_match.group(1))

        # Дополнительные требования
        requirements = []

        if "парк" in query_lower:
            requirements.append("рядом с парком")
            criteria["near_park"] = True

        if "ремонт" in query_lower:
            requirements.append("с ремонтом")
            criteria["with_repair"] = True

        if "раздельн" in query_lower and ("санузел" in query_lower or "с/у" in query_lower):
            requirements.append("раздельный санузел")
            criteria["separate_bathroom"] = True

        if "балкон" in query_lower:
            requirements.append("с балконом")

        if "школ" in query_lower:
            requirements.append("рядом школа")
            criteria["near_school"] = True

        if "сад" in query_lower and "детск" in query_lower:
            requirements.append("рядом детский сад")
            criteria["near_kindergarten"] = True

        if "ипотек" in query_lower:
            requirements.append("подходит под ипотеку")
            criteria["mortgage_compatible"] = True

            # Проверяем конкретный банк
            if "сбер" in query_lower:
                criteria["mortgage_bank"] = "Сбербанк"

        if "не перв" in query_lower or "не послед" in query_lower:
            criteria["avoid_edge_floors"] = True

        if "тих" in query_lower or "двор" in query_lower:
            requirements.append("тихое место")
            criteria["quiet"] = True

        if requirements:
            criteria["requirements"] = requirements

        # Районы
        districts = []
        district_keywords = {
            "крылатск": "Крылатское",
            "строгин": "Строгино",
            "тушин": "Тушино",
            "митин": "Митино",
        }

        for keyword, district in district_keywords.items():
            if keyword in query_lower:
                districts.append(district)

        if districts:
            criteria["districts"] = districts

        return criteria

    def _extract_price(self, prop: Dict[str, Any]) -> float:
        """Извлечь цену из объекта"""
        try:
            price = prop.get("price", 0)
            if isinstance(price, str):
                # Убираем все нечисловые символы
                price = ''.join(filter(str.isdigit, price))
            return float(price) if price else 0.0
        except:
            return 0.0

    def _extract_area(self, prop: Dict[str, Any]) -> float:
        """Извлечь площадь из объекта"""
        try:
            area = prop.get("area", 0)
            if isinstance(area, str):
                # Извлекаем первое число из строки
                import re
                match = re.search(r'(\d+\.?\d*)', area)
                if match:
                    area = match.group(1)
            return float(area) if area else 0.0
        except:
            return 0.0

    def _safe_int(self, value: Any) -> int:
        """Безопасное преобразование в int"""
        try:
            return int(value)
        except:
            return 0

    def _check_metro_time(self, prop: Dict[str, Any], max_time: int) -> bool:
        """Проверка времени до метро"""
        try:
            metro_info = prop.get("location", {}).get("metro", {})
            if isinstance(metro_info, dict):
                time = metro_info.get("time_on_foot", 999)
                return time <= max_time
            return False
        except:
            return False

    def _check_requirement(self, prop: Dict[str, Any], requirement: str) -> bool:
        """
        Проверка выполнения дополнительного требования
        """

        req_lower = requirement.lower()

        # Проверяем различные требования
        if "парк" in req_lower:
            description = str(prop.get("description", "")).lower()
            return "парк" in description or "сквер" in description

        if "ремонт" in req_lower:
            renovation = str(prop.get("renovation", "")).lower()
            return "евро" in renovation or "дизайн" in renovation

        if "балкон" in req_lower:
            description = str(prop.get("description", "")).lower()
            return "балкон" in description or "лоджия" in description

        if "санузел" in req_lower and "раздельн" in req_lower:
            bathroom = str(prop.get("bathroom", "")).lower()
            description = str(prop.get("description", "")).lower()
            return "раздельн" in bathroom or "раздельн" in description

        if "школ" in req_lower:
            description = str(prop.get("description", "")).lower()
            return "школ" in description

        if "сад" in req_lower and "детск" in req_lower:
            description = str(prop.get("description", "")).lower()
            return "детск" in description and "сад" in description

        if "ипотек" in req_lower:
            # Проверяем, что объект подходит под ипотеку
            mortgage_info = prop.get("mortgage", {})
            if isinstance(mortgage_info, dict):
                return mortgage_info.get("available", True)
            return True  # По умолчанию считаем что подходит

        return False

    def clear_user_context(self, user_id: int):
        """Очистить контекст пользователя"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]
            logger.info("user_context_cleared", user_id=user_id)

    def get_user_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить контекст пользователя"""
        return self.user_contexts.get(user_id)
