#!/usr/bin/env python3
"""Test property search with various queries."""

import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('PROPERTY_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
TEST_USER_ID = '2296243'  # Your user ID

# Test queries with different parameters
test_queries = [
    # Basic searches with budget variations
    "Найди квартиру до 10 млн рублей",
    "Ищу квартиру за 15000000 рублей",
    "Квартира до 20 млн",
    "Однушка до 8 миллионов",
    "Двушка до 12000000",

    # With room count
    "Трехкомнатная квартира до 18 млн",
    "Студия до 6000000",
    "Четырехкомнатная до 25 млн",
    "2-комнатная квартира 15 млн",
    "3-х комнатная 20 миллионов",

    # With districts
    "Квартира в Выборгском районе до 15 млн",
    "Двушка в Приморском до 18000000",
    "Квартира в Калининском районе 12 млн",
    "Трешка на севере города до 20 млн",
    "Однушка в центре до 10 миллионов",

    # With metro
    "Квартира у метро Озерки до 15 млн",
    "Двушка рядом с метро Проспект Просвещения 18 млн",
    "Квартира в 10 минутах от метро до 12000000",
    "Трешка в 20 минутах от центра до 25 млн",

    # With mortgage
    "Квартира под ипотеку Сбербанка до 15 млн",
    "Двушка с ипотекой до 18000000",
    "Трехкомнатная под ипотеку ВТБ 20 млн",
    "Квартира подходящая под военную ипотеку 10 млн",

    # Complex queries
    "Найди мне квартиру за 18000000 двухкомнатную на севере города в 20 минутах от центра Подходящую под ипотеку сбербанка",
    "Трехкомнатная квартира в Выборгском районе до 20 млн с ипотекой",
    "Двушка у метро Озерки до 16 миллионов под ипотеку",
    "Студия в новостройке до 7000000 в Приморском районе",
    "Четырехкомнатная квартира на севере города до 30 млн с парковкой",
    "Двушка до 15 млн в 15 минутах от метро с ипотекой Сбербанка",
    "Трехкомнатная до 22 миллионов в Калининском районе новостройка"
]

def send_message(chat_id: str, text: str):
    """Send message to bot via Telegram API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Error sending message: {e}")
        return None

def main():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return

    print(f"🚀 Starting property search tests...")
    print(f"📊 Total test cases: {len(test_queries)}")
    print(f"👤 Test user ID: {TEST_USER_ID}\n")

    success_count = 0
    error_count = 0

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_queries)}")
        print(f"Query: {query}")
        print(f"{'='*80}")

        result = send_message(TEST_USER_ID, query)

        if result and result.get('ok'):
            print(f"✅ Message sent successfully")
            success_count += 1
        else:
            print(f"❌ Failed to send message: {result}")
            error_count += 1

        # Wait between messages to avoid rate limiting and allow bot to process
        if i < len(test_queries):
            wait_time = 15  # 15 seconds between messages
            print(f"⏳ Waiting {wait_time}s before next test...")
            time.sleep(wait_time)

    print(f"\n{'='*80}")
    print(f"📊 Test Summary:")
    print(f"✅ Successful: {success_count}/{len(test_queries)}")
    print(f"❌ Failed: {error_count}/{len(test_queries)}")
    print(f"{'='*80}")

    print("\n💡 Check bot logs on server:")
    print("   ssh root@95.163.227.26")
    print("   docker logs telegram-bot-polling 2>&1 | grep 'search_criteria\\|listings_found\\|search_execution_error'")

if __name__ == "__main__":
    main()
