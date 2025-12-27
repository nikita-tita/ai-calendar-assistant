# 🚀 Production Deployment - SMS Authentication

Пошаговая инструкция для деплоя в production.

---

## ⚡ Быстрый деплой (5 минут)

### Шаг 1: Подготовка сервера

```bash
# Подключитесь к серверу
ssh user@your-server.com

# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Docker и Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверьте установку
docker --version
docker-compose --version
```

### Шаг 2: Клонируйте проект

```bash
# Клонируйте репозиторий
cd /opt
sudo git clone https://github.com/your-repo/ai-calendar-assistant.git
cd ai-calendar-assistant/ai-calendar-assistant

# Установите права
sudo chown -R $USER:$USER .
```

### Шаг 3: Настройте .env

```bash
# Создайте .env из production шаблона
cp env.sms_production.example .env

# Сгенерируйте SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo "Ваш SECRET_KEY: $SECRET_KEY"

# Сгенерируйте RADICALE_BOT_PASSWORD
RADICALE_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
echo "Ваш RADICALE_PASSWORD: $RADICALE_PASSWORD"

# Отредактируйте .env
nano .env
```

**Важные настройки в .env:**

```bash
# === PRODUCTION НАСТРОЙКИ ===
APP_ENV=production
DEBUG=False
LOG_LEVEL=INFO

# === SMS (ваши данные) ===
SMS_PROVIDER=sms.ru
SMS_RU_API_ID=779FBF5C-56D6-6AF8-5C8B-63C2F6CF9C90

# === БЕЗОПАСНОСТЬ (ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!) ===
SECRET_KEY=<вставьте_сгенерированный_ключ>
RADICALE_BOT_PASSWORD=<вставьте_сгенерированный_пароль>

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN=<ваш_токен_от_BotFather>
TELEGRAM_WEBAPP_URL=https://your-domain.com

# === CORS ===
CORS_ORIGINS=https://your-domain.com,https://webapp.telegram.org

# === ДОМЕН ===
# Замените на ваш реальный домен!
```

### Шаг 4: Настройте Nginx с SSL

```bash
# Установите Nginx и Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Создайте конфиг Nginx
sudo nano /etc/nginx/sites-available/calendar-assistant
```

**Конфиг Nginx:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Для Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Редирект на HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL сертификаты (будут созданы Certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Размер загружаемых файлов
    client_max_body_size 10M;

    # Proxy к FastAPI
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Статические файлы
    location /static/ {
        alias /opt/ai-calendar-assistant/ai-calendar-assistant/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Логи
    access_log /var/log/nginx/calendar-assistant-access.log;
    error_log /var/log/nginx/calendar-assistant-error.log;
}
```

```bash
# Активируйте конфиг
sudo ln -s /etc/nginx/sites-available/calendar-assistant /etc/nginx/sites-enabled/

# Проверьте конфиг
sudo nginx -t

# Получите SSL сертификат
sudo certbot --nginx -d your-domain.com

# Перезагрузите Nginx
sudo systemctl restart nginx

# Включите автозапуск
sudo systemctl enable nginx
```

### Шаг 5: Запустите приложение

```bash
# Вернитесь в директорию проекта
cd /opt/ai-calendar-assistant/ai-calendar-assistant

# Создайте директорию для данных
mkdir -p data

# Запустите через Docker Compose
docker-compose up -d --build

# Проверьте статус
docker-compose ps

# Проверьте логи
docker-compose logs -f calendar-assistant
```

### Шаг 6: Проверка работоспособности

```bash
# Health check
curl https://your-domain.com/health

# Запрос SMS (на ваш номер!)
curl -X POST https://your-domain.com/api/auth/sms/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567"}'

# Вам придёт SMS!
# Проверьте код
curl -X POST https://your-domain.com/api/auth/sms/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567", "code": "123456"}'
```

---

## 🔐 Безопасность

### Firewall

```bash
# Установите UFW
sudo apt install -y ufw

# Разрешите SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Включите firewall
sudo ufw enable

# Проверьте статус
sudo ufw status
```

### Fail2Ban (защита от брутфорса)

```bash
# Установите Fail2Ban
sudo apt install -y fail2ban

# Создайте конфиг для Nginx
sudo nano /etc/fail2ban/jail.local
```

**Конфиг Fail2Ban:**

```ini
[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/*error.log
findtime = 600
bantime = 7200
maxretry = 10
```

```bash
# Перезапустите Fail2Ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### Ограничение доступа к .env

```bash
# Установите правильные права
chmod 600 .env
chmod 700 data/

# Проверьте
ls -la .env
```

---

## 📊 Мониторинг

### Логи приложения

```bash
# Логи Docker
docker-compose logs -f

# Только SMS логи
docker-compose logs -f | grep sms

# Логи Nginx
sudo tail -f /var/log/nginx/calendar-assistant-access.log
sudo tail -f /var/log/nginx/calendar-assistant-error.log
```

### Мониторинг ресурсов

```bash
# Использование Docker
docker stats

# Дисковое пространство
df -h

# Память
free -h

# CPU
htop
```

### Настройка systemd service (автозапуск)

```bash
# Создайте service файл
sudo nano /etc/systemd/system/calendar-assistant.service
```

**Service файл:**

```ini
[Unit]
Description=AI Calendar Assistant
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ai-calendar-assistant/ai-calendar-assistant
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

```bash
# Включите автозапуск
sudo systemctl enable calendar-assistant
sudo systemctl start calendar-assistant

# Проверьте статус
sudo systemctl status calendar-assistant
```

---

## 🔄 Обновление

```bash
# Остановите приложение
docker-compose down

# Обновите код
git pull origin main

# Пересоберите образы
docker-compose build --no-cache

# Запустите
docker-compose up -d

# Проверьте логи
docker-compose logs -f
```

---

## 💾 Бэкапы

### Автоматический бэкап

```bash
# Создайте скрипт бэкапа
sudo nano /usr/local/bin/backup-calendar-assistant.sh
```

**Скрипт бэкапа:**

```bash
#!/bin/bash

BACKUP_DIR="/backup/calendar-assistant"
APP_DIR="/opt/ai-calendar-assistant/ai-calendar-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

# Создайте директорию для бэкапов
mkdir -p $BACKUP_DIR

# Бэкап данных
tar -czf $BACKUP_DIR/data_$DATE.tar.gz $APP_DIR/data/

# Бэкап .env
cp $APP_DIR/.env $BACKUP_DIR/env_$DATE

# Удалите старые бэкапы (старше 30 дней)
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Сделайте исполняемым
sudo chmod +x /usr/local/bin/backup-calendar-assistant.sh

# Добавьте в cron (каждый день в 3:00)
sudo crontab -e
```

**Cron:**

```bash
0 3 * * * /usr/local/bin/backup-calendar-assistant.sh >> /var/log/backup-calendar.log 2>&1
```

---

## 📈 Оптимизация

### Docker оптимизация

```bash
# Очистите неиспользуемые образы
docker system prune -a

# Ограничьте память для контейнера
# Добавьте в docker-compose.yml:
```

```yaml
services:
  calendar-assistant:
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```

### PostgreSQL вместо SQLite (рекомендуется)

```bash
# Добавьте в docker-compose.yml
```

```yaml
services:
  postgres:
    image: postgres:14
    environment:
      POSTGRES_DB: calendar_db
      POSTGRES_USER: calendar_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
# Обновите .env
DATABASE_URL=postgresql://calendar_user:${DB_PASSWORD}@postgres:5432/calendar_db
```

### Redis для кодов (рекомендуется)

```bash
# Добавьте в docker-compose.yml
```

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  redis_data:
```

```bash
# Обновите .env
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
```

---

## 🚨 Алерты

### Email уведомления при ошибках

```bash
# Установите mailutils
sudo apt install -y mailutils

# Создайте скрипт мониторинга
sudo nano /usr/local/bin/monitor-calendar-assistant.sh
```

**Скрипт мониторинга:**

```bash
#!/bin/bash

SERVICE="calendar-assistant"
EMAIL="admin@your-domain.com"

if ! systemctl is-active --quiet $SERVICE; then
    echo "Service $SERVICE is down!" | mail -s "ALERT: $SERVICE DOWN" $EMAIL
    systemctl restart $SERVICE
fi
```

```bash
# Добавьте в cron (проверка каждые 5 минут)
*/5 * * * * /usr/local/bin/monitor-calendar-assistant.sh
```

---

## 📋 Production Checklist

### Перед запуском

- [ ] `APP_ENV=production` в `.env`
- [ ] `DEBUG=False` в `.env`
- [ ] `SECRET_KEY` сгенерирован (32+ символа)
- [ ] `RADICALE_BOT_PASSWORD` сгенерирован
- [ ] SMS.ru API ID настроен
- [ ] SMS.ru баланс пополнен (мин. 100₽)
- [ ] Telegram Bot Token настроен
- [ ] Домен указан в `TELEGRAM_WEBAPP_URL`
- [ ] `CORS_ORIGINS` настроен правильно
- [ ] `.env` не в git (`chmod 600 .env`)

### Безопасность

- [ ] SSL сертификат установлен (Let's Encrypt)
- [ ] Firewall настроен (UFW)
- [ ] Fail2Ban установлен
- [ ] Nginx настроен как reverse proxy
- [ ] Логи ротируются
- [ ] Бэкапы настроены

### Мониторинг

- [ ] Health check работает
- [ ] Логи пишутся
- [ ] Email алерты настроены
- [ ] Systemd service включен
- [ ] Docker автозапуск настроен

### Тестирование

- [ ] Тестовая SMS получена
- [ ] JWT токены работают
- [ ] API endpoints отвечают
- [ ] Demo страница работает
- [ ] HTTPS работает
- [ ] Rate limiting активен

---

## 🎯 Первый запуск

```bash
# 1. Проверьте конфигурацию
cat .env | grep -E "SMS_PROVIDER|SECRET_KEY|APP_ENV"

# 2. Запустите
docker-compose up -d

# 3. Проверьте логи
docker-compose logs -f | grep "application_started"

# Должны увидеть:
# [info] application_started environment=production debug=False
# [info] sms_service_initialized provider=sms.ru

# 4. Тестовая SMS
curl -X POST https://your-domain.com/api/auth/sms/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567"}'

# 5. Проверьте телефон - должна прийти SMS!

# 6. Введите код
curl -X POST https://your-domain.com/api/auth/sms/verify \
  -H "Content-Type: application/json" \
  -d '{"phone": "+79991234567", "code": "полученный_код"}'

# 7. Если получили токен - всё работает! 🎉
```

---

## 📊 Метрики Production

### Рекомендуемые лимиты

```bash
# Rate limiting
MAX_SMS_PER_PHONE_PER_HOUR=5
MAX_SMS_PER_IP_PER_HOUR=10
MAX_SMS_PER_DAY=100

# JWT
JWT_EXPIRATION_DAYS=7
MAX_CONCURRENT_SESSIONS=3

# SMS
SMS_CODE_LIFETIME_SECONDS=300
SMS_MAX_ATTEMPTS=3
SMS_MIN_SEND_INTERVAL=60
```

### Алерты на расходы

```bash
# Настройте в SMS.ru
# Личный кабинет → Настройки → Уведомления

# Уведомление при балансе < 50₽
# Уведомление при расходе > 500₽/день
```

---

## 🆘 Troubleshooting

### Приложение не запускается

```bash
# Проверьте Docker
docker-compose ps
docker-compose logs

# Проверьте .env
cat .env | grep -v "^#" | grep -v "^$"

# Проверьте порты
sudo netstat -tlnp | grep :8000
```

### SMS не отправляются

```bash
# Проверьте логи
docker-compose logs | grep sms

# Проверьте баланс SMS.ru
curl "https://sms.ru/my/balance?api_id=779FBF5C-56D6-6AF8-5C8B-63C2F6CF9C90"

# Проверьте провайдер в .env
grep SMS_PROVIDER .env
```

### SSL проблемы

```bash
# Обновите сертификат
sudo certbot renew

# Проверьте Nginx
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🎉 Готово!

После выполнения всех шагов у вас:

✅ Production-ready деплой  
✅ SSL/HTTPS  
✅ Автозапуск  
✅ Бэкапы  
✅ Мониторинг  
✅ Алерты  
✅ Безопасность  

**Приложение готово к боевой нагрузке!** 🚀

---

## 📞 Поддержка

- 📧 Email: support@your-domain.com
- 📱 Telegram: @your_support_bot
- 🌐 Docs: https://your-domain.com/docs

---

<div align="center">

**Production Deployment Guide v1.0**  
**Дата:** 22 декабря 2025

Made with ❤️ in Russia 🇷🇺

</div>
