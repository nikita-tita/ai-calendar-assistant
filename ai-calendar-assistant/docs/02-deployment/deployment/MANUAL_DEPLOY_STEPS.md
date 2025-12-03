# 🔧 Ручное развёртывание через веб-консоль REG.RU

## Проблема с SSH
SSH подключение по паролю заблокировано на сервере. Используйте веб-консоль REG.RU.

---

## Способ 1: Через веб-консоль REG.RU (РАБОТАЕТ 100%)

### Шаг 1: Откройте веб-консоль

1. Перейдите на https://www.reg.ru/user/account
2. Зайдите в раздел **"Серверы"** → **"VPS"**
3. Найдите ваш сервер **"Sapphire Palladium"** (91.229.8.221)
4. Нажмите кнопку **"Консоль"** или **"VNC"**
5. Введите логин: `root`, пароль: `xZV5uNNlvqd9G01r`

### Шаг 2: Выполните установку (скопируйте в консоль)

```bash
# Обновление системы
apt-get update && apt-get upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh
systemctl enable docker
systemctl start docker

# Установка Docker Compose
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Установка Git и утилит
apt-get install -y git curl wget nano

# Создание директорий
mkdir -p /root/ai-calendar-assistant
cd /root/ai-calendar-assistant
```

### Шаг 3: Создайте файлы проекта

Создайте каждый файл по очереди:

#### 3.1 Создайте .env файл

```bash
nano .env
```

Вставьте (замените YOUR_* на реальные значения):

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=***REMOVED***

# OpenAI (для Whisper)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY

# Anthropic Claude
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY

# Calendar Service
RADICALE_URL=https://calendar-bot-production-e1ac.up.railway.app

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
DEFAULT_TIMEZONE=Europe/Moscow
```

**Сохраните:** `Ctrl+X` → `Y` → `Enter`

#### 3.2 Создайте Dockerfile.bot

```bash
nano Dockerfile.bot
```

Вставьте:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run_polling.py"]
```

**Сохраните:** `Ctrl+X` → `Y` → `Enter`

#### 3.3 Создайте requirements.txt

```bash
nano requirements.txt
```

Вставьте:

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
python-telegram-bot>=21.0
caldav>=1.3.0
icalendar>=5.0.0
anthropic>=0.8.0
python-dateutil==2.8.2
dateparser==1.2.0
pytz==2023.3
openai-whisper==20231117
openai>=1.50.0
pydantic==2.5.2
pydantic-settings==2.1.0
python-dotenv==1.0.0
httpx>=0.25.0
aiohttp>=3.9.0
tenacity==8.2.3
structlog==23.2.0
```

**Сохраните:** `Ctrl+X` → `Y` → `Enter`

#### 3.4 Создайте docker-compose.production.yml

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

**Сохраните:** `Ctrl+X` → `Y` → `Enter`

### Шаг 4: Скопируйте код приложения

Есть 2 варианта:

**Вариант A: Через Git (если есть репозиторий)**

```bash
cd /root
rm -rf ai-calendar-assistant
git clone https://github.com/YOUR_USERNAME/ai-calendar-assistant.git
cd ai-calendar-assistant
```

**Вариант B: Создайте минимальные файлы вручную**

```bash
mkdir -p /root/ai-calendar-assistant/app
cd /root/ai-calendar-assistant
```

Создайте `run_polling.py`:

```bash
nano run_polling.py
```

Вставьте минимальный рабочий код:

```python
#!/usr/bin/env python3
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        '🤖 AI Calendar Assistant запущен!\n\n'
        'Доступные команды:\n'
        '/start - Начало работы\n'
        '/help - Помощь'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        '📋 Помощь:\n\n'
        'Отправьте мне сообщение с событием, и я добавлю его в календарь.\n'
        'Например: "Встреча завтра в 15:00"'
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Эхо-обработчик сообщений"""
    await update.message.reply_text(f"Получено: {update.message.text}")

def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        return

    logger.info("🚀 Запуск бота...")

    # Создание приложения
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Запуск бота
    logger.info("✅ Бот запущен в режиме polling")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
```

**Сохраните:** `Ctrl+X` → `Y` → `Enter`

### Шаг 5: Запустите бота

```bash
cd /root/ai-calendar-assistant

# Создайте необходимые директории
mkdir -p logs credentials

# Запустите
docker-compose -f docker-compose.production.yml up -d --build
```

### Шаг 6: Проверьте работу

```bash
# Проверка статуса
docker ps

# Логи
docker logs -f telegram-bot

# Для выхода из логов нажмите Ctrl+C
```

---

## Способ 2: Настройка SSH-ключа для автоматического деплоя

Если хотите использовать автоматический скрипт deploy-auto.sh:

### На локальной машине:

```bash
# Генерация SSH-ключа (если нет)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/regru_key -N ""

# Копирование ключа (через веб-консоль REG.RU)
cat ~/.ssh/regru_key.pub
```

### В веб-консоли REG.RU:

```bash
# Создайте директорию .ssh
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Добавьте публичный ключ
nano ~/.ssh/authorized_keys
# Вставьте содержимое regru_key.pub
# Сохраните: Ctrl+X → Y → Enter

chmod 600 ~/.ssh/authorized_keys

# Включите SSH аутентификацию по ключу
nano /etc/ssh/sshd_config
# Найдите и раскомментируйте/измените:
# PubkeyAuthentication yes
# Сохраните и перезапустите SSH:
systemctl restart sshd
```

### На локальной машине:

```bash
# Теперь можно подключаться без пароля
ssh -i ~/.ssh/regru_key root@91.229.8.221

# И использовать rsync
rsync -avz -e "ssh -i ~/.ssh/regru_key" /Users/fatbookpro/ai-calendar-assistant/ root@91.229.8.221:/root/ai-calendar-assistant/
```

---

## Способ 3: Использование GitHub Actions (автодеплой при push)

Если ваш проект в GitHub:

### Создайте .github/workflows/deploy.yml

```yaml
name: Deploy to REG.RU VPS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: 91.229.8.221
          username: root
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /root/ai-calendar-assistant
            git pull
            docker-compose -f docker-compose.production.yml down
            docker-compose -f docker-compose.production.yml up -d --build
```

Добавьте приватный SSH-ключ в GitHub Secrets (Settings → Secrets → Actions):
- Имя: `SSH_PRIVATE_KEY`
- Значение: содержимое файла `~/.ssh/regru_key`

---

## Полезные команды в веб-консоли

```bash
# Просмотр логов
docker logs -f telegram-bot

# Последние 100 строк
docker logs --tail 100 telegram-bot

# Перезапуск
docker restart telegram-bot

# Остановка
docker stop telegram-bot

# Запуск
docker start telegram-bot

# Пересборка и запуск
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build

# Проверка ресурсов
docker stats telegram-bot
free -h
df -h

# Очистка
docker system prune -a
```

---

## Устранение проблем

### Проблема: "TELEGRAM_BOT_TOKEN не установлен"

```bash
# Проверьте .env файл
cat /root/ai-calendar-assistant/.env

# Убедитесь что нет пробелов вокруг =
# Правильно: TELEGRAM_BOT_TOKEN=1234567
# Неправильно: TELEGRAM_BOT_TOKEN = 1234567
```

### Проблема: "Cannot connect to Docker daemon"

```bash
systemctl start docker
systemctl enable docker
```

### Проблема: "Out of memory"

```bash
# Создайте swap
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Проблема: "No space left on device"

```bash
# Очистите Docker
docker system prune -a

# Удалите логи
rm -rf /root/ai-calendar-assistant/logs/*
journalctl --vacuum-time=7d
```

---

## ✅ После успешного запуска

1. Найдите вашего бота в Telegram
2. Отправьте `/start`
3. Проверьте что бот отвечает

**Готово! Бот работает 24/7!** 🎉
