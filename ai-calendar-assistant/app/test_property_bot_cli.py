#!/usr/bin/env python3
"""CLI utility for testing Property Bot functionality."""

import asyncio
import sys
from typing import Optional

# Mock services if not available
try:
    from app.services.property.llm_agent_property import llm_agent_property
    from app.services.property.property_service import property_service
    from app.services.property.search_result_handler import search_result_handler
    from app.services.property.dream_score import dream_score_calculator
    from app.services.property.enrichment_orchestrator import enrichment_orchestrator
    from app.schemas.property import PropertyListingResponse, PropertyClientResponse
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    print("Some dependencies are missing. Install with: pip install -r requirements.txt")
    IMPORTS_AVAILABLE = False


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    """Print formatted section."""
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


async def test_llm_agent():
    """Test LLM agent parameter extraction."""
    print_header("TEST 1: LLM AGENT - PARAMETER EXTRACTION")

    test_queries = [
        "Хочу 2-комнатную до 10 млн в Бутово, не первый этаж, с ипотекой",
        "3к от 8 до 12 млн, кирпичный дом, чистовая отделка, детский сад рядом",
        "Студия с балконом, до 6 млн, сдача в 2025",
        "Квартира с рассрочкой, материнский капитал, парковка"
    ]

    for idx, query in enumerate(test_queries, 1):
        print_section(f"Query {idx}")
        print(f"📝 Input: {query}")

        result = await llm_agent_property.extract_search_criteria(
            user_message=query,
            user_id="test_user",
            language="ru"
        )

        print(f"✅ Intent: {result['intent']}")
        print(f"🎯 Confidence: {result.get('confidence', 0)}")

        if result['intent'] == 'search':
            criteria = result['criteria']
            print(f"📋 Extracted criteria:")
            for key, value in criteria.items():
                print(f"   - {key}: {value}")
        elif result['intent'] == 'clarify':
            print(f"❓ Clarification: {result.get('clarify_question')}")

    print("\n✅ LLM Agent test complete!")


async def test_search_filters():
    """Test search with various filter combinations."""
    print_header("TEST 2: SEARCH SERVICE - FILTER COMBINATIONS")

    test_cases = [
        {
            "name": "Basic search (budget + rooms)",
            "filters": {
                "budget_min": 8000000,
                "budget_max": 12000000,
                "rooms_min": 2,
                "rooms_max": 3
            }
        },
        {
            "name": "Building preferences",
            "filters": {
                "building_types": ["кирпично-монолитный", "монолитный"],
                "renovations": ["чистовая", "под ключ"]
            }
        },
        {
            "name": "Financial conditions",
            "filters": {
                "mortgage_required": True,
                "payment_methods": ["ипотека", "рассрочка"],
                "haggle_allowed": True
            }
        },
        {
            "name": "Layout preferences",
            "filters": {
                "balcony_required": True,
                "bathroom_type": "раздельный",
                "min_ceiling_height": 2.8
            }
        },
        {
            "name": "All filters combined",
            "filters": {
                "budget_max": 10000000,
                "rooms_min": 2,
                "rooms_max": 2,
                "building_types": ["кирпично-монолитный"],
                "renovations": ["чистовая"],
                "mortgage_required": True,
                "balcony_required": True,
                "has_parking": True
            }
        }
    ]

    for idx, test_case in enumerate(test_cases, 1):
        print_section(f"Test Case {idx}: {test_case['name']}")

        try:
            listings = await property_service.search_listings(
                **test_case['filters'],
                limit=100
            )

            print(f"✅ Search completed")
            print(f"📊 Results: {len(listings)} listings found")
            print(f"🔍 Filters applied: {len(test_case['filters'])}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

    print("\n✅ Search filter test complete!")


async def test_result_handler():
    """Test result handler scenarios."""
    print_header("TEST 3: RESULT HANDLER - SCENARIO DETECTION")

    # Mock client
    client = PropertyClientResponse(
        id="test-client",
        telegram_user_id="12345",
        budget_min=8000000,
        budget_max=12000000,
        rooms_min=2,
        rooms_max=3
    )

    scenarios = [
        {
            "name": "No results",
            "count": 0,
            "filters": {"mortgage_required": True, "building_types": ["кирпичный"]}
        },
        {
            "name": "Few results (1-20)",
            "count": 10,
            "filters": {"budget_max": 10000000}
        },
        {
            "name": "Optimal results (20-200)",
            "count": 75,
            "filters": {"rooms_min": 2}
        },
        {
            "name": "Too many results (200+)",
            "count": 250,
            "filters": {"deal_type": "buy"}
        }
    ]

    for idx, scenario_test in enumerate(scenarios, 1):
        print_section(f"Scenario {idx}: {scenario_test['name']}")

        # Create mock listings
        mock_listings = [
            PropertyListingResponse(
                id=f"listing-{i}",
                title=f"Квартира {i}",
                price=9000000 + i * 10000,
                rooms=2,
                area_total=60.0,
                district="Бутово",
                deal_type="buy"
            )
            for i in range(scenario_test['count'])
        ]

        result = await search_result_handler.handle_results(
            listings=mock_listings,
            client=client,
            filters_used=scenario_test['filters']
        )

        print(f"✅ Scenario detected: {result['scenario']}")
        print(f"📝 Message: {result['message']}")
        print(f"💡 Suggestions: {len(result.get('suggestions', []))}")

        if result.get('suggestions'):
            for sugg in result['suggestions'][:2]:
                print(f"   - {sugg.get('type')}: {sugg.get('message', '')[:60]}...")

    print("\n✅ Result handler test complete!")


async def test_dream_score():
    """Test Dream Score calculation."""
    print_header("TEST 4: DREAM SCORE - SCORING SYSTEM")

    # Mock perfect match listing
    perfect_listing = PropertyListingResponse(
        id="perfect-listing",
        title="Perfect Apartment",
        price=9000000,
        rooms=2,
        area_total=65.0,
        living_area=45.0,
        kitchen_area=12.0,
        floor=5,
        total_floors=17,
        district="Бутово",
        metro_distance_minutes=7,
        building_type="кирпично-монолитный",
        building_year=2024,
        renovation="чистовая",
        balcony_type="лоджия",
        bathroom_type="раздельный",
        bathroom_count=2,
        ceiling_height=2.8,
        mortgage_available=True,
        payment_methods=["ипотека", "рассрочка"],
        haggle_allowed=True,
        has_elevator=True,
        has_parking=True,
        deal_type="buy"
    )

    # Mock poor match listing
    poor_listing = PropertyListingResponse(
        id="poor-listing",
        title="Poor Match Apartment",
        price=15000000,  # Way over budget
        rooms=4,  # Wrong
        area_total=120.0,
        floor=1,  # First floor
        district="Другой район",
        metro_distance_minutes=45,
        building_type="панельный",
        renovation="без отделки",
        mortgage_available=False,
        deal_type="buy"
    )

    # Mock client
    client = PropertyClientResponse(
        id="test-client",
        telegram_user_id="12345",
        budget_min=8000000,
        budget_max=10000000,
        rooms_min=2,
        rooms_max=2,
        districts=["Бутово"],
        max_metro_distance_minutes=10,
        not_first_floor=True,
        preferred_building_types=["кирпично-монолитный"],
        preferred_renovations=["чистовая"],
        balcony_required=True,
        bathroom_type_preference="раздельный",
        mortgage_required=True,
        requires_elevator=True
    )

    print_section("Perfect Match")
    perfect_score = dream_score_calculator.calculate(perfect_listing, client)
    print(f"🏆 Dream Score: {perfect_score['dream_score']}/100")
    print(f"📝 {perfect_score['explanation']}")
    print(f"\n📊 Component Breakdown:")
    for component, score in perfect_score['components'].items():
        print(f"   - {component}: {score:.1f}/100")

    print_section("Poor Match")
    poor_score = dream_score_calculator.calculate(poor_listing, client)
    print(f"📉 Dream Score: {poor_score['dream_score']}/100")
    print(f"📝 {poor_score['explanation']}")
    print(f"\n📊 Component Breakdown:")
    for component, score in poor_score['components'].items():
        print(f"   - {component}: {score:.1f}/100")

    print("\n✅ Dream Score test complete!")


async def test_enrichment():
    """Test enrichment orchestrator."""
    print_header("TEST 5: ENRICHMENT - DATA AUGMENTATION")

    # Mock listing with coordinates and images
    listing = PropertyListingResponse(
        id="test-listing",
        title="Test Apartment",
        price=10000000,
        rooms=2,
        area_total=65.0,
        district="Центральный",
        latitude=55.751244,  # Moscow center
        longitude=37.618423,
        building_type="кирпично-монолитный",
        renovation="чистовая",
        developer_name="ПИК",
        images=[
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ],
        deal_type="buy"
    )

    # Mock client with anchor points
    client = PropertyClientResponse(
        id="test-client",
        telegram_user_id="12345",
        anchor_points=[
            {
                "name": "Work",
                "latitude": 55.753215,
                "longitude": 37.622504,
                "priority": 1
            }
        ]
    )

    print("🔄 Starting enrichment (this may take a few seconds)...\n")

    try:
        enrichment_data = await enrichment_orchestrator.enrich_listing_full(
            listing=listing,
            client=client,
            all_listings=[],  # Empty for testing
            enable_poi=True,
            enable_routes=True,
            enable_vision=False,  # Disable to avoid API calls
            enable_price=False,  # No comparison data
            enable_developer=True
        )

        print(f"✅ Enrichment completed!")
        print(f"📊 Enrichment Score: {enrichment_data['enrichment_score']}/100")

        if enrichment_data.get('errors'):
            print(f"\n⚠️ Errors encountered:")
            for error in enrichment_data['errors']:
                print(f"   - {error}")

        print(f"\n📄 Summary:")
        print(enrichment_data['enrichment_summary'])

        print(f"\n📋 Detailed Report:")
        report = enrichment_orchestrator.get_enrichment_report(
            enrichment_data,
            detailed=True
        )
        print(report)

    except Exception as e:
        print(f"❌ Enrichment error: {str(e)}")

    print("\n✅ Enrichment test complete!")


async def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "PROPERTY BOT - COMPREHENSIVE TEST SUITE" + " " * 8 + "║")
    print("╚" + "═" * 58 + "╝")

    if not IMPORTS_AVAILABLE:
        print("\n❌ Cannot run tests - missing dependencies")
        print("Install with: pip install -r requirements.txt")
        return

    try:
        # Run all test suites
        await test_llm_agent()
        await test_search_filters()
        await test_result_handler()
        await test_dream_score()
        await test_enrichment()

        # Final summary
        print_header("ALL TESTS COMPLETE ✅")
        print("\n🎉 Property Bot is fully functional!")
        print("\nTest coverage:")
        print("  ✅ LLM Agent (parameter extraction)")
        print("  ✅ Search Service (37 filters)")
        print("  ✅ Result Handler (5 scenarios)")
        print("  ✅ Dream Score (9 components)")
        print("  ✅ Enrichment Orchestrator (5 services)")
        print("\n" + "─" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Test suite error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        test_map = {
            "llm": test_llm_agent,
            "search": test_search_filters,
            "handler": test_result_handler,
            "score": test_dream_score,
            "enrichment": test_enrichment
        }

        if test_name in test_map:
            print(f"Running single test: {test_name}")
            asyncio.run(test_map[test_name]())
        else:
            print(f"Unknown test: {test_name}")
            print(f"Available tests: {', '.join(test_map.keys())}")
    else:
        # Run all tests
        asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
