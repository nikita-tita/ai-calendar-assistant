# Полная инструкция по развёртыванию AI Calendar Bot на REG.RU VPS

## Информация о вашем сервере

**Сервер:** Sapphire Palladium
**IP-адрес:** 95.163.227.26
**ОС:** Ubuntu 22.04 LTS
**Логин:** root
**Пароль:** xZV5uNNlvqd9G01r

**DNS Управление:**
- URL: https://dnsadmin.hosting.reg.ru/manager/ispmgr
- Логин: ce113047753
- Пароль: 51M_wz9gP9oPMdC
- DNS серверы: ns5.hosting.reg.ru, ns6.hosting.reg.ru

---

## Способ 1: Автоматическая установка (РЕКОМЕНДУЕТСЯ)

### Шаг 1: Подключение к серверу

**Вариант A: Через терминал Mac**

```bash
ssh root@95.163.227.26
```

Когда попросит пароль, введите: `xZV5uNNlvqd9G01r`

**Вариант B: Через веб-консоль REG.RU**

1. Откройте https://www.reg.ru/user/account
2. Перейдите в раздел "Серверы" → "VPS"
3. Найдите сервер "Sapphire Palladium"
4. Нажмите кнопку "Консоль" или "VNC"

### Шаг 2: Запуск автоустановки

После подключения к серверу выполните:

```bash
cd /root
apt-get update && apt-get install -y curl git
curl -fsSL https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/ai-calendar-assistant/main/install.sh -o install.sh
chmod +x install.sh
./install.sh
```

**ВАЖНО:** Замените `YOUR_GITHUB_USERNAME` на ваш реальный GitHub username, либо используйте способ 2.

### Шаг 3: Введите переменные окружения

Скрипт запросит следующую информацию:

1. **TELEGRAM_BOT_TOKEN**: Получите у @BotFather в Telegram
2. **OPENAI_API_KEY**: Ваш ключ от OpenAI (для Whisper и GPT)
3. **ANTHROPIC_API_KEY**: Ваш ключ от Anthropic Claude
4. **RADICALE_URL**: URL вашего CalDAV сервера

### Шаг 4: Проверка работы

```bash
# Проверить статус
docker ps

# Посмотреть логи
docker logs -f telegram-bot

# Если всё ок, нажмите Ctrl+C чтобы выйти из логов
```

---

## Способ 2: Ручная установка (если нет GitHub репозитория)

### Шаг 1: Подключение к серверу

```bash
ssh root@95.163.227.26
# Введите пароль: xZV5uNNlvqd9G01r
```

### Шаг 2: Установка необходимых компонентов

```bash
# Обновление системы
apt-get update
apt-get upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
systemctl enable docker
systemctl start docker

# Установка Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Установка Git
apt-get install -y git nano curl
```

### Шаг 3: Создание структуры проекта

```bash
# Создаем директорию
mkdir -p /root/ai-calendar-assistant
cd /root/ai-calendar-assistant
```

### Шаг 4: Загрузка файлов с локальной машины

**На вашей локальной машине (Mac)** откройте новый терминал:

```bash
cd /Users/fatbookpro/ai-calendar-assistant

# Копируем файлы на сервер
scp -r app/ root@95.163.227.26:/root/ai-calendar-assistant/
scp Dockerfile.bot root@95.163.227.26:/root/ai-calendar-assistant/
scp requirements.txt root@95.163.227.26:/root/ai-calendar-assistant/
scp .env.example root@95.163.227.26:/root/ai-calendar-assistant/
```

Введите пароль: `xZV5uNNlvqd9G01r` для каждой команды.

### Шаг 5: Создание .env файла

**Вернитесь в терминал с сервером:**

```bash
cd /root/ai-calendar-assistant

# Создаем .env файл
nano .env
```

Вставьте следующее содержимое (замените значения на свои):

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI (для Whisper)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Calendar Service (Radicale)
RADICALE_URL=https://your-radicale-server.com
RADICALE_USERNAME=admin
RADICALE_PASSWORD=your_radicale_password

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Сохранение:** Нажмите `Ctrl+X`, затем `Y`, затем `Enter`

### Шаг 6: Создание docker-compose.yml

```bash
nano docker-compose.production.yml
```

Вставьте:

```yaml
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
```

**Сохранение:** `Ctrl+X` → `Y` → `Enter`

### Шаг 7: Запуск бота

```bash
# Создаем необходимые директории
mkdir -p logs credentials

# Запускаем бота
docker-compose -f docker-compose.production.yml up -d --build

# Ждём 5 секунд
sleep 5

# Проверяем статус
docker ps
```

### Шаг 8: Проверка логов

```bash
# Смотрим логи в реальном времени
docker logs -f telegram-bot

# Выход из логов: Ctrl+C
```

---

## Способ 3: Быстрое развёртывание через rsync (САМЫЙ БЫСТРЫЙ)

Создайте на своей **локальной машине** файл `deploy-to-regru.sh`:

```bash
#!/bin/bash

SERVER="root@95.163.227.26"
PROJECT_PATH="/root/ai-calendar-assistant"

echo "🚀 Развёртывание AI Calendar Bot на REG.RU..."

# Синхронизация файлов
rsync -avz --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='venv' \
  /Users/fatbookpro/ai-calendar-assistant/ \
  ${SERVER}:${PROJECT_PATH}/

# Подключаемся к серверу и запускаем
ssh ${SERVER} << 'ENDSSH'
cd /root/ai-calendar-assistant

# Проверка .env
if [ ! -f .env ]; then
  echo "❌ Файл .env не найден!"
  echo "Создайте его на основе .env.example"
  exit 1
fi

# Установка Docker если нужно
if ! command -v docker &> /dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

# Установка Docker Compose если нужно
if ! command -v docker-compose &> /dev/null; then
  curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  chmod +x /usr/local/bin/docker-compose
fi

# Остановка старой версии
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Запуск новой версии
docker-compose -f docker-compose.production.yml up -d --build

# Проверка
sleep 5
docker ps | grep telegram-bot

echo "✅ Развёртывание завершено!"
echo "📋 Проверьте логи: docker logs -f telegram-bot"
ENDSSH
```

**Использование:**

```bash
chmod +x deploy-to-regru.sh
./deploy-to-regru.sh
```

---

## Управление ботом

### Просмотр логов

```bash
# В реальном времени
docker logs -f telegram-bot

# Последние 100 строк
docker logs --tail 100 telegram-bot
```

### Перезапуск

```bash
docker restart telegram-bot
```

### Остановка

```bash
docker stop telegram-bot
```

### Запуск

```bash
docker start telegram-bot
```

### Обновление бота

**Если используете Git:**

```bash
cd /root/ai-calendar-assistant
git pull
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

**Если используете rsync:** Просто запустите скрипт развёртывания снова.

### Проверка ресурсов

```bash
# Использование CPU/RAM
docker stats telegram-bot

# Место на диске
df -h

# Логи Docker
du -sh /var/lib/docker/
```

### Очистка

```bash
# Удалить неиспользуемые образы
docker system prune -a

# Удалить логи старше 7 дней
find /root/ai-calendar-assistant/logs -name "*.log" -mtime +7 -delete
```

---

## Настройка автозапуска

Бот автоматически перезапустится после перезагрузки сервера благодаря `restart: always` в docker-compose.yml.

Проверить можно так:

```bash
# Перезагрузить сервер
reboot

# Через минуту подключиться снова
ssh root@95.163.227.26

# Проверить что бот запустился
docker ps
```

---

## Настройка домена (опционально)

Если хотите привязать домен к серверу:

### Шаг 1: Настройка DNS

1. Зайдите в https://dnsadmin.hosting.reg.ru/manager/ispmgr
2. Логин: `ce113047753`
3. Пароль: `51M_wz9gP9oPMdC`
4. Добавьте A-запись:
   - Имя: `@` (для основного домена) или `bot` (для поддомена)
   - Тип: A
   - Значение: `95.163.227.26`
   - TTL: 3600

### Шаг 2: Установка Nginx + SSL

```bash
# Установка Nginx
apt-get install -y nginx certbot python3-certbot-nginx

# Создание конфига
nano /etc/nginx/sites-available/calendar-bot

# Вставьте:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}

# Активация конфига
ln -s /etc/nginx/sites-available/calendar-bot /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# Получение SSL сертификата
certbot --nginx -d your-domain.com
```

---

## Мониторинг и безопасность

### Автоматический мониторинг

Создайте скрипт проверки:

```bash
nano /root/check-bot.sh
```

```bash
#!/bin/bash

if ! docker ps | grep -q telegram-bot; then
  echo "⚠️ Бот не запущен! Перезапуск..."
  cd /root/ai-calendar-assistant
  docker-compose -f docker-compose.production.yml up -d
  echo "✅ Бот перезапущен"
fi
```

```bash
chmod +x /root/check-bot.sh

# Добавить в cron (каждые 5 минут)
crontab -e

# Добавить строку:
*/5 * * * * /root/check-bot.sh >> /root/bot-monitor.log 2>&1
```

### Настройка firewall

```bash
# Установка UFW
apt-get install -y ufw

# Разрешить SSH
ufw allow 22/tcp

# Разрешить HTTP/HTTPS (если используете домен)
ufw allow 80/tcp
ufw allow 443/tcp

# Включить firewall
ufw enable
```

---

## Полезные команды

### Docker

```bash
# Все контейнеры
docker ps -a

# Удалить остановленные контейнеры
docker container prune

# Использование места
docker system df

# Полная очистка
docker system prune -a --volumes
```

### Система

```bash
# Использование диска
df -h

# Использование RAM
free -h

# Процессы
htop  # (установить: apt-get install htop)

# Нагрузка на систему
uptime

# Сетевые подключения
netstat -tulpn
```

### Логи системы

```bash
# Системные логи
journalctl -u docker -f

# Последние ошибки
journalctl -p err -b
```

---

## Решение проблем

### Бот не запускается

```bash
# Проверьте логи
docker logs telegram-bot

# Проверьте .env файл
cat /root/ai-calendar-assistant/.env

# Пересоберите контейнер
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

### Нет места на диске

```bash
# Очистка Docker
docker system prune -a

# Очистка логов
journalctl --vacuum-time=7d

# Удаление старых логов приложения
rm -rf /root/ai-calendar-assistant/logs/*.log.old
```

### Медленная работа

```bash
# Проверка ресурсов
docker stats

# Если не хватает RAM, включите swap
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## Стоимость и характеристики

**Тариф REG.RU:**
- 1 vCPU
- 512 MB RAM (+ можно добавить swap)
- 10 GB SSD
- Ubuntu 22.04 LTS
- **Стоимость:** ~200-300₽/месяц

**Для улучшения производительности можно:**
- Увеличить RAM до 1GB (+100₽/мес)
- Добавить больше места на диске
- Настроить swap файл (бесплатно)

---

## Поддержка

**Если что-то не работает:**

1. Проверьте логи: `docker logs -f telegram-bot`
2. Проверьте статус: `docker ps -a`
3. Проверьте .env файл: `cat .env`
4. Проверьте место на диске: `df -h`
5. Перезапустите: `docker restart telegram-bot`

**Контакты поддержки REG.RU:**
- Телефон: 8 800 333-33-33
- Email: support@reg.ru
- Личный кабинет: https://www.reg.ru/user/account

---

## Чеклист успешного развёртывания

- [ ] Подключились к серверу через SSH
- [ ] Установили Docker и Docker Compose
- [ ] Загрузили файлы проекта
- [ ] Создали .env файл с правильными токенами
- [ ] Запустили docker-compose
- [ ] Проверили что контейнер работает (`docker ps`)
- [ ] Посмотрели логи и нет ошибок
- [ ] Написали боту в Telegram и получили ответ
- [ ] Настроили автозапуск (уже есть в docker-compose)
- [ ] (Опционально) Настроили домен и SSL

**Готово! Ваш бот работает 24/7! 🎉**
