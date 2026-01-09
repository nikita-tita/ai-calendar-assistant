#!/bin/bash

# Скрипт быстрого развёртывания AI Calendar Bot на REG.RU VPS
# Использование: ./deploy-to-regru.sh

set -e

# Конфигурация
SERVER="root@95.163.227.26"
PROJECT_PATH="/root/ai-calendar-assistant"
LOCAL_PROJECT="/Users/fatbookpro/ai-calendar-assistant"

echo "🚀 Развёртывание AI Calendar Bot на REG.RU..."
echo "================================================"
echo ""
echo "Сервер: 95.163.227.26"
echo "Проект: ${PROJECT_PATH}"
echo ""

# Проверка наличия локального проекта
if [ ! -d "${LOCAL_PROJECT}" ]; then
    echo "❌ Проект не найден: ${LOCAL_PROJECT}"
    exit 1
fi

# Проверка .env файла
if [ ! -f "${LOCAL_PROJECT}/.env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте его на основе .env.example"
    echo ""
    read -p "Создать .env сейчас? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "${LOCAL_PROJECT}/.env.example" "${LOCAL_PROJECT}/.env"
        echo "✅ Файл .env создан. Отредактируйте его перед продолжением!"
        open -e "${LOCAL_PROJECT}/.env"
        exit 0
    else
        exit 1
    fi
fi

echo "📦 Синхронизация файлов..."
rsync -avz --progress \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  --exclude='.pytest_cache' \
  --exclude='venv' \
  --exclude='env' \
  --exclude='.venv' \
  --exclude='node_modules' \
  --exclude='.DS_Store' \
  --exclude='logs/*.log' \
  --exclude='.env.local' \
  "${LOCAL_PROJECT}/" \
  "${SERVER}:${PROJECT_PATH}/"

echo ""
echo "🔧 Настройка и запуск на сервере..."
echo ""

# Подключаемся к серверу и выполняем команды
ssh ${SERVER} bash << 'ENDSSH'
cd /root/ai-calendar-assistant

echo "📋 Проверка окружения..."

# Проверка .env
if [ ! -f .env ]; then
  echo "❌ Файл .env не найден на сервере!"
  echo "Файл должен был скопироваться с локальной машины."
  exit 1
fi

# Установка Docker если нужно
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

# Установка Docker Compose если нужно
if ! command -v docker-compose &> /dev/null; then
  echo "🐳 Установка Docker Compose..."
  COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
  curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
  echo "✅ Docker Compose установлен"
else
  echo "✅ Docker Compose уже установлен"
fi

# Создание необходимых директорий
mkdir -p logs credentials radicale_config

# Создание docker-compose.production.yml если не существует
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
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
EOF
fi

# Остановка старой версии
echo "🛑 Остановка предыдущей версии..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Очистка старых образов
echo "🧹 Очистка старых образов..."
docker system prune -f

# Сборка и запуск новой версии
echo "🏗️  Сборка нового образа..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🚀 Запуск бота..."
docker-compose -f docker-compose.production.yml up -d

# Ожидание запуска
echo "⏳ Ожидание запуска (5 секунд)..."
sleep 5

# Проверка статуса
echo ""
echo "📊 Статус контейнера:"
docker ps --filter name=telegram-bot

echo ""
if docker ps | grep -q telegram-bot; then
  echo "✅ Бот успешно запущен!"
  echo ""
  echo "📋 Полезные команды:"
  echo "  docker logs -f telegram-bot          # Просмотр логов в реальном времени"
  echo "  docker logs --tail 100 telegram-bot  # Последние 100 строк логов"
  echo "  docker restart telegram-bot          # Перезапуск бота"
  echo "  docker stop telegram-bot             # Остановка бота"
  echo "  docker start telegram-bot            # Запуск бота"
  echo "  docker stats telegram-bot            # Мониторинг ресурсов"
  echo ""
  echo "📝 Показываем последние логи..."
  echo "================================================"
  docker logs --tail 50 telegram-bot
else
  echo "❌ Ошибка запуска бота!"
  echo ""
  echo "Просмотрите логи для диагностики:"
  echo "  docker logs telegram-bot"
  exit 1
fi
ENDSSH

echo ""
echo "================================================"
echo "✅ Развёртывание завершено!"
echo ""
echo "🔗 Полезные ссылки:"
echo "  SSH: ssh root@95.163.227.26"
echo "  DNS: https://dnsadmin.hosting.reg.ru/manager/ispmgr"
echo ""
echo "💡 Для просмотра логов выполните:"
echo "  ssh root@95.163.227.26 'docker logs -f telegram-bot'"
echo ""
