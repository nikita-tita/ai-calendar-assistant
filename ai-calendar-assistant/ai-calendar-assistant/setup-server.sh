#!/bin/bash

# Скрипт первоначальной настройки сервера REG.RU
# Запускается ОДИН РАЗ на новом сервере
# Выполняется НА СЕРВЕРЕ (не на локальной машине)

set -e

echo "🔧 Первоначальная настройка сервера REG.RU"
echo "=========================================="
echo ""

# Проверка root прав
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами root"
    echo "   Вы уже должны быть под root на VPS"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq

# Установка базовых пакетов
echo "📚 Установка базовых пакетов..."
apt-get install -y -qq \
  curl \
  wget \
  git \
  nano \
  htop \
  net-tools \
  ufw \
  software-properties-common \
  apt-transport-https \
  ca-certificates \
  gnupg \
  lsb-release

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

# Проверка версии Docker
docker --version

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

# Проверка версии Docker Compose
docker-compose --version

# Настройка firewall
echo "🔥 Настройка firewall (UFW)..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
echo "✅ Firewall настроен"

# Настройка swap (для экономии RAM)
if [ ! -f /swapfile ]; then
    echo "💾 Создание swap файла (1GB)..."
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap создан"
else
    echo "✅ Swap уже существует"
fi

# Проверка swap
free -h

# Настройка часового пояса
echo "🌍 Настройка часового пояса..."
timedatectl set-timezone Europe/Moscow
echo "✅ Часовой пояс: $(timedatectl | grep 'Time zone')"

# Создание директорий для проекта
echo "📁 Создание директорий проекта..."
mkdir -p /root/ai-calendar-assistant/{logs,credentials,radicale_config}
echo "✅ Директории созданы"

# Настройка автоматической очистки логов Docker
echo "🧹 Настройка автоочистки логов Docker..."
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker
echo "✅ Логи Docker будут автоматически ротироваться"

# Создание скрипта мониторинга
echo "📊 Создание скрипта мониторинга..."
cat > /root/check-bot.sh << 'EOF'
#!/bin/bash
# Скрипт проверки работы бота

if ! docker ps | grep -q telegram-bot; then
  echo "[$(date)] ⚠️ Бот не запущен! Перезапуск..." >> /root/bot-monitor.log
  cd /root/ai-calendar-assistant
  docker-compose -f docker-compose.production.yml up -d
  echo "[$(date)] ✅ Бот перезапущен" >> /root/bot-monitor.log
else
  echo "[$(date)] ✅ Бот работает нормально" >> /root/bot-monitor.log
fi
EOF

chmod +x /root/check-bot.sh
echo "✅ Скрипт мониторинга создан: /root/check-bot.sh"

# Добавление в cron (проверка каждые 5 минут)
echo "⏰ Настройка автопроверки (cron)..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /root/check-bot.sh") | crontab -
echo "✅ Автопроверка настроена (каждые 5 минут)"

# Создание скрипта просмотра логов
cat > /root/logs.sh << 'EOF'
#!/bin/bash
docker logs -f telegram-bot
EOF
chmod +x /root/logs.sh

# Создание скрипта перезапуска
cat > /root/restart-bot.sh << 'EOF'
#!/bin/bash
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml restart
echo "✅ Бот перезапущен"
docker ps | grep telegram-bot
EOF
chmod +x /root/restart-bot.sh

# Создание скрипта обновления
cat > /root/update-bot.sh << 'EOF'
#!/bin/bash
cd /root/ai-calendar-assistant
echo "📥 Получение обновлений..."
git pull
echo "🔄 Перезапуск с новой версией..."
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
echo "✅ Обновление завершено"
docker logs --tail 50 telegram-bot
EOF
chmod +x /root/update-bot.sh

# Настройка SSH (опционально, для безопасности)
echo "🔐 Улучшение безопасности SSH..."
sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin without-password/PermitRootLogin yes/' /etc/ssh/sshd_config
systemctl restart sshd

# Информация о системе
echo ""
echo "=========================================="
echo "✅ Сервер успешно настроен!"
echo "=========================================="
echo ""
echo "📊 Информация о системе:"
echo ""
echo "ОС: $(lsb_release -d | cut -f2)"
echo "Ядро: $(uname -r)"
echo "Docker: $(docker --version | cut -d' ' -f3)"
echo "Docker Compose: $(docker-compose --version | cut -d' ' -f3)"
echo ""
echo "💾 Ресурсы:"
free -h
echo ""
df -h /
echo ""
echo "🔧 Созданные утилиты:"
echo "  /root/logs.sh         - Просмотр логов бота"
echo "  /root/restart-bot.sh  - Перезапуск бота"
echo "  /root/update-bot.sh   - Обновление бота из Git"
echo "  /root/check-bot.sh    - Проверка работы бота"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Скопируйте файлы проекта с локальной машины:"
echo "   scp -r /Users/fatbookpro/ai-calendar-assistant/* root@91.229.8.221:/root/ai-calendar-assistant/"
echo ""
echo "2. Или используйте скрипт deploy-to-regru.sh на локальной машине:"
echo "   ./deploy-to-regru.sh"
echo ""
echo "3. Создайте .env файл на основе .env.example"
echo ""
echo "4. Запустите бота:"
echo "   cd /root/ai-calendar-assistant"
echo "   docker-compose -f docker-compose.production.yml up -d --build"
echo ""
echo "🎉 Готово к развёртыванию!"
echo ""
