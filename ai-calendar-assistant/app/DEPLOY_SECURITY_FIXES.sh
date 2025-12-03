#!/bin/bash
#
# Quick Deploy Script - Security Fixes
# Deploys security updates to production server
#

set -e

SERVER="root@91.229.8.221"
SERVER_PATH="/root/ai-calendar-assistant"
PASSWORD="upvzrr3LH4pxsaqs"

echo "═══════════════════════════════════════════════════════════"
echo "  🚀 Deploying Security Fixes to Production"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Server: $SERVER"
echo "Path: $SERVER_PATH"
echo "Branch: main (latest security fixes)"
echo ""

# Check if sshpass is available
if ! command -v sshpass &> /dev/null; then
    echo "⚠️  sshpass not found. Installing..."
    brew install hudochenkov/sshpass/sshpass 2>/dev/null || {
        echo "❌ Failed to install sshpass. Please install manually:"
        echo "   brew install hudochenkov/sshpass/sshpass"
        exit 1
    }
fi

echo "📦 Step 1: Pulling latest code from GitLab..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant
echo "Current directory: $(pwd)"

# Pull latest changes
git fetch origin
git checkout main
git pull origin main

echo "✅ Code updated"
ENDSSH

echo ""
echo "🔧 Step 2: Updating .env with new secure secrets..."
# Note: .env is already configured on server, just verify it exists
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
if [ ! -f /root/ai-calendar-assistant/.env ]; then
    echo "❌ ERROR: .env file not found on server!"
    echo "Please create .env file with secure secrets:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Generate secrets: python3 -c 'import secrets; print(secrets.token_urlsafe(32))'"
    exit 1
fi

# Check if new required fields exist
if ! grep -q "TELEGRAM_WEBAPP_URL" /root/ai-calendar-assistant/.env; then
    echo "⚠️  Adding TELEGRAM_WEBAPP_URL to .env..."
    echo "" >> /root/ai-calendar-assistant/.env
    echo "# Telegram WebApp URL (for calendar interface)" >> /root/ai-calendar-assistant/.env
    echo "TELEGRAM_WEBAPP_URL=https://calendar-webapp-beige.vercel.app" >> /root/ai-calendar-assistant/.env
fi

echo "✅ .env configured"
ENDSSH

echo ""
echo "🐳 Step 3: Rebuilding Docker containers..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

# Stop containers
echo "Stopping containers..."
docker-compose down

# Rebuild with no cache (ensure new code is used)
echo "Building containers..."
docker-compose build --no-cache telegram-bot-polling

# Start containers
echo "Starting containers..."
docker-compose up -d

echo "✅ Containers rebuilt and started"
ENDSSH

echo ""
echo "🔍 Step 4: Checking deployment status..."
sleep 5  # Wait for containers to start

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

echo ""
echo "Container Status:"
docker-compose ps

echo ""
echo "Recent Logs (last 20 lines):"
docker-compose logs --tail=20 telegram-bot-polling

echo ""
echo "Checking for validation errors..."
if docker-compose logs telegram-bot-polling | grep -q "CRITICAL.*SECRET_KEY"; then
    echo "❌ SECRET_KEY validation failed!"
    echo "Please check logs above and verify .env configuration"
    exit 1
fi

if docker-compose logs telegram-bot-polling | grep -q "Configuration validated"; then
    echo "✅ Configuration validated successfully"
else
    echo "⚠️  No validation message found in logs yet"
    echo "Container may still be starting... Check logs manually:"
    echo "  docker-compose logs -f telegram-bot-polling"
fi
ENDSSH

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Deployment Complete!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Next Steps:"
echo "  1. Monitor logs: ssh $SERVER 'docker-compose logs -f telegram-bot-polling'"
echo "  2. Test bot: Send /start to your Telegram bot"
echo "  3. Check webapp menu button appears"
echo ""
echo "Security Improvements Applied:"
echo "  ✅ Removed hardcoded SECRET_KEY"
echo "  ✅ Removed hardcoded RADICALE_BOT_PASSWORD"
echo "  ✅ Set DEBUG=False by default"
echo "  ✅ Excluded .env from Docker images"
echo "  ✅ Added secret validation (min 32 chars)"
echo "  ✅ Removed hardcoded webapp domain"
echo ""
echo "Documentation:"
echo "  - SECURITY.md: Complete security guide"
echo "  - CODE_REVIEW.md: Detailed fixes"
echo "  - QUICKSTART_SECURITY.md: Quick reference"
echo ""
