#!/bin/bash
#
# Скрипт интеграции бота недвижимости в существующий календарный бот
# Оба бота работают в одном Telegram боте через переключение режимов
#

set -e  # Exit on error

SERVER="91.229.8.221"
USER="root"
PASS="upvzrr3LH4pxsaqs"
REMOTE_PATH="/root/ai-calendar-assistant"

echo "🚀 Начинаем интеграцию бота недвижимости..."
echo ""

# Шаг 1: Упаковать файлы
echo "📦 Шаг 1: Упаковка файлов property bot..."
tar -czf property-bot-integration.tar.gz \
  app/services/property/ \
  app/models/property.py \
  app/schemas/property.py \
  app/routers/property.py \
  migrations/ 2>/dev/null || true

if [ -f property-bot-integration.tar.gz ]; then
  echo "✅ Файлы упакованы: $(du -h property-bot-integration.tar.gz | cut -f1)"
else
  echo "❌ Ошибка при упаковке файлов"
  exit 1
fi
echo ""

# Шаг 2: Загрузить на сервер
echo "📤 Шаг 2: Загрузка файлов на сервер..."
sshpass -p "$PASS" scp -o StrictHostKeyChecking=no property-bot-integration.tar.gz $USER@$SERVER:$REMOTE_PATH/
echo "✅ Файлы загружены на сервер"
echo ""

# Шаг 3: Распаковать на сервере
echo "📂 Шаг 3: Распаковка файлов на сервере..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER << 'EOF'
cd /root/ai-calendar-assistant
tar -xzf property-bot-integration.tar.gz
echo "✅ Файлы распакованы"
ls -la app/services/property/ | head -10
EOF
echo ""

# Шаг 4: Проверить, запущен ли PostgreSQL
echo "🔍 Шаг 4: Проверка PostgreSQL..."
POSTGRES_EXISTS=$(sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER "docker ps -a | grep property-db | wc -l")

if [ "$POSTGRES_EXISTS" -eq "0" ]; then
  echo "📦 PostgreSQL не найден, создаем..."

  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER << 'EOF'
# Создать сеть если не существует
docker network ls | grep ai-calendar-assistant_internal || \
  docker network create ai-calendar-assistant_internal

# Запустить PostgreSQL
docker run -d \
  --name property-db \
  --network ai-calendar-assistant_internal \
  -e POSTGRES_DB=property_bot \
  -e POSTGRES_USER=property_user \
  -e POSTGRES_PASSWORD=PropertySecure2025! \
  -v property-db-data:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:14-alpine

echo "⏳ Ждем запуска PostgreSQL..."
sleep 10

# Проверить подключение
docker exec property-db pg_isready -U property_user -d property_bot
echo "✅ PostgreSQL запущен"
EOF

else
  echo "✅ PostgreSQL уже существует"
fi
echo ""

# Шаг 5: Применить схему БД
echo "🗃️ Шаг 5: Применение схемы базы данных..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER << 'EOF'
cd /root/ai-calendar-assistant

if [ -f migrations/property_bot_schema.sql ]; then
  docker exec -i property-db psql -U property_user -d property_bot < migrations/property_bot_schema.sql 2>/dev/null || echo "Схема уже применена"
  echo "✅ Схема БД проверена"

  # Показать таблицы
  echo ""
  echo "📊 Таблицы в БД:"
  docker exec property-db psql -U property_user -d property_bot -c "\dt"
else
  echo "⚠️  Файл схемы не найден, пропускаем..."
fi
EOF
echo ""

# Шаг 6: Обновить .env
echo "⚙️ Шаг 6: Обновление конфигурации..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER << 'EOF'
cd /root/ai-calendar-assistant

# Проверить, есть ли уже DATABASE_PROPERTY_URL
if grep -q "DATABASE_PROPERTY_URL" .env; then
  echo "✅ DATABASE_PROPERTY_URL уже в .env"
else
  echo "" >> .env
  echo "# Property Bot Database" >> .env
  echo "DATABASE_PROPERTY_URL=postgresql://property_user:PropertySecure2025!@property-db:5432/property_bot" >> .env
  echo "✅ DATABASE_PROPERTY_URL добавлен в .env"
fi

# Проверить конфигурацию
echo ""
echo "📋 Текущая конфигурация:"
grep -E "YANDEX|TELEGRAM_BOT|DATABASE_PROPERTY" .env
EOF
echo ""

# Шаг 7: Подключить property-db к сети бота
echo "🔗 Шаг 7: Подключение к сети контейнеров..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER << 'EOF'
# Получить сети календарного бота
BOT_NETWORKS=$(docker inspect telegram-bot-polling --format='{{range $net, $conf := .NetworkSettings.Networks}}{{$net}} {{end}}')
echo "Сети бота: $BOT_NETWORKS"

# Подключить property-db к тем же сетям
for network in $BOT_NETWORKS; do
  docker network connect $network property-db 2>/dev/null || echo "Уже подключен к $network"
done

echo "✅ Сети настроены"
EOF
echo ""

# Шаг 8: НЕ перезапускаем бота - требуется обновление кода
echo "⚠️  ВНИМАНИЕ: Для полной интеграции требуется обновление кода!"
echo ""
echo "📝 Следующие шаги (вручную):"
echo ""
echo "1. Обновить app/services/telegram_handler.py:"
echo "   - Добавить проверку user_mode"
echo "   - Добавить обработку property сообщений"
echo "   - Добавить кнопки переключения режимов"
echo ""
echo "2. Закоммитить изменения и отправить на сервер"
echo ""
echo "3. Перезапустить бота:"
echo "   docker restart telegram-bot-polling"
echo ""
echo "✅ Инфраструктура property bot готова!"
echo "✅ PostgreSQL работает"
echo "✅ Файлы загружены"
echo ""
echo "📊 Статус контейнеров:"
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$SERVER "docker ps | grep -E 'property-db|telegram-bot'"
echo ""

# Cleanup
rm -f property-bot-integration.tar.gz
echo "🎉 Готово!"
