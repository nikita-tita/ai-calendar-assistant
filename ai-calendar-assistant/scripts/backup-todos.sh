#!/bin/bash
#
# Todos Data Backup Script
# Creates backup of all todos stored in Docker container
#
# Usage: ./scripts/backup-todos.sh [--quiet]
# Cron:  0 3 * * * /root/ai-calendar-assistant/ai-calendar-assistant/scripts/backup-todos.sh --quiet
#
# Backups stored in: /root/backups/todos/
# Retention: 30 days

set -euo pipefail

# Configuration
BACKUP_DIR="/root/backups/todos"
CONTAINER_NAME="telegram-bot"
TODOS_PATH="/var/lib/calendar-bot/todos"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
QUIET=${1:-""}

log() {
    if [ "$QUIET" != "--quiet" ]; then
        echo "$1"
    fi
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "=== Todos Backup: $DATE ==="

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Container $CONTAINER_NAME not running!"
    exit 1
fi

# Count todos files before backup
FILE_COUNT=$(docker exec "$CONTAINER_NAME" find "$TODOS_PATH" -name "*.enc" -type f 2>/dev/null | wc -l || echo "0")
log "Todo files to backup: $FILE_COUNT"

if [ "$FILE_COUNT" -eq 0 ]; then
    log "WARNING: No todo files found!"
fi

# Create backup
BACKUP_FILE="$BACKUP_DIR/todos_${DATE}.tar.gz"

log "Creating backup: $BACKUP_FILE"

# Copy from container and create tarball
TMP_DIR=$(mktemp -d)
docker cp "${CONTAINER_NAME}:${TODOS_PATH}" "$TMP_DIR/todos"
tar czf "$BACKUP_FILE" -C "$TMP_DIR" todos
rm -rf "$TMP_DIR"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created: $SIZE"

    # Save metadata
    echo "date=$DATE" > "$BACKUP_FILE.meta"
    echo "files=$FILE_COUNT" >> "$BACKUP_FILE.meta"
    echo "container=$CONTAINER_NAME" >> "$BACKUP_FILE.meta"
    echo "path=$TODOS_PATH" >> "$BACKUP_FILE.meta"
else
    echo "ERROR: Backup file not created!"
    exit 1
fi

# Clean old backups
log "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "todos_*.tar.gz*" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

REMAINING=$(find "$BACKUP_DIR" -name "todos_*.tar.gz" -type f | wc -l)
log "Backups remaining: $REMAINING"

log "=== Backup Complete ==="
