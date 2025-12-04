#!/bin/bash
#
# Setup cron job for smoke tests on server
# Runs at 10:00 and 17:00 Moscow time daily
#

set -e

SCRIPT_DIR="/root/ai-calendar-assistant/ai-calendar-assistant/scripts/monitoring"
SCRIPT_PATH="${SCRIPT_DIR}/smoke_test.sh"
LOG_PATH="/var/log/smoke_test.log"

echo "=== Setting up Smoke Test Cron Job ==="

# Check if script exists
if [[ ! -f "$SCRIPT_PATH" ]]; then
    echo "ERROR: Script not found at $SCRIPT_PATH"
    echo "Run: git pull origin main"
    exit 1
fi

# Make executable
chmod +x "$SCRIPT_PATH"

# Get chat ID instruction
echo ""
echo "IMPORTANT: You need to set your Telegram Chat ID!"
echo ""
echo "1. Send any message to @dogovorarenda_bot"
echo "2. Run this command to get your chat_id:"
echo '   curl -s "https://api.telegram.org/bot***REMOVED***/getUpdates" | grep -o '"'"'"chat":{"id":[0-9]*'"'"' | head -1'
echo ""
echo "3. Enter your Chat ID: "
read -r CHAT_ID

if [[ -z "$CHAT_ID" ]]; then
    echo "ERROR: Chat ID is required"
    exit 1
fi

# Create cron job
# Moscow timezone is UTC+3, server is likely UTC
# 10:00 MSK = 07:00 UTC
# 17:00 MSK = 14:00 UTC
CRON_JOB="# AI Calendar Smoke Test - runs at 10:00 and 17:00 Moscow time
0 7,14 * * * SMOKE_TEST_CHAT_ID=${CHAT_ID} ${SCRIPT_PATH} >> ${LOG_PATH} 2>&1"

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
echo "Schedule:"
echo "  - 10:00 Moscow time (07:00 UTC)"
echo "  - 17:00 Moscow time (14:00 UTC)"
echo ""
echo "Chat ID: $CHAT_ID"
echo "Log file: $LOG_PATH"
echo ""
echo "To verify: crontab -l"
echo "To test now: SMOKE_TEST_CHAT_ID=$CHAT_ID $SCRIPT_PATH"
echo ""
