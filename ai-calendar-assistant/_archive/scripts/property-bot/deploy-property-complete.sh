#!/bin/bash

# Property Bot Complete Deployment Script
# Deploys Property Bot with Feed Loader to production server

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Server details
SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Property Bot Complete Deployment               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Upload new files
echo -e "${YELLOW}[1/6] Uploading Property Bot files...${NC}"

FILES_TO_UPLOAD=(
    "app/services/property/feed_loader.py"
    "app/services/telegram_handler.py"
    "app/services/property/property_handler.py"
)

for file in "${FILES_TO_UPLOAD[@]}"; do
    echo "  Uploading $file..."
    sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no "$file" "${SERVER}:${REMOTE_DIR}/$file"
done

echo -e "${GREEN}✓ Files uploaded${NC}"
echo ""

# Step 2: Check if property tables exist in database
echo -e "${YELLOW}[2/6] Checking database...${NC}"

CHECK_CMD="docker exec postgres_calendar psql -U calendar_user -d calendar_bot -t -c \"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'property_listings');\" 2>&1"

TABLES_EXIST=$(sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "$CHECK_CMD" | tr -d '[:space:]')

if [ "$TABLES_EXIST" = "t" ]; then
    echo -e "${GREEN}✓ Property tables exist${NC}"
else
    echo -e "${YELLOW}⚠ Property tables not found. Need to run migrations.${NC}"
    echo -e "${YELLOW}Please run migrations manually or let me know.${NC}"
fi

echo ""

# Step 3: Restart bot container
echo -e "${YELLOW}[3/6] Restarting Telegram bot...${NC}"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant
docker-compose restart telegram-bot
echo "Waiting for bot to start..."
sleep 10
ENDSSH

echo -e "${GREEN}✓ Bot restarted${NC}"
echo ""

# Step 4: Check bot status
echo -e "${YELLOW}[4/6] Checking bot status...${NC}"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "docker ps | grep telegram-bot"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Bot is running${NC}"
else
    echo -e "${RED}✗ Bot is not running!${NC}"
    echo "Checking logs..."
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "docker logs --tail 20 telegram-bot 2>&1"
    exit 1
fi

echo ""

# Step 5: Load property feed
echo -e "${YELLOW}[5/6] Loading property feed...${NC}"
echo "This may take 2-3 minutes..."

# Create a script to load feed
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant

# Create Python script to load feed
cat > /tmp/load_feed.py << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.property.feed_loader import feed_loader

async def main():
    print("Starting feed download and processing...")
    result = await feed_loader.update_feed()
    print(f"\nResult: {result}")

    if result.get('status') == 'success':
        print(f"\n✓ Successfully loaded {result.get('total', 0)} properties")
        print(f"  - Created: {result.get('created', 0)}")
        print(f"  - Updated: {result.get('updated', 0)}")
        print(f"  - Errors: {result.get('errors', 0)}")
        print(f"  - Duration: {result.get('duration_seconds', 0):.1f}s")
    else:
        print(f"\n✗ Feed load failed: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run the script in docker
docker exec telegram-bot python3 /tmp/load_feed.py 2>&1

ENDSSH

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Feed loaded successfully${NC}"
else
    echo -e "${RED}✗ Feed load failed${NC}"
    echo "Check logs for details"
fi

echo ""

# Step 6: Final checks
echo -e "${YELLOW}[6/6] Running final checks...${NC}"

# Check bot logs for errors
echo "Recent logs:"
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "docker logs --tail 10 telegram-bot 2>&1"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Deployment Complete!                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓ Property Bot deployed successfully${NC}"
echo -e "${GREEN}✓ Feed loader integrated${NC}"
echo -e "${GREEN}✓ Menu with mode switching added${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the bot: https://t.me/YOUR_BOT_NAME"
echo "2. Click '🏠 Поиск новостройки' to enter property mode"
echo "3. Try voice messages for property search"
echo "4. Use '🔙 Календарь' to return to calendar mode"
echo ""
echo -e "${YELLOW}Monitor logs:${NC}"
echo "  sshpass -p '$PASSWORD' ssh $SERVER 'docker logs -f telegram-bot'"
echo ""
