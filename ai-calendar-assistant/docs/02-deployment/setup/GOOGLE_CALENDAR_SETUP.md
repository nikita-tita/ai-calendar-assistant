# Google Calendar Integration Setup

Эта инструкция поможет настроить двустороннюю синхронизацию с Google Calendar.

## Возможности

✅ **Двусторонняя синхронизация:**
- События созданные в боте автоматически добавляются в Google Calendar
- События из Google Calendar импортируются в бота каждые 10 минут
- Изменения и удаления синхронизируются в обе стороны

✅ **Безопасность:**
- OAuth токены хранятся в зашифрованном виде (Fernet encryption)
- Используется SQLite база данных с ограниченными правами доступа
- Поддержка автоматического обновления access tokens

## Шаг 1: Получение Google OAuth Credentials

### 1.1. Создайте проект в Google Cloud Console

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Название: "AI Calendar Assistant" (или любое другое)

### 1.2. Включите Google Calendar API

1. В меню слева: **APIs & Services** → **Library**
2. Найдите "Google Calendar API"
3. Нажмите **Enable**

### 1.3. Настройте OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen**
2. Выберите **External** (если у вас нет Google Workspace)
3. Заполните форму:
   - **App name:** AI Calendar Assistant
   - **User support email:** ваш email
   - **Developer contact:** ваш email
4. На странице "Scopes" нажмите **Add or Remove Scopes:**
   - Найдите и добавьте:
     - `https://www.googleapis.com/auth/calendar.events`
     - `https://www.googleapis.com/auth/calendar.readonly`
5. На странице "Test users" добавьте email'ы пользователей, которые смогут подключаться
   - В режиме "Testing" можно добавить до 100 test users
   - Для публичного использования нужно пройти верификацию Google

### 1.4. Создайте OAuth Client ID

1. **APIs & Services** → **Credentials**
2. Нажмите **Create Credentials** → **OAuth client ID**
3. Выберите **Application type:** Web application
4. **Name:** AI Calendar Bot
5. **Authorized redirect URIs** добавьте:
   ```
   https://этонесамыйдлинныйдомен.рф/sync/oauth/google/callback
   ```
   (замените на ваш домен)

6. Нажмите **Create**
7. **ВАЖНО:** Сохраните **Client ID** и **Client Secret**

## Шаг 2: Настройка переменных окружения

Добавьте в `.env` файл:

```bash
# Google Calendar OAuth
GOOGLE_OAUTH_CLIENT_ID=ваш-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=ваш-client-secret
GOOGLE_OAUTH_REDIRECT_URI=https://этонесамыйдлинныйдомен.рф/sync/oauth/google/callback
```

## Шаг 3: Деплой обновлённого кода

```bash
# Загрузите новые файлы на сервер
./deploy-full-update.sh

# Или вручную:
scp -r app/models/calendar_sync.py root@server:/root/ai-calendar-assistant/app/models/
scp -r app/services/sync_*.py root@server:/root/ai-calendar-assistant/app/services/
scp -r app/services/google_calendar_service.py root@server:/root/ai-calendar-assistant/app/services/
scp -r app/routers/calendar_sync.py root@server:/root/ai-calendar-assistant/app/routers/
scp app/config.py root@server:/root/ai-calendar-assistant/app/
scp app/main.py root@server:/root/ai-calendar-assistant/app/

# Перезапустите контейнер
ssh root@server "docker restart telegram-bot"
```

## Шаг 4: Подключение пользователя

### Вариант А: Через WebApp (рекомендуется)

1. Откройте WebApp бота
2. Перейдите в раздел "Настройки" → "Подключенные календари"
3. Нажмите "Подключить Google Calendar"
4. Авторизуйтесь через Google
5. Разрешите доступ к календарю

### Вариант Б: Прямая ссылка

Отправьте пользователю ссылку:
```
https://этонесамыйдлинныйдомен.рф/sync/connect/google?user_id=TELEGRAM_USER_ID
```

Где `TELEGRAM_USER_ID` - это Telegram ID пользователя (числовой).

## Шаг 5: Проверка работы

### 5.1. Проверьте что синхронизация запустилась

```bash
# Посмотрите логи
ssh root@server "docker logs telegram-bot --tail 100 | grep sync"

# Должны увидеть:
# - calendar_sync_initialized
# - background_sync_task_started
# - google_calendar_connected (после подключения пользователя)
```

### 5.2. Проверьте базу данных

```bash
ssh root@server "docker exec telegram-bot ls -lh /var/lib/calendar-bot/"

# Должны увидеть:
# - sync.db (SQLite база)
# - sync_encryption.key (ключ шифрования)
```

### 5.3. Тестирование синхронизации

**Тест 1: Экспорт из бота в Google**
1. Создайте событие через бота: "Поставь встречу завтра в 15:00"
2. Проверьте что событие появилось в Google Calendar
3. Должно появиться в течение нескольких секунд

**Тест 2: Импорт из Google в бота**
1. Создайте событие в Google Calendar напрямую
2. Подождите до 10 минут (или вызовите ручную синхронизацию)
3. Откройте WebApp бота - событие должно отобразиться

**Тест 3: Ручная синхронизация**
```bash
# Через API
curl -X POST "https://этонесамыйдлинныйдомен.рф/sync/connections/1/sync"

# Где 1 - это ID подключения (можно узнать из логов или API)
```

## API Endpoints

### Получить подключения пользователя
```bash
GET /sync/connections/{user_id}

# Пример
curl "https://этонесамыйдлинныйдомен.рф/sync/connections/123456789"
```

### Запустить синхронизацию вручную
```bash
POST /sync/connections/{connection_id}/sync

# Пример
curl -X POST "https://этонесамыйдлинныйдомен.рф/sync/connections/1/sync"
```

### Отключить календарь
```bash
DELETE /sync/connections/{connection_id}

# Пример
curl -X DELETE "https://этонесамыйдлинныйдомен.рф/sync/connections/1"
```

### Включить/отключить синхронизацию
```bash
POST /sync/connections/{connection_id}/toggle?enabled=true

# Пример
curl -X POST "https://этонесамыйдлинныйдомен.рф/sync/connections/1/toggle?enabled=false"
```

## Troubleshooting

### Ошибка: "Calendar sync service not initialized"

**Причина:** Не установлены переменные окружения Google OAuth

**Решение:**
1. Проверьте что в `.env` есть все 3 переменные
2. Перезапустите контейнер: `docker restart telegram-bot`

### Ошибка: "Invalid or expired state"

**Причина:** OAuth state истёк (10 минут timeout)

**Решение:** Начните процесс подключения заново

### События не синхронизируются

**Проверьте:**
1. Логи: `docker logs telegram-bot --tail 100 | grep sync`
2. Connection в БД: `docker exec telegram-bot sqlite3 /var/lib/calendar-bot/sync.db "SELECT * FROM calendar_connections;"`
3. Что sync_enabled = 1
4. Что token не истёк (token_expires_at)

### Ошибка: "Token expired"

**Причина:** Access token истёк, а refresh token не работает

**Решение:**
1. Удалите подключение через API
2. Переподключите календарь заново

### Ошибка: "403 Forbidden" при доступе к Calendar API

**Причина:**
- Google Calendar API не включён в проекте
- OAuth scopes неправильные
- Приложение не прошло верификацию (для публичного использования)

**Решение:**
1. Проверьте что Calendar API включён в Google Cloud Console
2. Проверьте scopes в OAuth consent screen
3. Для тестирования добавьте пользователей в Test users

## Ограничения

**Google API Quotas:**
- **Запросы:** 1,000,000 в день (бесплатно)
- **Создание событий:** 100,000 в день
- **Чтение событий:** неограниченно (в рамках общей квоты)

Для большинства пользователей этого более чем достаточно.

**Синхронизация:**
- **Импорт:** каждые 10 минут (настраивается в `main.py`)
- **Экспорт:** мгновенно при создании события в боте
- **Incremental sync:** использует Google sync tokens для оптимизации

## Security Best Practices

1. **Никогда не коммитьте `.env` в git**
2. **Регулярно делайте бэкапы `sync.db` и `sync_encryption.key`**
3. **Ограничивайте доступ к файлам:**
   ```bash
   chmod 600 /var/lib/calendar-bot/sync_encryption.key
   chmod 644 /var/lib/calendar-bot/sync.db
   ```
4. **Используйте HTTPS для OAuth redirects** (обязательно!)
5. **Ротируйте OAuth secrets** раз в полгода

## Расширение функциональности

### Добавление других календарей

Архитектура поддерживает другие провайдеры:
- **Yandex Calendar** (CalDAV) - TODO
- **Apple iCloud** (CalDAV, app-specific password) - TODO
- **Microsoft Outlook** (Graph API) - TODO

Для добавления нового провайдера:
1. Создайте сервис по аналогии с `GoogleCalendarService`
2. Добавьте провайдера в `CalendarProvider` enum
3. Обновите `CalendarSyncService` для поддержки нового провайдера
4. Добавьте OAuth flow в `calendar_sync.py` router

### UI в WebApp

TODO: Добавить интерфейс подключения календарей прямо в WebApp (вместо прямых ссылок)

---

**Нужна помощь?** Создайте issue в репозитории или свяжитесь с разработчиком.
