# 🚀 Deployment Guide - AI Calendar Assistant

## ⚠️ КРИТИЧЕСКИ ВАЖНО

**НИКОГДА не используйте `docker-compose build --no-cache`!**
**НИКОГДА не делайте `docker-compose down` без проверки volumes!**

При rebuild теряются:
- ✅ Environment variables (API ключи)
- ✅ Runtime configurations
- ❌ Volumes с данными (НЕ теряются, если не удалять volumes)

---

## 📋 Необходимые API ключи

### 1. Telegram Bot Token
- Получить у @BotFather в Telegram
- Формат: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- Переменная: `TELEGRAM_BOT_TOKEN`

### 2. Yandex GPT API Key
- Получить в [Yandex Cloud Console](https://console.cloud.yandex.ru/)
- Создать API ключ для сервисного аккаунта
- Формат: `YOUR_YANDEX_API_KEY_HERE`
- Переменная: `YANDEX_GPT_API_KEY`

### 3. Yandex Folder ID
- Взять из [Yandex Cloud Console](https://console.cloud.yandex.ru/)
- Формат: `b1gxxxxxxxxxxxxx`
- Переменная: `YANDEX_GPT_FOLDER_ID`

### 4. Где хранить ключи

**НА СЕРВЕРЕ:**
```bash
# Создать файл с ключами
cat > /root/ai-calendar-assistant/.env.production << 'EOF'
TELEGRAM_BOT_TOKEN=ваш_токен
YANDEX_GPT_API_KEY=ваш_ключ
YANDEX_GPT_FOLDER_ID=ваш_folder_id
EOF

# Защитить файл
chmod 600 /root/ai-calendar-assistant/.env.production

# Создать симлинк
ln -sf /root/ai-calendar-assistant/.env.production /root/ai-calendar-assistant/.env
```

**ЛОКАЛЬНО (для разработки):**
```bash
# Никогда не коммитить .env в git!
cp .env.example .env
# Отредактировать .env своими ключами
```

---

## 🔄 Правильный процесс деплоя

### Вариант 1: Обновление без rebuild (БЕЗОПАСНО)

```bash
#!/bin/bash
# safe-deploy.sh

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

# 1. Upload updated files
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no \
    app/services/*.py "$SERVER:$REMOTE_DIR/app/services/"

# 2. Copy to running container
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
    docker cp $REMOTE_DIR/app/services/telegram_handler.py telegram-bot:/app/app/services/telegram_handler.py &&
    docker cp $REMOTE_DIR/app/services/stt_yandex.py telegram-bot:/app/app/services/stt_yandex.py &&
    docker cp $REMOTE_DIR/app/services/llm_agent_yandex.py telegram-bot:/app/app/services/llm_agent_yandex.py &&
    docker restart telegram-bot
"

echo "✅ Deployed without rebuild - data preserved!"
```

### Вариант 2: Полный rebuild (ОПАСНО - только если нужны новые зависимости)

```bash
#!/bin/bash
# full-rebuild.sh - ИСПОЛЬЗУЙТЕ ТОЛЬКО если нужны новые pip пакеты!

SERVER="root@91.229.8.221"
PASSWORD="upvzrr3LH4pxsaqs"
REMOTE_DIR="/root/ai-calendar-assistant"

# 1. Создать бэкап .env
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
    cp $REMOTE_DIR/.env $REMOTE_DIR/.env.backup-\$(date +%Y%m%d-%H%M%S)
"

# 2. Остановить контейнеры (НЕ удалять!)
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
    cd $REMOTE_DIR &&
    docker-compose -f docker-compose.hybrid.yml stop
"

# 3. Rebuild образ
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
    cd $REMOTE_DIR &&
    docker-compose -f docker-compose.hybrid.yml build telegram-bot
"

# 4. Запустить с сохранением env
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no "$SERVER" "
    cd $REMOTE_DIR &&
    docker-compose -f docker-compose.hybrid.yml up -d
"

echo "✅ Full rebuild complete!"
```

---

## 🐛 Если что-то сломалось

### Проблема: API ключи потеряны

**Симптомы:**
```
{"error": "Unknown api key 'YOUR****HERE'"}
```

**Решение:**
```bash
# 1. Восстановить .env из бэкапа
ssh root@91.229.8.221 "
    ls -la /root/ai-calendar-assistant/.env.backup* &&
    cat /root/ai-calendar-assistant/.env.backup-YYYYMMDD > /root/ai-calendar-assistant/.env
"

# 2. Перезапустить контейнер
ssh root@91.229.8.221 "
    cd /root/ai-calendar-assistant &&
    docker-compose -f docker-compose.hybrid.yml restart telegram-bot
"
```

### Проблема: Потеряны данные календаря

**Симптомы:**
```
События пользователя исчезли
```

**Решение:**
```bash
# Проверить volumes
docker volume ls | grep radicale

# Восстановить из бэкапа
tar -xzf /root/backups/radicale-data/radicale-YYYYMMDD.tar.gz -C /
```

---

## 📝 Чеклист перед деплоем

- [ ] Бэкап .env файла сделан
- [ ] Бэкап Radicale данных актуален (автоматический ежедневный)
- [ ] Знаю где взять API ключи если что-то сломается
- [ ] Использую safe-deploy.sh вместо full-rebuild.sh
- [ ] Проверил, что volumes НЕ будут удалены

---

## 🔐 Где хранятся критичные данные

### API Ключи
- Основной: `/root/ai-calendar-assistant/.env`
- Бэкапы: `/root/ai-calendar-assistant/.env.backup-*`
- В runtime: `docker exec telegram-bot printenv | grep YANDEX`

### Данные календаря
- Volume: `ai-calendar-assistant_radicale_data`
- Path: `/var/lib/docker/volumes/ai-calendar-assistant_radicale_data/_data`
- Бэкапы: `/root/backups/radicale-data/`

### Логи
- Container: `docker logs telegram-bot`
- Path: `/root/ai-calendar-assistant/logs/`

---

## ✅ Тест после деплоя

```bash
# 1. Проверить контейнер запущен
docker ps | grep telegram-bot

# 2. Проверить логи без ошибок
docker logs --tail 50 telegram-bot 2>&1 | grep -i error

# 3. Проверить API ключи загружены
docker exec telegram-bot printenv | grep YANDEX_GPT_API_KEY

# 4. Отправить тестовое голосовое сообщение в бот
# 5. Проверить создание события
```

---

## 🆘 Быстрое восстановление

```bash
# Если ВСЁ сломалось - восстановить из последнего рабочего бэкапа
cd /root/backups/deployments
tar -xzf backup_LATEST.tar.gz -C /root/ai-calendar-assistant
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.hybrid.yml up -d
```

---

## 📞 Контакты для получения ключей

- **Telegram Bot**: @BotFather
- **Yandex Cloud**: console.cloud.yandex.ru
- **Сервер**: root@91.229.8.221

**Пароль сервера:** upvzrr3LH4pxsaqs
