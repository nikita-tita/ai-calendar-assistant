#!/bin/bash

# 🚀 Быстрый деплой calendar.housler.ru - ВСЁ В ОДНОЙ КОМАНДЕ
# Запустите этот скрипт и введите пароль VPS один раз

set -e

VPS_IP="91.229.8.221"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/calendar_deploy"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Настройка calendar.housler.ru"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Проверяем DNS
echo "1️⃣ Проверяю DNS..."
DNS_IP=$(nslookup calendar.housler.ru 8.8.8.8 | grep "Address:" | tail -1 | awk '{print $2}')
if [ "$DNS_IP" == "$VPS_IP" ]; then
    echo "✅ DNS настроен: calendar.housler.ru → $VPS_IP"
else
    echo "❌ DNS не настроен. Ожидалось: $VPS_IP, получено: $DNS_IP"
    exit 1
fi

# Проверяем SSH ключ
echo ""
echo "2️⃣ Проверяю SSH доступ..."
if ssh -i "$SSH_KEY" -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$VPS_USER@$VPS_IP" "echo 'OK'" &>/dev/null; then
    echo "✅ SSH ключ уже настроен!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 Запускаю автоматическую настройку..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    exec ./auto_setup_calendar.sh
else
    echo "⚠️  SSH ключ не настроен"
    echo ""
    echo "Сейчас добавлю SSH ключ на VPS."
    echo "Вам нужно будет ввести пароль VPS ОДИН РАЗ."
    echo ""
    read -p "Нажмите Enter для продолжения..."
    echo ""

    # Добавляем SSH ключ
    if ssh-copy-id -i "${SSH_KEY}.pub" "$VPS_USER@$VPS_IP"; then
        echo ""
        echo "✅ SSH ключ добавлен!"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "🚀 Запускаю автоматическую настройку..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        exec ./auto_setup_calendar.sh
    else
        echo ""
        echo "❌ Не удалось добавить SSH ключ"
        echo ""
        echo "Возможные причины:"
        echo "1. Неверный пароль VPS"
        echo "2. SSH сервер не принимает ключи"
        echo ""
        echo "📖 Что делать:"
        echo "1. Проверьте пароль VPS (root@91.229.8.221)"
        echo "2. Следуйте инструкции: ADD_SSH_KEY.md"
        echo ""
        exit 1
    fi
fi
