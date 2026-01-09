# ✅ Настройка Безопасной Конфигурации Завершена

**Дата:** 22 октября 2025
**Статус:** Готово к запуску

---

## 🎉 Что Сделано

### 1. ✅ Сгенерированы Секреты

- **Telegram Webhook Secret**: `dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=`
- **Redis Password**: `***REDACTED_REDIS***`
- **CORS Origins**: `https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org`

### 2. ✅ Настроена Radicale Аутентификация

**Создано:**
- `radicale/users` - htpasswd файл с bcrypt
- `radicale/rights` - правила доступа
- `radicale/config.ini` - конфигурация сервера

**Учетные записи:**
- **Admin**: `admin` / `AdminSecurePass2025!`
- **Bot Service Account**: `calendar_bot` / `sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=`

### 3. ✅ Обновлен .env Файл

Добавлены следующие переменные:
```bash
TELEGRAM_WEBHOOK_SECRET=dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=
REDIS_PASSWORD=***REDACTED_REDIS***
CORS_ORIGINS=https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=
```

### 4. ✅ Обновлен Код

**Файлы:**
- `app/config.py` - добавлены Redis и Radicale bot credentials
- `app/services/calendar_radicale.py` - использует bot credentials для аутентификации
- `app/main.py` - CORS origins из config
- `docker-compose.secure.yml` - монтирование rights файла

---

## 🚀 Следующий Шаг: Запуск на Сервере

### Вариант A: Локальное Тестирование (Опционально)

Если хотите протестировать локально перед деплоем на сервер:

```bash
# 1. Остановить старую конфигурацию (если запущена)
docker-compose down

# 2. Сборка
docker-compose -f docker-compose.secure.yml build

# 3. Запуск
docker-compose -f docker-compose.secure.yml up -d

# 4. Проверка логов
docker-compose -f docker-compose.secure.yml logs -f

# 5. Проверка статуса
docker-compose -f docker-compose.secure.yml ps
```

### Вариант B: Деплой на Сервер (Рекомендуется)

```bash
# 1. Подключиться к серверу
sshpass -p '$SERVER_PASSWORD' ssh root@95.163.227.26

# 2. Перейти в директорию проекта
cd /root/ai-calendar-assistant

# 3. Остановить текущий бот
docker stop telegram-bot
docker rm telegram-bot

# 4. Скопировать новые файлы с локальной машины
# (выполнить на ЛОКАЛЬНОЙ машине в новом терминале)
```

**На локальной машине:**
```bash
cd /Users/fatbookpro/ai-calendar-assistant

# Скопировать обновленные файлы
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/services/calendar_radicale.py \
  app/config.py \
  app/main.py \
  app/utils/pii_masking.py \
  docker-compose.secure.yml \
  root@95.163.227.26:/root/ai-calendar-assistant/

# Скопировать Radicale конфигурацию
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no -r \
  radicale/ \
  root@95.163.227.26:/root/ai-calendar-assistant/

# Обновить .env (добавить новые переменные)
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 << 'EOF'
cd /root/ai-calendar-assistant

# Добавить секреты в .env
cat >> .env << 'ENVEOF'

# Security Configuration (Generated 2025-10-22)
TELEGRAM_WEBHOOK_SECRET=dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=
REDIS_PASSWORD=***REDACTED_REDIS***
CORS_ORIGINS=https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=
ENVEOF

echo "✅ .env updated"
EOF
```

**На сервере:**
```bash
# 5. Запустить с новой конфигурацией
docker-compose -f docker-compose.secure.yml up -d

# 6. Проверить статус
docker-compose -f docker-compose.secure.yml ps

# 7. Проверить логи
docker logs -f telegram-bot

# 8. Проверить, что все сервисы работают
docker ps
# Должны быть: telegram-bot, radicale, calendar-redis
```

---

## 🔍 Проверка Безопасности

После запуска проверьте:

### 1. Webhook Secret

```bash
# На локальной машине
BOT_TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d '=' -f2)

curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo" | jq .

# Убедитесь что url установлен правильно
```

### 2. CORS

```bash
# Попытка доступа с неразрешенного домена
curl -v -H "Origin: https://evil.com" \
  https://этонесамыйдлинныйдомен.рф/api/events/123 2>&1 | grep -i "access-control"

# Не должно быть Access-Control-Allow-Origin заголовка
```

### 3. Radicale Auth

```bash
# На сервере
docker exec radicale cat /config/users
# Должен показать зашифрованные пароли

docker logs radicale | grep -i auth
# Должны быть логи об аутентификации
```

### 4. Redis

```bash
# На сервере
docker exec calendar-redis redis-cli -a "***REDACTED_REDIS***" ping

# Должно вернуть: PONG
```

### 5. PII Masking

```bash
# На сервере
docker logs telegram-bot 2>&1 | tail -50 | grep -E "(user_id_hash|title_masked)"

# Должны быть замаскированные данные вместо plaintext
```

---

## ⚠️ Важные Замечания

### 1. Обновление Webhook

После запуска на сервере НЕ ЗАБУДЬТЕ обновить webhook с secret token:

```bash
BOT_TOKEN="ваш_токен_бота"
WEBHOOK_SECRET="dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc="

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://этонесамыйдлинныйдомен.рф/telegram/webhook\",
    \"secret_token\": \"${WEBHOOK_SECRET}\"
  }"
```

### 2. Режим Тестирования Daily Reminders

Напоминаю, что в `app/services/daily_reminders.py` сейчас:
```python
TEST_MODE = True  # Тестовое расписание для user_id 2296243
```

После тестирования измените на:
```python
TEST_MODE = False  # Production расписание для всех
```

### 3. Backup Credentials

**СОХРАНИТЕ эти данные в безопасном месте!**

```
Admin Radicale:
  Username: admin
  Password: AdminSecurePass2025!

Bot Service Account:
  Username: calendar_bot
  Password: sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=

Webhook Secret: dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=
Redis Password: ***REDACTED_REDIS***
```

---

## 📝 Checklist Деплоя

- [ ] Скопированы обновленные файлы на сервер
- [ ] Обновлен .env с новыми секретами
- [ ] Остановлен старый контейнер telegram-bot
- [ ] Запущена новая конфигурация (docker-compose.secure.yml)
- [ ] Проверены логи всех сервисов (bot, radicale, redis)
- [ ] Установлен webhook с secret token
- [ ] Протестирован бот (отправка сообщения)
- [ ] Проверена работа создания событий
- [ ] Проверена работа напоминаний
- [ ] Изменен TEST_MODE на False (после тестирования)

---

## 🆘 Troubleshooting

### Проблема: "Authentication required" в логах бота

**Решение:**
```bash
# Проверить что bot credentials в .env
grep RADICALE_BOT /root/ai-calendar-assistant/.env

# Проверить что Radicale их видит
docker logs radicale | grep calendar_bot

# Перезапустить бота
docker-compose -f docker-compose.secure.yml restart telegram-bot
```

### Проблема: Redis connection refused

**Решение:**
```bash
# Проверить что Redis запущен
docker ps | grep redis

# Проверить пароль
docker exec calendar-redis redis-cli -a "***REDACTED_REDIS***" ping

# Если нет - запустить
docker-compose -f docker-compose.secure.yml up -d redis
```

### Проблема: Webhook не работает

**Решение:**
```bash
# 1. Проверить webhook info
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"

# 2. Удалить и установить заново
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/deleteWebhook"

# Подождать 5 секунд

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=https://этонесамыйдлинныйдомен.рф/telegram/webhook" \
  -d "secret_token=dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc="
```

---

## 📚 Дополнительная Документация

- [QUICK_START_SECURITY.md](QUICK_START_SECURITY.md) - Пошаговая инструкция
- [IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md) - Сводка доработок
- [SECURITY_IMPROVEMENTS_APPLIED.md](SECURITY_IMPROVEMENTS_APPLIED.md) - Детали реализации
- [CRITICAL_IMPROVEMENTS.md](CRITICAL_IMPROVEMENTS.md) - Полный список доработок

---

## ✅ Готово!

Все файлы обновлены, секреты сгенерированы, конфигурация готова.

**Следующий шаг:** Деплой на сервер (см. "Вариант B" выше)

Удачи! 🚀
