# 🚀 Быстрый Старт - Безопасная Конфигурация

**Время:** 15-20 минут
**Сложность:** Средняя

---

## Шаг 1: Генерация Секретов (2 минуты)

```bash
cd /path/to/ai-calendar-assistant

# Генерация webhook secret
export WEBHOOK_SECRET=$(openssl rand -base64 32)

# Генерация Redis password
export REDIS_PASSWORD=$(openssl rand -base64 32)

# Добавление в .env
cat >> .env << EOF

# Security Configuration (Generated on $(date))
TELEGRAM_WEBHOOK_SECRET=$WEBHOOK_SECRET
REDIS_PASSWORD=$REDIS_PASSWORD
CORS_ORIGINS=https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org
EOF

echo "✅ Секреты сгенерированы и добавлены в .env"
```

---

## Шаг 2: Настройка Radicale (5 минут)

```bash
# Генерация admin и bot пользователей
./radicale/generate_users.sh

# Скрипт запросит:
# 1. Admin username (default: admin)
# 2. Admin password (введите надежный пароль)
# 3. Автоматически создаст bot service account

# Результат:
# - radicale/users (htpasswd файл)
# - radicale/rights (access control rules)
# - RADICALE_BOT_USER и RADICALE_BOT_PASSWORD в .env
```

---

## Шаг 3: Сборка и Запуск (5 минут)

```bash
# Остановить старую конфигурацию (если запущена)
docker-compose down

# Сборка с новой конфигурацией
docker-compose -f docker-compose.secure.yml build

# Запуск безопасной конфигурации
docker-compose -f docker-compose.secure.yml up -d

# Проверка статуса
docker-compose -f docker-compose.secure.yml ps

# Все сервисы должны быть в состоянии "Up"
```

---

## Шаг 4: Настройка Telegram Webhook (2 минуты)

```bash
# Загрузка переменных из .env
export $(grep -v '^#' .env | xargs)

# Установка webhook с secret token
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"https://этонесамыйдлинныйдомен.рф/telegram/webhook\",
    \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\"
  }"

# Проверка webhook
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | jq .

# Ожидаемый результат:
# {
#   "ok": true,
#   "result": {
#     "url": "https://этонесамыйдлинныйдомен.рф/telegram/webhook",
#     "has_custom_certificate": false,
#     "pending_update_count": 0
#   }
# }
```

---

## Шаг 5: Проверка Безопасности (5 минут)

### 5.1. Проверка CORS

```bash
# Попытка доступа с неразрешенного домена
curl -v -H "Origin: https://evil.com" \
  -H "Content-Type: application/json" \
  https://этонесамыйдлинныйдомен.рф/api/events/12345

# ✅ Ожидается:
# - CORS error
# - Или отсутствие Access-Control-Allow-Origin header
```

### 5.2. Проверка Webhook Secret

```bash
# Попытка отправки webhook без secret token
curl -X POST https://этонесамыйдлинныйдомен.рф/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{"update_id": 123}'

# ✅ Ожидается: 401 Unauthorized
```

### 5.3. Проверка Radicale Auth

```bash
# Попытка доступа без аутентификации
curl http://localhost:5232/.web/

# ✅ Ожидается: 401 Unauthorized или login form
# (только если порт 5232 exposed локально)
```

### 5.4. Проверка PII Masking

```bash
# Проверка логов на маскирование
docker logs telegram-bot 2>&1 | tail -50 | grep -E "(user_id_hash|title_masked)"

# ✅ Ожидается: строки вида:
# user_id_hash="a3f8c2d9" title_masked="Вст***"
```

### 5.5. Проверка Redis

```bash
# Проверка доступа к Redis
docker exec calendar-redis redis-cli -a "$REDIS_PASSWORD" ping

# ✅ Ожидается: PONG
```

### 5.6. Проверка UUID

```bash
# Создать тестовое событие через бота
# Проверить формат UID в логах
docker logs telegram-bot 2>&1 | grep "event_created" | tail -1

# ✅ Ожидается: uid в формате UUID v4:
# uid="f47ac10b-58cc-4372-a567-0e02b2c3d479"
```

---

## 🎉 Готово!

Если все проверки прошли успешно:

- ✅ CORS origins ограничены
- ✅ Webhook защищен secret token
- ✅ Radicale требует аутентификацию
- ✅ PII данные замаскированы в логах
- ✅ Event UID генерируются как UUID v4
- ✅ Redis работает и защищен паролем

---

## 🔧 Полезные Команды

### Логи

```bash
# Все логи
docker-compose -f docker-compose.secure.yml logs -f

# Только telegram-bot
docker logs -f telegram-bot

# Только Redis
docker logs -f calendar-redis

# Только Radicale
docker logs -f radicale

# Поиск ошибок
docker logs telegram-bot 2>&1 | grep -i error
```

### Перезапуск

```bash
# Перезапуск одного сервиса
docker-compose -f docker-compose.secure.yml restart telegram-bot

# Перезапуск всех сервисов
docker-compose -f docker-compose.secure.yml restart

# Полная пересборка
docker-compose -f docker-compose.secure.yml down
docker-compose -f docker-compose.secure.yml build --no-cache
docker-compose -f docker-compose.secure.yml up -d
```

### Очистка

```bash
# Остановка и удаление контейнеров
docker-compose -f docker-compose.secure.yml down

# Остановка и удаление с volumes (⚠️ удалит все данные!)
docker-compose -f docker-compose.secure.yml down -v

# Удаление старых образов
docker image prune -a
```

---

## 🆘 Troubleshooting

### Проблема: Webhook не работает

**Симптомы:**
- Бот не отвечает на сообщения
- `getWebhookInfo` показывает ошибки

**Решение:**
```bash
# 1. Проверить логи
docker logs telegram-bot 2>&1 | grep webhook

# 2. Проверить, что webhook установлен
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo" | jq .

# 3. Переустановить webhook
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/deleteWebhook"
# Затем установить заново (см. Шаг 4)

# 4. Проверить доступность URL
curl -I https://этонесамыйдлинныйдомен.рф/health
```

### Проблема: Radicale auth не работает

**Симптомы:**
- Ошибки "Authentication required" в логах бота

**Решение:**
```bash
# 1. Проверить, что файл users существует
ls -la radicale/users

# 2. Проверить credentials в .env
grep RADICALE_BOT radicale/.env

# 3. Пересоздать пользователей
./radicale/generate_users.sh

# 4. Перезапустить Radicale
docker-compose -f docker-compose.secure.yml restart radicale
```

### Проблема: Redis connection refused

**Симптомы:**
- Ошибки "Connection refused" к Redis

**Решение:**
```bash
# 1. Проверить, что Redis запущен
docker ps | grep redis

# 2. Проверить логи Redis
docker logs calendar-redis

# 3. Проверить пароль
echo $REDIS_PASSWORD

# 4. Перезапустить Redis
docker-compose -f docker-compose.secure.yml restart redis

# 5. Проверить доступность
docker exec calendar-redis redis-cli -a "$REDIS_PASSWORD" ping
```

### Проблема: CORS ошибки в WebApp

**Симптомы:**
- WebApp не может делать API запросы
- Ошибки CORS в консоли браузера

**Решение:**
```bash
# 1. Проверить CORS_ORIGINS в .env
grep CORS_ORIGINS .env

# 2. Добавить ваш домен
# Отредактировать .env:
CORS_ORIGINS=https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org,https://ваш-домен.рф

# 3. Перезапустить бота
docker-compose -f docker-compose.secure.yml restart telegram-bot

# 4. Проверить в логах
docker logs telegram-bot 2>&1 | grep "allow_origins"
```

---

## 📚 Дополнительная Документация

- **[IMPROVEMENTS_SUMMARY.md](IMPROVEMENTS_SUMMARY.md)** - Сводка всех доработок
- **[SECURITY_IMPROVEMENTS_APPLIED.md](SECURITY_IMPROVEMENTS_APPLIED.md)** - Детали реализации
- **[CRITICAL_IMPROVEMENTS.md](CRITICAL_IMPROVEMENTS.md)** - Полный список доработок
- **[COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md)** - Техническая документация

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте Troubleshooting раздел выше
2. Изучите логи: `docker logs telegram-bot`
3. Проверьте конфигурацию: `.env` файл
4. Откройте Issue на GitHub с логами и описанием проблемы

**Удачи! 🚀**
