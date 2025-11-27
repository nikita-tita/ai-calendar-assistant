#!/bin/bash

# 🚀 Автоматическая настройка calendar.housler.ru на VPS
# Этот скрипт выполнит все шаги настройки автоматически

set -e  # Остановить при ошибке

VPS_IP="91.229.8.221"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/calendar_deploy"
DOMAIN="calendar.housler.ru"
EMAIL="your-email@example.com"  # Замените на свой email
SSH_CMD="ssh -i $SSH_KEY -o StrictHostKeyChecking=no"

echo "🚀 Начинаю автоматическую настройку calendar.housler.ru"
echo "=================================================="

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функция для проверки DNS
check_dns() {
    echo -e "${YELLOW}⏳ Проверяю DNS...${NC}"
    DNS_IP=$(dig +short $DOMAIN | tail -n1)
    if [ "$DNS_IP" == "$VPS_IP" ]; then
        echo -e "${GREEN}✅ DNS настроен правильно: $DOMAIN → $VPS_IP${NC}"
        return 0
    else
        echo -e "${RED}❌ DNS ещё не обновился. Текущий IP: $DNS_IP${NC}"
        echo -e "${YELLOW}Ожидаю обновления DNS...${NC}"
        return 1
    fi
}

# Ждём обновления DNS
echo "1️⃣ Проверяю DNS..."
MAX_ATTEMPTS=30
ATTEMPT=0
while ! check_dns; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo -e "${RED}❌ DNS не обновился за 15 минут. Проверьте настройки DNS в Reg.ru${NC}"
        exit 1
    fi
    echo "Попытка $ATTEMPT/$MAX_ATTEMPTS. Жду 30 секунд..."
    sleep 30
done

# Проверяем SSH доступ
echo ""
echo "2️⃣ Проверяю SSH доступ к VPS..."
if $SSH_CMD $VPS_USER@$VPS_IP "echo 'SSH OK'" &>/dev/null; then
    echo -e "${GREEN}✅ SSH доступ работает${NC}"
else
    echo -e "${RED}❌ Нет SSH доступа к VPS${NC}"
    echo "Настройте SSH ключ командой:"
    echo "ssh-copy-id -i ${SSH_KEY}.pub $VPS_USER@$VPS_IP"
    echo ""
    echo "Или следуйте инструкции: ADD_SSH_KEY.md"
    exit 1
fi

# 3. Настройка Nginx
echo ""
echo "3️⃣ Настраиваю Nginx на VPS..."
$SSH_CMD $VPS_USER@$VPS_IP << 'ENDSSH'
# Создаём Nginx конфигурацию
cat > /etc/nginx/sites-available/calendar.housler.ru << 'EOF'
server {
    listen 80;
    server_name calendar.housler.ru;

    # Для получения SSL сертификата
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name calendar.housler.ru;

    # SSL сертификаты (будут добавлены Certbot)
    ssl_certificate /etc/letsencrypt/live/calendar.housler.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.housler.ru/privkey.pem;

    # Современные SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Проксирование к Flask приложению
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://localhost:5000/health;
    }
}
EOF

# Активируем конфигурацию
ln -sf /etc/nginx/sites-available/calendar.housler.ru /etc/nginx/sites-enabled/

# Проверяем конфигурацию
nginx -t

echo "✅ Nginx конфигурация создана"
ENDSSH

echo -e "${GREEN}✅ Nginx настроен${NC}"

# 4. Получаем SSL сертификат
echo ""
echo "4️⃣ Получаю SSL сертификат от Let's Encrypt..."
$SSH_CMD $VPS_USER@$VPS_IP << ENDSSH
# Устанавливаем Certbot если нет
if ! command -v certbot &> /dev/null; then
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Получаем SSL сертификат
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect

# Перезапускаем Nginx
systemctl reload nginx

echo "✅ SSL сертификат получен"
ENDSSH

echo -e "${GREEN}✅ SSL сертификат установлен${NC}"

# 5. Обновляем .env
echo ""
echo "5️⃣ Обновляю переменные окружения..."
$SSH_CMD $VPS_USER@$VPS_IP << 'ENDSSH'
cd /root/ai-calendar-assistant

# Создаём резервную копию
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Обновляем WEBAPP_URL
if grep -q "^WEBAPP_URL=" .env; then
    sed -i 's|^WEBAPP_URL=.*|WEBAPP_URL=https://calendar.housler.ru|' .env
else
    echo "WEBAPP_URL=https://calendar.housler.ru" >> .env
fi

# Обновляем DOMAIN
if grep -q "^DOMAIN=" .env; then
    sed -i 's|^DOMAIN=.*|DOMAIN=calendar.housler.ru|' .env
else
    echo "DOMAIN=calendar.housler.ru" >> .env
fi

echo "✅ .env обновлён"
ENDSSH

echo -e "${GREEN}✅ Переменные окружения обновлены${NC}"

# 6. Обновляем Telegram Menu Button
echo ""
echo "6️⃣ Обновляю Telegram Menu Button..."
TELEGRAM_TOKEN=$($SSH_CMD $VPS_USER@$VPS_IP "grep TELEGRAM_BOT_TOKEN /root/ai-calendar-assistant/.env | cut -d '=' -f2")

RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setChatMenuButton" \
-H "Content-Type: application/json" \
-d '{
  "menu_button": {
    "type": "web_app",
    "text": "🗓 Календарь",
    "web_app": {
      "url": "https://calendar.housler.ru"
    }
  }
}')

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo -e "${GREEN}✅ Telegram Menu Button обновлён${NC}"
else
    echo -e "${RED}❌ Ошибка обновления Menu Button: $RESPONSE${NC}"
fi

# 7. Перезапускаем приложение
echo ""
echo "7️⃣ Перезапускаю приложение..."
$SSH_CMD $VPS_USER@$VPS_IP << 'ENDSSH'
cd /root/ai-calendar-assistant
docker-compose restart
echo "✅ Приложение перезапущено"
ENDSSH

echo -e "${GREEN}✅ Приложение перезапущено${NC}"

# 8. Проверка
echo ""
echo "8️⃣ Проверяю работу..."
echo "=================================================="

# Проверяем DNS
echo -n "DNS: "
if dig +short $DOMAIN | grep -q $VPS_IP; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
fi

# Проверяем HTTP
echo -n "HTTP: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN/health)
if [ "$HTTP_CODE" == "301" ] || [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✅ ($HTTP_CODE)${NC}"
else
    echo -e "${RED}❌ ($HTTP_CODE)${NC}"
fi

# Проверяем HTTPS
echo -n "HTTPS: "
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN/health)
if [ "$HTTPS_CODE" == "200" ]; then
    echo -e "${GREEN}✅ ($HTTPS_CODE)${NC}"
else
    echo -e "${RED}❌ ($HTTPS_CODE)${NC}"
fi

# Проверяем SSL сертификат
echo -n "SSL сертификат: "
if echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | grep -q "Verify return code: 0"; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️ Проверьте вручную${NC}"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}🎉 Настройка завершена!${NC}"
echo ""
echo "✅ Веб-приложение доступно: https://calendar.housler.ru"
echo "✅ Telegram бот: Нажмите кнопку '🗓 Календарь'"
echo ""
echo "📋 Следующие шаги:"
echo "1. Откройте https://calendar.housler.ru в браузере"
echo "2. Проверьте Telegram бот (кнопка Menu)"
echo "3. Задеплойте обновлённый веб-апп: ./deploy_updates.sh"
echo ""
echo "📊 Логи приложения:"
echo "$SSH_CMD $VPS_USER@$VPS_IP 'cd /root/ai-calendar-assistant && docker-compose logs -f'"
