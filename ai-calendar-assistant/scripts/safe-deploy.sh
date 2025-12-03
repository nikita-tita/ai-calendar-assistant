#!/bin/bash
#
# Safe Deployment Script for AI Calendar Assistant
# Automatically creates backup before deployment
#
# Usage: ./scripts/safe-deploy.sh
#
# This script:
# 1. Creates backup of Radicale data
# 2. Pulls latest code from git
# 3. Rebuilds and restarts containers
# 4. Verifies deployment
#
# Run on the server, not locally!

set -euo pipefail

# Configuration
WORK_DIR="/root/ai-calendar-assistant/ai-calendar-assistant"
COMPOSE_FILE="docker-compose.secure.yml"
BACKUP_SCRIPT="$WORK_DIR/scripts/backup-radicale.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$WORK_DIR"

echo "=========================================="
echo "AI Calendar Assistant - Safe Deployment"
echo "=========================================="
echo ""

# Step 1: Pre-deployment backup
echo -e "${YELLOW}[1/5] Creating pre-deployment backup...${NC}"

if [ -f "$BACKUP_SCRIPT" ]; then
    chmod +x "$BACKUP_SCRIPT"
    "$BACKUP_SCRIPT"
else
    echo "Backup script not found, creating manual backup..."
    mkdir -p /root/backups/radicale
    DATE=$(date +%Y%m%d_%H%M%S)
    docker run --rm \
        -v "calendar-radicale-data:/data:ro" \
        -v "/root/backups/radicale:/backup" \
        alpine tar czf "/backup/radicale_predeploy_${DATE}.tar.gz" -C /data .
    echo "Backup created: /root/backups/radicale/radicale_predeploy_${DATE}.tar.gz"
fi

echo -e "${GREEN}Backup complete${NC}"
echo ""

# Step 2: Pull latest code
echo -e "${YELLOW}[2/5] Pulling latest code from git...${NC}"
git fetch origin main
git reset --hard origin/main
echo -e "${GREEN}Code updated${NC}"
echo ""

# Step 3: Rebuild bot container
echo -e "${YELLOW}[3/5] Rebuilding telegram-bot container...${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache telegram-bot
echo -e "${GREEN}Build complete${NC}"
echo ""

# Step 4: Restart containers
echo -e "${YELLOW}[4/5] Restarting containers...${NC}"
docker-compose -f "$COMPOSE_FILE" up -d telegram-bot
echo "Waiting for container to start..."
sleep 10
echo -e "${GREEN}Containers restarted${NC}"
echo ""

# Step 5: Verify deployment
echo -e "${YELLOW}[5/5] Verifying deployment...${NC}"

# Check container status
echo "Container status:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(telegram-bot|radicale|redis)"

echo ""

# Check health endpoint
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH=$(curl -s http://localhost:8000/health)
    echo -e "${GREEN}Health check passed:${NC} $HEALTH"
else
    echo -e "${RED}Health check failed!${NC}"
    echo "Check logs: docker logs telegram-bot --tail 50"
    exit 1
fi

echo ""

# Check Radicale connection
RADICALE_LOG=$(docker logs radicale --tail 5 2>&1)
if echo "$RADICALE_LOG" | grep -q "Successful login"; then
    echo -e "${GREEN}Radicale connection OK${NC}"
else
    echo -e "${YELLOW}Radicale status:${NC}"
    echo "$RADICALE_LOG" | tail -3
fi

echo ""
echo "=========================================="
echo -e "${GREEN}DEPLOYMENT SUCCESSFUL${NC}"
echo "=========================================="
echo ""
echo "Rollback if needed:"
echo "  ./scripts/restore-radicale.sh --latest"
echo ""
