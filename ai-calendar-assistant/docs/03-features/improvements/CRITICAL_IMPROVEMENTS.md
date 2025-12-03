# Критические Доработки AI Calendar Assistant

**Дата:** 22 октября 2025
**Версия:** 2.0
**Статус:** Требуется реализация

---

## 🔴 КРИТИЧНЫЕ РИСКИ (Обязательно закрыть)

### 1. Безопасность Radicale CalDAV Server

**Проблема:**
- В `docker-compose.production.yml` нет Radicale сервиса
- По документации должен быть `AUTH_TYPE=none` - это публичные календари без защиты
- Любой может получить доступ к календарям пользователей

**Текущее состояние:**
```yaml
# Radicale сервис отсутствует в docker-compose.production.yml
```

**Риски:**
- Утечка персональных данных (события, встречи, контакты)
- Несанкционированное изменение/удаление событий
- GDPR/152-ФЗ нарушения

**Решение:**
1. Добавить аутентификацию в Radicale (Basic Auth минимум)
2. Изолировать Radicale в приватной сети (не торчать наружу)
3. Реализовать per-user доступ через reverse proxy
4. Использовать TLS для всех соединений

**Приоритет:** 🔴 КРИТИЧНЫЙ
**Сложность:** Средняя
**Время:** 4-6 часов

---

### 2. UID Генерация Событий (Коллизии)

**Проблема:**
```python
# app/services/calendar_radicale.py:138
uid = hashlib.md5(
    f"{user_id}_{event.title}_{event.start_time.isoformat()}_{time.time_ns()}".encode()
).hexdigest()
```

**Риски:**
- MD5 считается слабым алгоритмом
- Хотя коллизии маловероятны при добавлении `time.time_ns()`, но риск существует
- UID должен быть глобально уникальным

**Решение:**
```python
import uuid

uid = str(uuid.uuid4())  # Криптографически стойкий уникальный ID
```

**Приоритет:** 🟠 ВЫСОКИЙ
**Сложность:** Низкая
**Время:** 30 минут

---

### 3. CORS allow_origins=["*"]

**Проблема:**
```python
# app/main.py:27
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Любой домен может делать запросы
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Риски:**
- CSRF атаки
- Кража сессий через XSS на сторонних сайтах
- Утечка токенов админ-панели

**Решение:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.ru",
        "https://www.yourdomain.ru",
        "https://webapp.telegram.org"  # Для Telegram Web App
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**Приоритет:** 🔴 КРИТИЧНЫЙ
**Сложность:** Низкая
**Время:** 15 минут

---

### 4. Небезопасное Хранение Админ-Токенов

**Проблема:**
```python
# app/services/admin_auth.py:40
self._sessions: Dict[str, dict] = {}  # ❌ В памяти, теряются при рестарте
```

**Риски:**
- Сессии теряются при перезапуске контейнера
- Невозможно масштабировать (несколько инстансов)
- Нет централизованного управления сессиями
- Нет механизма logout на всех устройствах

**Текущие проблемы:**
1. Токены не защищены от подделки
2. Нет привязки к IP/User-Agent (можно украсть токен)
3. Нет ротации токенов
4. Используется простая генерация `secrets.token_urlsafe(32)` без подписи

**Решение:**
1. **JWT токены с подписью RS256:**
```python
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class AdminAuthService:
    def __init__(self):
        # Генерация RSA ключей или загрузка из .env
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def authenticate(self, primary: str, secondary: str, ip: str, user_agent: str):
        if self._verify_passwords(primary, secondary):
            payload = {
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=1),
                'ip': ip,
                'ua': hashlib.sha256(user_agent.encode()).hexdigest()
            }
            token = jwt.encode(payload, self.private_key, algorithm='RS256')
            return token
        return None

    def verify_session(self, token: str, ip: str, user_agent: str) -> bool:
        try:
            payload = jwt.decode(token, self.public_key, algorithms=['RS256'])
            # Проверка IP и User-Agent
            if payload['ip'] != ip:
                return False
            ua_hash = hashlib.sha256(user_agent.encode()).hexdigest()
            if payload['ua'] != ua_hash:
                return False
            return True
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False
```

2. **Или Redis для хранения сессий:**
```python
import redis
import secrets

class AdminAuthService:
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379, db=0)

    def authenticate(self, primary: str, secondary: str):
        if self._verify_passwords(primary, secondary):
            token = secrets.token_urlsafe(32)
            # Сохранить в Redis с TTL 1 час
            self.redis.setex(f"admin_session:{token}", 3600, "valid")
            return token
        return None

    def verify_session(self, token: str) -> bool:
        return self.redis.exists(f"admin_session:{token}")

    def logout(self, token: str):
        self.redis.delete(f"admin_session:{token}")
```

**Приоритет:** 🔴 КРИТИЧНЫЙ
**Сложность:** Средняя
**Время:** 3-4 часа

---

### 5. Персональные Данные в Логах

**Проблема:**
```python
# Логи содержат:
logger.info("event_created", user_id=user_id, title=event.title)  # ❌ Название события
logger.info("audio_transcribed", text=transcribed_text)  # ❌ Текст сообщения
```

**В analytics_data.json:**
```json
{
  "username": "nikita_tita",  // ❌ Персональные данные
  "first_name": "Nikita",     // ❌ Персональные данные
  "details": "Встреча с клиентом"  // ❌ Детали событий
}
```

**Риски:**
- Нарушение GDPR (штраф до 20M EUR или 4% от оборота)
- Нарушение 152-ФЗ РФ (штраф до 500k RUB)
- Отсутствие механизма удаления данных по запросу пользователя

**Решение:**

1. **PII Redaction в логах:**
```python
def mask_pii(text: str) -> str:
    """Маскировка персональных данных."""
    if len(text) <= 3:
        return "***"
    return text[:3] + "*" * (len(text) - 3)

logger.info("event_created",
    user_id=hashlib.sha256(user_id.encode()).hexdigest()[:8],  # Хеш вместо ID
    title_masked=mask_pii(event.title)  # Первые 3 символа
)
```

2. **Срок хранения логов - 30 дней:**
```bash
# /etc/logrotate.d/ai-calendar
/opt/ai-calendar-assistant/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
}
```

3. **Команда удаления данных пользователя:**
```python
@bot.command("delete_my_data")
async def delete_user_data(user_id: str):
    # Удалить события из календаря
    await calendar_service.delete_user_calendar(user_id)

    # Удалить из analytics
    analytics_service.delete_user_data(user_id)

    # Удалить preferences
    user_preferences.delete_user(user_id)

    # Уведомить пользователя
    await bot.send_message(chat_id, "Все ваши данные удалены.")
```

**Приоритет:** 🔴 КРИТИЧНЫЙ (Юридический риск)
**Сложность:** Средняя
**Время:** 4-6 часов

---

### 6. JSON File Storage под нагрузкой

**Проблема:**
```python
# app/services/analytics_service.py
def _save_data(self):
    with open(self.data_file, 'w') as f:
        json.dump({"actions": [a.dict() for a in self.actions]}, f)
```

**Риски при 1000+ DAU:**
- Race conditions (2 процесса пишут одновременно)
- Блокировка I/O при больших файлах (100k+ записей)
- Потеря данных при крашах во время записи
- Невозможность атомарных транзакций

**Решение:**

1. **File locking для JSON (временное):**
```python
import fcntl

def _save_data(self):
    with open(self.data_file, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Эксклюзивная блокировка
        json.dump({"actions": [a.dict() for a in self.actions]}, f)
        fcntl.flock(f, fcntl.LOCK_UN)
```

2. **Переход на SQLite с WAL (быстрый):**
```python
import sqlite3

class AnalyticsService:
    def __init__(self):
        self.db = sqlite3.connect('/var/lib/calendar-bot/analytics.db')
        self.db.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
        self._create_tables()

    def _create_tables(self):
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                success BOOLEAN DEFAULT 1,
                INDEX idx_user_id (user_id),
                INDEX idx_timestamp (timestamp)
            )
        ''')
```

3. **Миграция на PostgreSQL (долгосрочно):**
- При > 5000 пользователей
- При > 100k действий

**Приоритет:** 🟠 ВЫСОКИЙ
**Сложность:** Средняя (SQLite) / Высокая (PostgreSQL)
**Время:** 2-3 часа (SQLite) / 8-12 часов (PostgreSQL)

---

### 7. Timezone и DST Edge Cases

**Проблема:**
```python
# app/services/calendar_radicale.py:118
moscow_tz = pytz.timezone('Europe/Moscow')  # ❌ Хардкод
start_time_utc = moscow_tz.localize(start_time_utc)
```

**Текущие проблемы:**
1. Все naive datetime считаются Moscow timezone
2. Нет обработки DST переходов (хотя в РФ нет DST с 2014)
3. Продукт мультиязычный (en/es/ar), но logic привязана к MSK

**Риски:**
- Неправильное время для пользователей из других timezone
- Проблемы при переходах на летнее время в США/ЕС
- События в 2:30 AM в день перехода DST (несуществующее время)

**Решение:**

1. **Всегда хранить в UTC:**
```python
def normalize_datetime(dt: datetime, user_timezone: str) -> datetime:
    """Нормализация datetime в UTC."""
    if dt.tzinfo is None:
        # Получить timezone пользователя
        user_tz = pytz.timezone(user_timezone)
        dt = user_tz.localize(dt)
    # Конвертировать в UTC для хранения
    return dt.astimezone(pytz.UTC)
```

2. **Конвертировать в user timezone только при отображении:**
```python
def format_event_time(event: CalendarEvent, user_timezone: str) -> str:
    """Форматирование времени события для пользователя."""
    user_tz = pytz.timezone(user_timezone)
    local_time = event.start.astimezone(user_tz)
    return local_time.strftime('%d %B %Y, %H:%M')
```

3. **Тесты для DST:**
```python
def test_dst_transition():
    # США: 2025-03-09 02:00 → 03:00 (spring forward)
    us_tz = pytz.timezone('America/New_York')

    # Событие в 02:30 - несуществующее время
    naive_dt = datetime(2025, 3, 9, 2, 30)

    # pytz.localize с is_dst=None выбросит AmbiguousTimeError
    try:
        us_tz.localize(naive_dt)
    except pytz.exceptions.NonExistentTimeError:
        # Правильная обработка: перенести на 03:30
        adjusted_dt = us_tz.localize(naive_dt, is_dst=False)
```

**Приоритет:** 🟠 ВЫСОКИЙ
**Сложность:** Средняя
**Время:** 4-6 часов (+ тесты)

---

### 8. Event Reminders Idempotency

**Проблема:**
```python
# app/services/event_reminders.py
# Проверяет окно 28-32 минуты каждую минуту
# Но нет гарантии, что не отправит дважды при рестарте
```

**Риски:**
- Двойные/тройные уведомления при рестартах
- Потеря напоминаний если упали в момент отправки
- Нет персистентного журнала отправленных напоминаний

**Решение:**

1. **Персистентный журнал в БД:**
```python
import sqlite3

class EventRemindersService:
    def __init__(self):
        self.db = sqlite3.connect('/var/lib/calendar-bot/reminders.db')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS sent_reminders (
                event_uid TEXT NOT NULL,
                user_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (event_uid, user_id)
            )
        ''')

    async def send_reminder(self, event_uid: str, user_id: str, chat_id: int):
        # Проверить, не отправляли ли уже
        cursor = self.db.execute(
            'SELECT 1 FROM sent_reminders WHERE event_uid = ? AND user_id = ?',
            (event_uid, user_id)
        )
        if cursor.fetchone():
            logger.info("reminder_already_sent", event_uid=event_uid)
            return

        # Отправить напоминание
        await self.bot.send_message(chat_id, reminder_text)

        # Записать в журнал
        self.db.execute(
            'INSERT INTO sent_reminders (event_uid, user_id, chat_id) VALUES (?, ?, ?)',
            (event_uid, user_id, chat_id)
        )
        self.db.commit()
```

2. **Очистка старых записей (> 7 дней):**
```python
def cleanup_old_reminders(self):
    self.db.execute('''
        DELETE FROM sent_reminders
        WHERE sent_at < datetime('now', '-7 days')
    ''')
    self.db.commit()
```

**Приоритет:** 🟠 ВЫСОКИЙ
**Сложность:** Низкая
**Время:** 2-3 часа

---

### 9. Rate Limiting в Памяти

**Проблема:**
```python
# app/services/rate_limiter.py
class RateLimiterService:
    def __init__(self):
        self.user_limits: Dict[str, dict] = {}  # ❌ В памяти
```

**Риски:**
- Лимиты сбрасываются при рестарте
- Не работает при нескольких инстансах (load balancing)
- Пользователь может обойти блокировку рестартом контейнера

**Решение:**

1. **Redis для distributed rate limiting:**
```python
import redis
from datetime import datetime, timedelta

class RateLimiterService:
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379, db=1)

    def check_rate_limit(self, user_id: str) -> Tuple[bool, str]:
        now = int(datetime.now().timestamp())

        # Minute window (10 messages)
        minute_key = f"rate_limit:{user_id}:minute:{now // 60}"
        count = self.redis.incr(minute_key)
        if count == 1:
            self.redis.expire(minute_key, 60)

        if count > 10:
            return False, "Too many messages per minute"

        # Hour window (50 messages)
        hour_key = f"rate_limit:{user_id}:hour:{now // 3600}"
        hour_count = self.redis.incr(hour_key)
        if hour_count == 1:
            self.redis.expire(hour_key, 3600)

        if hour_count > 50:
            return False, "Too many messages per hour"

        return True, ""

    def block_user(self, user_id: str, duration_seconds: int):
        """Блокировка пользователя."""
        block_key = f"blocked:{user_id}"
        self.redis.setex(block_key, duration_seconds, "1")

    def is_blocked(self, user_id: str) -> bool:
        return self.redis.exists(f"blocked:{user_id}")
```

2. **Добавить Redis в docker-compose:**
```yaml
redis:
  image: redis:7-alpine
  container_name: calendar-redis
  restart: unless-stopped
  volumes:
    - redis-data:/data
  networks:
    - calendar-network
```

**Приоритет:** 🟠 ВЫСОКИЙ
**Сложность:** Средняя
**Время:** 3-4 часа

---

### 10. Секреты в .env файле

**Проблема:**
```bash
# .env
TELEGRAM_BOT_TOKEN=***REDACTED_BOT_TOKEN***
YANDEX_API_KEY=your_yandex_api_key
ADMIN_PRIMARY_PASSWORD=admin123
```

**Риски:**
- Секреты в plaintext в репозитории (если коммитнули .env)
- Секреты в логах Docker (`docker inspect`)
- Нет ротации секретов
- Все секреты в одном файле (компрометация одного = компрометация всех)

**Решение:**

1. **Docker Secrets (Swarm mode):**
```yaml
services:
  telegram-bot:
    secrets:
      - telegram_token
      - yandex_api_key
    environment:
      - TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_token

secrets:
  telegram_token:
    external: true
  yandex_api_key:
    external: true
```

2. **HashiCorp Vault (production):**
```python
import hvac

class SecretsManager:
    def __init__(self):
        self.client = hvac.Client(url='http://vault:8200')
        self.client.token = os.getenv('VAULT_TOKEN')

    def get_secret(self, path: str) -> str:
        secret = self.client.secrets.kv.v2.read_secret_version(path=path)
        return secret['data']['data']['value']

# Usage
telegram_token = secrets_manager.get_secret('calendar-bot/telegram_token')
```

3. **Railway/Cloud Secrets (managed):**
```bash
# Railway CLI
railway variables set TELEGRAM_BOT_TOKEN=xxx --secret
```

4. **Минимум: encrypted .env:**
```bash
# Использовать git-crypt или sops
sops -e .env > .env.encrypted
sops -d .env.encrypted > .env
```

**Приоритет:** 🔴 КРИТИЧНЫЙ
**Сложность:** Средняя (Secrets) / Высокая (Vault)
**Время:** 2-3 часа (Secrets) / 8+ часов (Vault)

---

## 🟡 ВАЖНЫЕ УЛУЧШЕНИЯ (Рекомендуется)

### 11. Webhook Secret Token Validation

**Проблема:**
```python
# app/routers/telegram.py
# Нет проверки X-Telegram-Bot-Api-Secret-Token в хедерах
```

**Решение:**
```python
from fastapi import Header, HTTPException

@router.post("/webhook")
async def telegram_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    expected_token = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if x_telegram_bot_api_secret_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid secret token")

    # Process update...
```

**Приоритет:** 🟡 СРЕДНИЙ
**Сложность:** Низкая
**Время:** 30 минут

---

### 12. Radicale Connection Pool

**Проблема:**
```python
# Каждый запрос создаёт новое соединение к Radicale
client = caldav.DAVClient(url=self.url, username=str(user_id))
```

**При 100+ RPS:**
- Исчерпание connection limits
- Медленные ответы из-за overhead connection setup

**Решение:**
```python
from urllib3.poolmanager import PoolManager
import requests

class RadicaleService:
    def __init__(self):
        self.session = requests.Session()
        self.session.mount('http://', requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=100,
            max_retries=3
        ))
```

**Приоритет:** 🟡 СРЕДНИЙ
**Сложность:** Средняя
**Время:** 2-3 часа

---

### 13. Structured Error Responses

**Проблема:**
```python
# Разные форматы ошибок в разных эндпоинтах
raise HTTPException(status_code=500, detail="Something went wrong")
```

**Решение:**
```python
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error_code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = datetime.now()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="Internal server error",
            details={"type": type(exc).__name__}
        ).dict()
    )
```

**Приоритет:** 🟡 СРЕДНИЙ
**Сложность:** Низкая
**Время:** 2-3 часа

---

### 14. Health Check Improvements

**Проблема:**
```yaml
# docker-compose.production.yml:24
healthcheck:
  test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]  # ❌ Не проверяет работоспособность
```

**Решение:**
```python
@app.get("/health")
async def health_check():
    checks = {
        "api": "ok",
        "radicale": calendar_service.is_connected(),
        "redis": rate_limiter.redis.ping(),
        "yandex_gpt": await llm_agent.health_check()
    }

    if not all(checks.values()):
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "checks": checks}
        )

    return {"status": "healthy", "checks": checks}
```

**Приоритет:** 🟡 СРЕДНИЙ
**Сложность:** Низкая
**Время:** 1-2 часа

---

## 📋 ROADMAP Реализации

### Фаза 1: Критическая безопасность (1-2 дня)
1. ✅ Заменить MD5 на UUID для event UID
2. ✅ Ограничить CORS origins
3. ✅ Добавить JWT для admin токенов
4. ✅ Настроить Radicale аутентификацию
5. ✅ Маскирование PII в логах

### Фаза 2: Стабильность и масштабирование (2-3 дня)
6. ✅ Миграция на SQLite для analytics
7. ✅ Идемпотентность event reminders
8. ✅ Redis для rate limiting
9. ✅ Webhook secret validation
10. ✅ Улучшенный health check

### Фаза 3: Production-ready (1 неделя)
11. ✅ Docker Secrets для токенов
12. ✅ Timezone тесты и edge cases
13. ✅ Radicale connection pool
14. ✅ Structured error responses
15. ✅ Monitoring и alerting

---

## 🚀 Следующие Шаги

1. **Немедленно:**
   - Ограничить CORS origins
   - Заменить MD5 на UUID
   - Добавить webhook secret validation

2. **На этой неделе:**
   - Настроить Radicale аутентификацию
   - Добавить JWT токены для админки
   - Миграция на SQLite

3. **В течение месяца:**
   - Redis для rate limiting
   - Полное покрытие тестами timezone
   - Vault для секретов

---

## 📊 Оценка Рисков

| Проблема | Риск | Вероятность | Воздействие | Приоритет |
|----------|------|-------------|-------------|-----------|
| CORS wildcard | Высокий | Высокая | Критичное | 🔴 |
| Admin tokens in-memory | Высокий | Средняя | Высокое | 🔴 |
| PII в логах | Критичный | Высокая | Катастрофическое | 🔴 |
| JSON race conditions | Средний | Высокая | Среднее | 🟠 |
| Rate limit in-memory | Средний | Средняя | Среднее | 🟠 |
| Radicale no auth | Критичный | Низкая | Катастрофическое | 🔴 |
| Webhook без validation | Высокий | Средняя | Высокое | 🟡 |

---

**Автор:** Claude Code Assistant
**Контакт:** development@ai-calendar-assistant.ru
**Последнее обновление:** 2025-10-22
