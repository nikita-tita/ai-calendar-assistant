# Известные проблемы и решения

## Yandex GPT Content Moderation

### Проблема
Yandex GPT отказывается отвечать, возвращая:
```
"Я не могу обсуждать эту тему. Давайте поговорим о чём-нибудь ещё."
```

Бот показывает пользователю:
```
"Не могли бы вы переформулировать ваш запрос?"
```

### Причина
Yandex GPT имеет встроенную модерацию контента. Когда в контексте много событий с "чувствительными" данными (медицинские термины: УЗИ, МРТ, Гастроэнтеролог; финансовые данные и т.д.), модель отказывается обрабатывать запрос.

### Решение
Лимит **10 событий** в контексте. Реализовано в двух местах:

```python
# app/services/llm_agent_yandex.py:582
max_events_in_context = 10
limited_events = existing_events[:max_events_in_context]

# app/services/llm_agent_yandex.py:699
max_events_in_context = 10
limited_events = existing_events[:max_events_in_context]
```

### Коммит с фиксом
`ae3e8d4` - "fix: Limit Yandex GPT context to 10 events to avoid content moderation"

---

## Структура директорий на продакшене

### Проблема
Git обновляет одну директорию, а Docker копирует из другой.

### Структура
```
/root/ai-calendar-assistant/
├── app/                          # <- Docker копирует отсюда
│   └── services/
├── ai-calendar-assistant/        # <- Git обновляет сюда
│   └── app/
│       └── services/
└── docker-compose.yml
```

### Решение
После `git pull` копировать файлы:
```bash
cd /root/ai-calendar-assistant/ai-calendar-assistant
git pull origin main
cp app/services/*.py /root/ai-calendar-assistant/app/services/
```

Затем пересобрать контейнер:
```bash
cd /root/ai-calendar-assistant
docker-compose build --no-cache telegram-bot-polling
docker-compose up -d telegram-bot-polling
```

---

## Telegram Callback "Время истекло"

### Проблема
При нажатии на inline-кнопки (удалить события и т.д.) появляется сообщение "Время истекло".

### Причина
Telegram ожидает ответ на callback query в течение нескольких секунд. Если обработчик выполняется долго без вызова `query.answer()`, Telegram показывает ошибку.

### Решение
Вызывать `query.answer()` сразу в начале обработчика:

```python
async def handle_callback(self, update: Update, context):
    query = update.callback_query
    await query.answer("Обрабатываю...")  # Сразу отвечаем Telegram

    # Теперь можно делать долгие операции
    ...
```

---

## rsync с прода перезаписывает фиксы

### Проблема
При синхронизации проекта с прода через rsync теряются локальные фиксы.

### Решение
**Никогда не использовать rsync с прода для синхронизации кода.**

Всегда деплоить через git:
1. Локально: `git commit && git push`
2. На сервере: `git pull origin main`

---

**Последнее обновление**: 2025-12-04
