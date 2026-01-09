#!/usr/bin/env python3
"""Manual test to check bot functionality."""

import asyncio
from app.services.llm_agent_yandex import llm_agent_yandex
from datetime import datetime

async def test_batch_command():
    """Test batch command parsing."""

    # User's command
    user_text = "И давай на 8 утра до конца недели поставим время для прозвона холодной базы"

    print(f"Testing command: {user_text}")
    print(f"Current date: {datetime.now()}")
    print("-" * 80)

    try:
        result = await llm_agent_yandex.extract_event(
            user_text=user_text,
            user_id="test_user",
            conversation_history=[],
            timezone="Europe/Moscow",
            existing_events=[],
            language="ru"
        )

        print(f"Intent: {result.intent}")
        print(f"Title: {result.title}")
        print(f"Start time: {result.start_time}")
        print(f"End time: {result.end_time}")
        print(f"Description: {result.description}")
        print(f"Batch actions: {result.batch_actions}")

        if result.batch_actions:
            print(f"\nBatch operations found: {len(result.batch_actions)}")
            for i, action in enumerate(result.batch_actions, 1):
                print(f"\n  Action {i}:")
                print(f"    Intent: {action.get('intent')}")
                print(f"    Title: {action.get('title')}")
                print(f"    Start: {action.get('start_time')}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_command())
