#!/bin/bash
# Полное обновление всех файлов на сервере без потери данных
# Использование: ./deploy-full-update.sh

set -e

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

echo "🚀 Начинаем полное обновление AI Calendar Assistant..."

# Функция для выполнения команд через SSH
ssh_exec() {
    sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "$@"
}

# Функция для копирования файлов
scp_upload() {
    sshpass -p "$PASSWORD" scp -r -o StrictHostKeyChecking=no "$@"
}

echo "📦 1. Загрузка файлов на сервер..."

# Загружаем основные файлы приложения
scp_upload app/main.py "$SERVER:$REMOTE_DIR/app/"
scp_upload app/config.py "$SERVER:$REMOTE_DIR/app/"

# Загружаем все сервисы
echo "   - Загрузка services..."
scp_upload app/services/*.py "$SERVER:$REMOTE_DIR/app/services/"

# Загружаем роутеры
echo "   - Загрузка routers..."
scp_upload app/routers/*.py "$SERVER:$REMOTE_DIR/app/routers/"

# Загружаем модели
echo "   - Загрузка models..."
scp_upload app/models/ "$SERVER:$REMOTE_DIR/app/"

# Загружаем утилиты
echo "   - Загрузка utils..."
scp_upload app/utils/ "$SERVER:$REMOTE_DIR/app/"

# Загружаем schemas
echo "   - Загрузка schemas..."
scp_upload app/schemas/ "$SERVER:$REMOTE_DIR/app/"

# Загружаем WebApp
echo "   - Загрузка WebApp..."
scp_upload webapp_server.html "$SERVER:/var/www/calendar/index.html"

echo "🐳 2. Копирование файлов в Docker контейнер..."

# Копируем всё в контейнер
ssh_exec "
docker cp $REMOTE_DIR/app/main.py telegram-bot:/app/app/main.py
docker cp $REMOTE_DIR/app/config.py telegram-bot:/app/app/config.py
docker cp $REMOTE_DIR/app/services telegram-bot:/app/app/
docker cp $REMOTE_DIR/app/routers telegram-bot:/app/app/
docker cp $REMOTE_DIR/app/models telegram-bot:/app/app/
docker cp $REMOTE_DIR/app/utils telegram-bot:/app/app/
docker cp $REMOTE_DIR/app/schemas telegram-bot:/app/app/
"

echo "🔄 3. Перезапуск бота..."
ssh_exec "docker restart telegram-bot"

echo "⏳ Ожидание запуска (15 секунд)..."
sleep 15

echo "✅ 4. Проверка статуса..."
ssh_exec "docker ps | grep telegram-bot"

echo ""
echo "🎉 Обновление завершено!"
echo ""
echo "📊 Проверьте:"
echo "   - Бот: отправьте /start в Telegram"
echo "   - Админка: https://этонесамыйдлинныйдомен.рф/admin_fbc36dd546d7746b862e45a7.html"
echo "   - WebApp: откройте через бота"
echo ""
echo "💾 Данные пользователей сохранены:"
ssh_exec "docker exec telegram-bot ls -lh /var/lib/calendar-bot/"
echo ""
