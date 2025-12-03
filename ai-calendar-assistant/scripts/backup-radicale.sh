#!/bin/bash
#
# Radicale Calendar Data Backup Script
# Creates backup of all calendar events stored in Docker volume
#
# Usage: ./scripts/backup-radicale.sh [--quiet]
# Cron:  0 3 * * * /root/ai-calendar-assistant/ai-calendar-assistant/scripts/backup-radicale.sh --quiet
#
# Backups stored in: /root/backups/radicale/
# Retention: 30 days

set -euo pipefail

# Configuration
BACKUP_DIR="/root/backups/radicale"
VOLUME_NAME="calendar-radicale-data"
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

log "=== Radicale Backup: $DATE ==="

# Check if volume exists
if ! docker volume ls -q | grep -q "^${VOLUME_NAME}$"; then
    echo "ERROR: Volume $VOLUME_NAME not found!"
    exit 1
fi

# Count events before backup
EVENT_COUNT=$(docker run --rm -v "${VOLUME_NAME}:/data:ro" alpine find /data -name "*.ics" -type f 2>/dev/null | wc -l || echo "0")
log "Events to backup: $EVENT_COUNT"

if [ "$EVENT_COUNT" -eq 0 ]; then
    log "WARNING: No events found in volume!"
fi

# Create backup
BACKUP_FILE="$BACKUP_DIR/radicale_${DATE}.tar.gz"

log "Creating backup: $BACKUP_FILE"
docker run --rm \
    -v "${VOLUME_NAME}:/data:ro" \
    -v "$BACKUP_DIR:/backup" \
    alpine tar czf "/backup/radicale_${DATE}.tar.gz" -C /data .

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup created: $SIZE"

    # Save metadata
    echo "date=$DATE" > "$BACKUP_FILE.meta"
    echo "events=$EVENT_COUNT" >> "$BACKUP_FILE.meta"
    echo "volume=$VOLUME_NAME" >> "$BACKUP_FILE.meta"
else
    echo "ERROR: Backup file not created!"
    exit 1
fi

# Clean old backups
log "Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "radicale_*.tar.gz*" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

REMAINING=$(find "$BACKUP_DIR" -name "radicale_*.tar.gz" -type f | wc -l)
log "Backups remaining: $REMAINING"

log "=== Backup Complete ==="
