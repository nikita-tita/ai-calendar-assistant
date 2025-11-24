#!/bin/bash

# Деплой улучшенного кода и запуск реальных тестов поискового бота

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo "==============================================="
echo "ДЕПЛОЙ И ТЕСТИРОВАНИЕ ПОИСКОВОГО БОТА"
echo "==============================================="
echo ""

# 1. Загружаем обновленные файлы на сервер
echo "📤 Шаг 1/5: Загрузка обновленных файлов..."

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
  app/services/property/search_service.py \
  app/services/property/feed_parser.py \
  app/services/property/feed_loader_wrapper.py \
  app/routers/property.py \
  app/routers/logs.py \
  app/main.py \
  $SERVER:$REMOTE_DIR/app_updates/

if [ $? -ne 0 ]; then
    echo "❌ Ошибка загрузки файлов"
    exit 1
fi

echo "✅ Файлы загружены"
echo ""

# 2. Загружаем тестовый скрипт
echo "📤 Шаг 2/5: Загрузка тестового скрипта..."

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
  scripts/test_property_bot_real.py \
  $SERVER:$REMOTE_DIR/scripts/

echo "✅ Тестовый скрипт загружен"
echo ""

# 3. Применяем обновления на сервере
echo "🔧 Шаг 3/5: Применение обновлений..."

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

# Создаем директории если их нет
mkdir -p app_updates
mkdir -p app/services/property
mkdir -p app/routers

# Копируем обновленные файлы
cp -f app_updates/search_service.py app/services/property/ 2>/dev/null
cp -f app_updates/feed_parser.py app/services/property/ 2>/dev/null
cp -f app_updates/feed_loader_wrapper.py app/services/property/ 2>/dev/null
cp -f app_updates/property.py app/routers/ 2>/dev/null
cp -f app_updates/logs.py app/routers/ 2>/dev/null
cp -f app_updates/main.py app/ 2>/dev/null

echo "✅ Файлы скопированы"

# Копируем файлы в контейнер
docker cp app/services/property/search_service.py telegram-bot:/app/app/services/property/ 2>/dev/null
docker cp app/services/property/feed_parser.py telegram-bot:/app/app/services/property/ 2>/dev/null
docker cp app/services/property/feed_loader_wrapper.py telegram-bot:/app/app/services/property/ 2>/dev/null
docker cp app/routers/property.py telegram-bot:/app/app/routers/ 2>/dev/null
docker cp app/routers/logs.py telegram-bot:/app/app/routers/ 2>/dev/null
docker cp app/main.py telegram-bot:/app/app/ 2>/dev/null
docker cp scripts/test_property_bot_real.py telegram-bot:/app/scripts/ 2>/dev/null

echo "✅ Файлы скопированы в контейнер"

ENDSSH

echo "✅ Обновления применены"
echo ""

# 4. Перезапускаем бот
echo "🔄 Шаг 4/5: Перезапуск бота..."

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

echo "Перезапуск контейнера..."
docker restart telegram-bot

echo "Ожидание запуска (10 секунд)..."
sleep 10

# Проверяем статус
docker ps | grep telegram-bot
echo "---"
docker logs --tail 20 telegram-bot 2>&1

ENDSSH

echo "✅ Бот перезапущен"
echo ""

# 5. Запускаем тесты
echo "🧪 Шаг 5/5: Запуск реальных тестов..."
echo ""

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

echo "================================================"
echo "ЗАПУСК ТЕСТОВ С РЕАЛЬНЫМИ API ВЫЗОВАМИ"
echo "================================================"
echo ""

# Запускаем тесты внутри контейнера
docker exec telegram-bot python3 /app/scripts/test_property_bot_real.py

echo ""
echo "================================================"
echo "ТЕСТЫ ЗАВЕРШЕНЫ"
echo "================================================"
echo ""

# Показываем результаты
echo "📊 Результаты тестирования:"
docker exec telegram-bot ls -lh /app/scripts/property_bot_real_test_*.json 2>/dev/null | tail -1

# Показываем статистику логов
echo ""
echo "📜 Статистика логов:"
docker exec telegram-bot python3 -c "
import requests
try:
    response = requests.get('http://localhost:8000/api/logs/stats', timeout=5)
    if response.status_code == 200:
        import json
        stats = response.json()
        print(f\"Пользователей протестировано: {stats.get('total_users', 0)}\")
        print(f\"Всего логов: {stats.get('total_logs', 0)}\")
        print(f\"По типам: {stats.get('type_counts', {})}\")
    else:
        print(f\"Ошибка получения статистики: {response.status_code}\")
except Exception as e:
    print(f\"Не удалось получить статистику: {e}\")
" 2>/dev/null || echo "⚠️ Статистика логов недоступна"

ENDSSH

echo ""
echo "==============================================="
echo "✅ ДЕПЛОЙ И ТЕСТИРОВАНИЕ ЗАВЕРШЕНЫ"
echo "==============================================="
echo ""
echo "💡 Подсказки:"
echo "   - Результаты сохранены в property_bot_real_test_*.json"
echo "   - Логи бота: docker logs telegram-bot"
echo "   - API логов: http://91.229.8.221:8000/api/logs/recent"
echo ""
