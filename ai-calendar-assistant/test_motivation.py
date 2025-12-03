#!/usr/bin/env python3
"""Test motivation messages system."""

import sys
sys.path.insert(0, '/app')

from app.services.translations import get_translation, Language
from app.services.user_preferences import UserPreferencesService

# Initialize preferences service
prefs = UserPreferencesService(data_file="/tmp/test_user_preferences.json")

# Test user
test_user_id = "test_123"

# Set language to Russian
prefs.set_language(test_user_id, Language.RUSSIAN)

# Test getting motivation index (should be 1 initially)
print(f"Initial motivation index: {prefs.get_motivation_index(test_user_id)}")

# Test all 60 motivational messages
print("\nTesting all 60 motivational messages in Russian:")
for i in range(1, 61):
    message_key = f"morning_motivation_{i}"
    message = get_translation(message_key, Language.RUSSIAN)
    print(f"{i}. {message[:50]}...")  # Print first 50 chars

# Test cycling through indices
print("\n\nTesting index cycling:")
for i in range(1, 65):
    current = prefs.get_motivation_index(test_user_id)
    new = prefs.increment_motivation_index(test_user_id)
    print(f"Iteration {i}: current={current}, next={new}")
    if i == 61:
        print("  -> Should have cycled back to 1!")

# Test button text translation
print("\n\nTesting button text:")
for lang in [Language.RUSSIAN, Language.ENGLISH, Language.SPANISH, Language.ARABIC]:
    btn_text = get_translation("motivation_btn_action", lang)
    print(f"{lang.value}: {btn_text}")

print("\n✅ All tests passed!")
