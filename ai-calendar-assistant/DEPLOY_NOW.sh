#!/bin/bash

set -e

echo "=================================================="
echo "🚀 AUTOMATED DEPLOYMENT TO calendar.housler.ru"
echo "=================================================="
echo ""
echo "This script will:"
echo "1. Check DNS propagation"
echo "2. Set up Nginx configuration"
echo "3. Get SSL certificate from Let's Encrypt"
echo "4. Update .env with new domain"
echo "5. Update Telegram Menu Button"
echo "6. Deploy web application"
echo ""
echo "Estimated time: ~10 minutes"
echo ""

# Configuration
SERVER_IP="95.163.227.26"
DOMAIN="calendar.housler.ru"
SSH_KEY="$HOME/.ssh/id_housler"
BOT_TOKEN="***REDACTED_BOT_TOKEN***"

# Check if we have the SSH key
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    exit 1
fi

# Step 1: Check DNS propagation
echo "=================================================="
echo "STEP 1: Checking DNS propagation"
echo "=================================================="
echo ""
echo "Checking if $DOMAIN points to $SERVER_IP..."
DNS_IP=$(dig +short "$DOMAIN" @8.8.8.8 | tail -n1)

if [ -z "$DNS_IP" ]; then
    echo "❌ DNS record not found!"
    echo ""
    echo "Please add the following DNS record in REG.RU:"
    echo "  Type: A"
    echo "  Name: calendar"
    echo "  Value: $SERVER_IP"
    echo "  TTL: 3600"
    echo ""
    echo "After adding the record, wait 5-10 minutes and run this script again."
    exit 1
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo "❌ DNS points to wrong IP: $DNS_IP (expected: $SERVER_IP)"
    echo ""
    echo "Please update your DNS record to point to $SERVER_IP"
    exit 1
else
    echo "✅ DNS is correctly configured: $DOMAIN → $SERVER_IP"
fi

echo ""
read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

# Step 2: Upload and configure Nginx
echo ""
echo "=================================================="
echo "STEP 2: Setting up Nginx"
echo "=================================================="
echo ""

# Check if nginx-housler.conf exists
if [ ! -f "nginx-housler.conf" ]; then
    echo "❌ nginx-housler.conf not found!"
    exit 1
fi

echo "Uploading Nginx configuration..."
scp -i "$SSH_KEY" nginx-housler.conf root@${SERVER_IP}:/etc/nginx/sites-available/calendar.housler.ru

echo "Creating symlink..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "ln -sf /etc/nginx/sites-available/calendar.housler.ru /etc/nginx/sites-enabled/"

echo "Testing Nginx configuration..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "nginx -t"

echo "✅ Nginx configuration uploaded"

# Step 3: Get SSL certificate
echo ""
echo "=================================================="
echo "STEP 3: Getting SSL certificate"
echo "=================================================="
echo ""

echo "Reloading Nginx to serve ACME challenge..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "systemctl reload nginx"

echo "Getting SSL certificate from Let's Encrypt..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "certbot certonly --webroot -w /var/www/html -d $DOMAIN --non-interactive --agree-tos --email noreply@housler.ru" || {
    echo "⚠️  Certbot failed. Trying standalone mode..."
    ssh -i "$SSH_KEY" root@${SERVER_IP} "systemctl stop nginx && certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos --email noreply@housler.ru && systemctl start nginx"
}

echo "Reloading Nginx with SSL..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "systemctl reload nginx"

echo "✅ SSL certificate obtained and configured"

# Step 4: Update .env file
echo ""
echo "=================================================="
echo "STEP 4: Updating .env file"
echo "=================================================="
echo ""

echo "Backing up .env..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "cd /root/ai-calendar-assistant/ai-calendar-assistant && cp .env .env.backup-\$(date +%Y%m%d-%H%M%S)"

echo "Updating WEBAPP_URL in .env..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "cd /root/ai-calendar-assistant/ai-calendar-assistant && sed -i 's|WEBAPP_URL=.*|WEBAPP_URL=https://$DOMAIN|' .env"

echo "✅ .env file updated"

# Step 5: Update Telegram Menu Button
echo ""
echo "=================================================="
echo "STEP 5: Updating Telegram Menu Button"
echo "=================================================="
echo ""

echo "Setting Telegram Menu Button URL to https://$DOMAIN..."
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" \
    -H "Content-Type: application/json" \
    -d "{
        \"menu_button\": {
            \"type\": \"web_app\",
            \"text\": \"📅 Календарь\",
            \"web_app\": {
                \"url\": \"https://$DOMAIN\"
            }
        }
    }" | jq .

echo "✅ Telegram Menu Button updated"

# Step 6: Deploy web application
echo ""
echo "=================================================="
echo "STEP 6: Deploying web application"
echo "=================================================="
echo ""

echo "Running deploy_updates.sh..."
if [ ! -f "deploy_updates.sh" ]; then
    echo "❌ deploy_updates.sh not found!"
    exit 1
fi

./deploy_updates.sh

echo "✅ Web application deployed"

# Step 7: Restart services
echo ""
echo "=================================================="
echo "STEP 7: Restarting services"
echo "=================================================="
echo ""

echo "Restarting Docker containers..."
ssh -i "$SSH_KEY" root@${SERVER_IP} "cd /root/ai-calendar-assistant/ai-calendar-assistant && docker-compose restart ai-calendar-assistant telegram-bot-polling"

echo "Waiting for services to start..."
sleep 5

echo "✅ Services restarted"

# Final verification
echo ""
echo "=================================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=================================================="
echo ""
echo "Your calendar is now available at: https://$DOMAIN"
echo ""
echo "Verification steps:"
echo "1. Open https://$DOMAIN in browser"
echo "2. Check that TODO list works"
echo "3. Check that calendar shows correct date range"
echo "4. Test Telegram bot Menu Button"
echo ""
echo "Testing web application..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Web application is responding (HTTP $HTTP_CODE)"
else
    echo "⚠️  Web application returned HTTP $HTTP_CODE"
fi

echo ""
echo "Testing API health..."
API_RESPONSE=$(curl -s "https://$DOMAIN/api/health")
echo "API Response: $API_RESPONSE"

echo ""
echo "All done! 🎉"
echo ""
