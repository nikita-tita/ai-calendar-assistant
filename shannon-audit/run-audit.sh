#!/bin/bash
# Shannon Security Audit for AI Calendar Assistant
# Usage: ./run-audit.sh

set -e

# Check prerequisites
if [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "ERROR: CLAUDE_CODE_OAUTH_TOKEN not set"
    echo ""
    echo "To get the token:"
    echo "1. Go to https://console.anthropic.com"
    echo "2. Navigate to Settings -> OAuth"
    echo "3. Create OAuth token for Claude Code"
    echo "4. Export: export CLAUDE_CODE_OAUTH_TOKEN='your-token'"
    exit 1
fi

# Build Shannon (first time only)
if ! docker images | grep -q "shannon:latest"; then
    echo "Building Shannon..."
    cd /tmp
    git clone https://github.com/KeygraphHQ/shannon.git
    cd shannon
    docker build -t shannon:latest .
    cd -
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting Shannon security audit..."
echo "Target: https://calendar.housler.ru"
echo "Source: $SCRIPT_DIR/repos/ai-calendar-assistant"
echo ""

# Run Shannon
docker run --rm -it \
  --network host \
  --cap-add=NET_RAW \
  --cap-add=NET_ADMIN \
  -e CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  -e CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000 \
  -v "$SCRIPT_DIR/repos:/app/repos" \
  -v "$SCRIPT_DIR/configs:/app/configs" \
  -v "$SCRIPT_DIR/deliverables:/app/deliverables" \
  shannon:latest \
  "https://calendar.housler.ru/" \
  "/app/repos/ai-calendar-assistant" \
  --config /app/configs/calendar-assistant.yaml

echo ""
echo "Audit complete! Results in: $SCRIPT_DIR/deliverables/"
