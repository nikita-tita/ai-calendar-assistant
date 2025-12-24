#!/bin/bash
# Cloud Backup Script for AI Calendar Assistant
# Supports: Yandex Object Storage (S3-compatible), local storage
#
# Usage:
#   ./scripts/backup.sh                    # Create backup
#   ./scripts/backup.sh --upload           # Create and upload to cloud
#   ./scripts/backup.sh --restore latest   # Restore from latest backup
#   ./scripts/backup.sh --list             # List available backups
#
# Required environment variables for cloud upload:
#   S3_ENDPOINT=https://storage.yandexcloud.net
#   S3_BUCKET=your-bucket-name
#   AWS_ACCESS_KEY_ID=your-key-id
#   AWS_SECRET_ACCESS_KEY=your-secret-key
#
# Cron example (daily at 3am):
#   0 3 * * * /root/ai-calendar-assistant/ai-calendar-assistant/scripts/backup.sh --upload >> /var/log/backup.log 2>&1

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/lib/calendar-bot/backups}"
DATA_DIR="${DATA_DIR:-/var/lib/calendar-bot}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="calendar_backup_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

create_backup() {
    log_info "Creating backup: $BACKUP_NAME"

    # Create temporary directory
    TMP_DIR=$(mktemp -d)
    BACKUP_PATH="$TMP_DIR/$BACKUP_NAME"
    mkdir -p "$BACKUP_PATH"

    # Backup SQLite database with WAL checkpoint
    if [ -f "$DATA_DIR/analytics.db" ]; then
        log_info "Backing up analytics database..."
        # Checkpoint WAL to ensure consistency
        sqlite3 "$DATA_DIR/analytics.db" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
        cp "$DATA_DIR/analytics.db" "$BACKUP_PATH/"
    fi

    # Backup encrypted data files
    log_info "Backing up encrypted data..."
    find "$DATA_DIR" -name "*.enc" -exec cp {} "$BACKUP_PATH/" \; 2>/dev/null || true

    # Backup Radicale calendar data
    if [ -d "/var/lib/radicale" ]; then
        log_info "Backing up Radicale calendars..."
        mkdir -p "$BACKUP_PATH/radicale"
        cp -r /var/lib/radicale/collections "$BACKUP_PATH/radicale/" 2>/dev/null || true
    fi

    # Backup encryption key (if exists and not in env)
    if [ -f "/etc/calendar-bot/.encryption_key" ]; then
        log_info "Backing up encryption key..."
        mkdir -p "$BACKUP_PATH/keys"
        cp "/etc/calendar-bot/.encryption_key" "$BACKUP_PATH/keys/"
    fi

    # Create metadata file
    cat > "$BACKUP_PATH/metadata.json" << EOF
{
    "created_at": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "backup_name": "$BACKUP_NAME",
    "data_dir": "$DATA_DIR",
    "version": "1.0"
}
EOF

    # Create tarball
    ARCHIVE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    log_info "Creating archive: $ARCHIVE"
    tar -czf "$ARCHIVE" -C "$TMP_DIR" "$BACKUP_NAME"

    # Cleanup temp directory
    rm -rf "$TMP_DIR"

    # Calculate checksum
    sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

    log_info "Backup created: $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

    # Cleanup old backups
    cleanup_old_backups
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "calendar_backup_*.tar.gz" -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "calendar_backup_*.tar.gz.sha256" -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true
}

upload_to_cloud() {
    if [ -z "$S3_ENDPOINT" ] || [ -z "$S3_BUCKET" ]; then
        log_warn "S3 configuration not set. Skipping cloud upload."
        log_warn "Set S3_ENDPOINT, S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
        return 0
    fi

    LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/calendar_backup_*.tar.gz 2>/dev/null | head -1)
    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No backup found to upload"
        return 1
    fi

    log_info "Uploading to cloud: $LATEST_BACKUP"

    # Check for aws cli or s3cmd
    if command -v aws &> /dev/null; then
        aws s3 cp "$LATEST_BACKUP" "s3://$S3_BUCKET/" \
            --endpoint-url "$S3_ENDPOINT"
        aws s3 cp "${LATEST_BACKUP}.sha256" "s3://$S3_BUCKET/" \
            --endpoint-url "$S3_ENDPOINT"
    elif command -v s3cmd &> /dev/null; then
        s3cmd put "$LATEST_BACKUP" "s3://$S3_BUCKET/" \
            --host="$S3_ENDPOINT" --host-bucket=""
        s3cmd put "${LATEST_BACKUP}.sha256" "s3://$S3_BUCKET/" \
            --host="$S3_ENDPOINT" --host-bucket=""
    else
        log_error "Neither 'aws' nor 's3cmd' found. Install one to enable cloud upload."
        return 1
    fi

    log_info "Upload complete!"
}

list_backups() {
    log_info "Local backups in $BACKUP_DIR:"
    ls -lh "$BACKUP_DIR"/calendar_backup_*.tar.gz 2>/dev/null || echo "  No backups found"

    if [ -n "$S3_ENDPOINT" ] && [ -n "$S3_BUCKET" ]; then
        log_info "Cloud backups in s3://$S3_BUCKET:"
        if command -v aws &> /dev/null; then
            aws s3 ls "s3://$S3_BUCKET/" --endpoint-url "$S3_ENDPOINT" | grep calendar_backup || echo "  No backups found"
        fi
    fi
}

restore_backup() {
    BACKUP_TO_RESTORE="$1"

    if [ "$BACKUP_TO_RESTORE" = "latest" ]; then
        BACKUP_TO_RESTORE=$(ls -t "$BACKUP_DIR"/calendar_backup_*.tar.gz 2>/dev/null | head -1)
    fi

    if [ -z "$BACKUP_TO_RESTORE" ] || [ ! -f "$BACKUP_TO_RESTORE" ]; then
        log_error "Backup not found: $BACKUP_TO_RESTORE"
        return 1
    fi

    log_warn "This will restore from: $BACKUP_TO_RESTORE"
    log_warn "Current data will be overwritten!"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Restore cancelled"
        return 0
    fi

    # Verify checksum
    if [ -f "${BACKUP_TO_RESTORE}.sha256" ]; then
        log_info "Verifying checksum..."
        sha256sum -c "${BACKUP_TO_RESTORE}.sha256" || {
            log_error "Checksum verification failed!"
            return 1
        }
    fi

    # Extract backup
    TMP_DIR=$(mktemp -d)
    log_info "Extracting backup..."
    tar -xzf "$BACKUP_TO_RESTORE" -C "$TMP_DIR"

    BACKUP_NAME=$(ls "$TMP_DIR")

    # Restore database
    if [ -f "$TMP_DIR/$BACKUP_NAME/analytics.db" ]; then
        log_info "Restoring analytics database..."
        cp "$TMP_DIR/$BACKUP_NAME/analytics.db" "$DATA_DIR/"
    fi

    # Restore encrypted files
    log_info "Restoring encrypted data..."
    find "$TMP_DIR/$BACKUP_NAME" -name "*.enc" -exec cp {} "$DATA_DIR/" \;

    # Restore Radicale if present
    if [ -d "$TMP_DIR/$BACKUP_NAME/radicale" ]; then
        log_info "Restoring Radicale calendars..."
        cp -r "$TMP_DIR/$BACKUP_NAME/radicale/collections" /var/lib/radicale/
    fi

    # Cleanup
    rm -rf "$TMP_DIR"

    log_info "Restore complete! You may need to restart services."
}

# Parse arguments
case "${1:-}" in
    --upload)
        create_backup
        upload_to_cloud
        ;;
    --list)
        list_backups
        ;;
    --restore)
        restore_backup "${2:-latest}"
        ;;
    --help|-h)
        echo "Usage: $0 [--upload|--list|--restore <backup>|--help]"
        echo ""
        echo "Options:"
        echo "  (none)     Create local backup"
        echo "  --upload   Create backup and upload to cloud"
        echo "  --list     List available backups"
        echo "  --restore  Restore from backup (default: latest)"
        echo "  --help     Show this help"
        ;;
    *)
        create_backup
        ;;
esac
