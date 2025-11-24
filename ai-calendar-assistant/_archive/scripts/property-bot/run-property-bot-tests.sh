#!/bin/bash

# Скрипт для запуска комплексных тестов поискового бота на сервере

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo "================================"
echo "ЗАПУСК ТЕСТОВ ПОИСКОВОГО БОТА"
echo "================================"
echo ""

# Загружаем файлы на сервер
echo "📤 Загрузка тестов на сервер..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
  scripts/test_property_bot_comprehensive.py \
  app/services/property/search_service.py \
  app/services/property/feed_parser.py \
  app/services/property/feed_loader_wrapper.py \
  $SERVER:$REMOTE_DIR/temp_test/

if [ $? -ne 0 ]; then
    echo "❌ Ошибка загрузки файлов"
    exit 1
fi

echo "✅ Файлы загружены"
echo ""

# Запускаем тесты на сервере
echo "🚀 Запуск тестов на сервере..."
echo ""

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

# Создаем временную директорию если её нет
mkdir -p temp_test/app/services/property

# Копируем файлы в правильные места
cp -f temp_test/test_property_bot_comprehensive.py scripts/
cp -f temp_test/search_service.py app/services/property/
cp -f temp_test/feed_parser.py app/services/property/
cp -f temp_test/feed_loader_wrapper.py app/services/property/

# Запускаем тесты через docker
docker exec telegram-bot python3 /app/scripts/test_property_bot_comprehensive.py

# Сохраняем результаты
docker exec telegram-bot ls -la /app/scripts/property_bot_test_results_*.json 2>/dev/null

ENDSSH

echo ""
echo "================================"
echo "ТЕСТЫ ЗАВЕРШЕНЫ"
echo "================================"
