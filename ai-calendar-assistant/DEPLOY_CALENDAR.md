# 🚀 Деплой Calendar Bot (БЕЗ Property Bot)

Это упрощенная конфигурация для запуска только календарного бота со списком дел.

## 📦 Что включено:

✅ **Telegram Bot** - основной бот с календарем
✅ **Radicale CalDAV** - сервер календаря (внутренний)
✅ **Список дел (Todos)** - хранится в JSON файлах

❌ **Property Bot** - АРХИВИРОВАН (не используется)
❌ **PostgreSQL** - не нужна без Property Bot

---

## 🔧 Быстрый старт на проде

### 1. Остановить текущую конфигурацию:

```bash
cd /root/ai-calendar-assistant/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down
```

### 2. Запустить новую конфигурацию (с Radicale):

```bash
docker-compose -f docker-compose.calendar.yml up -d
```

### 3. Проверить статус:

```bash
docker-compose -f docker-compose.calendar.yml ps
docker-compose -f docker-compose.calendar.yml logs -f --tail=50
```

### 4. Проверить работоспособность:

```bash
# Проверить календарь (Radicale)
docker exec -it radicale-calendar curl -f http://localhost:5232 || echo "❌ Radicale недоступен"

# Проверить бота
docker exec -it telegram-bot python -c "import sys; print('✅ Bot OK')"

# Проверить список дел
ls -la data/todos/ 2>/dev/null || echo "📝 Директория todos будет создана при первом использовании"
```

---

## 🔄 Обновление кода

```bash
cd /root/ai-calendar-assistant
git pull origin claude/add-todo-list-015UEaqQosVAebaUvUCn4PTF

cd ai-calendar-assistant
docker-compose -f docker-compose.calendar.yml build --no-cache
docker-compose -f docker-compose.calendar.yml up -d
```

---

## 📊 Мониторинг

### Логи:

```bash
# Все логи
docker-compose -f docker-compose.calendar.yml logs -f

# Только бот
docker logs -f telegram-bot

# Только Radicale
docker logs -f radicale-calendar
```

### Использование ресурсов:

```bash
docker stats --no-stream
```

---

## 🗂️ Структура данных

```
/root/ai-calendar-assistant/ai-calendar-assistant/
├── data/
│   ├── todos/           # JSON файлы списков дел (user_{id}.json)
│   ├── analytics.db     # SQLite база аналитики
│   └── preferences.json # Настройки пользователей
├── logs/                # Логи приложения
└── credentials/         # Учетные данные (если нужны)
```

---

## ⚠️ Важно

1. **Переменные окружения** - убедитесь что `.env` содержит:
   ```bash
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_WEBAPP_URL=https://your-domain.com
   RADICALE_URL=http://radicale:5232
   ```

2. **Данные сохраняются** в Docker volumes:
   - `radicale_data` - календари пользователей
   - `./data` - список дел, аналитика, настройки

3. **Backup** - регулярно бэкапьте директорию `data/`

---

## 🐛 Решение проблем

### Бот не отвечает:
```bash
docker logs telegram-bot --tail=100
```

### Календарь не работает:
```bash
docker logs radicale-calendar --tail=50
docker exec -it radicale-calendar curl http://localhost:5232
```

### Список дел не работает:
```bash
# Проверить права
ls -la data/todos/
chmod -R 755 data/todos/

# Проверить логи
docker logs telegram-bot | grep -i todo
```

---

## 📝 Что изменилось

**До:**
- ✅ Telegram Bot
- ❌ Radicale НЕ запущен → календарь не работал
- ✅ Property Bot (не нужен)
- ✅ PostgreSQL (не нужна)

**После:**
- ✅ Telegram Bot
- ✅ Radicale ЗАПУЩЕН → календарь работает
- ✅ Список дел (todos) - новая фича
- ❌ Property Bot УБРАН
- ❌ PostgreSQL УБРАНА

---

## 🎯 Проверка функционала

После деплоя проверьте в боте:

1. **Календарь:**
   - Отправьте: "Встреча завтра в 14:00"
   - Должно создаться событие

2. **Список дел:**
   - Нажмите кнопку "📝 Список дел"
   - Добавьте задачу
   - Отметьте чекбоксом

3. **Быстрые кнопки:**
   - "📋 Дела на сегодня"
   - "📅 Дела на завтра"

Все должно работать! ✅
