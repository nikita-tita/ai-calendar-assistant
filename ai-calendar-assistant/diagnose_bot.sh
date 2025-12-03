#!/bin/bash
# ================================================================
# AI Calendar Assistant - Diagnostic Script
# ================================================================
# This script diagnoses issues with the Telegram bot
# Usage:
#   Local: ./diagnose_bot.sh
#   Remote: ssh root@91.229.8.221 'bash -s' < diagnose_bot.sh
# ================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================"
echo "🔍 AI Calendar Assistant - Diagnostics"
echo "================================================"
echo ""

# Function to check status
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1${NC}"
        return 1
    fi
}

# ================================
# 1. Environment Check
# ================================
echo -e "${BLUE}[1/8] Checking Environment...${NC}"

# Check if running in Docker or directly
if [ -f /.dockerenv ]; then
    echo "  🐳 Running inside Docker container"
    PROJECT_DIR="/app"
else
    echo "  💻 Running on host machine"
    if [ -d "/root/ai-calendar-assistant/ai-calendar-assistant" ]; then
        PROJECT_DIR="/root/ai-calendar-assistant/ai-calendar-assistant"
    elif [ -d "/root/ai-calendar-assistant" ]; then
        PROJECT_DIR="/root/ai-calendar-assistant"
    elif [ -d "./ai-calendar-assistant" ]; then
        PROJECT_DIR="./ai-calendar-assistant"
    else
        PROJECT_DIR="."
    fi
fi

echo "  📁 Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || exit 1

# ================================
# 2. Check .env File
# ================================
echo ""
echo -e "${BLUE}[2/8] Checking .env Configuration...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "  Please create .env file from .env.example"
    exit 1
fi

echo -e "${GREEN}✅ .env file exists${NC}"

# Check critical variables
REQUIRED_VARS=(
    "TELEGRAM_BOT_TOKEN"
    "YANDEX_GPT_API_KEY"
    "YANDEX_GPT_FOLDER_ID"
    "SECRET_KEY"
    "RADICALE_BOT_PASSWORD"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
    if ! grep -q "^${var}=" .env || grep -q "^${var}=$" .env || grep -q "^${var}=your_" .env; then
        MISSING_VARS+=("$var")
        echo -e "${RED}  ❌ $var is missing or not set${NC}"
    else
        VALUE=$(grep "^${var}=" .env | cut -d'=' -f2)
        if [ ${#VALUE} -lt 10 ]; then
            echo -e "${YELLOW}  ⚠️  $var is too short (${#VALUE} chars)${NC}"
        else
            echo -e "${GREEN}  ✅ $var is set (${#VALUE} chars)${NC}"
        fi
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required variables:${NC}"
    printf '  %s\n' "${MISSING_VARS[@]}"
    exit 1
fi

# Check APP_ENV
APP_ENV=$(grep "^APP_ENV=" .env | cut -d'=' -f2)
echo ""
echo "  Environment: $APP_ENV"
if [ "$APP_ENV" = "production" ]; then
    echo -e "${YELLOW}  ⚠️  Running in PRODUCTION mode - stricter validation${NC}"
else
    echo -e "${GREEN}  ✅ Running in DEVELOPMENT mode - relaxed validation${NC}"
fi

# ================================
# 3. Check Docker Containers
# ================================
echo ""
echo -e "${BLUE}[3/8] Checking Docker Containers...${NC}"

if command -v docker &> /dev/null; then
    echo "  🐳 Docker is installed"

    # Check if containers are running
    CONTAINERS=(
        "ai-calendar-assistant"
        "telegram-bot-polling"
        "radicale-calendar"
        "calendar-redis"
    )

    for container in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            STATUS=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "not found")
            HEALTH=$(docker inspect -f '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "no healthcheck")

            if [ "$STATUS" = "running" ]; then
                echo -e "${GREEN}  ✅ $container: running ($HEALTH)${NC}"
            else
                echo -e "${RED}  ❌ $container: $STATUS${NC}"
            fi
        else
            echo -e "${YELLOW}  ⚠️  $container: not found${NC}"
        fi
    done
else
    echo -e "${YELLOW}  ⚠️  Docker not installed or not accessible${NC}"
fi

# ================================
# 4. Check Network Connectivity
# ================================
echo ""
echo -e "${BLUE}[4/8] Checking Network Connectivity...${NC}"

# Check Telegram API
if command -v curl &> /dev/null; then
    BOT_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d'=' -f2)

    echo "  🌐 Testing Telegram Bot API..."
    TELEGRAM_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "https://api.telegram.org/bot${BOT_TOKEN}/getMe")

    if [ "$TELEGRAM_RESPONSE" = "200" ]; then
        echo -e "${GREEN}  ✅ Telegram API is accessible${NC}"
        BOT_INFO=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
        echo "     Bot username: @$BOT_INFO"
    else
        echo -e "${RED}  ❌ Telegram API returned: $TELEGRAM_RESPONSE${NC}"
        echo "     Check your TELEGRAM_BOT_TOKEN"
    fi

    # Check Yandex GPT API
    echo ""
    echo "  🌐 Testing Yandex GPT API..."
    YANDEX_KEY=$(grep "^YANDEX_GPT_API_KEY=" .env | cut -d'=' -f2)
    YANDEX_FOLDER=$(grep "^YANDEX_GPT_FOLDER_ID=" .env | cut -d'=' -f2)

    YANDEX_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Api-Key ${YANDEX_KEY}" \
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion")

    if [ "$YANDEX_RESPONSE" = "400" ] || [ "$YANDEX_RESPONSE" = "200" ]; then
        echo -e "${GREEN}  ✅ Yandex GPT API is accessible${NC}"
    else
        echo -e "${RED}  ❌ Yandex GPT API returned: $YANDEX_RESPONSE${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️  curl not installed - skipping network tests${NC}"
fi

# ================================
# 5. Check Application Health
# ================================
echo ""
echo -e "${BLUE}[5/8] Checking Application Health...${NC}"

if command -v curl &> /dev/null; then
    # Try to reach health endpoint
    for port in 8000 8001; do
        HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/health" 2>/dev/null)
        if [ "$HEALTH_RESPONSE" = "200" ]; then
            echo -e "${GREEN}  ✅ Application is healthy on port $port${NC}"
            HEALTH_DATA=$(curl -s "http://localhost:${port}/health")
            echo "     $HEALTH_DATA"
            break
        fi
    done

    if [ "$HEALTH_RESPONSE" != "200" ]; then
        echo -e "${RED}  ❌ Application health check failed${NC}"
        echo "     Try: docker-compose logs calendar-assistant"
    fi
else
    echo -e "${YELLOW}  ⚠️  curl not installed - skipping health check${NC}"
fi

# ================================
# 6. Check Recent Logs
# ================================
echo ""
echo -e "${BLUE}[6/8] Checking Recent Logs...${NC}"

if docker ps -q -f name=telegram-bot-polling &> /dev/null; then
    echo "  📜 Last 15 lines from telegram-bot-polling:"
    echo "  ─────────────────────────────────────────────"
    docker logs telegram-bot-polling --tail 15 2>&1 | sed 's/^/     /'
    echo "  ─────────────────────────────────────────────"
elif docker ps -q -f name=ai-calendar-assistant &> /dev/null; then
    echo "  📜 Last 15 lines from ai-calendar-assistant:"
    echo "  ─────────────────────────────────────────────"
    docker logs ai-calendar-assistant --tail 15 2>&1 | sed 's/^/     /'
    echo "  ─────────────────────────────────────────────"
elif [ -d "logs" ]; then
    LATEST_LOG=$(find logs -name "*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2)
    if [ -n "$LATEST_LOG" ]; then
        echo "  📜 Last 15 lines from $LATEST_LOG:"
        echo "  ─────────────────────────────────────────────"
        tail -15 "$LATEST_LOG" | sed 's/^/     /'
        echo "  ─────────────────────────────────────────────"
    fi
else
    echo -e "${YELLOW}  ⚠️  No logs found${NC}"
fi

# ================================
# 7. Check Radicale Service
# ================================
echo ""
echo -e "${BLUE}[7/8] Checking Radicale CalDAV Service...${NC}"

if docker ps -q -f name=radicale-calendar &> /dev/null; then
    RADICALE_STATUS=$(docker inspect -f '{{.State.Status}}' radicale-calendar)
    if [ "$RADICALE_STATUS" = "running" ]; then
        echo -e "${GREEN}  ✅ Radicale is running${NC}"

        # Try to reach Radicale
        if command -v curl &> /dev/null; then
            RADICALE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:5232" 2>/dev/null)
            if [ "$RADICALE_RESPONSE" = "200" ] || [ "$RADICALE_RESPONSE" = "401" ]; then
                echo -e "${GREEN}  ✅ Radicale is accessible${NC}"
            else
                echo -e "${YELLOW}  ⚠️  Radicale returned: $RADICALE_RESPONSE${NC}"
            fi
        fi
    else
        echo -e "${RED}  ❌ Radicale status: $RADICALE_STATUS${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️  Radicale container not found${NC}"
fi

# ================================
# 8. System Resources
# ================================
echo ""
echo -e "${BLUE}[8/8] Checking System Resources...${NC}"

# Disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
echo "  💾 Disk usage: ${DISK_USAGE}%"
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}     ⚠️  Disk space is critically low!${NC}"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}     ⚠️  Disk space is running low${NC}"
fi

# Memory usage
if command -v free &> /dev/null; then
    MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3*100/$2}')
    echo "  🧠 Memory usage: ${MEM_USAGE}%"
    if [ "$MEM_USAGE" -gt 90 ]; then
        echo -e "${RED}     ⚠️  Memory is critically high!${NC}"
    fi
fi

# Docker disk usage
if command -v docker &> /dev/null; then
    echo ""
    echo "  🐳 Docker disk usage:"
    docker system df | sed 's/^/     /'
fi

# ================================
# Summary and Recommendations
# ================================
echo ""
echo "================================================"
echo "📋 Summary"
echo "================================================"

# Count issues
ISSUES=0

# Check if bot token is valid
if [ "$TELEGRAM_RESPONSE" != "200" ]; then
    ISSUES=$((ISSUES + 1))
    echo -e "${RED}❌ Issue $ISSUES: Invalid Telegram bot token${NC}"
    echo "   Fix: Update TELEGRAM_BOT_TOKEN in .env"
fi

# Check if containers are running
if ! docker ps -q -f name=telegram-bot-polling &> /dev/null && \
   ! docker ps -q -f name=ai-calendar-assistant &> /dev/null; then
    ISSUES=$((ISSUES + 1))
    echo -e "${RED}❌ Issue $ISSUES: No bot containers running${NC}"
    echo "   Fix: Run 'docker-compose up -d' or 'docker-compose restart'"
fi

# Check if health endpoint is down
if [ "$HEALTH_RESPONSE" != "200" ]; then
    ISSUES=$((ISSUES + 1))
    echo -e "${YELLOW}⚠️  Issue $ISSUES: Application health check failed${NC}"
    echo "   Check logs with: docker-compose logs -f"
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ No critical issues detected!${NC}"
    echo ""
    echo "If the bot is still not responding, try:"
    echo "  1. Restart: docker-compose restart"
    echo "  2. Check logs: docker-compose logs -f telegram-bot-polling"
    echo "  3. Test manually: python run_polling.py"
else
    echo ""
    echo "Total issues found: $ISSUES"
    echo ""
    echo "🔧 Quick fixes:"
    echo "  - Restart containers: docker-compose restart"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Rebuild: docker-compose down && docker-compose build --no-cache && docker-compose up -d"
fi

echo ""
echo "================================================"
echo "For detailed logs, run:"
echo "  docker-compose logs -f telegram-bot-polling"
echo "================================================"
