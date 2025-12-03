"""Test script for schedule format detection."""

import asyncio
from datetime import datetime
import pytz

# Mock EventDTO and IntentType for testing
class IntentType:
    BATCH_CONFIRM = "batch_confirm"

class EventDTO:
    def __init__(self, intent, confidence, batch_actions, batch_summary, raw_text):
        self.intent = intent
        self.confidence = confidence
        self.batch_actions = batch_actions
        self.batch_summary = batch_summary
        self.raw_text = raw_text

# Test the schedule detection
test_input = """тайминг на 23 октября (завтра):
12:45-13:00 Приезд, заселение (по готовности номеров), либо вещи в багажную комнату
13:00-13:30 Кофе-брейк с сендвичами
13:30-15:00 Дискуссия по ИИ
15:00-16:00 Обед
16:00-16:30 Заезд, свободное время
16:30-18:00 Игра "Го"
18:00-18:20 Кофе-брейк
18:20-20:00 Игра "Го"
20:00 Ужин"""

print("Testing schedule format detection...")
print(f"Input text:\n{test_input}\n")

# Import the actual function
import sys
sys.path.insert(0, '/Users/fatbookpro/ai-calendar-assistant')

from app.services.llm_agent_yandex import llm_agent_yandex

# Test detection
result = llm_agent_yandex._detect_schedule_format(test_input, timezone='Europe/Moscow')

if result:
    print(f"✅ Schedule detected!")
    print(f"Intent: {result.intent}")
    print(f"Confidence: {result.confidence}")
    print(f"Events count: {len(result.batch_actions)}")
    print(f"\nBatch summary:\n{result.batch_summary}")
    print(f"\nParsed events:")
    for i, action in enumerate(result.batch_actions, 1):
        start = datetime.fromisoformat(action['start_time'])
        end = datetime.fromisoformat(action['end_time'])
        print(f"{i}. {start.strftime('%H:%M')}-{end.strftime('%H:%M')} {action['title']} ({action['duration_minutes']} мин)")
else:
    print("❌ Schedule format not detected")
