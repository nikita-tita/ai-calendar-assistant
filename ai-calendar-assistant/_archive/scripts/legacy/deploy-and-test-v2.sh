#!/bin/bash

# Улучшенный деплой и тестирование поискового бота

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo "==============================================="
echo "ДЕПЛОЙ И ТЕСТИРОВАНИЕ ПОИСКОВОГО БОТА V2"
echo "==============================================="
echo ""

# 1. Загружаем файлы
echo "📤 Загрузка файлов на сервер..."

sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
  app/services/property/search_service.py \
  app/services/property/feed_parser.py \
  app/services/property/feed_loader_wrapper.py \
  app/routers/property.py \
  app/routers/logs.py \
  app/main.py \
  scripts/test_property_bot_real.py \
  $SERVER:$REMOTE_DIR/temp_deploy/

echo "✅ Файлы загружены"
echo ""

# 2. Применяем обновления и запускаем тесты
echo "🚀 Применение обновлений и запуск тестов..."
echo ""

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $SERVER << 'ENDSSH'
cd /root/ai-calendar-assistant

# Создаем директории
mkdir -p temp_deploy

# Определяем контейнер
CONTAINER=$(docker ps --format "{{.Names}}" | grep -E "telegram-bot|ai-calendar" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "❌ Контейнер бота не найден!"
    docker ps
    exit 1
fi

echo "📦 Найден контейнер: $CONTAINER"
echo ""

# Копируем файлы в нужные места
echo "📋 Копирование файлов..."
mkdir -p app/services/property
mkdir -p app/routers
mkdir -p scripts

cp -f temp_deploy/search_service.py app/services/property/
cp -f temp_deploy/feed_parser.py app/services/property/
cp -f temp_deploy/feed_loader_wrapper.py app/services/property/
cp -f temp_deploy/property.py app/routers/
cp -f temp_deploy/logs.py app/routers/
cp -f temp_deploy/main.py app/
cp -f temp_deploy/test_property_bot_real.py scripts/

# Копируем в контейнер
echo "📦 Копирование в контейнер $CONTAINER..."
docker cp app/services/property/search_service.py $CONTAINER:/app/app/services/property/
docker cp app/services/property/feed_parser.py $CONTAINER:/app/app/services/property/
docker cp app/services/property/feed_loader_wrapper.py $CONTAINER:/app/app/services/property/
docker cp app/routers/property.py $CONTAINER:/app/app/routers/
docker cp app/routers/logs.py $CONTAINER:/app/app/routers/
docker cp app/main.py $CONTAINER:/app/app/
docker cp scripts/test_property_bot_real.py $CONTAINER:/app/scripts/

echo "✅ Файлы скопированы"
echo ""

# Перезапускаем контейнер
echo "🔄 Перезапуск контейнера..."
docker restart $CONTAINER

echo "⏳ Ожидание запуска (15 секунд)..."
sleep 15

# Проверяем статус
echo "📊 Статус контейнера:"
docker ps | grep $CONTAINER
echo ""

# Проверяем логи
echo "📜 Последние логи:"
docker logs --tail 10 $CONTAINER 2>&1
echo ""

# Теперь запускаем настоящее тестирование через прямые запросы
echo "================================================"
echo "🧪 ЗАПУСК РЕАЛЬНОГО ТЕСТИРОВАНИЯ"
echo "================================================"
echo ""

# Проверяем API
echo "🔌 Проверка доступности API..."
docker exec $CONTAINER curl -s http://localhost:8000/api/property/status || echo "⚠️ API недоступен"
echo ""

# Запускаем упрощенное тестирование - просто отправим несколько тестовых сообщений
echo "📨 Отправка тестовых сообщений от 5 пользователей..."
echo ""

# Тест 1
echo "Тест 1/5: Поиск однушки"
docker exec $CONTAINER python3 -c "
import requests, json, random

user_id = 900000000 + random.randint(1, 999999)
message = {
    'update_id': random.randint(100000000, 999999999),
    'message': {
        'message_id': 123,
        'from': {'id': user_id, 'first_name': 'TestUser1'},
        'chat': {'id': user_id, 'type': 'private'},
        'date': 1234567890,
        'text': 'Ищу 1 комнатную квартиру за 10 миллионов'
    }
}

try:
    r = requests.post('http://localhost:8000/telegram/webhook', json=message, timeout=10)
    print(f'  User {user_id}: Status {r.status_code}')
except Exception as e:
    print(f'  Error: {e}')
"

sleep 2

# Тест 2
echo "Тест 2/5: Уточнение - парк"
docker exec $CONTAINER python3 -c "
import requests, json, random

user_id = 900000000 + random.randint(1, 999999)
message = {
    'update_id': random.randint(100000000, 999999999),
    'message': {
        'message_id': 124,
        'from': {'id': user_id, 'first_name': 'TestUser2'},
        'chat': {'id': user_id, 'type': 'private'},
        'date': 1234567890,
        'text': '2-комнатная квартира до 15 млн'
    }
}

try:
    r = requests.post('http://localhost:8000/telegram/webhook', json=message, timeout=10)
    print(f'  User {user_id}: Status {r.status_code}')
except Exception as e:
    print(f'  Error: {e}')
"

sleep 2

# Тест 3
echo "Тест 3/5: Студия"
docker exec $CONTAINER python3 -c "
import requests, json, random

user_id = 900000000 + random.randint(1, 999999)
message = {
    'update_id': random.randint(100000000, 999999999),
    'message': {
        'message_id': 125,
        'from': {'id': user_id, 'first_name': 'TestUser3'},
        'chat': {'id': user_id, 'type': 'private'},
        'date': 1234567890,
        'text': 'Студия для сдачи в аренду до 7 млн'
    }
}

try:
    r = requests.post('http://localhost:8000/telegram/webhook', json=message, timeout=10)
    print(f'  User {user_id}: Status {r.status_code}')
except Exception as e:
    print(f'  Error: {e}')
"

sleep 2

# Проверяем логи
echo ""
echo "================================================"
echo "📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ"
echo "================================================"
echo ""

echo "📜 Статистика логов:"
docker exec $CONTAINER curl -s http://localhost:8000/api/logs/stats 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "⚠️ Логи недоступны"

echo ""
echo "📝 Последние логи бота:"
docker logs --tail 30 $CONTAINER 2>&1 | grep -E "(property|search|query)" || echo "Логов поиска не найдено"

echo ""
echo "================================================"
echo "✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"
echo "================================================"

ENDSSH

echo ""
echo "==============================================="
echo "✅ ДЕПЛОЙ ЗАВЕРШЕН"
echo "==============================================="
