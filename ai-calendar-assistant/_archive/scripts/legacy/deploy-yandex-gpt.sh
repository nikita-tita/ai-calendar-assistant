#!/bin/bash

# Скрипт для деплоя Yandex GPT интеграции на сервер REG.RU
# Использование: ./deploy-yandex-gpt.sh

set -e

SERVER="root@91.229.8.221"
PROJECT_DIR="/root/ai-calendar-assistant"

echo "🚀 Деплой Yandex GPT интеграции на сервер..."

# Проверяем, что файлы существуют локально
if [ ! -f "app/services/llm_agent_yandex.py" ]; then
    echo "❌ Ошибка: app/services/llm_agent_yandex.py не найден!"
    exit 1
fi

echo "📦 Создаем архив с обновленными файлами..."
tar -czf yandex-gpt-update.tar.gz \
    app/services/llm_agent_yandex.py \
    app/services/telegram_handler.py \
    app/config.py \
    requirements.txt

echo "📤 Загружаем файлы на сервер..."
# Используем scp с паролем
sshpass -p 'Aollewtyn99' scp yandex-gpt-update.tar.gz "$SERVER:$PROJECT_DIR/"

echo "📂 Распаковываем файлы на сервере..."
sshpass -p 'Aollewtyn99' ssh "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant

# Распаковываем
tar -xzf yandex-gpt-update.tar.gz

# Удаляем архив
rm yandex-gpt-update.tar.gz

echo "✅ Файлы обновлены"
ls -lah app/services/llm_agent_yandex.py

ENDSSH

echo "🔄 Перезапускаем бота с обновленным кодом..."
sshpass -p 'Aollewtyn99' ssh "$SERVER" << 'ENDSSH'
cd /root/ai-calendar-assistant

# Останавливаем старые контейнеры
docker-compose -f docker-compose.production.yml down

# Пересобираем образ с новым кодом
docker-compose -f docker-compose.production.yml up -d --build

echo "⏳ Ждем 5 секунд..."
sleep 5

echo "📋 Логи бота:"
docker logs telegram-bot --tail 30

ENDSSH

# Удаляем локальный архив
rm yandex-gpt-update.tar.gz

echo ""
echo "✅ Деплой завершен!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Получи API ключи Yandex Cloud (см. YANDEX_GPT_SETUP.md)"
echo "2. Добавь их в .env на сервере:"
echo "   ssh root@91.229.8.221"
echo "   nano /root/ai-calendar-assistant/.env"
echo "   # Добавь:"
echo "   YANDEX_GPT_API_KEY=твой_ключ"
echo "   YANDEX_GPT_FOLDER_ID=твой_folder_id"
echo "3. Перезапусти бота:"
echo "   docker-compose -f docker-compose.production.yml restart"
echo "4. Протестируй: 'Встреча с Петровым завтра в 14:00'"
echo ""
