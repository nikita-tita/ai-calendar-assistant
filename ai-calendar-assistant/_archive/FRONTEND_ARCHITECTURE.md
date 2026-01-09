# 🎨 Frontend Architecture: Telegram Mini App

## Обзор

Ваше приложение - это **Single Page Application (SPA)** на чистом JavaScript, которое работает внутри Telegram как Mini App.

## 📋 Структура

```
index.html (705 строк)
├── HTML структура (строки 1-95)
├── CSS стили (строки 9-77)
└── JavaScript логика (строки 96-705)
    ├── Инициализация Telegram WebApp
    ├── Аутентификация
    ├── State management
    ├── API запросы
    ├── UI rendering
    └── Event handlers
```

---

## 🔄 Как это работает: Пошаговый Flow

### 1️⃣ **Загрузка и инициализация**

```javascript
// Строка 7: Подключение Telegram SDK
<script src="https://telegram.org/js/telegram-web-app.js"></script>

// Строка 102: Получение объекта Telegram WebApp
const tg = window.Telegram?.WebApp;

// Строка 114-115: Инициализация
tg.ready();   // Сообщает Telegram что приложение готово
tg.expand();  // Разворачивает на весь экран
```

**Что происходит:**
1. Telegram загружает ваш HTML
2. Браузер загружает `telegram-web-app.js`
3. SDK создаёт объект `window.Telegram.WebApp`
4. Приложение получает доступ к Telegram API

---

### 2️⃣ **Получение данных пользователя**

```javascript
// Строка 141: Получение ID пользователя
const userId = tg.initDataUnsafe?.user?.id;

// Строка 162: Получение данных для аутентификации
const initData = tg.initData;
```

**Откуда берутся данные:**
- `tg.initDataUnsafe` - объект с информацией о пользователе (НЕ безопасный)
  ```javascript
  {
    user: {
      id: 123456789,
      first_name: "Nikita",
      username: "nikita_tita",
      language_code: "ru"
    },
    auth_date: 1700000000,
    hash: "abc123..."
  }
  ```

- `tg.initData` - закодированная строка для проверки на бэкенде
  ```
  user={"id":123456789,...}&auth_date=1700000000&hash=abc123...
  ```

**Зачем два формата?**
- `initDataUnsafe` - для UI (показать имя, язык)
- `initData` - для безопасности (проверить HMAC на сервере)

---

### 3️⃣ **Аутентификация с бэкендом**

```javascript
// Каждый API запрос включает заголовок
headers: {
    'Content-Type': 'application/json',
    'X-Telegram-Init-Data': initData  // Telegram подпись
}
```

**Flow аутентификации:**

```
┌─────────────┐
│  Frontend   │
│  (Browser)  │
└─────┬───────┘
      │
      │ 1. GET /api/events/{userId}
      │    Header: X-Telegram-Init-Data: user=...&hash=abc123
      ▼
┌─────────────────┐
│   FastAPI       │
│   Backend       │
└─────┬───────────┘
      │
      │ 2. Middleware проверяет HMAC
      │    - Берёт BOT_TOKEN
      │    - Вычисляет hash
      │    - Сравнивает с полученным
      ▼
┌─────────────────┐
│ Если OK:        │
│ Возвращает      │
│ события         │
└─────────────────┘
```

---

### 4️⃣ **State Management**

```javascript
// Строка 191: Глобальное состояние приложения
const state = {
    events: [],           // Список событий
    todos: [],            // Список задач
    selectedDate: new Date(),  // Выбранная дата
    currentMonth: new Date(),  // Текущий месяц календаря
    showCalendar: false,  // Открыт ли календарь
    view: 'list',         // Текущий экран
    viewEvent: null,      // Просматриваемое событие
    edit: {},             // Редактируемое событие
    currentTab: 'events'  // Активная вкладка
};
```

**Как изменяется состояние:**

```javascript
// 1. Пользователь выбирает дату
function selectDate(date) {
    state.selectedDate = new Date(date);  // ← Изменение state
    state.showCalendar = false;
    render();  // ← Перерисовка UI
}

// 2. Загрузка событий с сервера
async function loadEvents() {
    const response = await fetch(`/api/events/${userId}`, {
        headers: { 'X-Telegram-Init-Data': initData }
    });
    state.events = await response.json();  // ← Обновление state
    render();  // ← Перерисовка
}
```

---

### 5️⃣ **Rendering (Отрисовка UI)**

```javascript
function render() {
    const container = document.getElementById('app');

    if (state.currentTab === 'events') {
        container.innerHTML = renderEventsList();
    } else {
        container.innerHTML = renderTodosList();
    }
}
```

**Пример генерации HTML:**

```javascript
function renderEventsList() {
    // Группировка событий по дням
    const eventsByDay = groupEventsByDay(state.events);

    // Генерация HTML
    return `
        <div class="px-4 pb-20">
            ${Object.entries(eventsByDay).map(([day, events]) => `
                <div class="day-separator">${formatDate(day)}</div>
                ${events.map(event => `
                    <div class="event-card" onclick="viewEvent('${event.id}')">
                        <div>${event.title}</div>
                        <div>${event.start_time}</div>
                    </div>
                `).join('')}
            `).join('')}
        </div>
    `;
}
```

**Как это работает:**
1. JavaScript генерирует HTML строку
2. Устанавливает её в `innerHTML`
3. Браузер парсит и отображает

---

### 6️⃣ **API взаимодействие**

#### Загрузка событий:
```javascript
async function loadEvents() {
    try {
        const daysAgo = 30;
        const daysAhead = 60;

        const start = new Date(state.selectedDate);
        start.setDate(start.getDate() - daysAgo);

        const end = new Date(state.selectedDate);
        end.setDate(end.getDate() + daysAhead);

        const url = `/api/events/${userId}?start=${start.toISOString()}&end=${end.toISOString()}`;

        const response = await fetch(url, {
            headers: {
                'X-Telegram-Init-Data': initData
            }
        });

        if (!response.ok) throw new Error('Failed to load events');

        state.events = await response.json();
        render();
    } catch (error) {
        console.error('Error loading events:', error);
        tg.showAlert('Ошибка загрузки событий');
    }
}
```

#### Создание события:
```javascript
async function saveEvent(eventData) {
    const url = `/api/events/${userId}`;

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': initData
        },
        body: JSON.stringify(eventData)
    });

    if (response.ok) {
        await loadEvents();  // Перезагрузка списка
        state.view = 'list';
        render();
    }
}
```

---

### 7️⃣ **Взаимодействие с Telegram**

#### Использование Telegram theme:
```javascript
// Строка 126: Применение темы
function applyTheme() {
    const colorScheme = tg.colorScheme || 'dark';

    if (colorScheme === 'light') {
        document.body.classList.add('light-theme');
    } else {
        document.body.classList.remove('light-theme');
    }
}

// Строка 136: Слушаем изменения темы
tg.onEvent('themeChanged', applyTheme);
```

#### Использование Telegram UI:
```javascript
// Показ уведомления
tg.showAlert('Событие создано!');

// Показ подтверждения
tg.showConfirm('Удалить событие?', (confirmed) => {
    if (confirmed) deleteEvent(eventId);
});

// Вибрация
tg.HapticFeedback.impactOccurred('medium');

// Закрытие приложения
tg.close();
```

---

## 🎯 Ключевые концепции

### Single Page Application (SPA)
- **Одна HTML страница** (`index.html`)
- **Динамическая отрисовка** через JavaScript
- **Нет перезагрузки** страницы при навигации
- **State-driven** - UI отражает состояние

### Reactive Rendering
```javascript
// Изменение состояния → Автоматическая перерисовка
state.selectedDate = newDate;  // Изменили
render();                       // Перерисовали
```

### Event-driven Architecture
```javascript
// Все действия через события
<button onclick="createEvent()">Создать</button>
<div onclick="selectDate('2025-11-25')">25</div>
```

---

## 📊 Диаграмма работы

```
┌─────────────────────────────────────────────────┐
│         TELEGRAM MINI APP LIFECYCLE             │
├─────────────────────────────────────────────────┤
│                                                  │
│  1. User clicks "📅 Календарь" in bot           │
│                    ↓                             │
│  2. Telegram opens: calendar.housler.ru         │
│                    ↓                             │
│  3. Browser loads index.html                    │
│                    ↓                             │
│  4. Telegram SDK injects:                       │
│     - window.Telegram.WebApp                    │
│     - initData (user info + HMAC)               │
│                    ↓                             │
│  5. App calls tg.ready() + tg.expand()          │
│                    ↓                             │
│  6. App extracts:                               │
│     - userId from tg.initDataUnsafe             │
│     - initData for authentication               │
│                    ↓                             │
│  7. App loads data:                             │
│     GET /api/events/{userId}                    │
│     Header: X-Telegram-Init-Data                │
│                    ↓                             │
│  8. Backend validates HMAC                      │
│                    ↓                             │
│  9. Backend returns events                      │
│                    ↓                             │
│ 10. App renders UI                              │
│                    ↓                             │
│ 11. User interacts                              │
│                    ↓                             │
│ 12. State changes → render()                    │
│                    ↓                             │
│ 13. Loop until user closes                      │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

## 🔐 Безопасность

### Проверка HMAC на бэкенде:
```python
# app/middleware.py
def validate_telegram_data(init_data: str, bot_token: str) -> bool:
    # 1. Парсим init_data
    data = parse_qs(init_data)

    # 2. Извлекаем hash
    received_hash = data.get('hash', [''])[0]

    # 3. Создаём проверочную строку
    data_check_string = '\n'.join(
        f"{k}={v[0]}" for k, v in sorted(data.items()) if k != 'hash'
    )

    # 4. Вычисляем секретный ключ
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()

    # 5. Вычисляем hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    # 6. Сравниваем
    return calculated_hash == received_hash
```

---

## 🎨 Стилизация

### Telegram Theme Variables:
```css
body {
    background: var(--tg-theme-bg-color, #0b0b0b);
    color: var(--tg-theme-text-color, #ffffff);
}

.button {
    background: var(--tg-theme-button-color, #2563eb);
    color: var(--tg-theme-button-text-color, #ffffff);
}
```

**Доступные переменные:**
- `--tg-theme-bg-color` - фон приложения
- `--tg-theme-text-color` - цвет текста
- `--tg-theme-hint-color` - цвет подсказок
- `--tg-theme-button-color` - цвет кнопок
- `--tg-theme-button-text-color` - цвет текста на кнопках
- `--tg-theme-secondary-bg-color` - вторичный фон

---

## 📱 Адаптивность

```css
/* Viewport meta */
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

/* Отключение выделения */
-webkit-tap-highlight-color: transparent;

/* Touch optimization */
overscroll-behavior: none;
touch-action: pan-y;
```

---

## 🚀 Оптимизация производительности

1. **Виртуальный скроллинг** - не используется (загружается всё сразу)
2. **Дебаунсинг** - нет (можно добавить для поиска)
3. **Кэширование** - через браузер (Cache-Control headers)

**Потенциальные улучшения:**
- Добавить виртуальный скроллинг для больших списков
- Кэшировать события в localStorage
- Добавить Service Worker для offline режима

---

## 📝 Итого

**Ваш Mini App это:**
- ✅ SPA на vanilla JavaScript (без фреймворков)
- ✅ Интеграция с Telegram WebApp SDK
- ✅ HMAC аутентификация
- ✅ RESTful API для данных
- ✅ Reactive rendering (state → UI)
- ✅ Адаптивный дизайн
- ✅ Поддержка тем Telegram

**Размер:** 705 строк в одном файле
**Зависимости:** Telegram SDK + Tailwind CSS (CDN)
**Браузеры:** Все современные (ES6+)
