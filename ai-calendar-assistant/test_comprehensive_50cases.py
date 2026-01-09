#!/usr/bin/env python3
"""
Comprehensive Test Suite - 50 Natural Language Cases
Tests AI Calendar Assistant LLM understanding across various scenarios
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
from app.schemas.events import IntentType


# Test cases grouped by category
TEST_CASES = [
    # ==========================================
    # CATEGORY 1: Single Event Creation (10 cases)
    # ==========================================
    {
        "id": 1,
        "category": "single_event",
        "input": "Встреча завтра в 15:00",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Simple event creation with relative date"
    },
    {
        "id": 2,
        "category": "single_event",
        "input": "В 17 часов презентация продукта",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event with time today"
    },
    {
        "id": 3,
        "category": "single_event",
        "input": "Завтра в 14 созвон с командой",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event tomorrow with specific time"
    },
    {
        "id": 4,
        "category": "single_event",
        "input": "В понедельник в 10 утра совещание",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event on specific weekday"
    },
    {
        "id": 5,
        "category": "single_event",
        "input": "Обед с клиентом в пятницу в 13:00",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event on Friday with time"
    },
    {
        "id": 6,
        "category": "single_event",
        "input": "25 ноября в 16:00 презентация",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event with specific date"
    },
    {
        "id": 7,
        "category": "single_event",
        "input": "Team meeting at 10am tomorrow",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "English event creation"
    },
    {
        "id": 8,
        "category": "single_event",
        "input": "Сходить к врачу послезавтра в 11",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event day after tomorrow"
    },
    {
        "id": 9,
        "category": "single_event",
        "input": "Встреча в офисе через 2 часа",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Relative time (in 2 hours)"
    },
    {
        "id": 10,
        "category": "single_event",
        "input": "Вебинар в среду в 19:00 по московскому времени",
        "expected_intent": IntentType.CREATE,
        "expected_fields": ["title", "start_time"],
        "description": "Event with timezone mention"
    },

    # ==========================================
    # CATEGORY 2: TODO Tasks (10 cases)
    # ==========================================
    {
        "id": 11,
        "category": "todo",
        "input": "Позвонить маме",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Simple task without time"
    },
    {
        "id": 12,
        "category": "todo",
        "input": "Купить молоко и хлеб",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Shopping task"
    },
    {
        "id": 13,
        "category": "todo",
        "input": "Написать отчет завтра",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title", "due_date"],
        "description": "Task with due date but no time"
    },
    {
        "id": 14,
        "category": "todo",
        "input": "Проверить почту",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Simple task"
    },
    {
        "id": 15,
        "category": "todo",
        "input": "Обновить персональные данные",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Administrative task"
    },
    {
        "id": 16,
        "category": "todo",
        "input": "Надо не забыть оплатить интернет",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Task with 'надо не забыть' pattern"
    },
    {
        "id": 17,
        "category": "todo",
        "input": "Сделать презентацию к понедельнику",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title", "due_date"],
        "description": "Task with deadline"
    },
    {
        "id": 18,
        "category": "todo",
        "input": "Изучить новый фреймворк",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Learning task"
    },
    {
        "id": 19,
        "category": "todo",
        "input": "Fix bug in authentication module",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "English tech task"
    },
    {
        "id": 20,
        "category": "todo",
        "input": "Поменять пнд и оферту на ИП",
        "expected_intent": IntentType.TODO,
        "expected_fields": ["title"],
        "description": "Task with abbreviation (пнд)"
    },

    # ==========================================
    # CATEGORY 3: Multiple Events/Tasks (10 cases)
    # ==========================================
    {
        "id": 21,
        "category": "multiple",
        "input": "Сегодня в 18 забрать лонгслив из Sela, потом в 19 сходить в Папа Принт",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 2,
        "description": "Two sequential events with 'потом'"
    },
    {
        "id": 22,
        "category": "multiple",
        "input": "В 17 встреча, в 19 ужин и еще позвонить маме",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Two events + one todo"
    },
    {
        "id": 23,
        "category": "multiple",
        "input": "Завтра встреча в 10, потом обед в 13, а потом нужно проверить почту",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Two events + task with multiple connectors"
    },
    {
        "id": 24,
        "category": "multiple",
        "input": "At 2pm call John, then at 4pm team meeting",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 2,
        "description": "English multiple events"
    },
    {
        "id": 25,
        "category": "multiple",
        "input": "Утром в 9 зарядка, в 10 завтрак, в 11 работа",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Three events in sequence"
    },
    {
        "id": 26,
        "category": "multiple",
        "input": "Сегодня: в 14 презентация, в 16 встреча с HR, в 18 выйти пораньше",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "List format with colon"
    },
    {
        "id": 27,
        "category": "multiple",
        "input": "В понедельник: 10:00 standup, 14:00 review, 17:00 ретро",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Monday schedule with time format"
    },
    {
        "id": 28,
        "category": "multiple",
        "input": "Завтра сделать зарядку, потом позавтракать, потом начать работу в 10",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Mix of todos and event"
    },
    {
        "id": 29,
        "category": "multiple",
        "input": "В среду в 11 встреча, затем в 13 обед, также нужно купить подарок",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Events with 'затем' and 'также'"
    },
    {
        "id": 30,
        "category": "multiple",
        "input": "В субботу: 10:00-11:00 тренировка, 12:00-13:00 обед, 15:00 кино",
        "expected_intent": IntentType.BATCH_CONFIRM,
        "expected_batch_count": 3,
        "description": "Schedule with time ranges"
    },

    # ==========================================
    # CATEGORY 4: Recurring Events (5 cases)
    # ==========================================
    {
        "id": 31,
        "category": "recurring",
        "input": "Бег по утрам в 9 часов",
        "expected_intent": IntentType.CREATE_RECURRING,
        "expected_fields": ["recurrence_type", "start_time"],
        "description": "Daily recurring implicit"
    },
    {
        "id": 32,
        "category": "recurring",
        "input": "Каждый вторник в 14 совещание",
        "expected_intent": IntentType.CREATE_RECURRING,
        "expected_fields": ["recurrence_type", "recurrence_days", "start_time"],
        "description": "Weekly recurring on Tuesday"
    },
    {
        "id": 33,
        "category": "recurring",
        "input": "Каждый день в 9 утра утренний ритуал",
        "expected_intent": IntentType.CREATE_RECURRING,
        "expected_fields": ["recurrence_type", "start_time"],
        "description": "Daily recurring explicit"
    },
    {
        "id": 34,
        "category": "recurring",
        "input": "Every Monday and Wednesday at 10am standup",
        "expected_intent": IntentType.CREATE_RECURRING,
        "expected_fields": ["recurrence_type", "recurrence_days"],
        "description": "Multiple weekdays recurring"
    },
    {
        "id": 35,
        "category": "recurring",
        "input": "Каждую пятницу в 18:00 планёрка на неделю",
        "expected_intent": IntentType.CREATE_RECURRING,
        "expected_fields": ["recurrence_type", "recurrence_days", "start_time"],
        "description": "Weekly Friday recurring"
    },

    # ==========================================
    # CATEGORY 5: Query/Search (10 cases)
    # ==========================================
    {
        "id": 36,
        "category": "query",
        "input": "Что у меня сегодня?",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start"],
        "description": "Query today's schedule"
    },
    {
        "id": 37,
        "category": "query",
        "input": "Скажи мне во сколько я занят сегодня",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start"],
        "description": "Natural query about today"
    },
    {
        "id": 38,
        "category": "query",
        "input": "Какие планы на завтра?",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start"],
        "description": "Query tomorrow"
    },
    {
        "id": 39,
        "category": "query",
        "input": "Что на этой неделе?",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start", "query_date_end"],
        "description": "Query this week"
    },
    {
        "id": 40,
        "category": "query",
        "input": "Покажи мои встречи на понедельник",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start"],
        "description": "Query specific weekday"
    },
    {
        "id": 41,
        "category": "query",
        "input": "What do I have tomorrow?",
        "expected_intent": IntentType.QUERY,
        "expected_fields": ["query_date_start"],
        "description": "English query"
    },
    {
        "id": 42,
        "category": "query",
        "input": "Когда я свободен завтра?",
        "expected_intent": IntentType.FIND_FREE_SLOTS,
        "expected_fields": ["query_date_start"],
        "description": "Find free time"
    },
    {
        "id": 43,
        "category": "query",
        "input": "Когда я свободен завтра после 16?",
        "expected_intent": IntentType.FIND_FREE_SLOTS,
        "expected_fields": ["query_date_start", "query_time_start"],
        "description": "Find free time after specific time"
    },
    {
        "id": 44,
        "category": "query",
        "input": "Свободное время в пятницу",
        "expected_intent": IntentType.FIND_FREE_SLOTS,
        "expected_fields": ["query_date_start"],
        "description": "Free slots on Friday"
    },
    {
        "id": 45,
        "category": "query",
        "input": "When am I free after 4pm today?",
        "expected_intent": IntentType.FIND_FREE_SLOTS,
        "expected_fields": ["query_date_start", "query_time_start"],
        "description": "English free time query"
    },

    # ==========================================
    # CATEGORY 6: Update/Delete (5 cases)
    # ==========================================
    {
        "id": 46,
        "category": "update_delete",
        "input": "Перенеси встречу на 15:00",
        "expected_intent": IntentType.UPDATE,
        "expected_fields": ["start_time"],
        "description": "Reschedule to different time"
    },
    {
        "id": 47,
        "category": "update_delete",
        "input": "Удали встречу завтра",
        "expected_intent": [IntentType.DELETE, IntentType.CLARIFY],
        "expected_fields": [],
        "description": "Delete event tomorrow (may need clarification)"
    },
    {
        "id": 48,
        "category": "update_delete",
        "input": "Отмени все встречи на понедельник",
        "expected_intent": IntentType.DELETE_BY_CRITERIA,
        "expected_fields": ["delete_criteria_title_contains"],
        "description": "Delete all events on Monday"
    },
    {
        "id": 49,
        "category": "update_delete",
        "input": "Удали все утренние ритуалы",
        "expected_intent": IntentType.DELETE_BY_CRITERIA,
        "expected_fields": ["delete_criteria_title_contains"],
        "description": "Delete by title pattern"
    },
    {
        "id": 50,
        "category": "update_delete",
        "input": "Удали дубликаты",
        "expected_intent": IntentType.DELETE_DUPLICATES,
        "expected_fields": [],
        "description": "Delete duplicate events"
    },
]


class TestResult:
    """Test result container"""
    def __init__(self, case_id: int, success: bool, actual_intent: str,
                 response: Any, error: str = None, details: str = ""):
        self.case_id = case_id
        self.success = success
        self.actual_intent = actual_intent
        self.response = response
        self.error = error
        self.details = details


async def run_test_case(test_case: Dict) -> TestResult:
    """Run single test case"""
    case_id = test_case["id"]
    user_input = test_case["input"]

    try:
        # Call LLM agent
        response = await llm_agent.process_message(
            user_text=user_input,
            timezone="Europe/Moscow",
            existing_events=[]
        )

        # Check intent
        actual_intent = response.intent
        expected_intent = test_case["expected_intent"]

        # Handle multiple possible intents
        if isinstance(expected_intent, list):
            intent_match = actual_intent in expected_intent
        else:
            intent_match = actual_intent == expected_intent

        # Check required fields
        fields_present = True
        missing_fields = []
        if "expected_fields" in test_case:
            for field in test_case["expected_fields"]:
                if not hasattr(response, field) or getattr(response, field) is None:
                    fields_present = False
                    missing_fields.append(field)

        # Check batch count if applicable
        batch_match = True
        if "expected_batch_count" in test_case:
            if hasattr(response, 'batch_actions') and response.batch_actions:
                batch_match = len(response.batch_actions) == test_case["expected_batch_count"]
            else:
                batch_match = False

        success = intent_match and fields_present and batch_match

        details = f"Intent: {actual_intent}"
        if missing_fields:
            details += f", Missing fields: {missing_fields}"
        if "expected_batch_count" in test_case:
            actual_count = len(response.batch_actions) if hasattr(response, 'batch_actions') and response.batch_actions else 0
            details += f", Batch: {actual_count}/{test_case['expected_batch_count']}"

        return TestResult(
            case_id=case_id,
            success=success,
            actual_intent=str(actual_intent),
            response=response,
            details=details
        )

    except Exception as e:
        return TestResult(
            case_id=case_id,
            success=False,
            actual_intent="ERROR",
            response=None,
            error=str(e),
            details=f"Exception: {str(e)[:100]}"
        )


async def run_all_tests():
    """Run all 50 test cases"""
    print("=" * 80)
    print("🧪 AI Calendar Assistant - Comprehensive Test Suite (50 Cases)")
    print("=" * 80)
    print()

    results = []
    categories = {}

    # Run tests
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/50] Testing: {test_case['input'][:60]}...")
        result = await run_test_case(test_case)
        results.append(result)

        # Track by category
        category = test_case["category"]
        if category not in categories:
            categories[category] = {"passed": 0, "failed": 0, "total": 0}
        categories[category]["total"] += 1
        if result.success:
            categories[category]["passed"] += 1
            print(f"    ✅ PASS - {result.details}")
        else:
            categories[category]["failed"] += 1
            print(f"    ❌ FAIL - {result.details}")
            if result.error:
                print(f"       Error: {result.error[:80]}")
        print()

    # Summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print()

    total_passed = sum(1 for r in results if r.success)
    total_failed = len(results) - total_passed
    success_rate = (total_passed / len(results)) * 100

    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {total_passed} ({success_rate:.1f}%)")
    print(f"❌ Failed: {total_failed}")
    print()

    # By category
    print("By Category:")
    print("-" * 80)
    for cat, stats in sorted(categories.items()):
        rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        status = "✅" if rate == 100 else "⚠️" if rate >= 70 else "❌"
        print(f"{status} {cat:20s}: {stats['passed']:2d}/{stats['total']:2d} ({rate:5.1f}%)")
    print()

    # Failed cases detail
    if total_failed > 0:
        print("=" * 80)
        print("❌ FAILED CASES DETAIL")
        print("=" * 80)
        for i, test_case in enumerate(TEST_CASES):
            result = results[i]
            if not result.success:
                print(f"\n#{test_case['id']}: {test_case['description']}")
                print(f"  Input: {test_case['input']}")
                print(f"  Expected: {test_case['expected_intent']}")
                print(f"  Actual: {result.actual_intent}")
                print(f"  Details: {result.details}")
                if result.error:
                    print(f"  Error: {result.error}")

    # Save results to JSON
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": len(results),
        "passed": total_passed,
        "failed": total_failed,
        "success_rate": success_rate,
        "categories": categories,
        "failed_cases": [
            {
                "id": TEST_CASES[i]["id"],
                "input": TEST_CASES[i]["input"],
                "category": TEST_CASES[i]["category"],
                "expected": str(TEST_CASES[i]["expected_intent"]),
                "actual": results[i].actual_intent,
                "error": results[i].error,
                "details": results[i].details
            }
            for i in range(len(results))
            if not results[i].success
        ]
    }

    with open("test_results_50cases.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print(f"✅ Report saved to: test_results_50cases.json")
    print("=" * 80)

    return results, categories, success_rate


if __name__ == "__main__":
    asyncio.run(run_all_tests())
