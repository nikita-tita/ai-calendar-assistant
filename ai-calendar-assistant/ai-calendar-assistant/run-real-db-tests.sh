#!/bin/bash

# Запуск тестов с реальной БД на сервере

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"

echo "========================================"
echo "ТЕСТИРОВАНИЕ С РЕАЛЬНОЙ БАЗОЙ ДАННЫХ"
echo "========================================"
echo ""

# 1. Загружаем скрипт
echo "📤 Загрузка тестового скрипта..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
  scripts/test_with_real_db.py \
  $SERVER:/root/ai-calendar-assistant/scripts/

echo "✅ Скрипт загружен"
echo ""

# 2. Запускаем тесты на сервере
echo "🧪 Запуск тестов..."
echo ""

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

# Определяем контейнер
CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "telegram-bot|ai-calendar" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "❌ Контейнер не найден!"
    exit 1
fi

echo "📦 Используем контейнер: $CONTAINER"
echo ""

# Копируем скрипт в контейнер
docker cp scripts/test_with_real_db.py $CONTAINER:/app/scripts/

# Проверяем БД
echo "🔍 Проверка базы данных..."
docker exec property-bot-db psql -U property_user -d property_bot -c "SELECT COUNT(*) as total FROM property_listings;" 2>&1
echo ""

# Запускаем тесты
echo "================================"
echo "🚀 ЗАПУСК ТЕСТОВ"
echo "================================"
echo ""

docker exec $CONTAINER python3 /app/scripts/test_with_real_db.py 2>&1

echo ""
echo "================================"
echo "✅ ТЕСТЫ ЗАВЕРШЕНЫ"
echo "================================"
echo ""

# Показываем результаты
echo "📁 Файлы результатов:"
docker exec $CONTAINER ls -lh /app/scripts/test_real_db_*.json 2>/dev/null | tail -3

ENDSSH

echo ""
echo "========================================"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "========================================"
