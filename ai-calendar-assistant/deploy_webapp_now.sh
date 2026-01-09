#!/bin/bash

set -e

echo "=================================================="
echo "🚀 Web App Deployment to calendar.housler.ru"
echo "=================================================="
echo ""

# Configuration
SERVER="root@95.163.227.26"
SSH_KEY="$HOME/.ssh/id_housler"
REMOTE_DIR="/root/ai-calendar-assistant"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    exit 1
fi

# Check if local index.html exists
if [ ! -f "app/static/index.html" ]; then
    echo "❌ Local index.html not found!"
    exit 1
fi

echo -e "${GREEN}✅ Local index.html found ($(stat -f "%z" app/static/index.html 2>/dev/null || stat -c "%s" app/static/index.html) bytes)${NC}"
echo ""

# Step 1: Backup old version on server
echo -e "${BLUE}[1/5] Creating backup of old version...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && cp app/static/index.html app/static/index.html.backup-\$(date +%Y%m%d-%H%M%S)"
echo -e "${GREEN}✅ Backup created${NC}"
echo ""

# Step 2: Copy new index.html to server
echo -e "${BLUE}[2/5] Uploading new index.html...${NC}"
scp -i "$SSH_KEY" app/static/index.html ${SERVER}:${REMOTE_DIR}/app/static/index.html
echo -e "${GREEN}✅ Uploaded${NC}"
echo ""

# Step 3: Rebuild Docker container to include new file
echo -e "${BLUE}[3/5] Rebuilding Docker container...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker-compose build calendar-assistant"
echo -e "${GREEN}✅ Container rebuilt${NC}"
echo ""

# Step 4: Restart container
echo -e "${BLUE}[4/5] Restarting container...${NC}"
ssh -i "$SSH_KEY" "$SERVER" "cd $REMOTE_DIR && docker-compose up -d calendar-assistant"
sleep 5
echo -e "${GREEN}✅ Container restarted${NC}"
echo ""

# Step 5: Verify deployment
echo -e "${BLUE}[5/5] Verifying deployment...${NC}"
TIMESTAMP=$(date +%s)
RESPONSE=$(ssh -i "$SSH_KEY" "$SERVER" "curl -s http://localhost:8000/ | head -20")

if echo "$RESPONSE" | grep -q "Календарь и дела"; then
    echo -e "${GREEN}✅ Web app is responding correctly${NC}"
else
    echo -e "${YELLOW}⚠️  Unexpected response from server${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo "=================================================="
echo ""
echo "🌐 Web app URL: https://calendar.housler.ru"
echo ""
echo "📱 Clear browser cache:"
echo "   • Chrome/Firefox: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)"
echo "   • Or hard refresh: Ctrl+F5 (Windows)"
echo ""
echo "🔍 Verify:"
echo "   ✅ Date shows: $(date '+%d %B %Y')"
echo "   ✅ TODO tab works"
echo "   ✅ Calendar shows correct date range"
echo ""
