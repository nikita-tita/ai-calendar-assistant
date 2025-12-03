#!/bin/bash

# 🔍 ПОЛНАЯ ДИАГНОСТИКА PRODUCTION СЕРВЕРА
# Проверяет ВСЁ: контейнеры, файлы, Nginx, процессы

VPS_IP="91.229.8.221"
VPS_USER="root"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 ПОЛНАЯ ДИАГНОСТИКА PRODUCTION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" << 'ENDSSH'

echo "1️⃣ DOCKER КОНТЕЙНЕРЫ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2️⃣ DOCKER COMPOSE ФАЙЛЫ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -la /root/ai-calendar-assistant/docker-compose*.yml 2>/dev/null || echo "Нет docker-compose файлов"
echo ""

echo "3️⃣ ПРОЦЕССЫ НА ПОРТАХ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Порт 5000 (Flask/FastAPI):"
netstat -tlnp | grep :5000 || echo "  Нет процесса на 5000"
echo "Порт 8000 (FastAPI):"
netstat -tlnp | grep :8000 || echo "  Нет процесса на 8000"
echo "Порт 80 (Nginx):"
netstat -tlnp | grep :80 || echo "  Нет процесса на 80"
echo "Порт 443 (Nginx HTTPS):"
netstat -tlnp | grep :443 || echo "  Нет процесса на 443"
echo ""

echo "4️⃣ NGINX КОНФИГУРАЦИЯ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Sites enabled:"
ls -la /etc/nginx/sites-enabled/
echo ""
echo "Конфиг для calendar.housler.ru:"
if [ -f "/etc/nginx/sites-enabled/calendar.housler.ru" ]; then
    grep -A 10 "location /" /etc/nginx/sites-enabled/calendar.housler.ru | head -15
else
    echo "  ❌ Файл не найден!"
fi
echo ""

echo "5️⃣ ФАЙЛЫ INDEX.HTML:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "На хосте:"
if [ -f "/root/ai-calendar-assistant/app/static/index.html" ]; then
    echo "  Размер: $(wc -c < /root/ai-calendar-assistant/app/static/index.html) bytes"
    if grep -q "let selectedDate = new Date()" /root/ai-calendar-assistant/app/static/index.html; then
        echo "  ✅ Содержит: new Date()"
    else
        echo "  ❌ НЕ содержит: new Date()"
    fi
else
    echo "  ❌ Файл не найден на хосте!"
fi
echo ""

echo "Внутри контейнера ai-calendar-assistant:"
if docker ps | grep -q ai-calendar-assistant; then
    echo "  Размер: $(docker exec ai-calendar-assistant cat /app/app/static/index.html 2>/dev/null | wc -c) bytes"
    if docker exec ai-calendar-assistant cat /app/app/static/index.html 2>/dev/null | grep -q "let selectedDate = new Date()"; then
        echo "  ✅ Содержит: new Date()"
    else
        echo "  ❌ НЕ содержит: new Date()"
    fi
else
    echo "  ⚠️  Контейнер не запущен"
fi
echo ""

echo "Внутри контейнера telegram-bot-polling:"
if docker ps | grep -q telegram-bot-polling; then
    echo "  Размер: $(docker exec telegram-bot-polling cat /app/app/static/index.html 2>/dev/null | wc -c) bytes"
    if docker exec telegram-bot-polling cat /app/app/static/index.html 2>/dev/null | grep -q "let selectedDate = new Date()"; then
        echo "  ✅ Содержит: new Date()"
    else
        echo "  ❌ НЕ содержит: new Date() ИЛИ файл не найден"
    fi
else
    echo "  ⚠️  Контейнер не запущен"
fi
echo ""

echo "6️⃣ DOCKER ОБРАЗЫ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker images | grep -E "ai-calendar|telegram-bot"
echo ""

echo "7️⃣ DOCKER VOLUMES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker volume ls | grep calendar
echo ""

echo "8️⃣ ЛОГИ КОНТЕЙНЕРОВ (последние 5 строк):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker ps | grep -q ai-calendar-assistant; then
    echo "ai-calendar-assistant:"
    docker logs ai-calendar-assistant --tail 5 2>&1
else
    echo "ai-calendar-assistant: не запущен"
fi
echo ""

if docker ps | grep -q telegram-bot-polling; then
    echo "telegram-bot-polling:"
    docker logs telegram-bot-polling --tail 5 2>&1
else
    echo "telegram-bot-polling: не запущен"
fi
echo ""

echo "9️⃣ ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ В КОНТЕЙНЕРАХ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if docker ps | grep -q ai-calendar-assistant; then
    echo "ai-calendar-assistant WEBAPP_URL:"
    docker exec ai-calendar-assistant env | grep WEBAPP_URL || echo "  Не задана"
fi
echo ""

echo "🔟 NGINX ЛОГИ (последние 3 строки):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -3 /var/log/nginx/access.log 2>/dev/null || echo "Нет access.log"
echo ""
tail -3 /var/log/nginx/error.log 2>/dev/null || echo "Нет error.log"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ ДИАГНОСТИКА ЗАВЕРШЕНА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

ENDSSH

echo ""
echo "📊 АНАЛИЗ ЗАВЕРШЁН"
echo ""
echo "Сохраните этот вывод и проанализируйте:"
echo "1. Какие контейнеры запущены?"
echo "2. Где находится index.html?"
echo "3. Что показывает Nginx конфиг?"
echo "4. Какие порты используются?"
echo ""
