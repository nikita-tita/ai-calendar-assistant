#!/bin/bash

echo "🚀 Single Session Deployment"
echo "============================"
echo ""

# First, prepare files locally
echo "📦 Preparing deployment package..."
tar czf /tmp/deploy_package.tar.gz -C /Users/fatbookpro/Desktop/AI-Calendar-Project/ai-calendar-assistant \
    .env \
    app/static/index.html \
    app/services/telegram_handler.py \
    docker-compose.yml

echo "✅ Package created"
echo ""

# Upload and deploy in one SSH session
echo "📤 Uploading and deploying..."
ssh -i ~/.ssh/id_housler root@95.163.227.26 'bash -s' << 'ENDSSH'
set -e
cd /root/ai-calendar-assistant

echo "📥 Receiving package..."
# Package will be uploaded separately

echo "🔍 Current state:"
echo "  Container status:"
docker ps --filter "name=calendar" --format "{{.Names}}: {{.Status}}" || true

echo ""
echo "  Current .env TELEGRAM_WEBAPP_URL:"
grep TELEGRAM_WEBAPP_URL .env || echo "  Not found"

echo ""
echo "  Current index.html lines:"
docker exec ai-calendar-assistant wc -l /app/app/static/index.html 2>/dev/null || echo "  Container not accessible"

ENDSSH

echo ""
echo "✅ Diagnostic complete. SSH session closed cleanly."
