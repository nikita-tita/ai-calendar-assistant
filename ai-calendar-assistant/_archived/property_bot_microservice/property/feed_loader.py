"""Feed loader service - downloads and processes property feed."""

import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
import structlog
import xml.etree.ElementTree as ET

from app.services.property.feed_mapper import FeedMapper
from app.services.property.property_service import property_service
from app.config import settings

logger = structlog.get_logger()


class FeedLoader:
    """Loads and processes property feed."""

    def __init__(self):
        # Feed URL from settings or default
        self.feed_url = getattr(settings, 'property_feed_url',
                               "https://ecatalog-service.nmarket.pro/BasePro/?login=YOUR_LOGIN&password=YOUR_PASSWORD&regionGroupId=78")
        self.last_update: Optional[datetime] = None
        self.last_count: int = 0
        self.last_error: Optional[str] = None

    async def download_feed(self) -> bytes:
        """Download feed XML."""
        logger.info("downloading_feed", url=self.feed_url[:50] + "...")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.feed_url,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                response.raise_for_status()
                content = await response.read()

        size_mb = len(content) / 1024 / 1024
        logger.info("feed_downloaded", size_mb=f"{size_mb:.1f}")
        return content

    async def process_feed(self, content: bytes) -> Dict:
        """Process feed and update database."""
        logger.info("processing_feed", size_mb=f"{len(content) / 1024 / 1024:.1f}")

        # Parse XML using iterparse for large files and process in batches
        try:
            import io
            logger.info("streaming_parse_xml")

            # Use iterparse to stream large XML directly from bytes
            namespace = '{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}'
            context = ET.iterparse(io.BytesIO(content), events=('end',))

            # Process offers in batches to avoid memory issues
            BATCH_SIZE = 100
            batch = []
            total_offers = 0
            created = 0
            updated = 0
            errors = 0
            parse_errors = 0
            skipped_count = 0

            for event, elem in context:
                # Remove namespace from tag
                tag = elem.tag.replace(namespace, '') if namespace in elem.tag else elem.tag

                if tag == 'offer':
                    total_offers += 1

                    # Remove namespace from all child elements
                    for child in elem.iter():
                        if namespace in child.tag:
                            child.tag = child.tag.replace(namespace, '')

                    # Parse offer immediately
                    try:
                        listing = FeedMapper.parse_offer(elem)
                        if listing:
                            batch.append(listing)
                        else:
                            skipped_count += 1
                    except Exception as e:
                        parse_errors += 1
                        logger.warning("offer_parse_failed",
                                     internal_id=elem.get("internal-id"),
                                     error=str(e))

                    # Clear element to free memory
                    elem.clear()

                    # Process batch when it reaches BATCH_SIZE
                    if len(batch) >= BATCH_SIZE:
                        batch_created, batch_updated, batch_errors = await self._process_batch(batch)
                        created += batch_created
                        updated += batch_updated
                        errors += batch_errors
                        batch = []

                        if total_offers % 1000 == 0:
                            logger.info("parsing_progress",
                                      offers_processed=total_offers,
                                      created=created,
                                      updated=updated,
                                      errors=errors)

            # Process remaining batch
            if batch:
                batch_created, batch_updated, batch_errors = await self._process_batch(batch)
                created += batch_created
                updated += batch_updated
                errors += batch_errors

            logger.info("feed_parsed_and_loaded",
                       total_offers=total_offers,
                       loaded=created + updated,
                       created=created,
                       updated=updated,
                       skipped=skipped_count,
                       parse_errors=parse_errors,
                       errors=errors)

        except Exception as e:
            logger.error("xml_parse_failed", error=str(e), exc_info=True)
            raise

        result = {
            "total": total_offers,
            "created": created,
            "updated": updated,
            "errors": errors,
            "parse_errors": parse_errors
        }

        logger.info("feed_processed", **result)

        self.last_update = datetime.now()
        self.last_count = created + updated

        return result

    async def _process_batch(self, listings: List) -> tuple:
        """Process a batch of listings - upsert to database."""
        created = 0
        updated = 0
        errors = 0

        for listing in listings:
            try:
                # Check if exists by external_id
                existing = await property_service.get_listing_by_external_id(
                    listing.external_id
                )

                if existing:
                    # Update
                    await property_service.update_listing(existing.id, listing)
                    updated += 1
                else:
                    # Create
                    await property_service.create_listing(listing)
                    created += 1

            except Exception as e:
                logger.error("listing_upsert_failed",
                           external_id=listing.external_id,
                           error=str(e))
                errors += 1

        return created, updated, errors

    async def update_feed(self) -> Dict:
        """Download and process feed."""
        start_time = datetime.now()

        try:
            # Download
            content = await self.download_feed()

            # Process
            result = await self.process_feed(content)

            duration = (datetime.now() - start_time).total_seconds()

            final_result = {
                "status": "success",
                **result,
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }

            logger.info("feed_update_success", **final_result)
            self.last_error = None
            return final_result

        except Exception as e:
            error_msg = str(e)
            logger.error("feed_update_failed", error=error_msg)

            self.last_error = error_msg

            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

    def get_status(self) -> Dict:
        """Get feed loader status."""
        return {
            "feed_url": self.feed_url[:50] + "..." if len(self.feed_url) > 50 else self.feed_url,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "last_count": self.last_count,
            "last_error": self.last_error
        }


# Global instance
feed_loader = FeedLoader()
