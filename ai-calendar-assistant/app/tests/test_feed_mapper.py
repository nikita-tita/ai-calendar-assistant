"""Tests for property feed mapper."""

import pytest
from app.services.property.feed_mapper import FeedMapper, feed_mapper


# Sample XML data based on База.Про format
SAMPLE_OFFER_XML = """
<offer internal-id="196921">
    <type>продажа</type>
    <property-type>жилая</property-type>
    <category>квартира</category>
    <creation-date>2014-05-21T05:40:36+00:00</creation-date>
    <last-update-date>2021-07-01T06:52:30+00:00</last-update-date>
    <manually-added>0</manually-added>
    <mortgage>true</mortgage>
    <haggle>false</haggle>
    <renovation>Без отделки</renovation>
    <description>Уютная квартира в новом доме</description>
    <new-flat>1</new-flat>
    <rooms>2</rooms>
    <balcony>терраса</balcony>
    <bathroom-unit>2 раздельный</bathroom-unit>
    <floor>5</floor>
    <floors-total>18</floors-total>
    <building-name>Привилегия</building-name>
    <building-type>кирпично-монолитный</building-type>
    <building-state>hand-over</building-state>
    <building-phase>Очередь 1</building-phase>
    <building-section>Корпус А</building-section>
    <built-year>2017</built-year>
    <ready-quarter>1</ready-quarter>
    <lift>1</lift>
    <parking>1</parking>
    <ceiling-height>2.9</ceiling-height>
    <nmarket-complex-id>769</nmarket-complex-id>
    <nmarket-building-id>1007</nmarket-building-id>

    <payment-methods>
        <payment-method>Ипотека</payment-method>
        <payment-method>Материнский капитал</payment-method>
        <payment-method>Рассрочка</payment-method>
    </payment-methods>

    <advantages>
        <advantage>Благоустроенная территория</advantage>
        <advantage>Подземный паркинг</advantage>
        <advantage>Детский сад на территории комплекса</advantage>
    </advantages>

    <complex-description>Современный жилой комплекс премиум-класса</complex-description>

    <approved-banks>
        <bank>Газпромбанк</bank>
        <bank>ВТБ</bank>
        <bank>Сбербанк</bank>
    </approved-banks>

    <developer-documents>
        <document>https://nmarket.pro/blob/id/doc1</document>
        <document>https://nmarket.pro/blob/id/doc2</document>
    </developer-documents>

    <location>
        <country>Россия</country>
        <region>Санкт-Петербург</region>
        <locality-name>Санкт-Петербург</locality-name>
        <sub-locality-name>Петроградский</sub-locality-name>
        <non-admin-sub-locality>Петроградский</non-admin-sub-locality>
        <address>Вязовая ул., д. 8/А</address>
        <apartment>218</apartment>
        <latitude>59.9669863398</latitude>
        <longitude>30.2763240491</longitude>
        <metro>
            <name>Крестовский остров</name>
            <time-on-foot>15</time-on-foot>
        </metro>
    </location>

    <price>
        <value>9200000</value>
        <currency>RUR</currency>
    </price>

    <area>
        <value>65.0</value>
        <unit>кв. м</unit>
    </area>

    <living-space>
        <value>40.5</value>
        <unit>кв. м</unit>
    </living-space>

    <kitchen-space>
        <value>12.3</value>
        <unit>кв. м</unit>
    </kitchen-space>

    <image tag="plan">http://img.nmarket.pro/photo/plan1.jpg</image>
    <image tag="housemain">http://img.nmarket.pro/photo/main1.jpg</image>
    <image tag="housemain">http://img.nmarket.pro/photo/main2.jpg</image>
    <image tag="floorplan">http://img.nmarket.pro/photo/floor1.jpg</image>
    <image>http://img.nmarket.pro/photo/other1.jpg</image>

    <sales-agent>
        <phone>+78123132538</phone>
        <organization>Test Agency</organization>
        <email>test@example.com</email>
        <category>agency</category>
    </sales-agent>

    <developer-name>ГК ПИК</developer-name>
</offer>
"""

SAMPLE_NON_APARTMENT_XML = """
<offer internal-id="999999">
    <type>продажа</type>
    <category>гараж</category>
    <garage-type>машиноместо</garage-type>
    <price><value>1500000</value></price>
    <area><value>15.0</value></area>
</offer>
"""

FULL_FEED_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<realty-feed>
    {SAMPLE_OFFER_XML}
    {SAMPLE_NON_APARTMENT_XML}
    <offer internal-id="196922">
        <type>продажа</type>
        <category>квартира</category>
        <rooms>1</rooms>
        <price><value>5000000</value></price>
        <area><value>35.0</value></area>
        <location>
            <address>Тестовая ул., д. 1</address>
        </location>
    </offer>
</realty-feed>
"""


class TestFeedMapper:
    """Tests for FeedMapper class."""

    def test_safe_get_text(self):
        """Test safe text extraction."""
        import xml.etree.ElementTree as ET

        xml = "<root><child>test</child></root>"
        root = ET.fromstring(xml)

        # Existing element
        assert FeedMapper.safe_get_text(root, "child") == "test"

        # Non-existing element
        assert FeedMapper.safe_get_text(root, "missing") is None
        assert FeedMapper.safe_get_text(root, "missing", "default") == "default"

    def test_safe_get_int(self):
        """Test safe integer extraction."""
        import xml.etree.ElementTree as ET

        xml = "<root><number>42</number><text>not a number</text></root>"
        root = ET.fromstring(xml)

        # Valid integer
        assert FeedMapper.safe_get_int(root, "number") == 42

        # Invalid integer
        assert FeedMapper.safe_get_int(root, "text") is None

        # Missing element
        assert FeedMapper.safe_get_int(root, "missing", 0) == 0

    def test_safe_get_float(self):
        """Test safe float extraction."""
        import xml.etree.ElementTree as ET

        xml = "<root><number>3.14</number></root>"
        root = ET.fromstring(xml)

        assert FeedMapper.safe_get_float(root, "number") == 3.14
        assert FeedMapper.safe_get_float(root, "missing") is None

    def test_safe_get_bool(self):
        """Test safe boolean extraction."""
        import xml.etree.ElementTree as ET

        xml = """<root>
            <true1>true</true1>
            <true2>1</true2>
            <false1>false</false1>
            <false2>0</false2>
        </root>"""
        root = ET.fromstring(xml)

        assert FeedMapper.safe_get_bool(root, "true1") is True
        assert FeedMapper.safe_get_bool(root, "true2") is True
        assert FeedMapper.safe_get_bool(root, "false1") is False
        assert FeedMapper.safe_get_bool(root, "false2") is False
        assert FeedMapper.safe_get_bool(root, "missing") is None

    def test_parse_offer_apartment(self):
        """Test parsing apartment offer."""
        import xml.etree.ElementTree as ET

        offer_elem = ET.fromstring(SAMPLE_OFFER_XML)
        listing = FeedMapper.parse_offer(offer_elem)

        assert listing is not None

        # Basic info
        assert listing.external_id == "196921"
        assert listing.category == "квартира"
        assert listing.property_type == "жилая"
        assert listing.deal_type.value == "buy"
        assert listing.price == 9200000

        # Building info
        assert listing.building_name == "Привилегия"
        assert listing.building_type == "кирпично-монолитный"
        assert listing.building_state == "hand-over"
        assert listing.building_phase == "Очередь 1"
        assert listing.building_section == "Корпус А"
        assert listing.building_year == 2017
        assert listing.ready_quarter == 1

        # Floors and areas
        assert listing.floor == 5
        assert listing.floors_total == 18
        assert listing.area_total == 65.0
        assert listing.living_area == 40.5
        assert listing.kitchen_area == 12.3

        # Rooms and layout
        assert listing.rooms == 2
        assert listing.balcony_type == "терраса"
        assert listing.bathroom_count == 2
        assert listing.bathroom_type == "раздельный"

        # Condition and amenities
        assert listing.renovation == "Без отделки"
        assert listing.ceiling_height == 2.9
        assert listing.has_elevator is True
        assert listing.has_parking is True

        # Financial
        assert listing.mortgage_available is True
        assert listing.haggle_allowed is False
        assert "Ипотека" in listing.payment_methods
        assert "Рассрочка" in listing.payment_methods
        assert "Материнский капитал" in listing.payment_methods
        assert "Сбербанк" in listing.approved_banks
        assert "ВТБ" in listing.approved_banks

        # Developer
        assert listing.developer_id == "1007"
        assert listing.developer_name == "ГК ПИК"

        # Images
        assert len(listing.plan_images) == 1
        assert "plan1.jpg" in listing.plan_images[0]
        assert len(listing.photos) == 3  # 2 housemain + 1 untagged
        assert len(listing.floor_plan_images) == 1

        # Complex info
        assert len(listing.complex_advantages) == 3
        assert "Подземный паркинг" in listing.complex_advantages
        assert listing.complex_description is not None

        # Location
        assert listing.district == "Петроградский"
        assert listing.address_raw == "Вязовая ул., д. 8/А"
        assert listing.lat == 59.9669863398
        assert listing.lon == 30.2763240491
        assert listing.metro_station == "Крестовский остров"
        assert listing.metro_distance_minutes == 15

        # Agent
        assert listing.agent_data is not None
        assert listing.agent_data["phone"] == "+78123132538"
        assert listing.agent_data["email"] == "test@example.com"

        # Source
        assert listing.source == "nmarket.pro"
        assert listing.is_new_flat is True

    def test_parse_offer_non_apartment(self):
        """Test that non-apartment offers are filtered out."""
        import xml.etree.ElementTree as ET

        offer_elem = ET.fromstring(SAMPLE_NON_APARTMENT_XML)
        listing = FeedMapper.parse_offer(offer_elem)

        # Should return None for non-apartments
        assert listing is None

    def test_parse_offer_missing_internal_id(self):
        """Test parsing offer without internal-id."""
        import xml.etree.ElementTree as ET

        xml = """<offer>
            <category>квартира</category>
            <price><value>5000000</value></price>
        </offer>"""

        offer_elem = ET.fromstring(xml)
        listing = FeedMapper.parse_offer(offer_elem)

        # Should return None without internal-id
        assert listing is None

    def test_parse_offer_invalid_price(self):
        """Test parsing offer with invalid price."""
        import xml.etree.ElementTree as ET

        xml = """<offer internal-id="123">
            <category>квартира</category>
            <price><value>0</value></price>
        </offer>"""

        offer_elem = ET.fromstring(xml)
        listing = FeedMapper.parse_offer(offer_elem)

        # Should return None for invalid price
        assert listing is None

    def test_parse_feed_xml(self):
        """Test parsing full feed XML."""
        listings = FeedMapper.parse_feed_xml(FULL_FEED_XML)

        # Should parse 2 apartments (excluding garage)
        assert len(listings) == 2

        # Check first listing
        assert listings[0].external_id == "196921"
        assert listings[0].building_name == "Привилегия"

        # Check second listing
        assert listings[1].external_id == "196922"
        assert listings[1].rooms == 1

    def test_parse_feed_xml_empty(self):
        """Test parsing empty feed."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <realty-feed></realty-feed>"""

        listings = FeedMapper.parse_feed_xml(xml)
        assert len(listings) == 0

    def test_parse_feed_xml_invalid(self):
        """Test parsing invalid XML."""
        listings = FeedMapper.parse_feed_xml("not valid xml")
        assert len(listings) == 0

    def test_bathroom_type_extraction(self):
        """Test bathroom type extraction from text."""
        import xml.etree.ElementTree as ET

        # Separated bathroom
        xml1 = """<offer internal-id="1">
            <category>квартира</category>
            <bathroom-unit>2 раздельный</bathroom-unit>
            <price><value>5000000</value></price>
        </offer>"""
        listing1 = FeedMapper.parse_offer(ET.fromstring(xml1))
        assert listing1.bathroom_type == "раздельный"

        # Combined bathroom
        xml2 = """<offer internal-id="2">
            <category>квартира</category>
            <bathroom-unit>1 совмещенный</bathroom-unit>
            <price><value>5000000</value></price>
        </offer>"""
        listing2 = FeedMapper.parse_offer(ET.fromstring(xml2))
        assert listing2.bathroom_type == "совмещенный"

    def test_title_generation(self):
        """Test automatic title generation."""
        import xml.etree.ElementTree as ET

        # With building name
        xml1 = """<offer internal-id="1">
            <category>квартира</category>
            <building-name>Test Complex</building-name>
            <price><value>5000000</value></price>
        </offer>"""
        listing1 = FeedMapper.parse_offer(ET.fromstring(xml1))
        assert listing1.title == "Test Complex"

        # Without building name - should generate from rooms and area
        xml2 = """<offer internal-id="2">
            <category>квартира</category>
            <rooms>2</rooms>
            <area><value>60.0</value></area>
            <price><value>5000000</value></price>
        </offer>"""
        listing2 = FeedMapper.parse_offer(ET.fromstring(xml2))
        assert "2-комн" in listing2.title
        assert "60.0" in listing2.title


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
