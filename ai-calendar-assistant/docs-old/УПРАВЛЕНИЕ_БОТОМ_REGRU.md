# 🎮 Управление AI Calendar Bot на REG.RU

## 📋 Информация о сервере

```
IP: 91.229.8.221
Логин: root
Пароль: upvzrr3LH4pxsaqs
```

**Подключение:**
```bash
ssh root@91.229.8.221
# Или через веб-консоль: https://www.reg.ru/user/account
```

---

## 🚀 Быстрые команды

### Запуск бота

```bash
ssh root@91.229.8.221
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.simple.yml up -d
```

### Остановка бота

```bash
ssh root@91.229.8.221
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.simple.yml down
```

### Перезапуск бота

```bash
ssh root@91.229.8.221
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.simple.yml restart
```

### Просмотр логов

```bash
ssh root@91.229.8.221
docker logs -f telegram-bot

# Для выхода нажмите Ctrl+C
```

### Проверка статуса

```bash
ssh root@91.229.8.221
docker ps
```

---

## 📝 Полезные команды

### Просмотр последних 100 строк логов

```bash
docker logs --tail 100 telegram-bot
```

### Проверка использования ресурсов

```bash
docker stats telegram-bot
```

### Очистка места на диске

```bash
# Остановить бота
docker-compose -f /root/ai-calendar-assistant/docker-compose.simple.yml down

# Очистка Docker
docker system prune -a

# Запустить снова
docker-compose -f /root/ai-calendar-assistant/docker-compose.simple.yml up -d
```

### Обновление кода

```bash
cd /root/ai-calendar-assistant

# Остановить бота
docker-compose -f docker-compose.simple.yml down

# Загрузить новый код (если есть Git)
git pull

# Или вручную отредактировать файл
nano run_simple_bot.py

# Пересобрать и запустить
docker-compose -f docker-compose.simple.yml up -d --build
```

---

## ⚙️ Изменение настроек

### Изменить токен Telegram

```bash
ssh root@91.229.8.221
cd /root/ai-calendar-assistant

# Редактировать .env
nano .env

# Изменить строку:
# TELEGRAM_BOT_TOKEN=новый_токен_здесь

# Сохранить: Ctrl+X → Y → Enter

# Перезапустить
docker-compose -f docker-compose.simple.yml restart
```

### Добавить новые переменные окружения

```bash
nano /root/ai-calendar-assistant/.env

# Добавить строки, например:
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# Сохранить и перезапустить
docker-compose -f docker-compose.simple.yml restart
```

---

## 🐛 Решение проблем

### Бот не отвечает

```bash
# Проверить логи
docker logs telegram-bot

# Перезапустить
docker restart telegram-bot
```

### Ошибка "Conflict: terminated by other getUpdates"

**Проблема:** Другой бот с тем же токеном уже запущен где-то ещё.

**Решение:**
1. Остановите бота на других серверах (Railway, Fly.io, Heroku, и т.д.)
2. Или создайте новый токен у @BotFather в Telegram
3. Обновите .env на сервере

```bash
nano /root/ai-calendar-assistant/.env
# Измените TELEGRAM_BOT_TOKEN
docker-compose -f docker-compose.simple.yml restart
```

### Нет места на диске

```bash
# Проверить место
df -h

# Очистить Docker
docker system prune -a

# Удалить логи
rm -rf /root/ai-calendar-assistant/logs/*
```

### Контейнер постоянно перезапускается

```bash
# Посмотреть что случилось
docker logs --tail 100 telegram-bot

# Проверить .env файл
cat /root/ai-calendar-assistant/.env

# Убедиться что токен правильный
```

---

## 📊 Мониторинг

### Автоматическая проверка работы бота

Создайте скрипт мониторинга:

```bash
nano /root/check-bot.sh
```

Вставьте:

```bash
#!/bin/bash

if ! docker ps | grep -q telegram-bot; then
  echo "[$(date)] ⚠️ Бот не запущен! Перезапуск..."
  cd /root/ai-calendar-assistant
  docker-compose -f docker-compose.simple.yml up -d
  echo "[$(date)] ✅ Бот перезапущен"
else
  echo "[$(date)] ✅ Бот работает"
fi
```

Сохраните и сделайте исполняемым:

```bash
chmod +x /root/check-bot.sh
```

Добавьте в cron (проверка каждые 5 минут):

```bash
crontab -e

# Добавьте строку:
*/5 * * * * /root/check-bot.sh >> /root/bot-monitor.log 2>&1
```

### Просмотр логов мониторинга

```bash
tail -f /root/bot-monitor.log
```

---

## 🔄 Обновление до полной версии

Когда захотите добавить все функции (STT, календарь, и т.д.):

### Вариант 1: Использовать requirements.txt с openai

```bash
cd /root/ai-calendar-assistant

# Обновить requirements-minimal.txt, добавить:
echo "openai>=1.50.0" >> requirements-minimal.txt

# Пересобрать
docker-compose -f docker-compose.simple.yml down
docker system prune -f
docker-compose -f docker-compose.simple.yml up -d --build
```

### Вариант 2: Увеличить размер диска на REG.RU

1. Зайдите в личный кабинет REG.RU
2. Увеличьте диск VPS до 20-30GB
3. Используйте полный requirements.txt

---

## 📁 Структура файлов на сервере

```
/root/ai-calendar-assistant/
├── .env                           # Настройки (токены, ключи)
├── run_simple_bot.py             # Основной код бота
├── requirements-minimal.txt       # Зависимости Python
├── Dockerfile.simple             # Конфигурация Docker
├── docker-compose.simple.yml     # Конфигурация Docker Compose
└── logs/                         # Логи (создаётся автоматически)
```

---

## 🆘 Экстренное восстановление

Если что-то сломалось:

### Полное переразвёртывание

```bash
ssh root@91.229.8.221

# Остановить всё
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)

# Удалить старые данные
rm -rf /root/ai-calendar-assistant/*

# Создать заново файлы (скопируйте из ПРОСТАЯ_УСТАНОВКА.txt)
cd /root/ai-calendar-assistant
# ... создайте файлы заново ...

# Запустить
docker-compose -f docker-compose.simple.yml up -d --build
```

---

## 💰 Управление сервером REG.RU

### Личный кабинет

https://www.reg.ru/user/account

### Управление VPS

1. Войдите в личный кабинет
2. Серверы → VPS → Sapphire Palladium
3. Доступные действия:
   - Перезагрузка сервера
   - Смена пароля root
   - Увеличение ресурсов (RAM, диск)
   - Создание снапшота (бэкап)
   - Консоль (веб-терминал)

### Создание бэкапа

**Рекомендуется делать раз в неделю:**

1. Личный кабинет REG.RU
2. Ваш VPS → Снимки (Snapshots)
3. Создать снимок → Указать название
4. Готово! Можно восстановить в любой момент

---

## 🔐 Безопасность

### Смена пароля root (рекомендуется)

```bash
ssh root@91.229.8.221
passwd
# Введите новый пароль дважды
```

### Настройка firewall

```bash
# Установка UFW
apt-get install -y ufw

# Настройка правил
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Включить
ufw enable
```

---

## 📞 Поддержка

### REG.RU
- Телефон: 8 800 333-33-33
- Email: support@reg.ru
- Личный кабинет: https://www.reg.ru/user/account

### Telegram Bot API
- Документация: https://core.telegram.org/bots/api
- BotFather: @BotFather в Telegram

---

## ✅ Чеклист регулярного обслуживания

**Еженедельно:**
- [ ] Проверить логи на ошибки: `docker logs --tail 100 telegram-bot`
- [ ] Проверить место на диске: `df -h`
- [ ] Проверить использование RAM: `free -h`
- [ ] Создать снапшот в панели REG.RU

**Ежемесячно:**
- [ ] Обновить систему: `apt-get update && apt-get upgrade -y`
- [ ] Очистить Docker: `docker system prune -a`
- [ ] Проверить размер логов: `du -sh /var/lib/docker/`

**По необходимости:**
- [ ] Обновить код бота
- [ ] Изменить токены/ключи
- [ ] Проверить работу после перезагрузки сервера

---

## 🎯 Быстрая справка

```bash
# Подключение
ssh root@91.229.8.221

# Запуск
docker-compose -f /root/ai-calendar-assistant/docker-compose.simple.yml up -d

# Остановка
docker-compose -f /root/ai-calendar-assistant/docker-compose.simple.yml down

# Логи
docker logs -f telegram-bot

# Статус
docker ps

# Перезапуск
docker restart telegram-bot

# Редактирование кода
nano /root/ai-calendar-assistant/run_simple_bot.py

# Редактирование настроек
nano /root/ai-calendar-assistant/.env
```

---

**Готово! Теперь вы можете полностью управлять ботом на REG.RU! 🎉**
