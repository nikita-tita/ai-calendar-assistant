#!/bin/bash

# Скрипт установки AI Calendar Bot из архива
# Запускается НА СЕРВЕРЕ после загрузки архива

set -e

echo "🚀 Установка AI Calendar Bot из архива"
echo "======================================"
echo ""

# Проверка root прав
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root"
    exit 1
fi

# Поиск архива
ARCHIVE_PATH=""
if [ -f "/root/ai-calendar-bot-deploy.tar.gz" ]; then
    ARCHIVE_PATH="/root/ai-calendar-bot-deploy.tar.gz"
elif [ -f "/tmp/ai-calendar-bot-deploy.tar.gz" ]; then
    ARCHIVE_PATH="/tmp/ai-calendar-bot-deploy.tar.gz"
elif [ -f "./ai-calendar-bot-deploy.tar.gz" ]; then
    ARCHIVE_PATH="./ai-calendar-bot-deploy.tar.gz"
else
    echo "❌ Архив ai-calendar-bot-deploy.tar.gz не найден!"
    echo "Загрузите его на сервер в /root/ или /tmp/"
    exit 1
fi

echo "✅ Найден архив: ${ARCHIVE_PATH}"
echo ""

# Установка Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен"
fi

# Установка Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Установка Docker Compose..."
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен"
else
    echo "✅ Docker Compose уже установлен"
fi

# Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p /root/ai-calendar-assistant
cd /root/ai-calendar-assistant

# Распаковка архива
echo "📦 Распаковка архива..."
tar -xzf ${ARCHIVE_PATH} -C /root/ai-calendar-assistant/
echo "✅ Архив распакован"

# Создание дополнительных директорий
mkdir -p logs credentials radicale_config

# Проверка .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте его вручную или скопируйте из .env.example"

    if [ -f .env.example ]; then
        echo "Создать .env из .env.example? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            cp .env.example .env
            echo "✅ Файл .env создан. ОБЯЗАТЕЛЬНО отредактируйте его!"
            echo "nano .env"
            exit 0
        fi
    fi
    exit 1
fi

echo "✅ Файл .env найден"

# Проверка docker-compose.production.yml
if [ ! -f docker-compose.production.yml ]; then
    echo "📝 Создание docker-compose.production.yml..."
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
    volumes:
      - ./logs:/app/logs
      - ./credentials:/app/credentials
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF
fi

# Остановка старой версии
echo "🛑 Остановка предыдущей версии..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Сборка и запуск
echo "🏗️  Сборка Docker образа..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🚀 Запуск бота..."
docker-compose -f docker-compose.production.yml up -d

# Ожидание
echo "⏳ Ожидание запуска (10 секунд)..."
sleep 10

# Проверка
echo ""
echo "📊 Статус:"
docker ps --filter name=telegram-bot

echo ""
if docker ps | grep -q telegram-bot; then
    echo "✅ Бот успешно запущен!"
    echo ""
    echo "📋 Полезные команды:"
    echo "  docker logs -f telegram-bot    # Логи"
    echo "  docker restart telegram-bot    # Перезапуск"
    echo "  docker stop telegram-bot       # Остановка"
    echo ""
    echo "📝 Последние логи:"
    echo "========================================"
    docker logs --tail 30 telegram-bot
    echo "========================================"
    echo ""
    echo "🎉 Готово! Проверьте бота в Telegram"
else
    echo "❌ Ошибка запуска!"
    echo "Просмотрите логи: docker logs telegram-bot"
    exit 1
fi
