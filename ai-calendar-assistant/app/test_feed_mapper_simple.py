#!/usr/bin/env python3
"""Simple test script for feed_mapper without pytest dependency."""

import sys
import xml.etree.ElementTree as ET

# Mock structlog if not installed
try:
    import structlog
except ImportError:
    class MockLogger:
        def info(self, *args, **kwargs): pass
        def error(self, *args, **kwargs): pass
        def warning(self, *args, **kwargs): pass
        def debug(self, *args, **kwargs): pass

    class MockStructlog:
        @staticmethod
        def get_logger(): return MockLogger()

    sys.modules['structlog'] = MockStructlog()

from app.services.property.feed_mapper import FeedMapper

# Sample XML
SAMPLE_XML = """
<offer internal-id="196921">
    <type>продажа</type>
    <property-type>жилая</property-type>
    <category>квартира</category>
    <mortgage>true</mortgage>
    <haggle>false</haggle>
    <renovation>Без отделки</renovation>
    <rooms>2</rooms>
    <balcony>терраса</balcony>
    <bathroom-unit>2 раздельный</bathroom-unit>
    <floor>5</floor>
    <floors-total>18</floors-total>
    <building-name>Привилегия</building-name>
    <building-type>кирпично-монолитный</building-type>
    <built-year>2017</built-year>
    <ready-quarter>1</ready-quarter>
    <lift>1</lift>
    <parking>1</parking>
    <ceiling-height>2.9</ceiling-height>

    <payment-methods>
        <payment-method>Ипотека</payment-method>
        <payment-method>Рассрочка</payment-method>
    </payment-methods>

    <approved-banks>
        <bank>Сбербанк</bank>
        <bank>ВТБ</bank>
    </approved-banks>

    <location>
        <address>Вязовая ул., д. 8/А</address>
        <latitude>59.9669863398</latitude>
        <longitude>30.2763240491</longitude>
        <sub-locality-name>Петроградский</sub-locality-name>
        <metro>
            <name>Крестовский остров</name>
            <time-on-foot>15</time-on-foot>
        </metro>
    </location>

    <price>
        <value>9200000</value>
    </price>

    <area>
        <value>65.0</value>
    </area>

    <living-space>
        <value>40.5</value>
    </living-space>

    <kitchen-space>
        <value>12.3</value>
    </kitchen-space>

    <image tag="plan">http://img.nmarket.pro/plan1.jpg</image>
    <image tag="housemain">http://img.nmarket.pro/main1.jpg</image>
    <image tag="floorplan">http://img.nmarket.pro/floor1.jpg</image>

    <developer-name>ГК ПИК</developer-name>
</offer>
"""

GARAGE_XML = """
<offer internal-id="999999">
    <type>продажа</type>
    <category>гараж</category>
    <price><value>1500000</value></price>
</offer>
"""


def test_safe_getters():
    """Test safe getter methods."""
    print("🧪 Testing safe getters...")

    xml = "<root><text>hello</text><number>42</number><bool>true</bool></root>"
    root = ET.fromstring(xml)

    # Test safe_get_text
    assert FeedMapper.safe_get_text(root, "text") == "hello", "safe_get_text failed"
    assert FeedMapper.safe_get_text(root, "missing") is None, "safe_get_text should return None"

    # Test safe_get_int
    assert FeedMapper.safe_get_int(root, "number") == 42, "safe_get_int failed"
    assert FeedMapper.safe_get_int(root, "missing") is None, "safe_get_int should return None"

    # Test safe_get_bool
    assert FeedMapper.safe_get_bool(root, "bool") is True, "safe_get_bool failed"
    assert FeedMapper.safe_get_bool(root, "missing") is None, "safe_get_bool should return None"

    print("✅ Safe getters work correctly")


def test_parse_apartment():
    """Test parsing apartment offer."""
    print("\n🧪 Testing apartment parsing...")

    offer_elem = ET.fromstring(SAMPLE_XML)
    listing = FeedMapper.parse_offer(offer_elem)

    assert listing is not None, "Listing should not be None"
    assert listing.external_id == "196921", f"Expected external_id '196921', got '{listing.external_id}'"
    assert listing.category == "квартира", f"Expected category 'квартира', got '{listing.category}'"
    assert listing.price == 9200000, f"Expected price 9200000, got {listing.price}"
    assert listing.rooms == 2, f"Expected 2 rooms, got {listing.rooms}"
    assert listing.building_name == "Привилегия", f"Expected building_name 'Привилегия', got '{listing.building_name}'"
    assert listing.building_type == "кирпично-монолитный", f"Expected building_type 'кирпично-монолитный'"
    assert listing.renovation == "Без отделки", f"Expected renovation 'Без отделки'"
    assert listing.has_elevator is True, "Expected has_elevator=True"
    assert listing.has_parking is True, "Expected has_parking=True"
    assert listing.ceiling_height == 2.9, f"Expected ceiling_height 2.9"
    assert listing.mortgage_available is True, "Expected mortgage_available=True"
    assert "Ипотека" in listing.payment_methods, "Expected 'Ипотека' in payment_methods"
    assert "Сбербанк" in listing.approved_banks, "Expected 'Сбербанк' in approved_banks"
    assert listing.area_total == 65.0, f"Expected area_total 65.0"
    assert listing.living_area == 40.5, f"Expected living_area 40.5"
    assert listing.kitchen_area == 12.3, f"Expected kitchen_area 12.3"
    assert listing.balcony_type == "терраса", "Expected balcony_type 'терраса'"
    assert listing.bathroom_type == "раздельный", "Expected bathroom_type 'раздельный'"
    assert len(listing.plan_images) == 1, "Expected 1 plan image"
    assert len(listing.photos) == 1, "Expected 1 photo (housemain)"
    assert len(listing.floor_plan_images) == 1, "Expected 1 floor plan image"
    assert listing.developer_name == "ГК ПИК", "Expected developer_name 'ГК ПИК'"

    print("✅ Apartment parsing works correctly")
    print(f"   - External ID: {listing.external_id}")
    print(f"   - Title: {listing.title}")
    print(f"   - Price: {listing.price:,} руб")
    print(f"   - Building: {listing.building_name}")
    print(f"   - Rooms: {listing.rooms}")
    print(f"   - Area: {listing.area_total} м²")
    print(f"   - Renovation: {listing.renovation}")
    print(f"   - Payment methods: {', '.join(listing.payment_methods)}")


def test_parse_non_apartment():
    """Test that non-apartments are filtered out."""
    print("\n🧪 Testing non-apartment filtering...")

    offer_elem = ET.fromstring(GARAGE_XML)
    listing = FeedMapper.parse_offer(offer_elem)

    assert listing is None, "Garage should be filtered out (return None)"

    print("✅ Non-apartment filtering works correctly")


def test_parse_full_feed():
    """Test parsing full feed with multiple offers."""
    print("\n🧪 Testing full feed parsing...")

    full_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<realty-feed>
    {SAMPLE_XML}
    {GARAGE_XML}
    <offer internal-id="test2">
        <category>квартира</category>
        <rooms>1</rooms>
        <price><value>5000000</value></price>
        <area><value>35.0</value></area>
    </offer>
</realty-feed>
"""

    listings = FeedMapper.parse_feed_xml(full_xml)

    assert len(listings) == 2, f"Expected 2 apartments (garage filtered), got {len(listings)}"
    assert listings[0].external_id == "196921", "First listing should be 196921"
    assert listings[1].external_id == "test2", "Second listing should be test2"

    print("✅ Full feed parsing works correctly")
    print(f"   - Total offers in feed: 3")
    print(f"   - Apartments parsed: {len(listings)}")
    print(f"   - Filtered out: 1 (garage)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Testing Feed Mapper")
    print("=" * 60)

    try:
        test_safe_getters()
        test_parse_apartment()
        test_parse_non_apartment()
        test_parse_full_feed()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
