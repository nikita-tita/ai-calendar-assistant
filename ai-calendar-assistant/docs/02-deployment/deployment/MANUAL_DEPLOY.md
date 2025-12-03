# Ручная установка Yandex GPT интеграции

## Шаг 1: Подключись к серверу

```bash
ssh root@91.229.8.221
```

Пароль: `YOUR_SSH_PASSWORD`

---

## Шаг 2: Создай файл llm_agent_yandex.py

```bash
cd /root/ai-calendar-assistant/app/services
nano llm_agent_yandex.py
```

Скопируй всё содержимое из файла на Mac:

**Путь на Mac:** `/Users/fatbookpro/ai-calendar-assistant/app/services/llm_agent_yandex.py`

**Как скопировать:**

На Mac выполни:
```bash
cat /Users/fatbookpro/ai-calendar-assistant/app/services/llm_agent_yandex.py | pbcopy
```

Это скопирует файл в буфер обмена.

Затем в nano на сервере:
1. Вставь содержимое (Cmd+V или правая кнопка мыши)
2. Сохрани: Ctrl+O, Enter
3. Выйди: Ctrl+X

---

## Шаг 3: Обнови config.py

```bash
cd /root/ai-calendar-assistant/app
nano config.py
```

Найди секцию с OpenAI (строка ~40):

```python
    # OpenAI (for Whisper)
    openai_api_key: str

    # Database
```

Добавь между ними:

```python
    # Yandex GPT (for regions where Claude/OpenAI are blocked)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None
```

Должно получиться:

```python
    # OpenAI (for Whisper)
    openai_api_key: str

    # Yandex GPT (for regions where Claude/OpenAI are blocked)
    yandex_gpt_api_key: Optional[str] = None
    yandex_gpt_folder_id: Optional[str] = None

    # Database
```

Сохрани: Ctrl+O, Enter, Ctrl+X

---

## Шаг 4: Обнови telegram_handler.py

```bash
cd /root/ai-calendar-assistant/app/services
nano telegram_handler.py
```

Найди строку 9:

```python
from app.services.llm_agent_openai import llm_agent_openai as llm_agent
```

Замени на:

```python
from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent
```

Сохрани: Ctrl+O, Enter, Ctrl+X

---

## Шаг 5: Обнови requirements.txt

```bash
cd /root/ai-calendar-assistant
nano requirements.txt
```

Найди секцию `# HTTP Client`:

```
# HTTP Client
httpx>=0.25.0
aiohttp>=3.9.0
```

Добавь:

```
requests>=2.31.0
```

Должно получиться:

```
# HTTP Client
httpx>=0.25.0
aiohttp>=3.9.0
requests>=2.31.0
```

Сохрани: Ctrl+O, Enter, Ctrl+X

---

## Шаг 6: Обнови .env с ключами Yandex

```bash
cd /root/ai-calendar-assistant
nano .env
```

Добавь в конец файла (или найди и обнови):

```
# Yandex GPT (работает из России без VPN)
YANDEX_GPT_API_KEY=твой_ключ_сюда
YANDEX_GPT_FOLDER_ID=твой_folder_id_сюда
```

**ВАЖНО:** Сначала получи ключи на https://console.cloud.yandex.ru/ (см. YANDEX_GPT_SETUP.md)

Сохрани: Ctrl+O, Enter, Ctrl+X

---

## Шаг 7: Перезапусти бота

```bash
cd /root/ai-calendar-assistant

# Останови старые контейнеры
docker-compose -f docker-compose.production.yml down

# Пересобери образ с новым кодом
docker-compose -f docker-compose.production.yml up -d --build

# Подожди 5 секунд
sleep 5

# Проверь логи
docker logs telegram-bot --tail 50
```

---

## Шаг 8: Тестирование

Отправь боту в Telegram:

```
Встреча с Петровым завтра в 14:00
```

**Ожидаемый результат:**

```
✅ Событие создано!

📅 Встреча с Петровым
🕐 Завтра в 14:00
```

---

## Проверка ошибок

Если бот не отвечает, проверь логи:

```bash
docker logs telegram-bot --tail 100
```

### Возможные проблемы:

#### 1. "Module not found: llm_agent_yandex"

Проверь, что файл создан:
```bash
ls -la /root/ai-calendar-assistant/app/services/llm_agent_yandex.py
```

Если нет - повтори Шаг 2.

#### 2. "yandex_gpt_api_key not found"

Проверь .env:
```bash
cat /root/ai-calendar-assistant/.env | grep YANDEX
```

Должно вывести:
```
YANDEX_GPT_API_KEY=...
YANDEX_GPT_FOLDER_ID=...
```

Если пусто - повтори Шаг 6.

#### 3. "401 Unauthorized" от Yandex API

Неверный API ключ. Проверь:
- Ключ скопирован полностью (без пробелов)
- Service Account имеет роль `ai.languageModels.user`

#### 4. Бот все еще дает автоответы "Извините, я не совсем понял"

Значит либо:
- Не перезапущен контейнер (Шаг 7)
- Не установлены ключи Yandex (Шаг 6)
- Не обновлен telegram_handler.py (Шаг 4)

Выполни:
```bash
# Полная пересборка
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Логи
docker logs -f telegram-bot
```

---

## Полезные команды

```bash
# Статус контейнеров
docker ps

# Логи в реальном времени
docker logs -f telegram-bot

# Перезапуск бота без пересборки
docker-compose -f docker-compose.production.yml restart

# Полная остановка
docker-compose -f docker-compose.production.yml down

# Полный старт с пересборкой
docker-compose -f docker-compose.production.yml up -d --build
```

---

Удачи! 🚀
