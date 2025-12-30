#!/bin/bash
#
# SQLite databases backup script
# Backs up all .db files from telegram-bot container
# Run daily via cron at 3:10
#

set -e

# Configuration
BACKUP_DIR="/root/backups/sqlite"
CONTAINER="telegram-bot"
SOURCE_DIR="/var/lib/calendar-bot"
KEEP_DAYS=30
QUIET=false

# Parse arguments
[[ "$1" == "--quiet" ]] && QUIET=true

log() {
    [[ "$QUIET" == "false" ]] && echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Date for backup filename
DATE=$(date '+%Y%m%d_%H%M%S')
BACKUP_SUBDIR="$BACKUP_DIR/$DATE"
mkdir -p "$BACKUP_SUBDIR"

log "Starting SQLite backup..."

# Known database files
DB_FILES="analytics.db admin_auth.db reminders.db"

# Backup each database using docker cp
COUNT=0
for db_name in $DB_FILES; do
    db_path="$SOURCE_DIR/$db_name"

    if docker cp "$CONTAINER:$db_path" "$BACKUP_SUBDIR/$db_name" 2>/dev/null; then
        log "✓ $db_name"
        ((COUNT++))
    else
        log "✗ $db_name (not found or error)"
    fi
done

if [[ $COUNT -eq 0 ]]; then
    log "No databases backed up!"
    rm -rf "$BACKUP_SUBDIR"
    exit 1
fi

# Compress backup
cd "$BACKUP_DIR"
tar -czf "sqlite_${DATE}.tar.gz" "$DATE"
rm -rf "$BACKUP_SUBDIR"

# Get backup size
SIZE=$(ls -lh "sqlite_${DATE}.tar.gz" | awk '{print $5}')
log "Backup complete: sqlite_${DATE}.tar.gz ($SIZE, $COUNT databases)"

# Cleanup old backups
DELETED=$(find "$BACKUP_DIR" -name "sqlite_*.tar.gz" -mtime +$KEEP_DAYS -delete -print | wc -l)
[[ "$DELETED" -gt 0 ]] && log "Deleted $DELETED old backups (>$KEEP_DAYS days)"

log "Done!"
