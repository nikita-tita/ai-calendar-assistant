#!/bin/bash
#
# AI Calendar Assistant - Automated Backup Script
#
# This script creates encrypted backups of:
# - Radicale calendar data (all user events)
# - Bot data (preferences, analytics, reminders)
# - Configuration files
#
# Backups are encrypted with GPG and can be stored locally or uploaded to cloud
#
# Usage: ./backup-calendar.sh
# Cron:  0 3 * * * /root/ai-calendar-assistant/backup-calendar.sh

set -euo pipefail

# Configuration
BACKUP_ROOT="/root/backups/calendar-assistant"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_ROOT/$DATE"
RETENTION_DAYS=30
ENCRYPT_BACKUPS=true
GPG_RECIPIENT="noreply@этонесамыйдлинныйдомен.рф"

# Logging
LOG_FILE="/var/log/calendar-backup.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "=================================================="
echo "AI Calendar Backup Started: $(date)"
echo "=================================================="

# Create backup directory
mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

echo "[1/5] Backing up Radicale calendar data..."
# Backup Radicale data volume
if docker ps -q -f name=radicale-calendar > /dev/null 2>&1; then
    docker run --rm \
        --volumes-from radicale-calendar \
        -v "$BACKUP_DIR":/backup \
        alpine tar czf /backup/radicale_data.tar.gz /data
    echo "✅ Radicale data backed up: $(du -h radicale_data.tar.gz | cut -f1)"
else
    echo "⚠️  Radicale container not running, skipping calendar data backup"
fi

echo "[2/5] Backing up bot data (preferences, analytics, reminders)..."
# Backup bot data from telegram-bot container
if docker ps -q -f name=telegram-bot > /dev/null 2>&1; then
    docker exec telegram-bot tar czf - /var/lib/calendar-bot > bot_data.tar.gz
    echo "✅ Bot data backed up: $(du -h bot_data.tar.gz | cut -f1)"
else
    echo "⚠️  Telegram bot container not running, skipping bot data backup"
fi

echo "[3/5] Backing up configuration files..."
# Backup .env (contains passwords and keys)
if [ -f "/root/ai-calendar-assistant/.env" ]; then
    cp /root/ai-calendar-assistant/.env .env.backup
    echo "✅ .env configuration backed up"
fi

# Backup docker-compose.yml
if [ -f "/root/ai-calendar-assistant/docker-compose.yml" ]; then
    cp /root/ai-calendar-assistant/docker-compose.yml docker-compose.yml.backup
    echo "✅ docker-compose.yml backed up"
fi

echo "[4/5] Creating backup manifest..."
cat > manifest.txt <<EOF
AI Calendar Assistant Backup
============================
Date: $(date)
Hostname: $(hostname)
Backup ID: $DATE

Contents:
- radicale_data.tar.gz: Calendar events (CalDAV)
- bot_data.tar.gz: User preferences, analytics, reminders
- .env.backup: Environment configuration
- docker-compose.yml.backup: Docker configuration

Restore Instructions:
1. Stop containers: docker-compose down
2. Extract radicale_data.tar.gz to volume
3. Extract bot_data.tar.gz to volume
4. Restore .env and docker-compose.yml
5. Restart: docker-compose up -d

Total size: $(du -sh . | cut -f1)
EOF

echo "✅ Manifest created"

# Encrypt backups if enabled
if [ "$ENCRYPT_BACKUPS" = true ]; then
    echo "[5/5] Encrypting backup..."

    cd "$BACKUP_ROOT"
    tar czf "${DATE}.tar.gz" "$DATE"

    # Check if GPG key exists
    if gpg --list-keys "$GPG_RECIPIENT" > /dev/null 2>&1; then
        gpg --encrypt --recipient "$GPG_RECIPIENT" --trust-model always \
            -o "${DATE}.tar.gz.gpg" "${DATE}.tar.gz"
        rm "${DATE}.tar.gz"  # Remove unencrypted archive
        echo "✅ Backup encrypted with GPG"
        echo "   Encrypted file: ${DATE}.tar.gz.gpg ($(du -h ${DATE}.tar.gz.gpg | cut -f1))"
    else
        echo "⚠️  GPG key not found, backup NOT encrypted (security risk!)"
        echo "   To encrypt, create GPG key: gpg --gen-key"
        echo "   Unencrypted file: ${DATE}.tar.gz ($(du -h ${DATE}.tar.gz | cut -f1))"
    fi

    # Remove unencrypted directory
    rm -rf "$BACKUP_DIR"
else
    echo "[5/5] Skipping encryption (ENCRYPT_BACKUPS=false)"
    cd "$BACKUP_ROOT"
    tar czf "${DATE}.tar.gz" "$DATE"
    rm -rf "$BACKUP_DIR"
    echo "✅ Backup compressed: ${DATE}.tar.gz ($(du -h ${DATE}.tar.gz | cut -f1))"
fi

# Clean old backups
echo ""
echo "Cleaning old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_ROOT" -name "*.tar.gz*" -type f -mtime +$RETENTION_DAYS -delete
REMAINING=$(find "$BACKUP_ROOT" -name "*.tar.gz*" -type f | wc -l)
echo "✅ Backups remaining: $REMAINING"

# Summary
echo ""
echo "=================================================="
echo "Backup Completed Successfully: $(date)"
echo "Backup location: $BACKUP_ROOT"
echo "Total backup size: $(du -sh $BACKUP_ROOT | cut -f1)"
echo "=================================================="

# Optional: Upload to cloud storage
# Uncomment and configure if you want to upload to cloud
#
# if command -v rclone &> /dev/null; then
#     echo "Uploading to cloud storage..."
#     rclone copy "$BACKUP_ROOT/${DATE}.tar.gz.gpg" remote:calendar-backups/
#     echo "✅ Uploaded to cloud"
# fi

exit 0
