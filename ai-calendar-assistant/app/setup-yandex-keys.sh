#!/bin/bash
# Setup Yandex Cloud API keys

echo "🔑 Setup Yandex Cloud API Keys"
echo ""
echo "Следуйте инструкции:"
echo ""
echo "1️⃣  Откройте https://console.cloud.yandex.ru/"
echo "2️⃣  Войдите в свой аккаунт"
echo "3️⃣  Перейдите в раздел 'Сервисные аккаунты'"
echo "4️⃣  Создайте новый сервисный аккаунт (если нет)"
echo "5️⃣  Назначьте роль 'ai.languageModels.user'"
echo "6️⃣  Создайте API-ключ"
echo "7️⃣  Скопируйте Folder ID из URL (b1gxxxxxxxxxxxxx)"
echo ""
echo "──────────────────────────────────────"
echo ""

read -p "Введите YANDEX_GPT_API_KEY (формат: AQVNxxx...): " API_KEY
read -p "Введите YANDEX_GPT_FOLDER_ID (формат: b1gxxx...): " FOLDER_ID

if [[ -z "$API_KEY" ]] || [[ -z "$FOLDER_ID" ]]; then
    echo "❌ Ошибка: оба ключа обязательны!"
    exit 1
fi

echo ""
echo "✅ Ключи получены. Обновляю конфигурацию..."

# Update .env on server
SERVER="root@95.163.227.26"
PASSWORD="$SERVER_PASSWORD"

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
# Backup current .env
cp /root/ai-calendar-assistant/.env /root/ai-calendar-assistant/.env.backup-\$(date +%Y%m%d-%H%M%S)

# Update Yandex keys
sed -i 's/YANDEX_GPT_API_KEY=.*/YANDEX_GPT_API_KEY=$API_KEY/' /root/ai-calendar-assistant/.env
sed -i 's/YANDEX_GPT_FOLDER_ID=.*/YANDEX_GPT_FOLDER_ID=$FOLDER_ID/' /root/ai-calendar-assistant/.env

echo '✅ .env updated'
cat /root/ai-calendar-assistant/.env | grep YANDEX
"

echo ""
echo "🔄 Перезапускаю бот с новыми ключами..."

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
cd /root/ai-calendar-assistant &&
docker-compose -f docker-compose.hybrid.yml restart telegram-bot
"

sleep 5

echo ""
echo "✅ Готово! Проверяю статус..."

sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
docker ps | grep telegram-bot &&
echo '---' &&
docker logs --tail 20 telegram-bot 2>&1 | tail -10
"

echo ""
echo "🧪 Протестируйте:"
echo "  1. Отправьте голосовое сообщение в бот"
echo "  2. Создайте событие текстом"
echo ""
