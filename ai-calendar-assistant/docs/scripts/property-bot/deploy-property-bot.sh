#!/bin/bash

# Deploy Property Bot Updates to Server
# This script deploys the property bot implementation to the server

set -e

echo "🚀 Deploying Property Bot to server..."

SERVER="root@91.229.8.221"
REMOTE_DIR="/root/ai-calendar-assistant"
PASSWORD="upvzrr3LH4pxsaqs"

# Files to deploy
FILES=(
    "app/models/property.py"
    "app/schemas/property.py"
    "app/services/property_service.py"
    "app/services/property_scoring.py"
    "app/services/property_handler.py"
    "app/services/llm_agent_property.py"
    "app/routers/property.py"
    "app/services/telegram_handler.py"
    "app/main.py"
)

echo "📦 Copying files to server..."
for file in "${FILES[@]}"; do
    echo "  → $file"
    sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$file" "$SERVER:$REMOTE_DIR/$file"
done

echo ""
echo "🔄 Restarting bot on server..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'EOF'
    cd /root/ai-calendar-assistant

    # Restart telegram bot
    docker restart telegram-bot

    # Wait for startup
    sleep 5

    # Check status
    echo ""
    echo "📊 Container status:"
    docker ps | grep -E "telegram-bot|radicale"

    echo ""
    echo "📋 Recent logs:"
    docker logs telegram-bot --tail 20 2>&1 | grep -E "application_started|radicale|property"
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📱 Test the bot:"
echo "  1. Open Telegram bot"
echo "  2. Press '🏠 Поиск новостройки'"
echo "  3. Try searching for property"
echo ""
echo "🌐 Check API:"
echo "  curl https://этонесамыйдлинныйдомен.рф/api/property/status"
echo ""
