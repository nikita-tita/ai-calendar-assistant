"""
Обертка для FeedLoader с поддержкой тестирования
"""

import structlog
from typing import List, Dict, Any

from app.services.property.feed_loader import feed_loader
from app.services.property.feed_parser import YandexFeedParser

logger = structlog.get_logger()


class PropertyFeedLoader:
    """Загрузчик фида с поддержкой моковых данных для тестирования"""

    def __init__(self):
        self.feed_loader = feed_loader
        self.parser = YandexFeedParser()

    async def get_cached_properties(self) -> List[Dict[str, Any]]:
        """Получить объекты (моковые для тестирования или реальные)"""

        # Для тестирования используем моковые данные
        logger.info("getting_properties_for_testing")
        return await self.parser.get_cached_properties()

    async def load_feed(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Загрузить фид"""
        return await self.parser.load_feed(force_refresh)
