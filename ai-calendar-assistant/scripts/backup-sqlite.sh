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

# Get list of .db files
DB_FILES=$(docker exec "$CONTAINER" find "$SOURCE_DIR" -name "*.db" 2>/dev/null || true)

if [[ -z "$DB_FILES" ]]; then
    log "No .db files found in $SOURCE_DIR"
    exit 0
fi

# Backup each database
COUNT=0
for db_path in $DB_FILES; do
    db_name=$(basename "$db_path")
    log "Backing up: $db_name"

    # Use SQLite backup command for safe copy (handles locks)
    docker exec "$CONTAINER" sqlite3 "$db_path" ".backup '/tmp/${db_name}.backup'" 2>/dev/null || {
        # Fallback to simple copy if sqlite3 not available
        docker exec "$CONTAINER" cp "$db_path" "/tmp/${db_name}.backup" 2>/dev/null
    }

    # Copy from container
    docker cp "$CONTAINER:/tmp/${db_name}.backup" "$BACKUP_SUBDIR/${db_name}" 2>/dev/null

    # Cleanup temp file
    docker exec "$CONTAINER" rm -f "/tmp/${db_name}.backup" 2>/dev/null || true

    ((COUNT++))
done

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
