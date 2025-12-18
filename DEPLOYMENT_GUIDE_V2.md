# 🚀 Руководство по развертыванию Admin Panel v2

**Дата:** 18 декабря 2025  
**Версия:** 2.0 (MVP)

---

## 📋 ЧТО ИЗМЕНИЛОСЬ

### Было (v1):
- ❌ 3 пароля для входа
- ❌ Нет 2FA
- ❌ localStorage (уязвим к XSS)
- ❌ Один админ
- ❌ Нет аудита

### Стало (v2):
- ✅ Login + Password + 2FA (Google Authenticator)
- ✅ httpOnly cookies (защита от XSS)
- ✅ Множественные админы с ролями
- ✅ Полный аудит всех действий
- ✅ Panic password (fake mode сохранен)
- ✅ IP/UA binding (защита от кражи токенов)
- ✅ Улучшенный rate limiting (3/5мин + блокировка)

---

## ⚙️ ПОДГОТОВКА

### 1. Backup (ОБЯЗАТЕЛЬНО!)

```bash
# Перейти в директорию проекта
cd /Users/fatbookpro/ai-calendar-assistant/ai-calendar-assistant

# Создать backup базы данных
cp analytics.db analytics.db.backup.$(date +%Y%m%d_%H%M%S)

# Создать backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Создать backup текущего кода
git add -A
git commit -m "Backup before admin v2 migration"
git branch backup-before-admin-v2
```

### 2. Установить зависимости

```bash
# Активировать виртуальное окружение (если используется)
source venv/bin/activate  # или: . venv/bin/activate

# Установить новые пакеты
pip install bcrypt==4.1.1 pyotp==2.9.0 qrcode[pil]==7.4.2 slowapi==0.1.9

# Проверить установку
python -c "import bcrypt, pyotp, qrcode, slowapi; print('✅ All packages installed')"
```

### 3. Проверить переменные окружения

```bash
# Проверить что есть ADMIN_PASSWORD_1
grep ADMIN_PASSWORD_1 .env

# Если нет - добавить
echo "ADMIN_PASSWORD_1=your_secure_password_here" >> .env
echo "ADMIN_EMAIL=nikitatitov070@yandex.ru" >> .env

# Опционально: добавить panic password (для fake mode)
echo "ADMIN_PASSWORD_2=your_panic_password_here" >> .env
```

---

## 🔄 МИГРАЦИЯ

### Шаг 1: Запустить миграцию (dry-run)

```bash
# Проверить что будет сделано (без изменений)
python scripts/migrate_admin_to_v2.py --dry-run

# Вывод должен показать:
# - Создание таблиц admin_users и admin_audit_log
# - Создание админа 'admin' из ADMIN_PASSWORD_1
# - Настройка panic password (если есть ADMIN_PASSWORD_2)
```

### Шаг 2: Применить миграцию

```bash
# Применить изменения
python scripts/migrate_admin_to_v2.py

# Должно вывести:
# ✅ Tables created
# ✅ Admin user created successfully!
# 
# 📋 Next steps:
#    1. Open admin panel
#    2. Login with username: admin
#    3. Setup 2FA
```

### Шаг 3: Проверить миграцию

```bash
# Проверить что таблицы созданы
sqlite3 analytics.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'admin%';"

# Должно вывести:
# admin_users
# admin_audit_log

# Проверить что админ создан
sqlite3 analytics.db "SELECT username, email, role, totp_enabled FROM admin_users WHERE username='admin';"

# Должно вывести:
# admin|nikitatitov070@yandex.ru|admin|0
```

---

## 🚀 РАЗВЕРТЫВАНИЕ

### Вариант A: Локальная разработка

```bash
# Остановить текущий сервер (Ctrl+C)

# Запустить с новыми роутами
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Открыть админку
open http://localhost:8000/static/admin.html
```

### Вариант B: Production (Docker)

```bash
# Остановить контейнер
docker-compose down

# Пересобрать с новыми зависимостями
docker-compose build

# Запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f telegram-bot
```

### Вариант C: Production (systemd)

```bash
# Остановить сервис
sudo systemctl stop telegram-bot

# Обновить код
git pull origin main

# Установить зависимости
pip install -r app/requirements.txt

# Запустить миграцию
python scripts/migrate_admin_to_v2.py

# Запустить сервис
sudo systemctl start telegram-bot

# Проверить статус
sudo systemctl status telegram-bot

# Проверить логи
sudo journalctl -u telegram-bot -f
```

---

## 🔐 ПЕРВЫЙ ВХОД И НАСТРОЙКА 2FA

### 1. Открыть админку

```
URL: https://your-domain.com/static/admin.html
или: http://localhost:8000/static/admin.html
```

### 2. Войти с новыми данными

```
Username: admin
Password: <ваш ADMIN_PASSWORD_1 из .env>
2FA Code: (оставить пустым при первом входе)
```

### 3. Настроить 2FA

После первого входа система предложит настроить 2FA:

1. **Появится QR код** - отсканируй его приложением Google Authenticator
2. **Или введи ключ вручную** - если QR не работает
3. **Введи 6-значный код** из приложения
4. **Готово!** Теперь 2FA активирована

### 4. Последующие входы

```
Username: admin
Password: <ваш пароль>
2FA Code: <6 цифр из Google Authenticator>
```

---

## 🧪 ТЕСТИРОВАНИЕ

### 1. Проверить вход

```bash
# Тест login endpoint
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password_here"
  }'

# Должно вернуть:
# {"success": true, "mode": "real", "totp_required": true, ...}
```

### 2. Проверить panic mode

```bash
# Если настроен ADMIN_PASSWORD_2 - проверить fake mode
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_panic_password_here"
  }'

# Должно вернуть:
# {"success": true, "mode": "fake", ...}
```

### 3. Проверить статистику

```bash
# Получить токен из cookies или ответа login
TOKEN="your_access_token_here"

# Запросить статистику
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer $TOKEN"

# Должно вернуть JSON со статистикой
```

### 4. Проверить audit log

```bash
# Проверить что логируются действия
sqlite3 analytics.db "SELECT * FROM admin_audit_log ORDER BY timestamp DESC LIMIT 5;"

# Должно показать последние 5 действий админа
```

---

## 🔧 НАСТРОЙКА .env

### Минимальная конфигурация

```env
# Основной пароль админа (обязательно)
ADMIN_PASSWORD_1=your_very_secure_password_123!

# Email админа (для восстановления пароля)
ADMIN_EMAIL=nikitatitov070@yandex.ru

# Опционально: Panic password для fake mode
ADMIN_PASSWORD_2=your_panic_password_456!

# JWT ключи (создаются автоматически в .keys/)
# JWT_PRIVATE_KEY_PATH=.keys/admin_jwt_private.pem
# JWT_PUBLIC_KEY_PATH=.keys/admin_jwt_public.pem
```

### Полная конфигурация

```env
# ===== ADMIN AUTHENTICATION =====

# Основной пароль (обязательно)
ADMIN_PASSWORD_1=your_very_secure_password_123!

# Email админа (обязательно для production)
ADMIN_EMAIL=nikitatitov070@yandex.ru

# Panic password для fake mode (опционально)
ADMIN_PASSWORD_2=your_panic_password_456!

# JWT ключи (опционально, создаются автоматически)
JWT_PRIVATE_KEY_PATH=.keys/admin_jwt_private.pem
JWT_PUBLIC_KEY_PATH=.keys/admin_jwt_public.pem

# ===== СТАРЫЕ ПЕРЕМЕННЫЕ (можно удалить после миграции) =====
# ADMIN_PRIMARY_PASSWORD=...  # не используется в v2
# ADMIN_SECONDARY_PASSWORD=... # не используется в v2
# ADMIN_TERTIARY_PASSWORD=...  # не используется в v2
# ADMIN_PASSWORD_3=...         # не используется в v2
```

---

## 🐛 TROUBLESHOOTING

### Проблема: "Admin passwords not configured"

**Решение:**
```bash
# Проверить что ADMIN_PASSWORD_1 установлен
grep ADMIN_PASSWORD_1 .env

# Если нет - добавить
echo "ADMIN_PASSWORD_1=your_password" >> .env

# Перезапустить сервер
```

### Проблема: "Failed to initialize admin auth"

**Решение:**
```bash
# Проверить что пакеты установлены
pip install bcrypt pyotp qrcode slowapi

# Проверить права на .keys/
mkdir -p .keys
chmod 700 .keys

# Перезапустить сервер
```

### Проблема: "Invalid or expired token"

**Решение:**
```bash
# Очистить cookies в браузере
# Или выйти и войти заново

# Проверить что JWT ключи не изменились
ls -la .keys/
# Если файлы пустые или отсутствуют - удалить и пересоздать:
rm -rf .keys/
# При следующем запуске создадутся автоматически
```

### Проблема: "Too many failed attempts"

**Решение:**
```bash
# Подождать 15 минут
# Или перезапустить сервер (сбросит rate limiting в памяти)

# Для production используйте Redis для rate limiting:
# В .env:
# REDIS_URL=redis://localhost:6379/0
```

### Проблема: "2FA code invalid"

**Решение:**
1. Проверить что время на сервере синхронизировано:
   ```bash
   date
   # Если время неправильное - синхронизировать:
   sudo ntpdate -s time.apple.com
   ```

2. Проверить что в Google Authenticator правильное время:
   - Настройки → Коррекция времени для кодов → Синхронизировать

3. Попробовать соседние коды (valid_window=1 позволяет ±30 секунд)

---

## 📊 МОНИТОРИНГ

### Проверить здоровье системы

```bash
# Health check
curl http://localhost:8000/api/admin/health

# Должно вернуть:
# {"status": "ok", "version": "v2"}
```

### Просмотр audit логов

```bash
# Последние 20 действий админов
sqlite3 analytics.db "
SELECT 
  datetime(timestamp) as time,
  username,
  action_type,
  details,
  ip_address,
  success
FROM admin_audit_log 
ORDER BY timestamp DESC 
LIMIT 20;
"
```

### Статистика входов

```bash
# Успешные входы за последние 7 дней
sqlite3 analytics.db "
SELECT 
  DATE(timestamp) as date,
  COUNT(*) as logins
FROM admin_audit_log 
WHERE action_type = 'login_success'
  AND timestamp > datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY date DESC;
"
```

---

## 🔄 ОТКАТ (Rollback)

Если что-то пошло не так:

### 1. Остановить сервер

```bash
# Docker
docker-compose down

# systemd
sudo systemctl stop telegram-bot

# Локально
# Ctrl+C
```

### 2. Восстановить backup

```bash
# Восстановить базу данных
cp analytics.db.backup.YYYYMMDD_HHMMSS analytics.db

# Восстановить .env
cp .env.backup.YYYYMMDD_HHMMSS .env

# Откатить код
git checkout backup-before-admin-v2
```

### 3. Запустить старую версию

```bash
# Docker
docker-compose up -d

# systemd
sudo systemctl start telegram-bot

# Локально
python -m uvicorn app.main:app --reload
```

---

## ✅ CHECKLIST РАЗВЕРТЫВАНИЯ

- [ ] Создан backup базы данных
- [ ] Создан backup .env файла
- [ ] Создана ветка backup в git
- [ ] Установлены новые пакеты (bcrypt, pyotp, qrcode, slowapi)
- [ ] Проверены переменные ADMIN_PASSWORD_1 и ADMIN_EMAIL
- [ ] Запущена миграция (dry-run)
- [ ] Применена миграция
- [ ] Проверено создание таблиц
- [ ] Проверено создание админа
- [ ] Перезапущен сервер
- [ ] Проверен health check
- [ ] Выполнен первый вход
- [ ] Настроена 2FA
- [ ] Проверен вход с 2FA
- [ ] Проверен panic mode (если настроен)
- [ ] Проверена статистика
- [ ] Проверен audit log
- [ ] Обновлена документация
- [ ] Уведомлена команда

---

## 📞 ПОДДЕРЖКА

Если возникли проблемы:

1. **Проверить логи:**
   ```bash
   # Docker
   docker-compose logs -f telegram-bot
   
   # systemd
   sudo journalctl -u telegram-bot -f
   
   # Локально
   # Смотреть в консоль
   ```

2. **Проверить документацию:**
   - `ADMIN_IMPROVEMENTS_PLAN.md` - детальный план
   - `ADMIN_COMPARISON.md` - сравнение версий
   - Этот файл - руководство по развертыванию

3. **Откатиться на backup** (см. раздел "Откат")

---

**Удачного развертывания! 🚀**

