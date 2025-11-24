#!/bin/bash
# Safe WebApp Deployment Script
# This script ensures zero-downtime deployment with automatic rollback on failure

set -e  # Exit on error

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
WEBAPP_FILE="webapp_current.html"
REMOTE_DIR="/var/www/calendar"
BACKUP_DIR="/var/www/calendar_backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🚀 Starting safe WebApp deployment..."
echo "📅 Timestamp: $TIMESTAMP"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if webapp file exists
if [ ! -f "$WEBAPP_FILE" ]; then
    echo -e "${RED}❌ Error: $WEBAPP_FILE not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Step 1: Creating backup of current version...${NC}"
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << EOF
    # Create backup directory if not exists
    mkdir -p $BACKUP_DIR

    # Backup current version with timestamp
    if [ -f $REMOTE_DIR/index.html ]; then
        cp $REMOTE_DIR/index.html $BACKUP_DIR/index.html.$TIMESTAMP
        echo "✅ Backup created: index.html.$TIMESTAMP"
    else
        echo "⚠️  No existing file to backup"
    fi

    # Keep only last 10 backups
    cd $BACKUP_DIR
    ls -t index.html.* 2>/dev/null | tail -n +11 | xargs -r rm --
    echo "📦 Backups maintained (keeping last 10)"
EOF

echo -e "${YELLOW}📋 Step 2: Uploading new version...${NC}"
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no $WEBAPP_FILE $SERVER:$REMOTE_DIR/index.html.new

echo -e "${YELLOW}📋 Step 3: Validating uploaded file...${NC}"
UPLOAD_CHECK=$(sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER "[ -f $REMOTE_DIR/index.html.new ] && echo 'OK' || echo 'FAIL'")

if [ "$UPLOAD_CHECK" != "OK" ]; then
    echo -e "${RED}❌ Upload validation failed!${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Step 4: Deploying new version (atomic swap)...${NC}"
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << EOF
    # Atomic move - this is instant and prevents partial reads
    mv -f $REMOTE_DIR/index.html.new $REMOTE_DIR/index.html
    chmod 644 $REMOTE_DIR/index.html
    echo "✅ New version deployed atomically"
EOF

echo -e "${YELLOW}📋 Step 5: Updating Nginx configuration for better cache control...${NC}"
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'EOF'
    cat > /tmp/calendar_nginx.conf << 'NGINX_EOF'
server {
    server_name этонесамыйдлинныйдомен.рф xn--80aiabdqfcqhgchaebm7bp0qg3a.xn--p1ai;

    root /var/www/calendar;
    index index.html;

    # HTML files - NO CACHE для WebApp
    location ~ \.html$ {
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always;
        add_header Pragma "no-cache" always;
        add_header Expires "0" always;
        add_header X-Content-Type-Options "nosniff" always;
        try_files $uri =404;
    }

    # API - проксируем на FastAPI бэкенд
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Остальные файлы (для SPA)
    location / {
        try_files $uri $uri/ /index.html;
        # Static assets можно кэшировать
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1h;
            add_header Cache-Control "public, immutable";
        }
    }

    # CORS headers для WebApp
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header Access-Control-Allow-Headers 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/xn--80aiabdqfcqhgchaebm7bp0qg3a.xn--p1ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/xn--80aiabdqfcqhgchaebm7bp0qg3a.xn--p1ai/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name этонесамыйдлинныйдомен.рф xn--80aiabdqfcqhgchaebm7bp0qg3a.xn--p1ai;

    if ($host = xn--80aiabdqfcqhgchaebm7bp0qg3a.xn--p1ai) {
        return 301 https://$host$request_uri;
    }
    return 404;
}
NGINX_EOF

    # Backup current nginx config
    cp /etc/nginx/sites-available/calendar /etc/nginx/sites-available/calendar.backup.$TIMESTAMP

    # Install new config
    cp /tmp/calendar_nginx.conf /etc/nginx/sites-available/calendar

    # Test nginx config
    if nginx -t 2>&1 | grep -q "successful"; then
        echo "✅ Nginx config test passed"
        systemctl reload nginx
        echo "✅ Nginx reloaded"
    else
        echo "❌ Nginx config test failed, rolling back..."
        cp /etc/nginx/sites-available/calendar.backup.$TIMESTAMP /etc/nginx/sites-available/calendar
        exit 1
    fi
EOF

echo -e "${YELLOW}📋 Step 6: Verifying deployment...${NC}"
VERIFY=$(sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER "grep -c '2025-10-21-12:00' $REMOTE_DIR/index.html || echo '0'")

if [ "$VERIFY" -gt "0" ]; then
    echo -e "${GREEN}✅ Verification successful! New version is live.${NC}"
    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "📌 Deployed version: 2025-10-21-12:00"
    echo "📦 Backup location: $BACKUP_DIR/index.html.$TIMESTAMP"
    echo "🌐 URL: https://этонесамыйдлинныйдомен.рф"
    echo ""
    echo "ℹ️  Note: Telegram WebApp users may need to:"
    echo "   1. Close and reopen the WebApp"
    echo "   2. Or wait for automatic version detection"
    echo ""
else
    echo -e "${RED}❌ Verification failed! Rolling back...${NC}"
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER "cp $BACKUP_DIR/index.html.$TIMESTAMP $REMOTE_DIR/index.html"
    echo -e "${RED}❌ Rolled back to previous version${NC}"
    exit 1
fi

echo "🔄 To rollback manually if needed:"
echo "   sshpass -p '$PASSWORD' ssh $SERVER 'cp $BACKUP_DIR/index.html.$TIMESTAMP $REMOTE_DIR/index.html'"
