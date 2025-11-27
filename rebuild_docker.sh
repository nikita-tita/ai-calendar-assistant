#!/bin/bash

# 🔥 ПРОБЛЕМА НАЙДЕНА!
# Docker образ содержит СТАРЫЙ index.html внутри!
# Dockerfile копирует app/* при СБОРКЕ образа (строка 32)
# Нужно ПЕРЕСОБРАТЬ образ!

set -e

VPS_IP="91.229.8.221"
VPS_USER="root"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔥 НАЙДЕНА ПРОБЛЕМА!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Docker образ содержит СТАРЫЙ index.html!"
echo ""
echo "Dockerfile (строка 32): COPY app ./app"
echo "Это копирует файлы при СБОРКЕ образа."
echo ""
echo "Решение: Пересобрать Docker образ на сервере"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверяем наличие локального файла
if [ ! -f "app/static/index.html" ]; then
    echo "❌ Ошибка: app/static/index.html не найден!"
    exit 1
fi

echo "1️⃣ Проверяю локальный файл..."
LOCAL_SIZE=$(wc -c < app/static/index.html | tr -d ' ')
echo "   Размер: $LOCAL_SIZE bytes"

if [ "$LOCAL_SIZE" -ne 31934 ]; then
    echo "   ⚠️  Предупреждение: ожидался размер 31934 bytes"
fi

if grep -q "let selectedDate = new Date()" app/static/index.html; then
    echo "   ✅ Использует new Date() - правильно!"
else
    echo "   ❌ НЕ найдено 'new Date()' - файл неправильный!"
    exit 1
fi
echo ""

echo "2️⃣ Копирую всю папку app на сервер..."
echo "   Потребуется пароль VPS: root@$VPS_IP"
echo ""

# Копируем всю папку app
scp -r -o StrictHostKeyChecking=no app "$VPS_USER@$VPS_IP:/root/ai-calendar-assistant/" || {
    echo ""
    echo "❌ Ошибка копирования"
    echo ""
    echo "Настройте SSH ключ: ssh-copy-id -i ~/.ssh/calendar_deploy.pub root@$VPS_IP"
    exit 1
}

echo ""
echo "✅ Папка app скопирована"
echo ""

echo "3️⃣ Пересобираю Docker образ на сервере..."
ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" << 'ENDSSH'
cd /root/ai-calendar-assistant

echo "   📦 Останавливаю контейнер..."
docker-compose down

echo "   🔨 Пересобираю образ (это займёт 1-2 минуты)..."
docker-compose build --no-cache calendar-assistant

echo "   🚀 Запускаю обновлённый контейнер..."
docker-compose up -d

echo "   ⏳ Жду запуска (10 секунд)..."
sleep 10

echo "   🏥 Проверяю health check..."
if docker-compose ps | grep -q "healthy\|Up"; then
    echo "   ✅ Контейнер запущен!"
else
    echo "   ⚠️  Контейнер может ещё запускаться, проверьте логи"
fi

echo ""
echo "   📊 Проверяю файл внутри контейнера..."
FILE_SIZE=$(docker exec ai-calendar-assistant cat /app/app/static/index.html | wc -c)
echo "   Размер внутри контейнера: $FILE_SIZE bytes"

if docker exec ai-calendar-assistant cat /app/app/static/index.html | grep -q "let selectedDate = new Date()"; then
    echo "   ✅ Файл внутри контейнера правильный!"
else
    echo "   ❌ Файл внутри контейнера неправильный!"
fi

echo ""
echo "✅ Пересборка завершена!"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Готово!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Docker образ пересобран с новым index.html"
echo ""
echo "📋 Проверьте:"
echo "1. Откройте (БЕЗ кеша!):"
echo "   https://calendar.housler.ru"
echo "   Ctrl+Shift+R (Windows) или Cmd+Shift+R (Mac)"
echo ""
echo "2. Проверьте дату:"
echo "   Должна быть: $(date '+%d %B %Y')"
echo ""
echo "3. В Telegram:"
echo "   Закройте и откройте заново"
echo "   Нажмите кнопку '📅 Календарь'"
echo ""
echo "📊 Логи контейнера:"
echo "ssh root@$VPS_IP 'docker logs ai-calendar-assistant --tail 50'"
echo ""
