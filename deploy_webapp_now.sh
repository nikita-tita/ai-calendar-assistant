#!/bin/bash

# 🚀 Деплой обновлённого Web App на production
# Этот скрипт обновит только app/static/index.html

set -e

VPS_IP="91.229.8.221"
VPS_USER="root"
LOCAL_FILE="app/static/index.html"
REMOTE_DIR="/root/ai-calendar-assistant/app/static"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Деплой Web App на calendar.housler.ru"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверяем наличие локального файла
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ Ошибка: Файл $LOCAL_FILE не найден!"
    echo "Убедитесь, что вы в папке ai-calendar-assistant"
    exit 1
fi

echo "1️⃣ Проверяю локальный файл..."
FILE_SIZE=$(wc -c < "$LOCAL_FILE" | tr -d ' ')
echo "✅ Файл найден: $LOCAL_FILE ($FILE_SIZE bytes)"
echo ""

# Проверяем текущую дату в файле
echo "2️⃣ Проверяю инициализацию даты в локальном файле..."
if grep -q "let selectedDate = new Date()" "$LOCAL_FILE"; then
    echo "✅ Использует new Date() - текущая дата"
else
    echo "⚠️  Внимание: не найдено 'new Date()'"
fi
echo ""

# Создаём backup на сервере и копируем файл
echo "3️⃣ Деплою файл на сервер..."
echo "Потребуется пароль VPS: root@$VPS_IP"
echo ""

# Используем scp с запросом пароля
scp -o StrictHostKeyChecking=no "$LOCAL_FILE" "$VPS_USER@$VPS_IP:$REMOTE_DIR/index.html.new" || {
    echo ""
    echo "❌ Ошибка копирования файла"
    echo ""
    echo "Возможные причины:"
    echo "1. Неверный пароль VPS"
    echo "2. SSH доступ заблокирован"
    echo "3. Проблемы с сетью"
    echo ""
    echo "💡 Попробуйте:"
    echo "1. Проверьте пароль VPS"
    echo "2. Настройте SSH ключ: ssh-copy-id -i ~/.ssh/calendar_deploy.pub root@$VPS_IP"
    echo ""
    exit 1
}

echo "✅ Файл скопирован на сервер"
echo ""

# Создаём backup и перемещаем новый файл
echo "4️⃣ Создаю backup и применяю изменения..."
ssh -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" << 'ENDSSH'
cd /root/ai-calendar-assistant/app/static

# Создаём backup
if [ -f "index.html" ]; then
    cp index.html "index.html.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ Backup создан"
fi

# Применяем новый файл
mv index.html.new index.html
echo "✅ Новый файл применён"

# Проверяем что файл правильный
if grep -q "new Date()" index.html; then
    echo "✅ Файл содержит правильную инициализацию даты"
else
    echo "⚠️  Внимание: не найдено 'new Date()' в новом файле"
fi

# Перезапускаем Nginx для очистки кеша
nginx -s reload 2>/dev/null || echo "⚠️  Не удалось перезапустить Nginx (не критично)"

echo "✅ Изменения применены"
ENDSSH

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Деплой завершён!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Web App обновлён на production"
echo ""
echo "📋 Проверьте работу:"
echo "1. Откройте (с очисткой кеша):"
echo "   https://calendar.housler.ru"
echo "   Нажмите Ctrl+F5 (Windows) или Cmd+Shift+R (Mac)"
echo ""
echo "2. Проверьте дату:"
echo "   Должна быть: $(date '+%d %B %Y')"
echo ""
echo "3. Проверьте TODO:"
echo "   Вкладка 'Дела' должна показывать задачи"
echo ""
echo "4. В Telegram:"
echo "   Бот → Кнопка '📅 Календарь' → должен открыть обновлённый веб-апп"
echo ""
