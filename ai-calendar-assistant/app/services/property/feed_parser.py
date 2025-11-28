"""
Парсер Yandex XML фида недвижимости
"""

import xml.etree.ElementTree as ET
import structlog
from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
from datetime import datetime, timedelta

logger = structlog.get_logger()


class YandexFeedParser:
    """Парсер Yandex XML фида"""

    def __init__(self, feed_url: Optional[str] = None):
        self.feed_url = feed_url or "https://example.com/feed.xml"
        self.cached_properties: List[Dict[str, Any]] = []
        self.last_update: Optional[datetime] = None
        self.cache_ttl = timedelta(hours=1)

    async def load_feed(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Загрузить и распарсить фид

        Args:
            force_refresh: Принудительно обновить кэш

        Returns:
            Список объектов недвижимости
        """

        # Проверяем кэш
        if not force_refresh and self.cached_properties and self.last_update:
            if datetime.now() - self.last_update < self.cache_ttl:
                logger.info("feed_from_cache",
                           count=len(self.cached_properties),
                           age_minutes=(datetime.now() - self.last_update).total_seconds() / 60)
                return self.cached_properties

        try:
            logger.info("feed_loading", url=self.feed_url)

            # Загружаем XML
            async with aiohttp.ClientSession() as session:
                async with session.get(self.feed_url, timeout=30) as response:
                    if response.status != 200:
                        logger.error("feed_load_error", status=response.status)
                        return self._get_mock_data()

                    xml_content = await response.text()

            # Парсим XML
            root = ET.fromstring(xml_content)

            properties = []
            for offer in root.findall(".//offer"):
                prop = self._parse_offer(offer)
                if prop:
                    properties.append(prop)

            self.cached_properties = properties
            self.last_update = datetime.now()

            logger.info("feed_loaded",
                       count=len(properties),
                       timestamp=self.last_update.isoformat())

            return properties

        except Exception as e:
            logger.error("feed_parse_error", error=str(e), exc_info=True)
            # Возвращаем моковые данные при ошибке
            return self._get_mock_data()

    def _parse_offer(self, offer: ET.Element) -> Optional[Dict[str, Any]]:
        """Распарсить один объект из фида"""

        try:
            return {
                "id": offer.get("internal-id", ""),
                "type": offer.find("type").text if offer.find("type") is not None else "",
                "property_type": offer.find("property-type").text if offer.find("property-type") is not None else "",
                "category": offer.find("category").text if offer.find("category") is not None else "",
                "url": offer.find("url").text if offer.find("url") is not None else "",
                "price": self._parse_price(offer),
                "area": self._parse_area(offer),
                "rooms": self._parse_rooms(offer),
                "floor": self._parse_floor(offer),
                "floors_total": self._parse_int(offer, "floors-total"),
                "location": self._parse_location(offer),
                "description": offer.find("description").text if offer.find("description") is not None else "",
                "images": self._parse_images(offer),
                "renovation": offer.find("renovation").text if offer.find("renovation") is not None else "",
                "building_type": offer.find("building-type").text if offer.find("building-type") is not None else "",
                "built_year": self._parse_int(offer, "built-year"),
                "ready_quarter": self._parse_int(offer, "ready-quarter"),
                "features": self._parse_features(offer),
            }
        except Exception as e:
            logger.error("offer_parse_error", error=str(e))
            return None

    def _parse_price(self, offer: ET.Element) -> float:
        """Парсинг цены"""
        price_elem = offer.find("price")
        if price_elem is not None:
            value = price_elem.find("value")
            if value is not None:
                try:
                    return float(value.text)
                except:
                    pass
        return 0.0

    def _parse_area(self, offer: ET.Element) -> float:
        """Парсинг площади"""
        area_elem = offer.find("area")
        if area_elem is not None:
            value = area_elem.find("value")
            if value is not None:
                try:
                    return float(value.text)
                except:
                    pass
        return 0.0

    def _parse_rooms(self, offer: ET.Element) -> Optional[int]:
        """Парсинг количества комнат"""
        rooms = offer.find("rooms")
        if rooms is not None and rooms.text:
            if rooms.text == "студия":
                return 0
            try:
                return int(rooms.text)
            except:
                pass
        return None

    def _parse_floor(self, offer: ET.Element) -> Optional[int]:
        """Парсинг этажа"""
        return self._parse_int(offer, "floor")

    def _parse_int(self, offer: ET.Element, tag: str) -> Optional[int]:
        """Парсинг целого числа"""
        elem = offer.find(tag)
        if elem is not None and elem.text:
            try:
                return int(elem.text)
            except:
                pass
        return None

    def _parse_location(self, offer: ET.Element) -> Dict[str, Any]:
        """Парсинг локации"""
        location = {}

        loc_elem = offer.find("location")
        if loc_elem is not None:
            for child in loc_elem:
                location[child.tag] = child.text

            # Парсинг метро
            metro = loc_elem.find("metro")
            if metro is not None:
                location["metro"] = {
                    "name": metro.find("name").text if metro.find("name") is not None else "",
                    "time_on_foot": self._parse_int(metro, "time-on-foot"),
                    "time_on_transport": self._parse_int(metro, "time-on-transport"),
                }

        return location

    def _parse_images(self, offer: ET.Element) -> List[str]:
        """Парсинг изображений"""
        images = []
        for img in offer.findall("image"):
            if img.text:
                images.append(img.text)
        return images

    def _parse_features(self, offer: ET.Element) -> Dict[str, Any]:
        """Парсинг дополнительных характеристик"""
        features = {}

        # Лифт
        lift = offer.find("lift")
        if lift is not None:
            features["lift"] = lift.text == "true"

        # Парковка
        parking = offer.find("parking")
        if parking is not None:
            features["parking"] = parking.text == "true"

        # Балкон/лоджия
        balcony = offer.find("balcony")
        if balcony is not None:
            features["balcony"] = balcony.text

        return features

    def _get_mock_data(self) -> List[Dict[str, Any]]:
        """Получить моковые данные для тестирования"""

        logger.info("using_mock_data")

        return [
            {
                "id": "mock_001",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/1",
                "price": 9500000,
                "area": 42.5,
                "rooms": 1,
                "floor": 12,
                "floors_total": 25,
                "location": {
                    "address": "Москва, район Крылатское, ул. Крылатская, 10",
                    "metro": {
                        "name": "Крылатское",
                        "time_on_foot": 8,
                    }
                },
                "description": "Уютная квартира в новом доме рядом с парком. Есть балкон, раздельный санузел. Подходит под ипотеку Сбербанка.",
                "images": ["https://example.com/img1.jpg"],
                "renovation": "евроремонт",
                "building_type": "монолитный",
                "built_year": 2022,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "есть"
                }
            },
            {
                "id": "mock_002",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/2",
                "price": 10200000,
                "area": 45.0,
                "rooms": 1,
                "floor": 15,
                "floors_total": 20,
                "location": {
                    "address": "Москва, район Строгино, ул. Строгинский бульвар, 5",
                    "metro": {
                        "name": "Строгино",
                        "time_on_foot": 5,
                    }
                },
                "description": "Отличная квартира с видом на парк. Высокий этаж, много света. Раздельный санузел. Ипотека одобрена.",
                "images": ["https://example.com/img2.jpg"],
                "renovation": "дизайнерский ремонт",
                "building_type": "монолитный",
                "built_year": 2023,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "застекленная лоджия"
                }
            },
            {
                "id": "mock_003",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/3",
                "price": 9800000,
                "area": 41.0,
                "rooms": 1,
                "floor": 8,
                "floors_total": 17,
                "location": {
                    "address": "Москва, район Тушино, ул. Свободы, 20",
                    "metro": {
                        "name": "Тушинская",
                        "time_on_foot": 15,
                    }
                },
                "description": "Просторная однушка в тихом районе. Окна во двор. Санузел раздельный.",
                "images": ["https://example.com/img3.jpg"],
                "renovation": "чистовая отделка",
                "building_type": "кирпичный",
                "built_year": 2021,
                "features": {
                    "lift": True,
                    "parking": False,
                    "balcony": "есть"
                }
            },
            {
                "id": "mock_004",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/4",
                "price": 14500000,
                "area": 65.0,
                "rooms": 2,
                "floor": 10,
                "floors_total": 16,
                "location": {
                    "address": "Москва, район Крылатское, Осенний бульвар, 12",
                    "metro": {
                        "name": "Крылатское",
                        "time_on_foot": 10,
                    }
                },
                "description": "Отличная двушка для семьи. Рядом школа и детский сад. Развитая инфраструктура. С ремонтом.",
                "images": ["https://example.com/img4.jpg"],
                "renovation": "евроремонт",
                "building_type": "монолитный",
                "built_year": 2022,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "застекленный балкон"
                }
            },
            {
                "id": "mock_005",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/5",
                "price": 6800000,
                "area": 25.0,
                "rooms": 0,  # студия
                "floor": 5,
                "floors_total": 25,
                "location": {
                    "address": "Москва, район Митино, ул. Митинская, 30",
                    "metro": {
                        "name": "Митино",
                        "time_on_foot": 3,
                    }
                },
                "description": "Студия в новостройке. Отличное инвестиционное предложение. Рядом с метро.",
                "images": ["https://example.com/img5.jpg"],
                "renovation": "без отделки",
                "building_type": "монолитный",
                "built_year": 2024,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "нет"
                }
            },
            {
                "id": "mock_006",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/6",
                "price": 19500000,
                "area": 75.0,
                "rooms": 3,
                "floor": 12,
                "floors_total": 20,
                "location": {
                    "address": "Москва, ЦАО, Пресненская набережная, 6",
                    "metro": {
                        "name": "Выставочная",
                        "time_on_foot": 7,
                    }
                },
                "description": "Трехкомнатная квартира для большой семьи. Рядом школа и детские сады. Два санузла. Кухня 15 кв.м. Не первый и не последний этаж.",
                "images": ["https://example.com/img6.jpg"],
                "renovation": "евроремонт",
                "building_type": "монолитный",
                "built_year": 2020,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "две лоджии"
                }
            },
            {
                "id": "mock_007",
                "type": "продажа",
                "property_type": "квартира",
                "category": "квартира",
                "url": "https://example.com/7",
                "price": 24000000,
                "area": 90.0,
                "rooms": 2,
                "floor": 18,
                "floors_total": 25,
                "location": {
                    "address": "Москва, район Хорошево-Мневники, наб. Живописная, 1",
                    "metro": {
                        "name": "Живописная",
                        "time_on_foot": 5,
                    }
                },
                "description": "Элитная квартира с панорамными окнами и видом на Москву-реку. Консьерж, охрана. Элитный ЖК.",
                "images": ["https://example.com/img7.jpg"],
                "renovation": "дизайнерский ремонт",
                "building_type": "монолитный",
                "built_year": 2023,
                "features": {
                    "lift": True,
                    "parking": True,
                    "balcony": "панорамное остекление"
                }
            },
        ]

    async def get_cached_properties(self) -> List[Dict[str, Any]]:
        """Получить закэшированные объекты или загрузить новые"""

        if not self.cached_properties:
            return await self.load_feed()

        return self.cached_properties
