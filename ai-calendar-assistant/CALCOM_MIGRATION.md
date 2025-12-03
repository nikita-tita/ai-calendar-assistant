# 🔄 Миграция на Cal.com

## Что изменилось

Проект обновлен с **Google Calendar** на **Cal.com** (open source платформа для планирования).

## 🎯 Преимущества Cal.com

### ✅ Почему Cal.com лучше

1. **Open Source** 🌟
   - Полностью открытый исходный код
   - Можно self-host на собственном сервере
   - GitHub: https://github.com/calcom/cal.com

2. **Простота интеграции** 🚀
   - Простой REST API
   - Не требует OAuth для каждого пользователя
   - Один API ключ для всего приложения

3. **Современный стек** 💎
   - Next.js + TypeScript
   - Prisma ORM
   - tRPC

4. **Бесплатный тариф** 💰
   - Unlimited bookings
   - API access
   - Все основные функции

## 📋 Что было изменено в коде

### 1. Конфигурация (app/config.py)
```python
# Было (Google Calendar):
google_client_id: str
google_client_secret: str
google_redirect_uri: str

# Стало (Cal.com):
calcom_api_key: str
calcom_api_url: str = "https://api.cal.com/v1"
calcom_username: str
```

### 2. Новый сервис (app/services/calendar_calcom.py)
Создан новый сервис вместо `calendar_google.py`:
- ✅ `create_event()` → `create_booking()`
- ✅ `list_events()` → `list_bookings()`
- ✅ `find_free_slots()` - поиск свободных слотов
- ✅ `cancel_booking()` - отмена бронирования

### 3. Роутеры (app/routers/)
```python
# Было:
app/routers/oauth.py (Google OAuth2)

# Стало:
app/routers/calcom.py (Cal.com API status & setup)
```

### 4. Environment Variables (.env)
```bash
# Удалено:
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=...

# Добавлено:
CALCOM_API_KEY=cal_live_...
CALCOM_API_URL=https://api.cal.com/v1
CALCOM_USERNAME=your_username
```

### 5. Dependencies (requirements.txt)
```txt
# Удалено:
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client

# Добавлено:
# httpx (уже был в проекте)
```

### 6. Telegram Handler (app/services/telegram_handler.py)
```python
# Было:
from app.services.calendar_google import calendar_service

# Стало:
from app.services.calendar_calcom import calendar_service

# Изменена логика /auth команды
# Cal.com не требует OAuth авторизации для каждого пользователя
```

## 🚀 Новые эндпоинты

### GET /calcom/status
Проверка статуса Cal.com API:
```bash
curl http://localhost:8000/calcom/status
```

Response:
```json
{
  "status": "configured",
  "message": "Cal.com API key is set",
  "api_url": "https://api.cal.com/v1",
  "username": "your_username"
}
```

### GET /calcom/setup
HTML страница с инструкциями по настройке:
```bash
open http://localhost:8000/calcom/setup
```

## 📝 Инструкция по настройке Cal.com

### Шаг 1: Создайте аккаунт
1. Перейдите на https://cal.com
2. Нажмите "Get Started"
3. Зарегистрируйтесь (GitHub/Google/Email)
4. Выберите username

### Шаг 2: Получите API Key
1. Войдите в Cal.com
2. Settings → Security → API Keys
3. "Create New API Key"
4. Скопируйте ключ (cal_live_...)

### Шаг 3: Настройте .env
```bash
CALCOM_API_KEY=cal_live_your_key_here
CALCOM_API_URL=https://api.cal.com/v1
CALCOM_USERNAME=your_username
```

### Шаг 4: Перезапустите приложение
```bash
uvicorn app.main:app --reload
```

## 🔗 API Endpoints Cal.com

### Основные эндпоинты:
- `POST /v1/bookings` - создать бронирование
- `GET /v1/bookings` - список бронирований
- `GET /v1/slots` - доступные слоты
- `DELETE /v1/bookings/{id}` - отменить бронирование
- `GET /v1/event-types` - типы событий

### Документация:
- https://cal.com/docs/api-reference
- https://cal.com/docs

## ⚠️ Breaking Changes

### Для пользователей:
- **Не требуется OAuth авторизация** каждого пользователя
- Команда `/auth` теперь просто проверяет статус API
- Больше не нужно переходить по ссылкам для авторизации

### Для разработчиков:
- Удалены зависимости Google API
- Изменен интерфейс calendar service
- OAuth router заменен на Cal.com router

## 🧪 Тестирование

### Проверка интеграции:
```bash
# 1. Статус API
curl http://localhost:8000/calcom/status

# 2. Health check
curl http://localhost:8000/health

# 3. Telegram команды
/start - приветствие
/auth - проверка API статуса
/status - статус Cal.com
```

### Создание события через Telegram:
```
"Запланируй встречу с командой завтра в 10:00"
"Какие у меня встречи на сегодня?"
"Какие свободные слоты завтра?"
```

## 📊 Сравнение Google Calendar vs Cal.com

| Функция | Google Calendar | Cal.com |
|---------|----------------|---------|
| Open Source | ❌ | ✅ |
| OAuth для каждого пользователя | ✅ Требуется | ❌ Не требуется |
| Self-hosting | ❌ | ✅ |
| API сложность | 🔴 Высокая | 🟢 Низкая |
| Стоимость | Бесплатно | Бесплатно |
| Интеграции | Много | Много |
| Современный стек | - | ✅ Next.js |

## 🔧 Self-hosting Cal.com (опционально)

Если хотите развернуть Cal.com на своем сервере:

```bash
# 1. Clone
git clone https://github.com/calcom/cal.com.git
cd cal.com

# 2. Setup
yarn install
yarn db-deploy

# 3. Configure
cp .env.example .env
# Настройте DATABASE_URL, NEXTAUTH_SECRET и т.д.

# 4. Run
yarn dev

# Теперь API доступен на http://localhost:3000/api/v1
```

Обновите `.env`:
```bash
CALCOM_API_URL=http://localhost:3000/api/v1
```

## 📚 Дополнительные ресурсы

- **Cal.com Docs**: https://cal.com/docs
- **API Reference**: https://cal.com/docs/api-reference
- **GitHub**: https://github.com/calcom/cal.com
- **Community**: https://cal.com/slack

## ✅ Checklist миграции

- [x] Обновлен `app/config.py`
- [x] Создан `app/services/calendar_calcom.py`
- [x] Создан `app/routers/calcom.py`
- [x] Обновлен `app/services/telegram_handler.py`
- [x] Обновлен `app/main.py`
- [x] Обновлен `requirements.txt`
- [x] Обновлен `.env` файл
- [x] Добавлен Anthropic API key
- [x] Создана документация миграции

## 🎉 Готово!

Проект успешно мигрирован на Cal.com!

**Преимущества:**
- ✅ Проще настройка
- ✅ Open source
- ✅ Меньше зависимостей
- ✅ Современный API

**Следующие шаги:**
1. Получите Cal.com API key
2. Настройте .env
3. Запустите и протестируйте

---

*Миграция выполнена с учетом ТЗ и лучших практик open source*
