#!/bin/bash

set -e

echo "=================================================="
echo "🔥 DOCKER IMAGE REBUILD - Root Cause Fix"
echo "=================================================="
echo ""
echo "Root Cause: Docker image contains OLD index.html"
echo "Solution: Rebuild image with latest files"
echo ""

# Configuration
SERVER="root@95.163.227.26"
SSH_KEY="$HOME/.ssh/id_housler"
REMOTE_DIR="/root/ai-calendar-assistant"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${RED}❌ SSH key not found: $SSH_KEY${NC}"
    exit 1
fi

# Check local app directory
if [ ! -d "app" ]; then
    echo -e "${RED}❌ app/ directory not found!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pre-flight checks passed${NC}"
echo ""

# Step 1: Show current container file info
echo -e "${BLUE}[1/7] Checking current container file...${NC}"
CURRENT_SIZE=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %s /app/app/static/index.html 2>/dev/null || echo 'unknown'")
CURRENT_DATE=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %y /app/app/static/index.html 2>/dev/null | cut -d' ' -f1 || echo 'unknown'")
echo "  Current container: $CURRENT_SIZE bytes (modified: $CURRENT_DATE)"

LOCAL_SIZE=$(stat -f "%z" app/static/index.html 2>/dev/null || stat -c "%s" app/static/index.html)
echo "  Local file: $LOCAL_SIZE bytes"

if [ "$CURRENT_SIZE" = "$LOCAL_SIZE" ]; then
    echo -e "${YELLOW}  ⚠️  Sizes match, but content might differ${NC}"
else
    echo -e "${YELLOW}  ⚠️  SIZES DON'T MATCH - rebuilding needed!${NC}"
fi
echo ""

# Step 2: Sync app directory to server
echo -e "${BLUE}[2/7] Syncing app/ directory to server...${NC}"
rsync -av --progress -e "ssh -i $SSH_KEY" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    app/ ${SERVER}:${REMOTE_DIR}/app/
echo -e "${GREEN}✅ Files synced${NC}"
echo ""

# Step 3: Stop container
echo -e "${BLUE}[3/7] Stopping container...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker-compose stop calendar-assistant"
echo -e "${GREEN}✅ Container stopped${NC}"
echo ""

# Step 4: Remove old image
echo -e "${BLUE}[4/7] Removing old Docker image...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "docker images | grep calendar-assistant | awk '{print \$3}' | xargs -r docker rmi -f 2>/dev/null || true"
echo -e "${GREEN}✅ Old image removed${NC}"
echo ""

# Step 5: Build new image with --no-cache
echo -e "${BLUE}[5/7] Building new Docker image (--no-cache)...${NC}"
echo -e "${YELLOW}This may take 2-3 minutes...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker-compose build --no-cache calendar-assistant"
echo -e "${GREEN}✅ New image built${NC}"
echo ""

# Step 6: Start container
echo -e "${BLUE}[6/7] Starting container...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker-compose up -d calendar-assistant"
sleep 10
echo -e "${GREEN}✅ Container started${NC}"
echo ""

# Step 7: Verify new file in container
echo -e "${BLUE}[7/7] Verifying new file in container...${NC}"
NEW_SIZE=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %s /app/app/static/index.html")
NEW_DATE=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %y /app/app/static/index.html | cut -d' ' -f1")
NEW_TIME=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %y /app/app/static/index.html | cut -d' ' -f2 | cut -d. -f1")

echo "  Container file: $NEW_SIZE bytes"
echo "  Modified: $NEW_DATE $NEW_TIME"

# Check if file was updated recently (within last 5 minutes)
CURRENT_TIMESTAMP=$(date +%s)
FILE_TIMESTAMP=$(ssh -i "$SSH_KEY" "$SERVER" "docker exec ai-calendar-assistant stat -c %Y /app/app/static/index.html")
TIME_DIFF=$((CURRENT_TIMESTAMP - FILE_TIMESTAMP))

if [ $TIME_DIFF -lt 300 ]; then
    echo -e "${GREEN}✅ File was updated within last 5 minutes!${NC}"
else
    echo -e "${YELLOW}⚠️  File modification time seems old: $TIME_DIFF seconds ago${NC}"
fi

# Test web app response
WEB_RESPONSE=$(ssh -i "$SSH_KEY" "$SERVER" "curl -s http://localhost:8000/ | head -10")
if echo "$WEB_RESPONSE" | grep -q "Календарь и дела"; then
    echo -e "${GREEN}✅ Web app responding correctly${NC}"
else
    echo -e "${RED}❌ Web app not responding as expected${NC}"
fi
echo ""

echo "=================================================="
echo -e "${GREEN}✅ DOCKER IMAGE REBUILD COMPLETE!${NC}"
echo "=================================================="
echo ""
echo "🌐 Web App: https://calendar.housler.ru"
echo ""
echo "📱 Clear browser cache:"
echo "   Mac: Cmd + Shift + R"
echo "   Windows: Ctrl + Shift + R"
echo ""
echo "🔍 Verify:"
echo "   1. Date shows: $(date '+%d %B %Y')"
echo "   2. TODO tab works"
echo "   3. Calendar shows correct range"
echo ""
echo "📊 Before/After:"
echo "   Before: $CURRENT_SIZE bytes ($CURRENT_DATE)"
echo "   After:  $NEW_SIZE bytes ($NEW_DATE $NEW_TIME)"
echo ""
