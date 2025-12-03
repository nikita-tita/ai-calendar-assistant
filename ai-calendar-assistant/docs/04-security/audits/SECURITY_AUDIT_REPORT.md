# 🔒 Отчет по аудиту безопасности AI Calendar Assistant

**Дата аудита:** 28 октября 2025
**Аудитор:** Claude (Anthropic)
**Версия системы:** Production на этонесамыйдлинныйдомен.рф

---

## 📊 Сводка

| Категория | Статус | Критичность |
|-----------|--------|-------------|
| Хранение учетных данных | ⚠️ КРИТИЧНО | 🔴 Высокая |
| Шифрование данных | ⚠️ НУЖНЫ УЛУЧШЕНИЯ | 🟡 Средняя |
| Аутентификация | ✅ ХОРОШО | 🟢 Низкая |
| Сетевая безопасность | ⚠️ НУЖНЫ УЛУЧШЕНИЯ | 🟡 Средняя |
| Резервное копирование | ❌ ОТСУТСТВУЕТ | 🔴 Высокая |
| Логирование | ✅ ХОРОШО | 🟢 Низкая |

---

## 🔴 КРИТИЧЕСКИЕ УЯЗВИМОСТИ

### 1. ⚠️ ПАРОЛИ В ОТКРЫТОМ ВИДЕ В КОДЕ

**Файл:** `app/routers/admin.py` строки 22-31

```python
# ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА
PASSWORD_1 = "Admin_Primary_2025_Secure!"
PASSWORD_2 = "Secondary_Admin_Key_2025"
PASSWORD_3 = "Tertiary_Access_Code_2025"
```

**Риски:**
- Пароли хранятся в открытом виде в исходном коде
- Доступны в git истории
- Видны всем, кто имеет доступ к репозиторию
- Невозможно изменить без редеплоя
- Компрометация репозитория = компрометация админ-панели

**Решение:** Переместить в переменные окружения (уже есть `admin_auth.py`, но `admin.py` использует хардкод)

---

### 2. ⚠️ ОТСУТСТВИЕ РЕЗЕРВНОГО КОПИРОВАНИЯ

**Проблема:**
- Календарные данные пользователей хранятся в Docker volume `radicale_data`
- JSON файлы (preferences, analytics) в `/var/lib/calendar-bot/` внутри контейнера
- При удалении контейнера или сбое сервера - данные теряются БЕЗВОЗВРАТНО

**Файлы без backup:**
```
/var/lib/calendar-bot/user_preferences.json     # Языки, часовые пояса пользователей
/var/lib/calendar-bot/analytics_data.json       # Статистика использования
/var/lib/calendar-bot/daily_reminder_users.json # Настройки напоминаний
/var/lib/calendar-bot/event_reminder_users.json # Настройки напоминаний о событиях
```

**Риски:**
- Потеря всех событий пользователей
- Потеря настроек и предпочтений
- Невозможность восстановления после сбоя

---

## 🟡 СРЕДНЯЯ КРИТИЧНОСТЬ

### 3. ⚠️ СЕРВИСЫ ДОСТУПНЫ ПУБЛИЧНО

**Проблема:** Radicale CalDAV сервер доступен извне на порту 5232

```bash
# На сервере:
tcp  0.0.0.0:5232  0.0.0.0:*  LISTEN  (docker-proxy)
tcp  0.0.0.0:8000  0.0.0.0:*  LISTEN  (docker-proxy)
```

**Риски:**
- Radicale может быть атакован напрямую
- Брутфорс аутентификации
- DDoS на CalDAV endpoint

**Примечание:** Порт 8000 (FastAPI) должен быть доступен, но Radicale должен быть только внутри Docker сети.

---

### 4. ⚠️ ОТСУТСТВИЕ ШИФРОВАНИЯ ДАННЫХ В ПОКОЕ

**Проблема:**
- Календарные события хранятся в plaintext в Radicale
- JSON файлы не зашифрованы
- База данных SQLite (если используется) не зашифрована

**Текущее состояние:**
```
/data/collections/collection-root/.../*.ics  # Незашифрованные iCal файлы
/var/lib/calendar-bot/*.json                 # Незашифрованные JSON
```

**Риски:**
- При физическом доступе к серверу данные читаются
- При утечке backup'а - данные в открытом виде

---

### 5. ⚠️ SECRET_KEY ПО УМОЛЧАНИЮ

**Файл:** `app/config.py:52`

```python
secret_key: Optional[str] = "default-secret-key-change-in-production"
```

**Проблема:** Если в .env не задан SECRET_KEY, используется дефолтный.

**Риски:**
- Подписи сессий могут быть подделаны
- JWT токены могут быть созданы злоумышленником

---

### 6. ⚠️ .ENV ФАЙЛЫ В GIT (IGNORED, НО РИСК ЕСТЬ)

**Текущее состояние:**
```
.env        # ignored ✅
.env.backup # ignored ✅
```

**Риски:**
- Если случайно сделать `git add -f .env`
- История git может содержать старые версии
- Локальные копии у разработчиков

---

## 🟢 ЧТО РАБОТАЕТ ХОРОШО

### ✅ 1. Трехфакторная аутентификация админ-панели

Система требует 3 пароля для доступа к админке + fake mode при 2 правильных паролях.

### ✅ 2. PII Masking в логах

Файл `app/utils/pii_masking.py` корректно маскирует:
- User ID (хешируется)
- Email, телефоны
- Текстовые поля событий
- Персональные данные

### ✅ 3. Rate Limiting

```python
max_requests_per_user_per_day: int = 20
max_concurrent_requests: int = 100
```

### ✅ 4. CORS правильно настроен

```python
cors_origins: str = "https://yourdomain.ru,https://www.yourdomain.ru,https://webapp.telegram.org"
```

### ✅ 5. Webhook Secret для Telegram

```python
telegram_webhook_secret: Optional[str] = None  # ✅ Используется
```

### ✅ 6. HTTPS для веб-приложения

SSL сертификат Let's Encrypt настроен корректно.

---

## 📋 ПЛАН УЛУЧШЕНИЙ БЕЗОПАСНОСТИ

### 🔴 КРИТИЧНО (Сделать немедленно)

#### 1. Убрать пароли из кода

**Файл:** `app/routers/admin.py`

**Действия:**
1. Удалить хардкод паролей из `admin.py`
2. Использовать только переменные окружения
3. Интегрировать с существующим `admin_auth.py` который уже правильно работает

**Код для исправления:**

```python
# ❌ УДАЛИТЬ:
PASSWORD_1 = "Admin_Primary_2025_Secure!"
PASSWORD_2 = "Secondary_Admin_Key_2025"
PASSWORD_3 = "Tertiary_Access_Code_2025"

# ✅ ИСПОЛЬЗОВАТЬ:
from app.services.admin_auth import admin_auth_service
```

#### 2. Настроить автоматическое резервное копирование

**Создать скрипт backup:**

```bash
#!/bin/bash
# /root/backup-calendar.sh

BACKUP_DIR="/root/backups/calendar"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup Radicale data
docker run --rm \
  --volumes-from radicale \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/radicale_$DATE.tar.gz /data

# Backup bot data
docker cp telegram-bot:/var/lib/calendar-bot $BACKUP_DIR/bot_data_$DATE/

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete

# Encrypt and upload to cloud (опционально)
# gpg --encrypt --recipient your@email.com $BACKUP_DIR/radicale_$DATE.tar.gz
# rclone copy $BACKUP_DIR/radicale_$DATE.tar.gz.gpg remote:backups/
```

**Cron job:**
```cron
# Backup every day at 3 AM
0 3 * * * /root/backup-calendar.sh >> /var/log/calendar-backup.log 2>&1
```

#### 3. Закрыть Radicale от внешнего доступа

**Файл:** `docker-compose.yml`

```yaml
# ❌ УДАЛИТЬ публичный порт:
radicale:
  ports:
    - "5232:5232"  # ❌ Убрать эту строку

# ✅ Оставить только internal network:
radicale:
  expose:
    - "5232"  # ✅ Только внутри Docker сети
  networks:
    - internal
```

**Добавить сеть:**
```yaml
networks:
  internal:
    internal: true  # Запрет внешних подключений
```

---

### 🟡 ВАЖНО (Сделать в течение недели)

#### 4. Генерировать уникальный SECRET_KEY

**В .env добавить:**
```bash
# Сгенерировать:
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Добавить в .env:
SECRET_KEY=<сгенерированный_ключ>
```

#### 5. Настроить шифрование данных

**Опции:**
- **Для Radicale:** Использовать encrypted filesystem (LUKS)
- **Для JSON файлов:** Использовать `cryptography` библиотеку

**Пример шифрования JSON:**

```python
from cryptography.fernet import Fernet
import os
import json

class EncryptedStorage:
    def __init__(self):
        key_file = "/var/lib/calendar-bot/.encryption_key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.key = f.read()
        else:
            self.key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(self.key)
            os.chmod(key_file, 0o600)

        self.cipher = Fernet(self.key)

    def save_encrypted(self, data: dict, path: str):
        json_data = json.dumps(data).encode()
        encrypted = self.cipher.encrypt(json_data)
        with open(path, 'wb') as f:
            f.write(encrypted)

    def load_encrypted(self, path: str) -> dict:
        with open(path, 'rb') as f:
            encrypted = f.read()
        decrypted = self.cipher.decrypt(encrypted)
        return json.loads(decrypted.decode())
```

#### 6. Ротация логов

```bash
# /etc/logrotate.d/calendar-assistant
/var/log/calendar-assistant/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

#### 7. Мониторинг безопасности

**Установить fail2ban для защиты от брутфорса:**

```bash
apt install fail2ban

# /etc/fail2ban/jail.local
[nginx-auth]
enabled = true
filter = nginx-auth
logpath = /var/log/nginx/error.log
maxretry = 3
bantime = 3600
```

---

### 🟢 ЖЕЛАТЕЛЬНО (Сделать при возможности)

#### 8. Двухфакторная аутентификация для пользователей

Добавить TOTP для особо важных пользователей через Telegram Bot.

#### 9. Audit логирование

Логировать все административные действия:
- Вход в админ-панель
- Просмотр данных пользователей
- Изменение настроек

#### 10. Регулярные проверки безопасности

```bash
# Автоматический security audit
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image your-calendar-bot:latest
```

---

## 🔐 ЧЕКЛИСТ НЕМЕДЛЕННЫХ ДЕЙСТВИЙ

- [ ] 1. Убрать пароли из `admin.py`, использовать переменные окружения
- [ ] 2. Создать скрипт автоматического бэкапа
- [ ] 3. Настроить cron для ежедневного бэкапа
- [ ] 4. Закрыть порт 5232 Radicale от внешнего доступа
- [ ] 5. Сгенерировать уникальный SECRET_KEY
- [ ] 6. Проверить что .env не попал в git (`git log --all --full-history -- .env`)
- [ ] 7. Настроить шифрование JSON файлов
- [ ] 8. Настроить ротацию логов
- [ ] 9. Установить fail2ban
- [ ] 10. Протестировать восстановление из бэкапа

---

## 📞 ПЛАН ДЕЙСТВИЙ ПРИ ИНЦИДЕНТЕ

### Если данные утекли:
1. Немедленно сменить все пароли (админ, Telegram token, API keys)
2. Ротировать SECRET_KEY
3. Уведомить пользователей
4. Проанализировать логи для определения масштаба

### Если сервер скомпрометирован:
1. Отключить сервер от сети
2. Создать snapshot диска для forensics
3. Развернуть из последнего backup на новом сервере
4. Провести полный аудит безопасности

### Если потеряны данные:
1. Восстановить из последнего backup
2. Проинформировать пользователей о потере данных между backup и инцидентом
3. Улучшить частоту backup'ов

---

## 📈 РЕЙТИНГ БЕЗОПАСНОСТИ

### Текущий уровень: 6/10 ⚠️

**Оценка по категориям:**
- Аутентификация: 8/10 ✅
- Хранение данных: 4/10 ⚠️
- Сетевая безопасность: 5/10 ⚠️
- Резервное копирование: 0/10 ❌
- Логирование: 9/10 ✅
- Шифрование: 3/10 ⚠️

### Целевой уровень после улучшений: 9/10 ✅

---

## 🎯 ВЫВОДЫ

Система имеет хорошую базу безопасности (трехфакторная аутентификация, PII masking, rate limiting), но **критически необходимо**:

1. **СРОЧНО:** Убрать пароли из кода
2. **СРОЧНО:** Настроить backup
3. **ВАЖНО:** Закрыть Radicale от публичного доступа
4. **ВАЖНО:** Добавить шифрование данных

Без этих улучшений система уязвима к:
- Компрометации админ-панели
- Безвозвратной потере данных пользователей
- Атакам на внутренние сервисы
- Утечке данных при физическом доступе к серверу

**Рекомендуемое время на реализацию:** 2-3 дня работы.
