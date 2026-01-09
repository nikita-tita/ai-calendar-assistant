#!/bin/bash

# Production Deployment Script for AI Calendar Assistant
# This script safely deploys to production with pre-checks and rollback capability

set -e

echo "🚀 AI Calendar Assistant - Production Deployment"
echo "================================================"
echo ""

# Configuration (override with environment variables)
SERVER="${DEPLOY_SERVER:-root@95.163.227.26}"
REMOTE_DIR="${DEPLOY_DIR:-/root/ai-calendar-assistant}"
USE_SSH_KEY="${USE_SSH_KEY:-true}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run commands on server
run_remote() {
    if [ "$USE_SSH_KEY" = "true" ]; then
        ssh -o StrictHostKeyChecking=no "$SERVER" "$@"
    else
        # For password auth, you need sshpass installed
        if ! command -v sshpass &> /dev/null; then
            echo "${RED}❌ sshpass not installed. Install it or use SSH keys.${NC}"
            exit 1
        fi
        echo "${YELLOW}⚠️  Using password auth is not recommended. Use SSH keys instead.${NC}"
        read -s -p "Enter SSH password: " SSH_PASSWORD
        echo ""
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "$@"
    fi
}

# Step 1: Pre-deployment checks
echo "📋 Step 1: Pre-deployment local checks"
echo ""

echo "  → Checking Python syntax..."
python3 -m py_compile app/main.py app/config.py
echo "  ✅ Main files compile successfully"

echo ""
echo "  → Validating docker-compose.yml..."
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose.yml config > /dev/null
    echo "  ✅ docker-compose.yml is valid"
else
    echo "  ⚠️  docker-compose not found, skipping validation"
fi

echo ""
echo "${GREEN}✅ Pre-deployment checks passed${NC}"
echo ""

# Step 2: Backup current version on server
echo "📦 Step 2: Creating backup on server"
echo ""

run_remote << 'EOF'
    cd $REMOTE_DIR || exit 1

    # Create backup directory
    BACKUP_DIR="/root/backups/calendar-assistant"
    mkdir -p "$BACKUP_DIR"

    # Create timestamped backup
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"

    echo "  → Creating backup: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        app/ \
        docker-compose.yml \
        Dockerfile \
        .env \
        radicale_config/ \
        2>/dev/null || true

    echo "  ✅ Backup created: $BACKUP_FILE"

    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

    echo "  → Keeping last 10 backups"
EOF

echo ""
echo "${GREEN}✅ Backup created${NC}"
echo ""

# Step 3: Copy files to server
echo "🚀 Step 3: Deploying files to server"
echo ""

# Create a temporary tarball
TEMP_TAR=$(mktemp).tar.gz
echo "  → Creating deployment package..."
tar -czf "$TEMP_TAR" \
    app/ \
    docker-compose.yml \
    Dockerfile \
    radicale_config/ \
    requirements.txt \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store'

echo "  → Uploading to server..."
if [ "$USE_SSH_KEY" = "true" ]; then
    scp -o StrictHostKeyChecking=no "$TEMP_TAR" "$SERVER:/tmp/deploy.tar.gz"
else
    sshpass -p "$SSH_PASSWORD" scp -o StrictHostKeyChecking=no "$TEMP_TAR" "$SERVER:/tmp/deploy.tar.gz"
fi

rm "$TEMP_TAR"

run_remote << 'EOF'
    cd $REMOTE_DIR || exit 1
    echo "  → Extracting files..."
    tar -xzf /tmp/deploy.tar.gz
    rm /tmp/deploy.tar.gz
    echo "  ✅ Files extracted"
EOF

echo ""
echo "${GREEN}✅ Files deployed${NC}"
echo ""

# Step 4: Health check before restart
echo "🏥 Step 4: Pre-restart health check"
echo ""

run_remote << 'EOF'
    cd $REMOTE_DIR || exit 1

    # Check Radicale is running
    if docker ps | grep -q radicale-calendar; then
        echo "  ✅ Radicale container is running"
    else
        echo "  ⚠️  Radicale container is NOT running"
        echo "  → Starting Radicale..."
        docker-compose up -d radicale
        sleep 5
    fi

    # Check calendar-assistant is running
    if docker ps | grep -q ai-calendar-assistant; then
        echo "  ✅ Calendar-assistant container is running"
    else
        echo "  ⚠️  Calendar-assistant container is NOT running"
    fi
EOF

echo ""
echo "${GREEN}✅ Pre-restart checks passed${NC}"
echo ""

# Step 5: Rebuild and restart
echo "🔄 Step 5: Rebuilding and restarting services"
echo ""

run_remote << 'EOF'
    cd $REMOTE_DIR || exit 1

    echo "  → Rebuilding Docker images..."
    docker-compose build --no-cache

    echo "  → Restarting services..."
    docker-compose down
    docker-compose up -d

    echo "  → Waiting for startup (15 seconds)..."
    sleep 15
EOF

echo ""
echo "${GREEN}✅ Services restarted${NC}"
echo ""

# Step 6: Post-deployment health check
echo "🏥 Step 6: Post-deployment health check"
echo ""

run_remote << 'EOF'
    cd $REMOTE_DIR || exit 1

    # Check containers are running
    echo "  → Checking containers..."
    if docker ps | grep -E "ai-calendar-assistant.*Up" > /dev/null; then
        echo "  ✅ calendar-assistant: Running"
    else
        echo "  ❌ calendar-assistant: NOT running"
        docker ps -a | grep ai-calendar-assistant
        exit 1
    fi

    if docker ps | grep -E "radicale-calendar.*Up" > /dev/null; then
        echo "  ✅ radicale: Running"
    else
        echo "  ❌ radicale: NOT running"
        docker ps -a | grep radicale
        exit 1
    fi

    # Check bot logs for errors
    echo ""
    echo "  → Checking recent logs..."
    LOGS=$(docker logs ai-calendar-assistant --tail 50 2>&1)

    if echo "$LOGS" | grep -qi "error"; then
        echo "  ⚠️  Found errors in logs (may be normal):"
        echo "$LOGS" | grep -i "error" | head -5
    else
        echo "  ✅ No errors in recent logs"
    fi

    # Test health endpoint
    echo ""
    echo "  → Testing health endpoint..."
    if curl -sf http://localhost:8000/health > /dev/null; then
        echo "  ✅ Health endpoint responding"
    else
        echo "  ❌ Health endpoint not responding"
        exit 1
    fi
EOF

DEPLOY_SUCCESS=$?

echo ""

if [ $DEPLOY_SUCCESS -eq 0 ]; then
    echo "${GREEN}✅ DEPLOYMENT SUCCESSFUL!${NC}"
    echo ""
    echo "📊 Summary:"
    echo "  • Pre-checks passed"
    echo "  • Backup created"
    echo "  • Files deployed"
    echo "  • Services rebuilt and restarted"
    echo "  • Health checks passed"
    echo ""
    echo "🧪 Next steps:"
    echo "  1. Test bot in Telegram"
    echo "  2. Check logs: ssh $SERVER 'docker logs ai-calendar-assistant --tail 100'"
    echo "  3. Monitor for errors: ssh $SERVER 'docker logs -f ai-calendar-assistant'"
    echo ""
else
    echo "${RED}❌ DEPLOYMENT FAILED!${NC}"
    echo ""
    echo "🔄 To rollback, run:"
    echo "  ssh $SERVER 'cd $REMOTE_DIR && tar -xzf /root/backups/calendar-assistant/backup_*.tar.gz && docker-compose up -d --build'"
    echo ""
    exit 1
fi
