#!/bin/bash

# Deploy Property Search Bot as separate bot
# Connects to @aipropertyfinder_bot (token: 7964619356:AAGXqaiVnsUfYpOSi45KP2LnSFCIrL-NIN8)

set -e

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
APP_DIR="/root/ai-calendar-assistant"

echo "=================================================="
echo "🚀 Deploying Property Search Bot"
echo "=================================================="

echo ""
echo "📦 Step 1: Copying files to server..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    run_property_bot.py \
    Dockerfile.property-bot \
    docker-compose.yml \
    app/services/telegram_handler.py \
    "$SERVER:$APP_DIR/"

echo ""
echo "📦 Step 2: Copying property bot modules..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no -r \
    app/services/property/ \
    "$SERVER:$APP_DIR/app/services/"

echo ""
echo "🐳 Step 3: Building and starting property bot..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant

# Build property bot image
echo "Building property bot image..."
docker-compose build property-bot

# Start property bot
echo "Starting property bot..."
docker-compose up -d property-bot

# Wait for startup
echo "Waiting for bot to start..."
sleep 5

# Check status
echo ""
echo "==================================================="
echo "📊 Property Bot Status:"
echo "==================================================="
docker-compose ps property-bot
echo ""
docker logs --tail 20 property-bot

echo ""
echo "==================================================="
echo "✅ Property Bot deployed!"
echo "Bot username: @aipropertyfinder_bot"
echo "Link: https://t.me/aipropertyfinder_bot"
echo "==================================================="

ENDSSH

echo ""
echo "🔄 Step 4: Restarting calendar bot with updated link..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant

# Copy updated telegram_handler to calendar bot
docker cp app/services/telegram_handler.py telegram-bot-polling:/app/app/services/telegram_handler.py

# Restart calendar bot
docker restart telegram-bot-polling

echo "Waiting for calendar bot restart..."
sleep 5

echo ""
echo "==================================================="
echo "📊 Calendar Bot Status:"
echo "==================================================="
docker logs --tail 15 telegram-bot-polling

ENDSSH

echo ""
echo "==================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "==================================================="
echo ""
echo "📱 Calendar Bot: https://t.me/your_calendar_bot"
echo "🏢 Property Bot: https://t.me/aipropertyfinder_bot"
echo ""
echo "Test by sending '🏢 Поиск новостроек' to calendar bot"
echo "==================================================="
