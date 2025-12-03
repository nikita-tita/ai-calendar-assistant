#!/bin/bash
#
# AI Calendar Assistant - Restore from Backup Script
#
# This script restores data from encrypted backups
#
# Usage: ./restore-from-backup.sh <backup_file>
# Example: ./restore-from-backup.sh /root/backups/calendar-assistant/20251028_030000.tar.gz.gpg

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "❌ Error: No backup file specified"
    echo ""
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh /root/backups/calendar-assistant/*.tar.gz* 2>/dev/null || echo "  No backups found"
    exit 1
fi

BACKUP_FILE="$1"
TEMP_DIR="/tmp/calendar-restore-$$"
DOCKER_COMPOSE_DIR="/root/ai-calendar-assistant"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=================================================="
echo "AI Calendar Restore Started: $(date)"
echo "=================================================="
echo "Backup file: $BACKUP_FILE"
echo ""

# Confirmation
read -p "⚠️  This will REPLACE all current data. Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Create temp directory
mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

echo "[1/6] Extracting backup..."

# Decrypt if encrypted
if [[ "$BACKUP_FILE" == *.gpg ]]; then
    echo "Decrypting backup..."
    gpg --decrypt "$BACKUP_FILE" > backup.tar.gz
    tar xzf backup.tar.gz
else
    tar xzf "$BACKUP_FILE"
fi

# Find the backup directory
BACKUP_DIR=$(find . -maxdepth 1 -type d ! -name '.' | head -1)
cd "$BACKUP_DIR"

echo "✅ Backup extracted"
echo ""
cat manifest.txt
echo ""

echo "[2/6] Stopping containers..."
cd "$DOCKER_COMPOSE_DIR"
docker-compose down
echo "✅ Containers stopped"

echo "[3/6] Restoring Radicale calendar data..."
if [ -f "$TEMP_DIR/$BACKUP_DIR/radicale_data.tar.gz" ]; then
    # Remove old volume data
    docker volume rm calendar-assistant_radicale_data 2>/dev/null || true

    # Create temporary container to restore data
    docker run --rm \
        -v calendar-assistant_radicale_data:/data \
        -v "$TEMP_DIR/$BACKUP_DIR":/backup \
        alpine sh -c "cd / && tar xzf /backup/radicale_data.tar.gz"

    echo "✅ Radicale data restored"
else
    echo "⚠️  radicale_data.tar.gz not found in backup"
fi

echo "[4/6] Restoring bot data..."
if [ -f "$TEMP_DIR/$BACKUP_DIR/bot_data.tar.gz" ]; then
    # Remove old volume data
    docker volume rm calendar-assistant_calendar_data 2>/dev/null || true

    # Create temporary container to restore data
    docker run --rm \
        -v calendar-assistant_calendar_data:/var/lib/calendar-bot \
        -v "$TEMP_DIR/$BACKUP_DIR":/backup \
        alpine sh -c "cd / && tar xzf /backup/bot_data.tar.gz"

    echo "✅ Bot data restored"
else
    echo "⚠️  bot_data.tar.gz not found in backup"
fi

echo "[5/6] Restoring configuration files..."
if [ -f "$TEMP_DIR/$BACKUP_DIR/.env.backup" ]; then
    cp "$TEMP_DIR/$BACKUP_DIR/.env.backup" "$DOCKER_COMPOSE_DIR/.env"
    echo "✅ .env restored"
fi

if [ -f "$TEMP_DIR/$BACKUP_DIR/docker-compose.yml.backup" ]; then
    cp "$TEMP_DIR/$BACKUP_DIR/docker-compose.yml.backup" "$DOCKER_COMPOSE_DIR/docker-compose.yml"
    echo "✅ docker-compose.yml restored"
fi

echo "[6/6] Starting containers..."
cd "$DOCKER_COMPOSE_DIR"
docker-compose up -d
echo "✅ Containers started"

# Cleanup
echo ""
echo "Cleaning up temporary files..."
rm -rf "$TEMP_DIR"
echo "✅ Cleanup complete"

echo ""
echo "=================================================="
echo "Restore Completed Successfully: $(date)"
echo "=================================================="
echo ""
echo "Services status:"
docker-compose ps
echo ""
echo "Check logs with: docker-compose logs -f"

exit 0
