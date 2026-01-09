#!/bin/bash

set -e

echo "=================================================="
echo "🔍 PRODUCTION ENVIRONMENT DIAGNOSTICS"
echo "=================================================="
echo ""

# Configuration
SERVER="root@95.163.227.26"
SSH_KEY="$HOME/.ssh/id_housler"

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

echo -e "${GREEN}✅ SSH key found${NC}"
echo ""

# ================================================
# 1. Container Status
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}1. DOCKER CONTAINERS STATUS${NC}"
echo -e "${BLUE}========================================${NC}"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
cd /root/ai-calendar-assistant
echo ""
echo "Running containers:"
docker-compose ps --format 'table {{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}'
echo ""
EOF

# ================================================
# 2. Index.html Location Check
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}2. INDEX.HTML FILE LOCATIONS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Checking index.html in different locations:"
echo ""

# Host file
echo -e "${YELLOW}[A] Host filesystem:${NC}"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
if [ -f "/root/ai-calendar-assistant/app/static/index.html" ]; then
    STAT=$(stat -c "Size: %s bytes | Modified: %y" /root/ai-calendar-assistant/app/static/index.html)
    echo "  ✅ /root/ai-calendar-assistant/app/static/index.html"
    echo "     $STAT"
    LINES=$(wc -l < /root/ai-calendar-assistant/app/static/index.html)
    echo "     Lines: $LINES"
else
    echo "  ❌ File not found on host"
fi
EOF
echo ""

# Container file
echo -e "${YELLOW}[B] Inside calendar-assistant container:${NC}"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
if docker exec ai-calendar-assistant test -f /app/app/static/index.html; then
    STAT=$(docker exec ai-calendar-assistant stat -c "Size: %s bytes | Modified: %y" /app/app/static/index.html)
    echo "  ✅ /app/app/static/index.html"
    echo "     $STAT"
    LINES=$(docker exec ai-calendar-assistant wc -l < /app/app/static/index.html)
    echo "     Lines: $LINES"
else
    echo "  ❌ File not found in container"
fi
EOF
echo ""

# Check if they match
echo -e "${YELLOW}[C] Comparing host vs container:${NC}"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
HOST_SIZE=$(stat -c %s /root/ai-calendar-assistant/app/static/index.html 2>/dev/null || echo "0")
CONTAINER_SIZE=$(docker exec ai-calendar-assistant stat -c %s /app/app/static/index.html 2>/dev/null || echo "0")

if [ "$HOST_SIZE" = "$CONTAINER_SIZE" ] && [ "$HOST_SIZE" != "0" ]; then
    echo "  ✅ Sizes match: $HOST_SIZE bytes"
else
    echo "  ❌ SIZES DON'T MATCH!"
    echo "     Host: $HOST_SIZE bytes"
    echo "     Container: $CONTAINER_SIZE bytes"
fi

HOST_LINES=$(wc -l < /root/ai-calendar-assistant/app/static/index.html 2>/dev/null || echo "0")
CONTAINER_LINES=$(docker exec ai-calendar-assistant wc -l < /app/app/static/index.html 2>/dev/null || echo "0")

if [ "$HOST_LINES" = "$CONTAINER_LINES" ] && [ "$HOST_LINES" != "0" ]; then
    echo "  ✅ Line counts match: $HOST_LINES lines"
else
    echo "  ❌ LINE COUNTS DON'T MATCH!"
    echo "     Host: $HOST_LINES lines"
    echo "     Container: $CONTAINER_LINES lines"
fi
EOF
echo ""

# ================================================
# 3. File Content Check
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}3. FILE CONTENT VERIFICATION${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Checking for key strings in container file:${NC}"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
# Check for TODO
TODO_COUNT=$(docker exec ai-calendar-assistant grep -c "TODO" /app/app/static/index.html 2>/dev/null || echo "0")
echo "  • 'TODO' occurrences: $TODO_COUNT"

# Check for new Date()
if docker exec ai-calendar-assistant grep -q "new Date()" /app/app/static/index.html; then
    echo "  ✅ Contains 'new Date()' (dynamic date)"
else
    echo "  ❌ Missing 'new Date()'"
fi

# Check for calendar text
if docker exec ai-calendar-assistant grep -q "Календарь и дела" /app/app/static/index.html; then
    echo "  ✅ Contains 'Календарь и дела'"
else
    echo "  ❌ Missing 'Календарь и дела'"
fi
EOF
echo ""

# ================================================
# 4. Docker Volumes
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}4. DOCKER VOLUME MOUNTS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Volume mounts for calendar-assistant container:"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
docker inspect ai-calendar-assistant --format '{{range .Mounts}}{{printf "  • %s → %s\n" .Source .Destination}}{{end}}'
echo ""
echo "Checking if app/static is mounted:"
if docker inspect ai-calendar-assistant --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' | grep -q "/app/app/static"; then
    echo "  ✅ app/static IS mounted as volume"
else
    echo "  ❌ app/static NOT mounted (uses image files)"
fi
EOF
echo ""

# ================================================
# 5. Nginx Configuration
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}5. NGINX CONFIGURATION${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
echo "Nginx sites enabled:"
ls -1 /etc/nginx/sites-enabled/ | while read site; do
    echo "  • $site"
done
echo ""

echo "calendar.housler.ru configuration:"
if [ -f "/etc/nginx/sites-enabled/calendar.housler.ru" ]; then
    echo "  ✅ Configuration exists"
    echo ""
    echo "  Root/proxy configuration:"
    grep -E "location /|proxy_pass|root|alias" /etc/nginx/sites-available/calendar.housler.ru | head -10 | sed 's/^/    /'
else
    echo "  ❌ Configuration not found"
fi
EOF
echo ""

# ================================================
# 6. Ports and Processes
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}6. PORTS AND PROCESSES${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
echo "Port 8000 (FastAPI):"
if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
    netstat -tlnp 2>/dev/null | grep ":8000" | sed 's/^/  /'
    echo "  ✅ Port 8000 is listening"
else
    echo "  ❌ Port 8000 not listening"
fi
echo ""

echo "Port 443 (HTTPS):"
if netstat -tlnp 2>/dev/null | grep -q ":443"; then
    echo "  ✅ Port 443 is listening (Nginx)"
else
    echo "  ❌ Port 443 not listening"
fi
EOF
echo ""

# ================================================
# 7. Docker Images
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}7. DOCKER IMAGES${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
echo "Calendar assistant images:"
docker images | grep calendar-assistant | sed 's/^/  /'
echo ""

echo "Image creation time:"
docker inspect ai-calendar-assistant --format 'Image ID: {{.Image}}' | sed 's/^/  /'
docker inspect ai-calendar-assistant --format 'Created: {{.Created}}' | sed 's/^/  /'
EOF
echo ""

# ================================================
# 8. Web Response Test
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}8. WEB APPLICATION RESPONSE${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Testing local response (http://localhost:8000):"
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
RESPONSE=$(curl -s http://localhost:8000/ | head -20)
if echo "$RESPONSE" | grep -q "Календарь и дела"; then
    echo "  ✅ Web app responding with correct HTML"
    echo "  ✅ Contains: 'Календарь и дела'"
else
    echo "  ❌ Unexpected response"
fi

# Check cache headers
echo ""
echo "Cache control headers:"
curl -s -D - http://localhost:8000/ -o /dev/null 2>/dev/null | grep -iE "cache-control|pragma|expires" | sed 's/^/  /'
EOF
echo ""

# ================================================
# 9. Recent Container Logs
# ================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}9. RECENT CONTAINER LOGS${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Last 10 log entries:"
ssh -i "$SSH_KEY" "$SERVER" "docker logs ai-calendar-assistant --tail 10 2>&1" | sed 's/^/  /'
echo ""

# ================================================
# SUMMARY
# ================================================
echo "=================================================="
echo -e "${GREEN}DIAGNOSTICS COMPLETE${NC}"
echo "=================================================="
echo ""
echo "Key Findings:"
echo ""

# Generate summary
ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
HOST_SIZE=$(stat -c %s /root/ai-calendar-assistant/app/static/index.html 2>/dev/null || echo "0")
CONTAINER_SIZE=$(docker exec ai-calendar-assistant stat -c %s /app/app/static/index.html 2>/dev/null || echo "0")

if [ "$HOST_SIZE" = "$CONTAINER_SIZE" ] && [ "$HOST_SIZE" != "0" ]; then
    echo "  ✅ Host and container files match"
else
    echo "  ⚠️  Host and container files DON'T match - REBUILD NEEDED"
fi

if docker inspect ai-calendar-assistant --format '{{range .Mounts}}{{.Destination}}{{"\n"}}{{end}}' | grep -q "/app/app/static"; then
    echo "  ✅ Static files mounted as volume"
else
    echo "  ⚠️  Static files from Docker image - changes require rebuild"
fi

if curl -s http://localhost:8000/ | grep -q "Календарь и дела"; then
    echo "  ✅ Web app serving HTML correctly"
else
    echo "  ❌ Web app not responding correctly"
fi
EOF

echo ""
echo "Next steps:"
echo "  1. If files don't match: Run ./rebuild_docker.sh"
echo "  2. If everything matches: Clear browser cache (Cmd+Shift+R)"
echo ""
