# Доступы к AI Calendar Assistant - Админ Панель

## Обновлено: 27 октября 2025

---

## 🌐 Веб-доступ

### Основной сайт
**URL:** https://этонесамыйдлинныйдомен.рф

### Админ-панель
**URL:** https://этонесамыйдлинныйдомен.рф/admin_fbc36dd546d7746b862e45a7.html

**Учетные данные (требуются все три пароля):**
- **Password 1 (Primary):** `Admin_Primary_2025_Secure!`
- **Password 2 (Secondary):** `Secondary_Admin_Key_2025`
- **Password 3 (Tertiary):** `Tertiary_Access_Code_2025`

**Примечание:**
- Если все 3 пароля правильные → **полный доступ**
- Если только пароли 1 и 2 правильные, а 3-й неверный → **fake mode** (показывает фейковую ошибку БД)
- Любая другая комбинация → **ошибка входа**

---

## 🤖 Telegram Bot

**Bot Username:** @ai_calendar_assistant_bot
**Bot Token:** `8378762774:AAE7oEvJX3fcHmLTQJPzQb9EIgQHXUWuaPI`

### Webhook
**Webhook URL:** https://этонесамыйдлинныйдомен.рф/webhook
**Webhook Secret:** `dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=`

---

## 🗄️ База данных и хранилище

### Radicale (CalDAV Server)

**URL:** http://radicale:5232 (внутренний)
**Доступ:** Только из Docker-сети

#### Административные учетные данные
- **Admin User:** `admin`
- **Admin Password:** `AdminSecurePass2025!`

#### Служебная учетная запись бота
- **Bot User:** `calendar_bot`
- **Bot Password:** `sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=`

#### Конфигурация
- **Config File:** `/root/ai-calendar-assistant/radicale/config`
- **Users File:** `/root/ai-calendar-assistant/radicale/users` (htpasswd format, bcrypt)
- **Rights File:** `/root/ai-calendar-assistant/radicale/rights`
- **Data Directory:** `/var/lib/calendar-bot/radicale/`

### Redis

**URL:** redis://redis:6379/0 (внутренний)
**Password:** `sVXGM73o7QxDJ9LFn02FqvT9HBNPz8vsQrAy5kfZMj0=`

**Использование:**
- Rate limiting для API
- Кэширование сессий
- Временные данные

---

## 🔐 API ключи

### Yandex GPT
**API Key:** `YOUR_YANDEX_API_KEY_HERE`
**Folder ID:** `b1g7ckqqrnfpdvj6v2iu`

**Модель:** `yandexgpt` (или `yandexgpt-lite`)
**Endpoint:** https://llm.api.cloud.yandex.net/foundationModels/v1/completion

### Yandex SpeechKit (STT)
**API Key:** `YOUR_YANDEX_API_KEY_HERE` (тот же ключ)
**Folder ID:** `b1g7ckqqrnfpdvj6v2iu`

**Endpoint:** https://stt.api.cloud.yandex.net/speech/v1/stt:recognize

---

## 🖥️ Сервер REG.RU

### SSH Доступ
**Host:** `91.229.8.221`
**User:** `root`
**Password:** `upvzrr3LH4pxsaqs`

### Основные пути

**Приложение:**
```bash
/root/ai-calendar-assistant/          # Исходный код
/var/www/calendar/                    # WebApp (статика)
/var/lib/calendar-bot/                # Persistent data
```

**Docker:**
```bash
docker ps | grep telegram-bot          # Проверить статус
docker logs telegram-bot               # Просмотр логов
docker restart telegram-bot            # Перезапуск
```

**Nginx:**
```bash
/etc/nginx/sites-available/default     # Конфигурация
/var/log/nginx/                        # Логи
```

---

## 📊 Структура пользователей

### Текущие пользователи (по состоянию на 27.10.2025)

1. **User ID: 2296243**
   - Calendar: `telegram_2296243`
   - UUID: `49d870f8-a613-11f0-ab82-f68a5f2444c4`
   - Timezone: `Europe/Moscow`
   - Language: `ru`

2. **User ID: 5602113922**
   - Calendar: `telegram_5602113922`
   - UUID: `031d836c-af1c-11f0-8124-420aac1f5c30`
   - Timezone: `Europe/Moscow`
   - Language: `ru`

3. **User ID: 7137357637**
   - Calendar: `telegram_7137357637`
   - UUID: `91c3a492-a9f0-11f0-be93-52f3e0988c59`
   - Timezone: `Europe/Moscow`
   - Language: `ru`

---

## 🔒 Безопасность

### SSL/TLS
**Сертификат:** Let's Encrypt
**Домен:** этонесамыйдлинныйдомен.рф
**Auto-renewal:** Настроен через certbot

### CORS
**Allowed Origins:**
- https://этонесамыйдлинныйдомен.рф
- https://webapp.telegram.org

### Rate Limiting
- **Per minute:** 10 запросов
- **Per hour:** 50 запросов
- **Burst detection:** 5 сообщений за 10 секунд
- **Auto-block:** 1 час после 3 bursts

---

## 🛠️ Конфигурация (.env)

```bash
# Bot
TELEGRAM_BOT_TOKEN=8378762774:AAE7oEvJX3fcHmLTQJPzQb9EIgQHXUWuaPI
TELEGRAM_WEBHOOK_SECRET=dGl89bN7zs4Qs4lod3nkUOEyjenmI26jFjEQj+kh1rc=

# Yandex API
YANDEX_GPT_API_KEY=YOUR_YANDEX_API_KEY_HERE
YANDEX_GPT_FOLDER_ID=b1g7ckqqrnfpdvj6v2iu

# Radicale
RADICALE_URL=http://radicale:5232
RADICALE_BOT_USER=calendar_bot
RADICALE_BOT_PASSWORD=sjR437KcljAWqn3QpuibWwqeu8vdp70EwRPQIx/nHdg=

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=sVXGM73o7QxDJ9LFn02FqvT9HBNPz8vsQrAy5kfZMj0=

# Security
CORS_ORIGINS=https://этонесамыйдлинныйдомен.рф,https://webapp.telegram.org
DEBUG=false
```

---

## 📱 Веб-приложение

### Основной файл
**Path:** `/var/www/calendar/index.html`
**Version:** 2025-10-27-13:45
**Features:**
- Автоматическое определение темы Telegram (светлая/темная)
- Поддержка только русского языка
- Адаптивный дизайн
- Calendar view с событиями

### Обновление
```bash
# Локально создать/изменить webapp_server.html
scp webapp_server.html root@91.229.8.221:/var/www/calendar/index.html

# Нет необходимости в перезапуске - статический файл
```

---

## 🔧 Полезные команды

### Проверка статуса
```bash
# Все контейнеры
ssh root@91.229.8.221 "docker ps"

# Логи бота
ssh root@91.229.8.221 "docker logs --tail 50 telegram-bot"

# Логи Radicale
ssh root@91.229.8.221 "docker logs --tail 50 radicale"

# Nginx статус
ssh root@91.229.8.221 "systemctl status nginx"
```

### Перезапуск сервисов
```bash
# Перезапуск бота
ssh root@91.229.8.221 "docker restart telegram-bot"

# Перезапуск всех контейнеров
ssh root@91.229.8.221 "cd /root/ai-calendar-assistant && docker-compose restart"

# Перезапуск Nginx
ssh root@91.229.8.221 "systemctl restart nginx"
```

### Обновление кода
```bash
# Загрузить файлы
scp app/services/*.py root@91.229.8.221:/root/ai-calendar-assistant/app/services/

# Скопировать в контейнер и перезапустить
ssh root@91.229.8.221 "docker cp /root/ai-calendar-assistant/app telegram-bot:/app/ && docker restart telegram-bot"
```

### Резервное копирование
```bash
# Backup Radicale data
ssh root@91.229.8.221 "tar -czf /root/radicale-backup-$(date +%Y%m%d).tar.gz /var/lib/calendar-bot/radicale/"

# Backup user preferences
ssh root@91.229.8.221 "tar -czf /root/prefs-backup-$(date +%Y%m%d).tar.gz /var/lib/calendar-bot/user_preferences.json"

# Download backups
scp root@91.229.8.221:/root/*-backup-*.tar.gz ./backups/
```

---

## ⚠️ Важная информация об аналитике

**Аналитика работает автоматически:**
- Все действия пользователей логируются в `/var/lib/calendar-bot/analytics_data.json`
- Данные отображаются в админ-панели в режиме реального времени
- При обновлении кода обязательно обновляйте ВСЕ файлы (не только изменённые)

**Если админка показывает пустые данные:**
1. Проверьте файл: `docker exec telegram-bot cat /var/lib/calendar-bot/analytics_data.json`
2. Если файл пустой или повреждён - это нормально для нового деплоя
3. Данные начнут собираться при следующем использовании бота
4. Пользователи появятся после отправки команды `/start`

**Для восстановления работы аналитики:**
```bash
# 1. Убедитесь, что все файлы обновлены
docker cp /root/ai-calendar-assistant/app/services/analytics_service.py telegram-bot:/app/app/services/
docker cp /root/ai-calendar-assistant/app/services/telegram_handler.py telegram-bot:/app/app/services/
docker cp /root/ai-calendar-assistant/app/routers/admin.py telegram-bot:/app/app/routers/
docker cp /root/ai-calendar-assistant/app/models telegram-bot:/app/app/

# 2. Перезапустите бот
docker restart telegram-bot
```

---

## 📝 Последние изменения (27.10.2025)

### Интерфейс бота
1. ✅ **Скрыт выбор языка** - все пользователи автоматически получают русский язык
2. ✅ **Скрыты нероссийские таймзоны** - оставлены только часовые пояса РФ (UTC+2 до UTC+12)
3. ✅ **Убрана кнопка "Язык"** из меню настроек

### WebApp
1. ✅ **Автоматическое определение темы** - WebApp теперь адаптируется под светлую/темную тему Telegram
2. ✅ **Улучшенные стили для светлой темы** - корректное отображение всех элементов
3. ✅ **Версия обновлена** до 2025-10-27-13:45

### Функциональность
1. ✅ **Batch Schedule Creation** - автоматическое создание расписаний из формата с временными диапазонами
2. ✅ **Year Clarification** - уточнение года для прошедших дат вместо автоматического выбора

---

## 🆘 Техническая поддержка

### Типичные проблемы

**Проблема:** Бот не отвечает
**Решение:**
```bash
ssh root@91.229.8.221 "docker logs telegram-bot | tail -50"
ssh root@91.229.8.221 "docker restart telegram-bot"
```

**Проблема:** WebApp не загружается
**Решение:**
```bash
ssh root@91.229.8.221 "cat /var/log/nginx/error.log | tail -20"
# Проверить, что файл index.html существует и доступен
ssh root@91.229.8.221 "ls -la /var/www/calendar/"
```

**Проблема:** События не создаются
**Решение:**
```bash
# Проверить Radicale
ssh root@91.229.8.221 "docker logs radicale | tail -50"
# Проверить права доступа
ssh root@91.229.8.221 "ls -la /var/lib/calendar-bot/radicale/"
```

---

## 📚 Документация

**Расположение:** `/Users/fatbookpro/ai-calendar-assistant/`

**Ключевые документы:**
- `README.md` - Общее описание проекта
- `BATCH_SCHEDULE_FEATURE.md` - Документация по пакетному созданию расписаний
- `YEAR_CLARIFICATION_GUIDE.md` - Руководство по уточнению года
- `SCHEDULE_FORMAT_IMPROVEMENTS.md` - Технические детали улучшений
- `SECURITY_IMPROVEMENTS_APPLIED.md` - Применённые улучшения безопасности
- `SETUP_COMPLETE.md` - Инструкции по первичной настройке

---

**ВАЖНО:** Этот документ содержит конфиденциальную информацию. Храните его в безопасном месте!

**Контакты:** Для вопросов обращайтесь к владельцу проекта.
