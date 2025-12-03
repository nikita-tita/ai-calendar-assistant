#!/bin/bash
#
# Radicale Calendar Data Restore Script
# Restores calendar events from backup to Docker volume
#
# Usage: ./scripts/restore-radicale.sh [backup_file]
#        ./scripts/restore-radicale.sh --list        # List available backups
#        ./scripts/restore-radicale.sh --latest      # Restore from latest backup
#
# CAUTION: This will REPLACE all current calendar data!

set -euo pipefail

# Configuration
BACKUP_DIR="/root/backups/radicale"
VOLUME_NAME="calendar-radicale-data"
COMPOSE_FILE="/root/ai-calendar-assistant/ai-calendar-assistant/docker-compose.secure.yml"
WORK_DIR="/root/ai-calendar-assistant/ai-calendar-assistant"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "Radicale Restore Script"
    echo ""
    echo "Usage:"
    echo "  ./restore-radicale.sh [backup_file]   Restore from specific backup"
    echo "  ./restore-radicale.sh --list          List available backups"
    echo "  ./restore-radicale.sh --latest        Restore from latest backup"
    echo ""
    echo "Available backups:"
    list_backups
}

list_backups() {
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "No backups found (directory does not exist)"
        return
    fi

    echo ""
    echo "Available backups in $BACKUP_DIR:"
    echo "-----------------------------------"

    for f in $(ls -t "$BACKUP_DIR"/radicale_*.tar.gz 2>/dev/null); do
        SIZE=$(du -h "$f" | cut -f1)
        NAME=$(basename "$f")

        # Read metadata if exists
        if [ -f "$f.meta" ]; then
            EVENTS=$(grep "events=" "$f.meta" 2>/dev/null | cut -d= -f2 || echo "?")
            echo "  $NAME ($SIZE, $EVENTS events)"
        else
            echo "  $NAME ($SIZE)"
        fi
    done

    echo ""
}

get_latest_backup() {
    ls -t "$BACKUP_DIR"/radicale_*.tar.gz 2>/dev/null | head -1
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

case "$1" in
    --list)
        list_backups
        exit 0
        ;;
    --latest)
        BACKUP_FILE=$(get_latest_backup)
        if [ -z "$BACKUP_FILE" ]; then
            echo -e "${RED}ERROR: No backups found!${NC}"
            exit 1
        fi
        echo "Using latest backup: $BACKUP_FILE"
        ;;
    --help|-h)
        show_help
        exit 0
        ;;
    *)
        if [ -f "$1" ]; then
            BACKUP_FILE="$1"
        elif [ -f "$BACKUP_DIR/$1" ]; then
            BACKUP_FILE="$BACKUP_DIR/$1"
        else
            echo -e "${RED}ERROR: Backup file not found: $1${NC}"
            list_backups
            exit 1
        fi
        ;;
esac

echo ""
echo -e "${YELLOW}WARNING: This will REPLACE all current calendar data!${NC}"
echo ""
echo "Backup to restore: $BACKUP_FILE"
echo ""

# Confirm restore
read -p "Are you sure you want to continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "=== Starting Restore ==="

# Step 1: Backup current data first
echo "[1/4] Creating safety backup of current data..."
DATE=$(date +%Y%m%d_%H%M%S)
SAFETY_BACKUP="$BACKUP_DIR/radicale_pre_restore_${DATE}.tar.gz"

docker run --rm \
    -v "${VOLUME_NAME}:/data:ro" \
    -v "$BACKUP_DIR:/backup" \
    alpine tar czf "/backup/radicale_pre_restore_${DATE}.tar.gz" -C /data . 2>/dev/null || true

if [ -f "$SAFETY_BACKUP" ]; then
    echo "  Safety backup: $SAFETY_BACKUP"
fi

# Step 2: Stop Radicale
echo "[2/4] Stopping Radicale..."
cd "$WORK_DIR"
docker-compose -f "$COMPOSE_FILE" stop radicale 2>/dev/null || true

# Step 3: Restore data
echo "[3/4] Restoring data..."
docker run --rm \
    -v "${VOLUME_NAME}:/data" \
    -v "$(dirname "$BACKUP_FILE"):/backup:ro" \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/$(basename "$BACKUP_FILE") -C /data"

# Step 4: Start Radicale
echo "[4/4] Starting Radicale..."
docker-compose -f "$COMPOSE_FILE" up -d radicale

# Verify
sleep 3
EVENT_COUNT=$(docker run --rm -v "${VOLUME_NAME}:/data:ro" alpine find /data -name "*.ics" -type f 2>/dev/null | wc -l || echo "0")

echo ""
echo -e "${GREEN}=== Restore Complete ===${NC}"
echo "Events restored: $EVENT_COUNT"
echo ""

# Check container status
if docker ps | grep -q radicale; then
    echo -e "${GREEN}Radicale container is running${NC}"
else
    echo -e "${RED}WARNING: Radicale container is not running!${NC}"
    echo "Check logs: docker logs radicale"
fi
