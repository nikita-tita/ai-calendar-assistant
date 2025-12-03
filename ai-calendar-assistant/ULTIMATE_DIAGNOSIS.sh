#!/bin/bash

# 🔬 ULTIMATE DIAGNOSIS
# Проверяет АБСОЛЮТНО ВСЁ на production сервере

VPS_IP="91.229.8.221"
VPS_USER="root"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔬 ULTIMATE PRODUCTION DIAGNOSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Это займёт 2-3 минуты. Проверяю ВСЁ..."
echo ""

ssh -o ConnectTimeout=15 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" << 'ENDSSH'

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣ DOCKER ECOSYSTEM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Running containers:"
docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "All containers (including stopped):"
docker ps -a --format "{{.Names}}\t{{.Status}}"
echo ""

echo "Docker images:"
docker images | grep -E "ai-calendar|telegram|calendar-assistant|REPOSITORY"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣ FILE SYSTEM ANALYSIS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "All HTML files on host:"
find /root -name "*.html" -type f 2>/dev/null | grep -v node_modules | head -20
echo ""

echo "Check app/static/index.html on HOST:"
if [ -f "/root/ai-calendar-assistant/app/static/index.html" ]; then
    HOST_SIZE=$(wc -c < /root/ai-calendar-assistant/app/static/index.html)
    echo "  Size: $HOST_SIZE bytes"
    if grep -q "let selectedDate = new Date()" /root/ai-calendar-assistant/app/static/index.html; then
        echo -e "  ${GREEN}✅ Contains: new Date()${NC}"
    else
        echo -e "  ${RED}❌ MISSING: new Date()${NC}"
    fi
    echo "  First 'selectedDate' line:"
    grep -m1 "selectedDate.*=" /root/ai-calendar-assistant/app/static/index.html | head -c 100
    echo ""
else
    echo -e "  ${RED}❌ FILE NOT FOUND!${NC}"
fi
echo ""

echo "Check docs/templates/webapp/ files:"
ls -lh /root/ai-calendar-assistant/docs/templates/webapp/*.html 2>/dev/null | awk '{print $9, $5}' || echo "  No template files"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣ FILES INSIDE CONTAINERS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for container in ai-calendar-assistant telegram-bot-polling telegram-bot calendar-assistant; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "Container: $container"
        echo "  Files in /app/:"
        docker exec "$container" find /app -name "*.html" -type f 2>/dev/null | head -10

        if docker exec "$container" test -f /app/app/static/index.html 2>/dev/null; then
            SIZE=$(docker exec "$container" cat /app/app/static/index.html 2>/dev/null | wc -c)
            echo "  /app/app/static/index.html: $SIZE bytes"
            if docker exec "$container" grep -q "let selectedDate = new Date()" /app/app/static/index.html 2>/dev/null; then
                echo -e "  ${GREEN}✅ Contains: new Date()${NC}"
            else
                echo -e "  ${RED}❌ MISSING: new Date()${NC}"
            fi
            echo "  First line with date:"
            docker exec "$container" grep -m1 "selectedDate" /app/app/static/index.html 2>/dev/null | head -c 100
        else
            echo "  ⚠️  File /app/app/static/index.html not found"
        fi
        echo ""
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣ NGINX CONFIGURATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Sites enabled:"
ls -la /etc/nginx/sites-enabled/
echo ""

if [ -f "/etc/nginx/sites-enabled/calendar.housler.ru" ]; then
    echo "calendar.housler.ru config:"
    cat /etc/nginx/sites-enabled/calendar.housler.ru | grep -A 15 "location /"
else
    echo -e "${RED}❌ calendar.housler.ru config NOT FOUND!${NC}"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣ PORTS AND PROCESSES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Port 5000:"
netstat -tlnp 2>/dev/null | grep :5000 || echo "  No process"
echo ""

echo "Port 8000:"
netstat -tlnp 2>/dev/null | grep :8000 || echo "  No process"
echo ""

echo "Port 80:"
netstat -tlnp 2>/dev/null | grep :80 | head -1 || echo "  No process"
echo ""

echo "Port 443:"
netstat -tlnp 2>/dev/null | grep :443 | head -1 || echo "  No process"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣ DIRECT HTTP TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Test localhost:8000/:"
curl -s http://localhost:8000/ 2>&1 | head -c 200
echo ""
echo "..."
echo ""

echo "Test localhost:8000/health:"
curl -s http://localhost:8000/health 2>&1
echo ""
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7️⃣ ENVIRONMENT VARIABLES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for container in ai-calendar-assistant telegram-bot-polling; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "Container: $container"
        echo "  TELEGRAM_WEBAPP_URL:"
        docker exec "$container" env 2>/dev/null | grep WEBAPP_URL || echo "  Not set"
        echo "  APP_ENV:"
        docker exec "$container" env 2>/dev/null | grep "^APP_ENV=" || echo "  Not set"
        echo ""
    fi
done

echo ".env file on host:"
if [ -f "/root/ai-calendar-assistant/.env" ]; then
    grep "TELEGRAM_WEBAPP_URL" /root/ai-calendar-assistant/.env || echo "  Not in .env"
else
    echo "  .env not found!"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8️⃣ DOCKER BUILD INFO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Image creation dates:"
docker images --format "{{.Repository}}:{{.Tag}}\t{{.CreatedAt}}" | grep -E "calendar|telegram"
echo ""

echo "Container creation times:"
docker ps -a --format "{{.Names}}\t{{.CreatedAt}}" | grep -E "calendar|telegram"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9️⃣ LOGS ANALYSIS (last 10 lines)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for container in ai-calendar-assistant telegram-bot-polling; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "Container: $container"
        docker logs "$container" --tail 10 2>&1 | sed 's/^/  /'
        echo ""
    fi
done

echo "Nginx access log (last 3):"
tail -3 /var/log/nginx/access.log 2>/dev/null | sed 's/^/  /' || echo "  No access.log"
echo ""

echo "Nginx error log (last 3):"
tail -3 /var/log/nginx/error.log 2>/dev/null | sed 's/^/  /' || echo "  No error.log"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔟 DOCKER COMPOSE FILES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Available docker-compose files:"
ls -lh /root/ai-calendar-assistant/docker-compose*.yml 2>/dev/null | awk '{print $9, $5}'
echo ""

echo "Active docker-compose.yml volumes:"
grep -A 5 "volumes:" /root/ai-calendar-assistant/docker-compose.yml 2>/dev/null | head -10
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Key findings:"
echo ""

# Check running containers
RUNNING=$(docker ps --format '{{.Names}}' | grep -E "calendar|telegram" | tr '\n' ', ')
echo "1. Running containers: ${RUNNING:-none}"

# Check file on host
if [ -f "/root/ai-calendar-assistant/app/static/index.html" ]; then
    HOST_SIZE=$(wc -c < /root/ai-calendar-assistant/app/static/index.html)
    if grep -q "new Date()" /root/ai-calendar-assistant/app/static/index.html; then
        echo -e "2. Host file: $HOST_SIZE bytes ${GREEN}✅ (has new Date)${NC}"
    else
        echo -e "2. Host file: $HOST_SIZE bytes ${RED}❌ (NO new Date!)${NC}"
    fi
else
    echo -e "2. Host file: ${RED}NOT FOUND${NC}"
fi

# Check container files
for container in ai-calendar-assistant telegram-bot-polling; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        if docker exec "$container" test -f /app/app/static/index.html 2>/dev/null; then
            SIZE=$(docker exec "$container" cat /app/app/static/index.html | wc -c)
            if docker exec "$container" grep -q "new Date()" /app/app/static/index.html 2>/dev/null; then
                echo -e "3. Container $container: $SIZE bytes ${GREEN}✅ (has new Date)${NC}"
            else
                echo -e "3. Container $container: $SIZE bytes ${RED}❌ (NO new Date!)${NC}"
            fi
        fi
    fi
done

# Check Nginx proxy
if grep -q "proxy_pass.*localhost:8000" /etc/nginx/sites-enabled/calendar.housler.ru 2>/dev/null; then
    echo -e "4. Nginx: ${GREEN}✅ Proxies to localhost:8000${NC}"
elif grep -q "proxy_pass.*localhost:5000" /etc/nginx/sites-enabled/calendar.housler.ru 2>/dev/null; then
    echo -e "4. Nginx: ${YELLOW}⚠️  Proxies to localhost:5000${NC}"
else
    echo -e "4. Nginx: ${RED}❌ Unknown config${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ DIAGNOSIS COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENDSSH

echo ""
echo "📊 ANALYSIS DONE!"
echo ""
echo "Сохраните этот вывод для анализа."
echo ""
