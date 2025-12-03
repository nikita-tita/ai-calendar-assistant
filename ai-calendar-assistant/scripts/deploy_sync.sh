#!/bin/bash
# Deploy script that syncs git repo with docker build context
# Created: 2025-12-04

set -e

PROD_DIR="/root/ai-calendar-assistant"
GIT_DIR="/root/ai-calendar-assistant/ai-calendar-assistant"

echo "=== AI Calendar Assistant Deploy Script ==="
echo "Timestamp: $(date)"

# 1. Pull latest from git
echo ""
echo "Step 1: Pulling latest changes from git..."
cd "$GIT_DIR"
git pull origin main

# 2. Sync app directory
echo ""
echo "Step 2: Syncing app/ directory..."
rsync -av --delete "$GIT_DIR/app/" "$PROD_DIR/app/"

# 3. Sync other important files
echo ""
echo "Step 3: Syncing config files..."
cp -v "$GIT_DIR/requirements.txt" "$PROD_DIR/requirements.txt"
cp -v "$GIT_DIR/run_polling.py" "$PROD_DIR/run_polling.py" 2>/dev/null || true
cp -v "$GIT_DIR/start.sh" "$PROD_DIR/start.sh" 2>/dev/null || true

# 4. Rebuild docker
echo ""
echo "Step 4: Rebuilding docker container..."
cd "$PROD_DIR"
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot

# 5. Restart container
echo ""
echo "Step 5: Restarting container..."
docker-compose -f docker-compose.secure.yml up -d telegram-bot

# 6. Verify
echo ""
echo "Step 6: Verifying deployment..."
sleep 3
APP_VERSION=$(docker exec telegram-bot cat /app/app/static/index.html 2>/dev/null | grep "APP_VERSION" | head -1 || echo "Could not read version")
echo "Container APP_VERSION: $APP_VERSION"

echo ""
echo "=== Deploy completed! ==="
echo "Check health: curl https://calendar.housler.ru/health"
