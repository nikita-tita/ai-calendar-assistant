#!/bin/bash
# Complete deployment script for Property Bot with full rebuild

set -e

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo "🚀 Starting Property Bot deployment with full rebuild..."

# 1. Upload updated requirements
echo "📦 Uploading requirements-full.txt..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    requirements-full.txt "$SERVER:$REMOTE_DIR/requirements-full.txt"

# 2. Upload Dockerfile
echo "📦 Uploading Dockerfile.hybrid..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    Dockerfile.hybrid "$SERVER:$REMOTE_DIR/Dockerfile.hybrid"

# 3. Upload Property Bot modules
echo "📦 Uploading Property Bot modules..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no -r \
    app/services/property "$SERVER:$REMOTE_DIR/app/services/"

# 4. Upload models and schemas
echo "📦 Uploading models and schemas..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "mkdir -p $REMOTE_DIR/app/models $REMOTE_DIR/app/schemas"

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/models/property.py "$SERVER:$REMOTE_DIR/app/models/property.py"

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/schemas/property.py "$SERVER:$REMOTE_DIR/app/schemas/property.py"

# 5. Upload updated telegram_handler with Property Bot support
echo "📦 Uploading telegram_handler..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/services/telegram_handler.py "$SERVER:$REMOTE_DIR/app/services/telegram_handler.py"

# 6. Upload LLM agent with improved batch confirmations
echo "📦 Uploading llm_agent_yandex.py..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/services/llm_agent_yandex.py "$SERVER:$REMOTE_DIR/app/services/llm_agent_yandex.py"

# 7. Upload STT service with unlimited audio support
echo "📦 Uploading stt_yandex.py..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/services/stt_yandex.py "$SERVER:$REMOTE_DIR/app/services/stt_yandex.py"

# 8. Stop containers
echo "⏹️  Stopping containers..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cd $REMOTE_DIR && docker-compose -f docker-compose.hybrid.yml down"

# 9. Rebuild Docker image with new dependencies
echo "🔨 Rebuilding Docker image (this may take a few minutes)..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cd $REMOTE_DIR && docker-compose -f docker-compose.hybrid.yml build --no-cache telegram-bot"

# 10. Start containers
echo "▶️  Starting containers..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "cd $REMOTE_DIR && docker-compose -f docker-compose.hybrid.yml up -d"

# 11. Wait for bot to start
echo "⏳ Waiting for bot to start..."
sleep 10

# 12. Check status
echo "✅ Checking deployment status..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" \
    "docker ps | grep telegram-bot && echo '---' && docker logs --tail 30 telegram-bot 2>&1"

echo ""
echo "✨ Deployment complete!"
echo ""
echo "📋 What was deployed:"
echo "  ✅ Voice recognition with unlimited audio length (chunked transcription)"
echo "  ✅ Improved batch event confirmation (shows detailed list for different events)"
echo "  ✅ Property Bot modules with full dependencies (SQLAlchemy, lxml, etc.)"
echo "  ✅ Mode switching between Calendar and Property search"
echo ""
echo "🧪 Test the bot:"
echo "  1. Send a voice message (any length)"
echo "  2. Create multiple events and check confirmation format"
echo "  3. Try switching to Property mode: '🏠 Поиск новостройки'"
echo ""
