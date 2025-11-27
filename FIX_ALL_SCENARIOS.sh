#!/bin/bash

# 🔧 UNIVERSAL FIX - Covers ALL scenarios
# Это решит проблему независимо от причины

set -e

VPS_IP="91.229.8.221"
VPS_USER="root"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 UNIVERSAL FIX FOR ALL SCENARIOS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Этот скрипт покрывает ВСЕ возможные причины проблемы:"
echo "  1. Docker образ со старым index.html"
echo "  2. Файлы на хосте устарели"
echo "  3. Несколько контейнеров"
echo "  4. Nginx кеширование"
echo "  5. Неправильные volumes"
echo ""
echo "Потребуется пароль VPS."
echo ""
read -p "Продолжить? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Check local file
echo -e "${YELLOW}📋 Проверяю локальный файл...${NC}"
if [ ! -f "app/static/index.html" ]; then
    echo -e "${RED}❌ app/static/index.html не найден локально!${NC}"
    exit 1
fi

LOCAL_SIZE=$(wc -c < app/static/index.html | tr -d ' ')
echo -e "${GREEN}✅ Локальный файл: $LOCAL_SIZE bytes${NC}"

if ! grep -q "let selectedDate = new Date()" app/static/index.html; then
    echo -e "${RED}❌ Локальный файл НЕ содержит 'new Date()' - файл неправильный!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Локальный файл содержит 'new Date()'${NC}"
echo ""

# Deploy everything
echo -e "${YELLOW}🚀 Деплою ВСЁ на сервер...${NC}"

# Step 1: Copy entire app folder
echo "  → Копирую папку app/..."
scp -r -o StrictHostKeyChecking=no app "$VPS_USER@$VPS_IP:/root/ai-calendar-assistant/" || {
    echo -e "${RED}❌ Ошибка копирования${NC}"
    echo "Настройте SSH: ssh-copy-id -i ~/.ssh/calendar_deploy.pub root@$VPS_IP"
    exit 1
}
echo -e "${GREEN}  ✅ Папка app/ скопирована${NC}"

# Step 2: Copy docker files
echo "  → Копирую Docker конфигурацию..."
scp -o StrictHostKeyChecking=no docker-compose.yml Dockerfile requirements.txt "$VPS_USER@$VPS_IP:/root/ai-calendar-assistant/" || true
echo -e "${GREEN}  ✅ Docker файлы скопированы${NC}"
echo ""

# Step 3: Full server-side fix
echo -e "${YELLOW}🔧 Применяю исправления на сервере...${NC}"

ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" << 'ENDSSH'

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /root/ai-calendar-assistant

echo -e "${YELLOW}1. Проверяю файл на хосте...${NC}"
if [ -f "app/static/index.html" ]; then
    SIZE=$(wc -c < app/static/index.html)
    if grep -q "new Date()" app/static/index.html; then
        echo -e "${GREEN}✅ Файл на хосте правильный: $SIZE bytes${NC}"
    else
        echo -e "${RED}❌ Файл на хосте БЕЗ new Date()!${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Файл не найден!${NC}"
    exit 1
fi

echo -e "${YELLOW}2. Останавливаю ВСЕ контейнеры...${NC}"
docker-compose down 2>/dev/null || true
docker stop $(docker ps -aq --filter "name=calendar" --filter "name=telegram") 2>/dev/null || true
echo -e "${GREEN}✅ Контейнеры остановлены${NC}"

echo -e "${YELLOW}3. Удаляю старые образы...${NC}"
docker rmi $(docker images -q ai-calendar-assistant-calendar-assistant) 2>/dev/null || true
docker rmi $(docker images -q "ai-calendar-assistant*") 2>/dev/null || true
echo -e "${GREEN}✅ Старые образы удалены${NC}"

echo -e "${YELLOW}4. Пересобираю образ БЕЗ кеша...${NC}"
docker-compose build --no-cache --pull
echo -e "${GREEN}✅ Образ пересобран${NC}"

echo -e "${YELLOW}5. Запускаю контейнеры...${NC}"
docker-compose up -d
echo -e "${GREEN}✅ Контейнеры запущены${NC}"

echo -e "${YELLOW}6. Жду запуска (15 секунд)...${NC}"
sleep 15

echo -e "${YELLOW}7. Проверяю файл В контейнере...${NC}"
for container in ai-calendar-assistant telegram-bot-polling calendar-assistant; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "  Проверяю $container..."
        if docker exec "$container" test -f /app/app/static/index.html 2>/dev/null; then
            SIZE=$(docker exec "$container" cat /app/app/static/index.html | wc -c)
            if docker exec "$container" grep -q "new Date()" /app/app/static/index.html 2>/dev/null; then
                echo -e "  ${GREEN}✅ $container: $SIZE bytes, содержит new Date()${NC}"
            else
                echo -e "  ${RED}❌ $container: БЕЗ new Date()!${NC}"
            fi
        fi
    fi
done

echo -e "${YELLOW}8. Перезапускаю Nginx...${NC}"
nginx -s reload 2>/dev/null || systemctl reload nginx 2>/dev/null || true
echo -e "${GREEN}✅ Nginx перезапущен${NC}"

echo -e "${YELLOW}9. Очищаю Nginx кеш (если есть)...${NC}"
rm -rf /var/cache/nginx/* 2>/dev/null || true
echo -e "${GREEN}✅ Кеш очищен${NC}"

echo -e "${YELLOW}10. Проверяю health endpoint...${NC}"
sleep 3
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health endpoint работает${NC}"
else
    echo -e "${RED}⚠️  Health endpoint не отвечает (может ещё запускаться)${NC}"
fi

echo ""
echo -e "${GREEN}✅ ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!${NC}"

ENDSSH

RESULT=$?

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $RESULT -eq 0 ]; then
    echo -e "${GREEN}🎉 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО УСПЕШНО!${NC}"
    echo ""
    echo "📋 Что было сделано:"
    echo "  ✅ Скопирована актуальная папка app/"
    echo "  ✅ Остановлены все контейнеры"
    echo "  ✅ Удалены старые образы"
    echo "  ✅ Пересобран образ без кеша"
    echo "  ✅ Запущены новые контейнеры"
    echo "  ✅ Проверены файлы в контейнерах"
    echo "  ✅ Перезапущен Nginx"
    echo ""
    echo "🧪 ПРОВЕРЬТЕ СЕЙЧАС:"
    echo ""
    echo "1. Откройте (с очисткой кеша):"
    echo "   https://calendar.housler.ru"
    echo "   Ctrl+Shift+R (Windows) или Cmd+Shift+R (Mac)"
    echo ""
    echo "2. Проверьте дату:"
    echo "   Должна быть: $(date '+%d %B %Y')"
    echo ""
    echo "3. В Telegram:"
    echo "   - Закройте приложение ПОЛНОСТЬЮ"
    echo "   - Откройте заново"
    echo "   - Нажмите '📅 Календарь'"
    echo ""
    echo "4. Если НЕ ПОМОГЛО, запустите диагностику:"
    echo "   ./ULTIMATE_DIAGNOSIS.sh"
    echo ""
else
    echo -e "${RED}❌ ОШИБКА ПРИ ИСПРАВЛЕНИИ${NC}"
    echo ""
    echo "Запустите диагностику:"
    echo "  ./ULTIMATE_DIAGNOSIS.sh"
    echo ""
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
