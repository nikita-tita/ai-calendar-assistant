#!/bin/bash
set -e

echo "🔍 VERIFICATION SCRIPT - Checking Production Deployment"
echo "========================================================"
echo ""

SERVER="root@95.163.227.26"
KEY="~/.ssh/id_housler"

echo "1️⃣ Checking .env file on server..."
ssh -i ~/.ssh/id_housler "$SERVER" 'cat /root/ai-calendar-assistant/.env | grep TELEGRAM_WEBAPP_URL' || echo "❌ Failed to read .env"
echo ""

echo "2️⃣ Checking environment in telegram-bot-polling container..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec telegram-bot-polling env | grep TELEGRAM_WEBAPP_URL' || echo "❌ Container not running or variable not set"
echo ""

echo "3️⃣ Checking recent logs for webapp URL..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker logs telegram-bot-polling --tail 50 | grep -E "(webapp|WebApp)" | tail -5' || echo "❌ No logs found"
echo ""

echo "4️⃣ Checking if containers are running..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker ps --filter "name=calendar" --format "table {{.Names}}\t{{.Status}}"'
echo ""

echo "5️⃣ Checking index.html line count in container..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec ai-calendar-assistant wc -l /app/app/static/index.html' || echo "❌ Failed to read index.html"
echo ""

echo "6️⃣ Checking if index.html has the date range fix..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec ai-calendar-assistant grep -n "fromDate.setDate(fromDate.getDate() - 30)" /app/app/static/index.html' || echo "❌ Date range fix NOT found!"
echo ""

echo "7️⃣ Checking telegram_handler.py for timestamp generation..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker exec telegram-bot-polling grep -A2 "time.time()" /app/app/services/telegram_handler.py | head -5' || echo "❌ Timestamp code not found"
echo ""

echo "✅ Verification complete!"
