# 🚀 Быстрый деплой на REG.RU VPS

## Ваши данные сервера

```
IP: 95.163.227.26
Логин: root
Пароль: xZV5uNNlvqd9G01r
ОС: Ubuntu 22.04 LTS
```

---

## ⚡ Способ 1: Автоматический деплой (5 минут)

### Шаг 1: Настройте .env файл

```bash
cd /Users/fatbookpro/ai-calendar-assistant
cp .env.example .env
nano .env
```

Заполните обязательные переменные:
- `TELEGRAM_BOT_TOKEN` - от @BotFather
- `OPENAI_API_KEY` - для Whisper
- `ANTHROPIC_API_KEY` - для Claude

### Шаг 2: Запустите деплой

```bash
./deploy-to-regru.sh
```

При первом запуске введите пароль: `xZV5uNNlvqd9G01r`

**Готово!** Бот запущен на сервере.

---

## 🔧 Способ 2: Ручная установка

### Шаг 1: Подключитесь к серверу

```bash
ssh root@95.163.227.26
# Пароль: xZV5uNNlvqd9G01r
```

### Шаг 2: Настройте сервер (ОДИН РАЗ)

Скопируйте скрипт на сервер и запустите:

```bash
# На локальной машине:
scp /Users/fatbookpro/ai-calendar-assistant/setup-server.sh root@95.163.227.26:/root/
# Пароль: xZV5uNNlvqd9G01r

# На сервере:
chmod +x /root/setup-server.sh
./setup-server.sh
```

### Шаг 3: Скопируйте файлы проекта

```bash
# На локальной машине:
cd /Users/fatbookpro/ai-calendar-assistant
scp -r * root@95.163.227.26:/root/ai-calendar-assistant/
```

### Шаг 4: Создайте .env на сервере

```bash
# На сервере:
cd /root/ai-calendar-assistant
nano .env
```

Вставьте:
```env
TELEGRAM_BOT_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
RADICALE_URL=https://your-radicale-url
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Сохраните: `Ctrl+X` → `Y` → `Enter`

### Шаг 5: Запустите бота

```bash
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml up -d --build
```

### Шаг 6: Проверьте логи

```bash
docker logs -f telegram-bot
```

---

## 📋 Полезные команды на сервере

После подключения через `ssh root@95.163.227.26`:

```bash
# Просмотр логов
/root/logs.sh
# или
docker logs -f telegram-bot

# Перезапуск бота
/root/restart-bot.sh
# или
docker restart telegram-bot

# Обновление бота
/root/update-bot.sh

# Проверка статуса
docker ps

# Проверка ресурсов
docker stats telegram-bot
free -h
df -h
```

---

## 🔄 Обновление бота

### С локальной машины:

```bash
./deploy-to-regru.sh
```

### На сервере:

```bash
/root/update-bot.sh
```

---

## 🐛 Решение проблем

### Бот не запускается

```bash
# Проверьте логи
docker logs telegram-bot

# Проверьте .env
cat /root/ai-calendar-assistant/.env

# Пересоберите
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
```

### Нет места на диске

```bash
# Очистка Docker
docker system prune -a

# Очистка логов
rm -rf /root/ai-calendar-assistant/logs/*.log
```

### Нужно больше памяти

```bash
# Проверить swap
free -h

# Swap уже создан скриптом setup-server.sh
```

---

## 📞 Контакты поддержки REG.RU

- Телефон: **8 800 333-33-33**
- Email: support@reg.ru
- Личный кабинет: https://www.reg.ru/user/account

---

## 📚 Дополнительная документация

- **Подробная инструкция:** [DEPLOY_REGRU_DETAILED.md](DEPLOY_REGRU_DETAILED.md)
- **Базовая инструкция:** [DEPLOY_REGRU.md](DEPLOY_REGRU.md)
- **Общий README:** [README.md](README.md)

---

## ✅ Чеклист развёртывания

- [ ] Сервер доступен по SSH
- [ ] Скрипт setup-server.sh выполнен (один раз)
- [ ] Файлы проекта скопированы на сервер
- [ ] .env файл создан и заполнен
- [ ] docker-compose.production.yml существует
- [ ] Бот запущен: `docker ps` показывает telegram-bot
- [ ] Логи без ошибок: `docker logs telegram-bot`
- [ ] Бот отвечает в Telegram

**Готово! Бот работает 24/7! 🎉**

---

## 💰 Стоимость

REG.RU VPS (тариф Start):
- 1 vCPU
- 512 MB RAM
- 10 GB SSD
- **~200₽/месяц**

---

## 🔐 Безопасность

Скрипт setup-server.sh автоматически:
- ✅ Настраивает firewall (UFW)
- ✅ Разрешает только SSH (22), HTTP (80), HTTPS (443)
- ✅ Создаёт swap файл для экономии RAM
- ✅ Настраивает автоочистку логов Docker
- ✅ Создаёт мониторинг бота (каждые 5 минут)

---

## 🎯 Быстрые ссылки

- SSH: `ssh root@95.163.227.26`
- DNS админка: https://dnsadmin.hosting.reg.ru/manager/ispmgr
- Личный кабинет REG.RU: https://www.reg.ru/user/account

**Пароль везде:** `xZV5uNNlvqd9G01r`
**DNS логин:** `ce113047753`
**DNS пароль:** `51M_wz9gP9oPMdC`
