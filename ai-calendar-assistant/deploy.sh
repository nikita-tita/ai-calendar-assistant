#!/bin/bash
# Deploy from git
set -e

cd /root/ai-calendar-assistant

echo "🔄 Pulling from git..."
git pull origin main

echo "🏗️ Rebuilding container..."
docker-compose build telegram-bot-polling

echo "🚀 Restarting container..."
docker-compose up -d telegram-bot-polling

echo "✅ Deploy complete!"
docker logs --tail 5 telegram-bot-polling
