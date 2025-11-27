#!/bin/bash

echo "🔍 Проверка Web App на сервере"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Размер файла
echo "1️⃣ Размер HTML файла:"
SIZE=$(curl -s https://calendar.housler.ru/ | wc -c | tr -d ' ')
echo "   $SIZE bytes"
if [ "$SIZE" -eq 31934 ]; then
    echo "   ✅ Правильный размер!"
else
    echo "   ⚠️  Ожидалось: 31934 bytes"
fi
echo ""

# 2. Инициализация даты
echo "2️⃣ Инициализация даты:"
if curl -s https://calendar.housler.ru/ | grep -q "let selectedDate = new Date()"; then
    echo "   ✅ Использует new Date() - текущая дата"
else
    echo "   ❌ НЕ найдено 'new Date()'"
fi
echo ""

# 3. TODO функциональность
echo "3️⃣ TODO функциональность:"
TODO_COUNT=$(curl -s https://calendar.housler.ru/ | grep -c "todo")
echo "   TODO упоминаний: $TODO_COUNT"
if [ "$TODO_COUNT" -gt 40 ]; then
    echo "   ✅ TODO функции присутствуют"
else
    echo "   ⚠️  Мало упоминаний TODO"
fi
echo ""

# 4. Cache headers
echo "4️⃣ Cache headers:"
CACHE=$(curl -s -I https://calendar.housler.ru/ 2>&1 | grep -i "cache-control" | cut -d: -f2- | xargs)
echo "   $CACHE"
if echo "$CACHE" | grep -q "no-cache"; then
    echo "   ✅ Кеширование отключено"
else
    echo "   ⚠️  Cache headers могут быть проблемой"
fi
echo ""

# 5. Telegram Bot Menu Button
echo "5️⃣ Telegram Bot Menu Button:"
MENU_URL=$(curl -s "https://api.telegram.org/bot***REDACTED_BOT_TOKEN***/getChatMenuButton" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['result']['web_app']['url'])" 2>/dev/null)
echo "   URL: $MENU_URL"
if echo "$MENU_URL" | grep -q "calendar.housler.ru"; then
    echo "   ✅ URL правильный"
else
    echo "   ⚠️  URL может быть неправильным"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Итог:"
echo ""
if [ "$SIZE" -eq 31934 ]; then
    echo "✅ Сервер отдаёт ПРАВИЛЬНЫЙ файл!"
    echo ""
    echo "🔴 Если в Telegram показывает 30 октября - это КЕШИРОВАНИЕ!"
    echo ""
    echo "📱 РЕШЕНИЕ:"
    echo ""
    echo "1. Откройте Web Telegram: https://web.telegram.org/a/"
    echo "2. Найдите бота @aibroker_bot"
    echo "3. Нажмите '📅 Календарь'"
    echo "4. Если всё ещё старая дата:"
    echo "   - F12 → Application → Clear site data"
    echo "   - Ctrl+Shift+R"
    echo ""
    echo "ИЛИ"
    echo ""
    echo "1. Закройте Telegram ПОЛНОСТЬЮ"
    echo "2. Settings → Advanced → Clear cache"
    echo "3. Откройте заново"
    echo ""
    echo "📖 Подробная инструкция: TELEGRAM_CACHE_FIX.md"
else
    echo "⚠️  Сервер отдаёт неправильный файл"
    echo "Нужно задеплоить заново: ./deploy_webapp_now.sh"
fi
echo ""
