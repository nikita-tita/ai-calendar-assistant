"""Feed mapper service - converts XML feed to PropertyListing models."""

import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any
from datetime import datetime
import structlog

from app.schemas.property import PropertyListingCreate, DealType

logger = structlog.get_logger()


class FeedMapper:
    """Maps XML feed (База.Про format) to PropertyListing schema."""

    @staticmethod
    def safe_get_text(element: Optional[ET.Element], tag: str, default: Any = None) -> Any:
        """Safely extract text from XML element."""
        if element is None:
            return default
        child = element.find(tag)
        if child is None or child.text is None:
            return default
        return child.text.strip()

    @staticmethod
    def safe_get_int(element: Optional[ET.Element], tag: str, default: Optional[int] = None) -> Optional[int]:
        """Safely extract integer from XML element."""
        text = FeedMapper.safe_get_text(element, tag)
        if text is None:
            return default
        try:
            return int(text)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_get_float(element: Optional[ET.Element], tag: str, default: Optional[float] = None) -> Optional[float]:
        """Safely extract float from XML element."""
        text = FeedMapper.safe_get_text(element, tag)
        if text is None:
            return default
        try:
            return float(text)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_get_bool(element: Optional[ET.Element], tag: str, default: Optional[bool] = None) -> Optional[bool]:
        """Safely extract boolean from XML element."""
        text = FeedMapper.safe_get_text(element, tag)
        if text is None:
            return default
        return text.lower() in ["true", "1", "да", "yes"]

    @staticmethod
    def parse_offer(offer: ET.Element) -> Optional[PropertyListingCreate]:
        """
        Parse single <offer> element from XML feed.

        Args:
            offer: XML <offer> element

        Returns:
            PropertyListingCreate instance or None if invalid
        """
        try:
            # Extract internal-id (required)
            internal_id = offer.get("internal-id")
            if not internal_id:
                logger.warning("offer_missing_internal_id", offer=ET.tostring(offer, encoding="unicode")[:200])
                return None

            # Category - get but don't filter for now (debug)
            category = FeedMapper.safe_get_text(offer, "category")
            # Temporarily accept all categories to debug
            # if category != "квартира":
            #     logger.info("offer_skipped_not_apartment", internal_id=internal_id, category=category)
            #     return None

            # Basic info
            offer_type = FeedMapper.safe_get_text(offer, "type", "продажа")
            deal_type = DealType.rent if "аренд" in offer_type.lower() else DealType.buy

            property_type = FeedMapper.safe_get_text(offer, "property-type", "жилая")

            # Title and description
            building_name = FeedMapper.safe_get_text(offer, "building-name")
            rooms = FeedMapper.safe_get_int(offer, "rooms")
            area = FeedMapper.safe_get_float(offer, "area/value")

            # Generate title
            title = building_name or f"{rooms}-комн. квартира, {area} м²"
            description = FeedMapper.safe_get_text(offer, "description")

            # Price
            price = FeedMapper.safe_get_int(offer, "price/value", 0)
            if price <= 0:
                logger.warning("offer_invalid_price", internal_id=internal_id, price=price)
                return None

            # Location
            location = offer.find("location")
            address_raw = FeedMapper.safe_get_text(location, "address")
            district = FeedMapper.safe_get_text(location, "sub-locality-name")
            lat = FeedMapper.safe_get_float(location, "latitude")
            lon = FeedMapper.safe_get_float(location, "longitude")

            # Metro
            metro = location.find("metro") if location else None
            metro_station = FeedMapper.safe_get_text(metro, "name")
            metro_distance_minutes = FeedMapper.safe_get_int(metro, "time-on-foot")
            if metro_distance_minutes is None:
                metro_distance_minutes = FeedMapper.safe_get_int(metro, "time-on-transport")

            # Building info
            building_type = FeedMapper.safe_get_text(offer, "building-type")
            building_state = FeedMapper.safe_get_text(offer, "building-state")
            building_phase = FeedMapper.safe_get_text(offer, "building-phase")
            building_section = FeedMapper.safe_get_text(offer, "building-section")
            building_year = FeedMapper.safe_get_int(offer, "built-year")
            ready_quarter = FeedMapper.safe_get_int(offer, "ready-quarter")

            # Floors
            floor = FeedMapper.safe_get_int(offer, "floor")
            floors_total = FeedMapper.safe_get_int(offer, "floors-total")

            # Areas
            area_total = FeedMapper.safe_get_float(offer, "area/value")
            living_area = FeedMapper.safe_get_float(offer, "living-space/value")
            kitchen_area = FeedMapper.safe_get_float(offer, "kitchen-space/value")

            # Rooms & Layout
            balcony_type = FeedMapper.safe_get_text(offer, "balcony")
            bathroom_count = FeedMapper.safe_get_int(offer, "bathroom-unit")
            bathroom_type = None
            if bathroom_count:
                bathroom_text = FeedMapper.safe_get_text(offer, "bathroom-unit", "")
                if "раздельн" in bathroom_text.lower():
                    bathroom_type = "раздельный"
                elif "совмещ" in bathroom_text.lower():
                    bathroom_type = "совмещенный"

            # Condition & Amenities
            renovation = FeedMapper.safe_get_text(offer, "renovation")
            ceiling_height = FeedMapper.safe_get_float(offer, "ceiling-height")
            has_elevator = FeedMapper.safe_get_bool(offer, "lift")
            has_parking = FeedMapper.safe_get_bool(offer, "parking")

            # Financial
            mortgage_available = FeedMapper.safe_get_bool(offer, "mortgage")
            haggle_allowed = FeedMapper.safe_get_bool(offer, "haggle")

            # Payment methods
            payment_methods = []
            payment_methods_elem = offer.find("payment-methods")
            if payment_methods_elem is not None:
                for pm in payment_methods_elem.findall("payment-method"):
                    if pm.text:
                        payment_methods.append(pm.text.strip())

            # Approved banks
            approved_banks = []
            approved_banks_elem = offer.find("approved-banks")
            if approved_banks_elem is not None:
                for bank in approved_banks_elem.findall("bank"):
                    if bank.text:
                        approved_banks.append(bank.text.strip())

            # Developer
            developer_id = FeedMapper.safe_get_text(offer, "nmarket-building-id")
            developer_name = FeedMapper.safe_get_text(offer, "developer-name")

            # Images (categorized)
            photos = []
            plan_images = []
            floor_plan_images = []
            complex_scheme_images = []

            for img in offer.findall("image"):
                url = img.text.strip() if img.text else None
                if not url:
                    continue

                tag = img.get("tag", "")
                if tag == "plan":
                    plan_images.append(url)
                elif tag == "floorplan":
                    floor_plan_images.append(url)
                elif tag == "complexscheme":
                    complex_scheme_images.append(url)
                elif tag == "housemain":
                    photos.append(url)
                elif not tag:  # No tag = general photo
                    photos.append(url)

            # Complex info
            complex_advantages = []
            advantages_elem = offer.find("advantages")
            if advantages_elem is not None:
                for adv in advantages_elem.findall("advantage"):
                    if adv.text:
                        complex_advantages.append(adv.text.strip())

            complex_description = FeedMapper.safe_get_text(offer, "complex-description")

            # Developer documents
            developer_documents = []
            docs_elem = offer.find("developer-documents")
            if docs_elem is not None:
                for doc in docs_elem.findall("document"):
                    if doc.text:
                        developer_documents.append(doc.text.strip())

            # Agent/Sales Info
            sales_agent_elem = offer.find("sales-agent")
            agent_data = None
            if sales_agent_elem is not None:
                agent_data = {
                    "phone": FeedMapper.safe_get_text(sales_agent_elem, "phone"),
                    "email": FeedMapper.safe_get_text(sales_agent_elem, "email"),
                    "organization": FeedMapper.safe_get_text(sales_agent_elem, "organization"),
                    "category": FeedMapper.safe_get_text(sales_agent_elem, "category"),
                }

            # Feed metadata
            creation_date = FeedMapper.safe_get_text(offer, "creation-date")
            last_update_date = FeedMapper.safe_get_text(offer, "last-update-date")

            # Create PropertyListingCreate instance
            listing = PropertyListingCreate(
                title=title,
                description=description,
                price=price,
                deal_type=deal_type,

                # Category & Type
                category=category,
                property_type=property_type,

                # Location
                address_raw=address_raw,
                lat=lat,
                lon=lon,
                district=district,
                metro_station=metro_station,
                metro_distance_minutes=metro_distance_minutes,

                # Building Info
                building_name=building_name,
                building_type=building_type,
                building_state=building_state,
                building_phase=building_phase,
                building_section=building_section,
                building_year=building_year,
                ready_quarter=ready_quarter,

                # Floors
                floor=floor,
                floors_total=floors_total,

                # Areas
                area_total=area_total,
                living_area=living_area,
                kitchen_area=kitchen_area,

                # Rooms & Layout
                rooms=rooms,
                balcony_type=balcony_type,
                bathroom_count=bathroom_count,
                bathroom_type=bathroom_type,

                # Condition & Amenities
                renovation=renovation,
                ceiling_height=ceiling_height,
                has_elevator=has_elevator,
                has_parking=has_parking,

                # Financial
                mortgage_available=mortgage_available,
                haggle_allowed=haggle_allowed,
                payment_methods=payment_methods if payment_methods else None,
                approved_banks=approved_banks if approved_banks else None,

                # Developer
                developer_id=developer_id,
                developer_name=developer_name,
                builder_data={"documents": developer_documents} if developer_documents else None,

                # Images (categorized)
                photos=photos if photos else None,
                plan_images=plan_images if plan_images else None,
                floor_plan_images=floor_plan_images if floor_plan_images else None,
                complex_scheme_images=complex_scheme_images if complex_scheme_images else None,

                # Complex Info
                complex_advantages=complex_advantages if complex_advantages else None,
                complex_description=complex_description,

                # Agent/Sales Info
                agent_data=agent_data,

                # Feed Metadata
                source="nmarket.pro",
                external_id=internal_id,
                is_new_flat=FeedMapper.safe_get_bool(offer, "new-flat", True),
            )

            logger.info("offer_parsed_successfully",
                       internal_id=internal_id,
                       title=title,
                       price=price,
                       district=district)

            return listing

        except Exception as e:
            logger.error("offer_parse_error",
                        error=str(e),
                        internal_id=offer.get("internal-id"),
                        exc_info=True)
            return None

    @staticmethod
    def parse_feed_xml(xml_content: str) -> List[PropertyListingCreate]:
        """
        Parse full XML feed content.

        Args:
            xml_content: Raw XML string

        Returns:
            List of PropertyListingCreate instances
        """
        listings = []

        try:
            root = ET.fromstring(xml_content)

            # Find all <offer> elements
            for offer in root.findall(".//offer"):
                listing = FeedMapper.parse_offer(offer)
                if listing:
                    listings.append(listing)

            logger.info("feed_parsed_successfully",
                       total_offers=len(root.findall(".//offer")),
                       valid_listings=len(listings))

        except ET.ParseError as e:
            logger.error("feed_xml_parse_error", error=str(e))
        except Exception as e:
            logger.error("feed_parse_error", error=str(e), exc_info=True)

        return listings


# Global instance
feed_mapper = FeedMapper()
