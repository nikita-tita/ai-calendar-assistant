#!/bin/bash

# Автоматическая установка AI Calendar Bot на VPS
# Поддержка: Ubuntu 20.04/22.04

set -e

echo "🤖 AI Calendar Bot - Установка на VPS"
echo "======================================"
echo ""

# Проверка root прав
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root: sudo bash install.sh"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
apt-get update -qq
apt-get upgrade -y -qq

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
else
    echo "✅ Docker уже установлен"
fi

# Установка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Установка Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    echo "✅ Docker Compose уже установлен"
fi

# Установка Git
if ! command -v git &> /dev/null; then
    echo "📚 Установка Git..."
    apt-get install -y git
else
    echo "✅ Git уже установлен"
fi

# Клонирование репозитория
echo "📥 Загрузка бота..."
cd /root
if [ -d "ai-calendar-assistant" ]; then
    echo "📂 Обновление существующего репозитория..."
    cd ai-calendar-assistant
    git pull
else
    git clone https://github.com/nikita-tita/ai-calendar-bot.git ai-calendar-assistant
    cd ai-calendar-assistant
fi

# Создание .env файла
echo ""
echo "⚙️  Настройка переменных окружения"
echo "===================================="
echo ""

# Запрос токена Telegram
read -p "Введите TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Токен не может быть пустым!"
    exit 1
fi

# Запрос OpenAI API ключа
read -p "Введите OPENAI_API_KEY: " OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ API ключ не может быть пустым!"
    exit 1
fi

# Запрос Radicale URL
read -p "Введите RADICALE_URL [https://calendar-bot-production-e1ac.up.railway.app]: " RADICALE_URL
RADICALE_URL=${RADICALE_URL:-https://calendar-bot-production-e1ac.up.railway.app}

# Создание .env
cat > .env << EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN

# OpenAI
OPENAI_API_KEY=$OPENAI_API_KEY

# Calendar Service
RADICALE_URL=$RADICALE_URL

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

echo "✅ Файл .env создан"

# Создание docker-compose.production.yml
cat > docker-compose.production.yml << 'EOF'
version: '3.8'

services:
  telegram-bot:
    container_name: telegram-bot
    build:
      context: .
      dockerfile: Dockerfile.bot
    env_file:
      - .env
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

echo "✅ Docker Compose конфигурация создана"

# Сборка и запуск
echo ""
echo "🚀 Запуск бота..."
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build

# Ожидание запуска
echo "⏳ Ожидание запуска бота..."
sleep 5

# Проверка статуса
if docker ps | grep -q telegram-bot; then
    echo ""
    echo "✅ Бот успешно запущен!"
    echo ""
    echo "📊 Статус:"
    docker ps | grep telegram-bot
    echo ""
    echo "📋 Полезные команды:"
    echo "  Логи:        docker logs -f telegram-bot"
    echo "  Перезапуск:  docker restart telegram-bot"
    echo "  Остановка:   docker stop telegram-bot"
    echo "  Статус:      docker ps"
    echo ""
    echo "🎉 Бот работает 24/7!"
else
    echo ""
    echo "❌ Ошибка запуска бота!"
    echo "Проверьте логи: docker logs telegram-bot"
    exit 1
fi
