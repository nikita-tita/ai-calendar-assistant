#!/usr/bin/env python3
"""Test feed download and parsing."""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime

# Feed URL
FEED_URL = "https://ecatalog-service.nmarket.pro/BasePro/?login=titworking_mail_ru&password=q3uCvV5Y6GB&regionGroupId=78"

def test_feed_download():
    """Test downloading and parsing the feed."""

    print("=" * 80)
    print("PROPERTY FEED TEST")
    print("=" * 80)
    print()

    # 1. Download feed
    print("1. Downloading feed...")
    print(f"   URL: {FEED_URL}")

    try:
        response = requests.get(FEED_URL, timeout=30)
        response.raise_for_status()

        content_length = len(response.content)
        print(f"   ✅ Downloaded: {content_length:,} bytes (~{content_length/1024/1024:.1f} MB)")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    # 2. Parse XML
    print("\n2. Parsing XML...")

    try:
        root = ET.fromstring(response.content)

        # Check namespace
        namespace = root.tag.split('}')[0].strip('{') if '}' in root.tag else ""
        if namespace:
            print(f"   Namespace: {namespace}")

        # Get generation date
        gen_date_elem = root.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}generation-date")
        if gen_date_elem is None:
            gen_date_elem = root.find(".//generation-date")

        if gen_date_elem is not None and gen_date_elem.text:
            print(f"   ✅ Feed generation date: {gen_date_elem.text}")

        # Count offers
        offers = root.findall(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}offer")
        if not offers:
            offers = root.findall(".//offer")

        print(f"   ✅ Total offers: {len(offers):,}")

    except Exception as e:
        print(f"   ❌ Parse error: {e}")
        return

    # 3. Analyze first few offers
    print("\n3. Analyzing sample offers...")

    categories = {}
    property_types = {}
    deal_types = {}
    apartments = []

    for offer in offers[:100]:  # First 100
        # Category
        cat_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}category")
        if cat_elem is None:
            cat_elem = offer.find(".//category")
        category = cat_elem.text if cat_elem is not None and cat_elem.text else "unknown"
        categories[category] = categories.get(category, 0) + 1

        # Property type
        prop_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}property-type")
        if prop_elem is None:
            prop_elem = offer.find(".//property-type")
        prop_type = prop_elem.text if prop_elem is not None and prop_elem.text else "unknown"
        property_types[prop_type] = property_types.get(prop_type, 0) + 1

        # Deal type
        type_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}type")
        if type_elem is None:
            type_elem = offer.find(".//type")
        deal_type = type_elem.text if type_elem is not None and type_elem.text else "unknown"
        deal_types[deal_type] = deal_types.get(deal_type, 0) + 1

        # Collect apartments
        if category == "квартира":
            internal_id = offer.get("internal-id")

            # Price
            price_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}price")
            if price_elem is None:
                price_elem = offer.find(".//price")

            price = None
            if price_elem is not None:
                value_elem = price_elem.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}value")
                if value_elem is None:
                    value_elem = price_elem.find(".//value")
                if value_elem is not None and value_elem.text:
                    try:
                        price = int(value_elem.text)
                    except:
                        pass

            # Rooms
            rooms_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}rooms")
            if rooms_elem is None:
                rooms_elem = offer.find(".//rooms")
            rooms = int(rooms_elem.text) if rooms_elem is not None and rooms_elem.text else None

            # Area
            area_elem = offer.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}area")
            if area_elem is None:
                area_elem = offer.find(".//area")

            area = None
            if area_elem is not None:
                value_elem = area_elem.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}value")
                if value_elem is None:
                    value_elem = area_elem.find(".//value")
                if value_elem is not None and value_elem.text:
                    try:
                        area = float(value_elem.text)
                    except:
                        pass

            apartments.append({
                'id': internal_id,
                'rooms': rooms,
                'area': area,
                'price': price
            })

    print("\n   Categories in first 100 offers:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"     - {cat}: {count}")

    print("\n   Property types in first 100 offers:")
    for pt, count in sorted(property_types.items(), key=lambda x: -x[1]):
        print(f"     - {pt}: {count}")

    print("\n   Deal types in first 100 offers:")
    for dt, count in sorted(deal_types.items(), key=lambda x: -x[1]):
        print(f"     - {dt}: {count}")

    # 4. Show sample apartments
    print("\n4. Sample apartments (first 5):")

    for i, apt in enumerate(apartments[:5], 1):
        price_str = f"{apt['price']:,} ₽" if apt['price'] else "N/A"
        rooms_str = f"{apt['rooms']}-комн" if apt['rooms'] else "N/A"
        area_str = f"{apt['area']} м²" if apt['area'] else "N/A"

        print(f"   {i}. ID: {apt['id']}")
        print(f"      {rooms_str}, {area_str}, {price_str}")

    # 5. Statistics
    print("\n5. Full feed statistics:")

    # Count all apartments
    all_apartments = [o for o in offers if (
        (o.find(".//{http://webmaster.yandex.ru/schemas/feed/realty/2010-06}category") or o.find(".//category") or ET.Element("")).text == "квартира"
    )]

    print(f"   Total offers: {len(offers):,}")
    print(f"   Apartments: {len(all_apartments):,} ({len(all_apartments)/len(offers)*100:.1f}%)")
    print(f"   Other: {len(offers) - len(all_apartments):,}")

    # 6. Conclusion
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()

    if len(offers) > 0:
        print("✅ Feed is ACCESSIBLE and PARSEABLE")
        print(f"✅ Contains {len(offers):,} total offers")
        print(f"✅ Contains {len(all_apartments):,} apartments")
        print()
        print("📋 Next steps:")
        print("   1. Update .env with feed URL")
        print("   2. Create cron job for auto-update (every 6 hours)")
        print("   3. Test feed_mapper.py with this feed")
        print("   4. Load data into database")
    else:
        print("⚠️ Feed is accessible but contains no offers")

    print()

if __name__ == "__main__":
    test_feed_download()
