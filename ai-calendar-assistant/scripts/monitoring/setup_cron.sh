#!/bin/bash
#
# Setup cron job for smoke tests on server
# Runs at 10:00 and 17:00 Moscow time daily
#

set -e

SCRIPT_DIR="/root/ai-calendar-assistant/ai-calendar-assistant/scripts/monitoring"
SCRIPT_PATH="${SCRIPT_DIR}/smoke_test.sh"
LOG_PATH="/var/log/smoke_test.log"

# Default Chat ID (Nikita Titov)
DEFAULT_CHAT_ID="2296243"

echo "=== Setting up Smoke Test Cron Job ==="

# Check if script exists
if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "ERROR: Script not found at $SCRIPT_PATH"
    echo "Run: git pull origin main"
    exit 1
fi

# Make executable
chmod +x "$SCRIPT_PATH"

# Ask for chat ID or use default
echo ""
echo "Telegram Chat ID для отправки отчётов."
echo "По умолчанию: $DEFAULT_CHAT_ID (@nikita_tita)"
echo ""
read -p "Enter Chat ID (или Enter для default): " CHAT_ID

if [[ -z "$CHAT_ID" ]]; then
    CHAT_ID="$DEFAULT_CHAT_ID"
fi

echo "Using Chat ID: $CHAT_ID"

# Create cron job
# Server timezone is MSK (UTC+3)
# So 10:00 MSK and 17:00 MSK
CRON_JOB="# AI Calendar Smoke Test - runs at 10:00 and 17:00 Moscow time
0 10,17 * * * SMOKE_TEST_CHAT_ID=${CHAT_ID} ${SCRIPT_PATH} >> ${LOG_PATH} 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "smoke_test.sh"; then
    echo "Cron job already exists. Updating..."
    crontab -l | grep -v "smoke_test.sh" | grep -v "AI Calendar Smoke Test" > /tmp/crontab_temp
else
    crontab -l 2>/dev/null > /tmp/crontab_temp || true
fi

# Add new cron job
echo "$CRON_JOB" >> /tmp/crontab_temp
crontab /tmp/crontab_temp
rm /tmp/crontab_temp

echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "Schedule (Moscow time):"
echo "  - 10:00"
echo "  - 17:00"
echo ""
echo "Chat ID: $CHAT_ID"
echo "Log file: $LOG_PATH"
echo ""
echo "Commands:"
echo "  View cron: crontab -l"
echo "  View logs: tail -f $LOG_PATH"
echo "  Test now:  SMOKE_TEST_CHAT_ID=$CHAT_ID $SCRIPT_PATH"
echo ""
