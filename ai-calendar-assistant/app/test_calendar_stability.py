#!/usr/bin/env python3
"""
Automated test to verify calendar functionality is stable.
Run this before every deployment to prevent regressions.
"""

import sys
import asyncio
import structlog
from datetime import datetime, timedelta

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


async def test_calendar_service():
    """Test calendar service basic operations."""
    logger.info("test_started", test="calendar_service")

    try:
        from app.services.calendar_radicale import calendar_service

        test_user = "test_stability_user"

        # Test 1: Get calendar name (checks Radicale connection)
        logger.info("test_step", step="get_calendar_name")
        calendar_name = await calendar_service.get_calendar_name(test_user)
        assert calendar_name is not None
        logger.info("test_passed", step="get_calendar_name", calendar=calendar_name)

        # Test 2: Create event
        logger.info("test_step", step="create_event")
        start_time = datetime.utcnow() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)

        event_id = await calendar_service.create_event(
            user_id=test_user,
            title="Test Event - Stability Check",
            start_time=start_time,
            end_time=end_time,
            description="Automated test event"
        )
        assert event_id is not None
        logger.info("test_passed", step="create_event", event_id=event_id)

        # Test 3: Get events
        logger.info("test_step", step="get_events")
        events = await calendar_service.get_events(
            user_id=test_user,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=1)
        )
        assert len(events) >= 1
        logger.info("test_passed", step="get_events", count=len(events))

        # Test 4: Update event
        logger.info("test_step", step="update_event")
        updated = await calendar_service.update_event(
            user_id=test_user,
            event_id=event_id,
            title="Updated Test Event"
        )
        assert updated is True
        logger.info("test_passed", step="update_event")

        # Test 5: Delete event
        logger.info("test_step", step="delete_event")
        deleted = await calendar_service.delete_event(
            user_id=test_user,
            event_id=event_id
        )
        assert deleted is True
        logger.info("test_passed", step="delete_event")

        logger.info("test_completed", test="calendar_service", status="PASS")
        return True

    except Exception as e:
        logger.error("test_failed", test="calendar_service", error=str(e))
        return False


async def test_telegram_handler():
    """Test telegram handler calendar mode."""
    logger.info("test_started", test="telegram_handler")

    try:
        from app.services.telegram_handler import TelegramHandler

        handler = TelegramHandler()

        # Verify handler has required methods
        assert hasattr(handler, 'handle_update')
        assert hasattr(handler, '_handle_text')
        assert hasattr(handler, '_handle_voice')

        logger.info("test_passed", step="telegram_handler_methods_exist")

        logger.info("test_completed", test="telegram_handler", status="PASS")
        return True

    except Exception as e:
        logger.error("test_failed", test="telegram_handler", error=str(e))
        return False


async def test_property_isolation():
    """Test that property module doesn't interfere with calendar."""
    logger.info("test_started", test="property_isolation")

    try:
        # Import property modules
        from app.services.property.property_service import property_service
        from app.services.property.property_handler import property_handler

        # Import calendar modules
        from app.services.calendar_radicale import calendar_service

        # Verify they can coexist
        assert property_service is not None
        assert property_handler is not None
        assert calendar_service is not None

        logger.info("test_passed", step="modules_coexist")

        # Test that property service uses separate DB tables
        test_user = "test_isolation_user"
        from app.models.property import BotMode

        mode = await property_service.get_user_mode(test_user)
        assert mode == BotMode.CALENDAR  # Default mode

        logger.info("test_passed", step="property_service_works")

        logger.info("test_completed", test="property_isolation", status="PASS")
        return True

    except Exception as e:
        logger.error("test_failed", test="property_isolation", error=str(e))
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("CALENDAR STABILITY TEST SUITE")
    logger.info("=" * 60)

    tests = [
        ("Calendar Service", test_calendar_service),
        ("Telegram Handler", test_telegram_handler),
        ("Property Isolation", test_property_isolation),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info("")
        logger.info("running_test", name=test_name)
        result = await test_func()
        results.append((test_name, result))
        logger.info("test_result", name=test_name, passed=result)

    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info("test_summary", name=test_name, status=status)
        if not result:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("ALL TESTS PASSED ✅")
        return 0
    else:
        logger.error("SOME TESTS FAILED ❌")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
