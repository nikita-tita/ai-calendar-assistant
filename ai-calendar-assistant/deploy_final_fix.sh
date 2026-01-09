#!/bin/bash
set -e

echo "🚀 FINAL DEPLOYMENT - Date Range Fix + Clean .env"
echo "=================================================="
echo ""

SERVER="root@95.163.227.26"
PROJECT_DIR="/root/ai-calendar-assistant"

echo "📦 Step 1: Upload .env file..."
scp -i ~/.ssh/id_housler .env "$SERVER:$PROJECT_DIR/.env" || {
    echo "❌ Failed to upload .env"
    exit 1
}
echo "✅ .env uploaded"
echo ""

echo "📦 Step 2: Upload index.html..."
scp -i ~/.ssh/id_housler app/static/index.html "$SERVER:$PROJECT_DIR/app/static/index.html" || {
    echo "❌ Failed to upload index.html"
    exit 1
}
echo "✅ index.html uploaded (705 lines with date range fix)"
echo ""

echo "📦 Step 3: Upload telegram_handler.py..."
scp -i ~/.ssh/id_housler app/services/telegram_handler.py "$SERVER:$PROJECT_DIR/app/services/telegram_handler.py" || {
    echo "❌ Failed to upload telegram_handler.py"
    exit 1
}
echo "✅ telegram_handler.py uploaded (with time.time() timestamp)"
echo ""

echo "🔄 Step 4: Restart containers with new .env..."
ssh -i ~/.ssh/id_housler "$SERVER" "cd $PROJECT_DIR && docker-compose down && docker-compose up -d" || {
    echo "❌ Failed to restart containers"
    exit 1
}
echo "✅ Containers restarted"
echo ""

echo "⏳ Waiting 10 seconds for containers to fully start..."
sleep 10
echo ""

echo "🔍 Step 5: Verification..."
echo ""

echo "  5.1 Checking container status..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker ps --filter "name=calendar" --format "{{.Names}}: {{.Status}}"'
echo ""

echo "  5.2 Checking .env in container..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec telegram-bot-polling env | grep TELEGRAM_WEBAPP_URL'
echo ""

echo "  5.3 Checking index.html in container..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec ai-calendar-assistant grep -c "fromDate.setDate(fromDate.getDate() - 30)" /app/app/static/index.html' && echo "  ✅ Date range fix found in container!" || echo "  ❌ Date range fix NOT in container!"
echo ""

echo "  5.4 Checking recent bot logs..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker logs telegram-bot-polling --tail 20 | grep -E "(Started|webapp)" || echo "  No relevant logs yet"'
echo ""

echo "✅ DEPLOYMENT COMPLETE!"
echo ""
echo "📋 TESTING INSTRUCTIONS:"
echo "========================"
echo "1. Open Telegram bot"
echo "2. Send /start command"
echo "3. Click \"🗓 Кабинет\" button"
echo "4. Check:"
echo "   - Should open calendar on current date (November 25, 2025)"
echo "   - Events from October 30 should be visible (30 days back)"
echo "   - Date selection should work and scroll to that date's events"
echo ""
echo "Expected behavior:"
echo "  ✓ URL format: https://calendar.housler.ru?v=1764022XXX (single ?v=)"
echo "  ✓ Shows events from 30 days ago to 60 days ahead"
echo "  ✓ No cached old version with tabs"
echo ""
