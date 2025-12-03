#!/bin/bash
# Quick deploy script to fix date detection issue
set -e

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"

echo "🚀 Deploying fix for date detection..."

# Upload fixed telegram_handler.py
echo "📤 Uploading telegram_handler.py to server..."
sshpass -p "$PASSWORD" scp app/services/telegram_handler.py $SERVER:/root/ai-calendar-assistant/app/services/telegram_handler.py

# Update Docker container and restart
echo "🔄 Updating Docker container..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'EOF'
    # Copy file into Docker container
    docker cp /root/ai-calendar-assistant/app/services/telegram_handler.py telegram-bot:/app/app/services/telegram_handler.py

    # Restart container
    docker restart telegram-bot

    # Wait for startup
    sleep 10

    # Check status
    if docker ps | grep -q telegram-bot; then
        echo "✅ Bot restarted successfully in Docker"
        docker ps | grep telegram-bot
    else
        echo "❌ Bot failed to start"
        docker logs --tail 30 telegram-bot
        exit 1
    fi
EOF

echo ""
echo "✅ Deploy complete!"
echo "📝 Test with 'Дела на сегодня' or '📋 Дела на сегодня'"
echo "📝 Check logs: docker logs -f telegram-bot"
