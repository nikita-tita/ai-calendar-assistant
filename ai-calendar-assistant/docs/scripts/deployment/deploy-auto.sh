#!/bin/bash

# Автоматическое развёртывание с использованием sshpass
# Использование: ./deploy-auto.sh

set -e

# Конфигурация
SERVER="95.163.227.26"
USER="root"
PASSWORD="$SERVER_PASSWORD"
PROJECT_PATH="/root/ai-calendar-assistant"
LOCAL_PROJECT="/Users/fatbookpro/ai-calendar-assistant"

echo "🚀 Автоматическое развёртывание AI Calendar Bot"
echo "================================================"
echo ""
echo "Сервер: ${SERVER}"
echo "Проект: ${PROJECT_PATH}"
echo ""

# Проверка наличия sshpass
if ! command -v sshpass &> /dev/null; then
    echo "❌ sshpass не установлен"
    echo "Установите его: brew install hudochenkov/sshpass/sshpass"
    exit 1
fi

# Проверка наличия локального проекта
if [ ! -d "${LOCAL_PROJECT}" ]; then
    echo "❌ Проект не найден: ${LOCAL_PROJECT}"
    exit 1
fi

# Проверка .env файла
if [ ! -f "${LOCAL_PROJECT}/.env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "Создайте его на основе .env.example"
    exit 1
fi

echo "📦 Синхронизация файлов..."
sshpass -p "${PASSWORD}" rsync -avz --progress \
  -e "ssh -o StrictHostKeyChecking=no" \
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
  "${USER}@${SERVER}:${PROJECT_PATH}/"

echo ""
echo "🔧 Настройка и запуск на сервере..."
echo ""

# Подключаемся к серверу и выполняем команды
sshpass -p "${PASSWORD}" ssh -o StrictHostKeyChecking=no ${USER}@${SERVER} bash << 'ENDSSH'
cd /root/ai-calendar-assistant

echo "📋 Проверка окружения..."

# Проверка .env
if [ ! -f .env ]; then
  echo "❌ Файл .env не найден на сервере!"
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
echo "⏳ Ожидание запуска (10 секунд)..."
sleep 10

# Проверка статуса
echo ""
echo "📊 Статус контейнера:"
docker ps --filter name=telegram-bot

echo ""
if docker ps | grep -q telegram-bot; then
  echo "✅ Бот успешно запущен!"
  echo ""
  echo "📝 Последние логи:"
  echo "================================================"
  docker logs --tail 50 telegram-bot
  echo "================================================"
  echo ""
  echo "📋 Полезные команды:"
  echo "  docker logs -f telegram-bot          # Логи в реальном времени"
  echo "  docker restart telegram-bot          # Перезапуск"
  echo "  docker stats telegram-bot            # Мониторинг"
else
  echo "❌ Ошибка запуска бота!"
  echo ""
  echo "Логи:"
  docker logs telegram-bot
  exit 1
fi
ENDSSH

echo ""
echo "================================================"
echo "✅ Развёртывание завершено!"
echo ""
echo "🔗 Подключение к серверу:"
echo "  sshpass -p 'xZV5uNNlvqd9G01r' ssh root@95.163.227.26"
echo ""
echo "💡 Для просмотра логов:"
echo "  sshpass -p 'xZV5uNNlvqd9G01r' ssh root@95.163.227.26 'docker logs -f telegram-bot'"
echo ""
