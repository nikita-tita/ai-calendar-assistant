#!/bin/bash

# 🔄 Обновление Telegram Menu Button с версией для очистки кеша

BOT_TOKEN="***REDACTED_BOT_TOKEN***"
VERSION=$(date +%Y%m%d%H%M)

echo "🔄 Обновляю Telegram Menu Button..."
echo "Версия: v=$VERSION"
echo ""

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setChatMenuButton" \
  -H "Content-Type: application/json" \
  -d "{
    \"menu_button\": {
      \"type\": \"web_app\",
      \"text\": \"📅 Календарь\",
      \"web_app\": {
        \"url\": \"https://calendar.housler.ru/?v=${VERSION}\"
      }
    }
  }" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

echo ""
echo "✅ Menu Button обновлён!"
echo ""
echo "📱 Теперь:"
echo "1. Закройте Telegram полностью (не просто чат, а всё приложение)"
echo "2. Откройте заново"
echo "3. Нажмите кнопку '📅 Календарь'"
echo "4. Должна загрузиться новая версия"
