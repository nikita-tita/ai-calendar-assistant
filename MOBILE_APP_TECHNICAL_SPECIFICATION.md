# 📱 AI Calendar Assistant Mobile Application
## Детальное техническое задание

**Версия документа:** 2.0  
**Дата создания:** 22 декабря 2025  
**Статус:** Detailed Specification  
**Конфиденциальность:** Internal  
**Автор:** AI Calendar Assistant Team

---

## 📑 Оглавление

1. [Общая информация](#1-общая-информация)
2. [Анализ существующей системы](#2-анализ-существующей-системы)
3. [Архитектура приложения](#3-архитектура-приложения)
4. [Технический стек](#4-технический-стек)
5. [Функциональные требования](#5-функциональные-требования)
6. [API спецификация](#6-api-спецификация)
7. [Модели данных](#7-модели-данных)
8. [Дизайн система](#8-дизайн-система)
9. [UX flows](#9-ux-flows)
10. [Безопасность](#10-безопасность)
11. [Performance](#11-performance)
12. [Оффлайн режим](#12-оффлайн-режим)
13. [Push уведомления](#13-push-уведомления)
14. [Локализация](#14-локализация)
15. [Аналитика](#15-аналитика)
16. [Тестирование](#16-тестирование)
17. [Deployment](#17-deployment)
18. [Мониторинг](#18-мониторинг)
19. [План разработки](#19-план-разработки)
20. [Риски и митигация](#20-риски-и-митигация)

---

# 1. Общая информация

## 1.1. Цель проекта

Создать нативное кросс-платформенное мобильное приложение для iOS и Android, которое:

1. **Расширяет возможности** существующего Telegram бота
2. **Предоставляет standalone решение** без привязки к Telegram
3. **Улучшает UX** за счет нативных компонентов и жестов
4. **Работает оффлайн** с автоматической синхронизацией
5. **Интегрируется** с системными календарями (iOS Calendar, Google Calendar)
6. **Монетизируется** через Premium подписку

## 1.2. Целевая аудитория

### Основная аудитория:
- **Возраст:** 25-45 лет
- **Профессии:** Менеджеры, риелторы, фрилансеры, предприниматели
- **Потребности:** Быстрое управление календарём, голосовой ввод, AI-ассистент
- **Tech-savvy:** Средний и высокий уровень

### Сегменты:
1. **Busy professionals** (60%) - нужна скорость и удобство
2. **Real estate agents** (20%) - много встреч и показов
3. **Freelancers** (15%) - гибкий график, проектное управление
4. **Small business owners** (5%) - управление командой и клиентами

## 1.3. Конкурентный анализ

| Приложение | Сильные стороны | Слабые стороны | Наше преимущество |
|------------|-----------------|----------------|-------------------|
| Google Calendar | Интеграция с экосистемой | Нет голосового AI, сложный UX | AI понимание естественного языка |
| Fantastical | Отличный natural language parsing | Дорого ($40/год), нет AI | Дешевле, лучше AI |
| Any.do | Простота, задачи | Слабый календарь | Полноценный календарь + AI |
| Notion Calendar | Красивый UI, интеграции | Медленный, требует аккаунт | Быстрый, оффлайн режим |
| Telegram Bot (наш) | AI, бесплатно, голос | Ограничения Telegram UI | Нативный UX, больше функций |

### Наше УТП (Unique Value Proposition):
> **"Умный календарь, который понимает вас с голоса и работает без интернета"**

**Ключевые отличия:**
- ✅ Yandex GPT - понимание русского языка на уровне носителя
- ✅ Голосовой ввод с AI обработкой
- ✅ Оффлайн режим (конкуренты требуют интернет)
- ✅ Доступная цена (99₽/мес vs 500₽+ у конкурентов)
- ✅ Синхронизация с Telegram ботом (уникально)

## 1.4. Бизнес-модель

### Freemium модель:

**Free tier (бесплатно):**
- До 100 событий в месяц
- Базовый AI парсинг
- Стандартные уведомления
- 1 календарь

**Premium ($1.99/мес или 99₽/мес):**
- ♾️ Безлимитные события
- 🚀 Приоритетная обработка AI
- 🎨 Кастомные темы
- 📊 Расширенная аналитика
- 👥 Совместные календари (до 5 человек)
- 📱 Синхронизация с Google Calendar / Outlook
- 🔔 Умные напоминания (ML-based)
- 📈 Insights (AI анализ продуктивности)

**Team tier ($9.99/мес за 10 пользователей):**
- Все из Premium
- Командные календари
- Админ панель
- API доступ
- Priority support

### Прогноз монетизации:

**Год 1:**
- 50,000 установок
- 5% конверсия в Premium (2,500 платящих)
- Выручка: 2,500 × $1.99 × 12 = $59,700 (~5.4 млн₽/год)

**Год 2:**
- 200,000 установок
- 7% конверсия (14,000 платящих)
- Выручка: $334,320 (~30 млн₽/год)

## 1.5. Success criteria

### KPI на 6 месяцев:

**Acquisition:**
- ✅ 50,000+ установок
- ✅ 25,000+ активных пользователей (MAU)
- ✅ CPI (Cost Per Install) < $1

**Engagement:**
- ✅ DAU/MAU > 30%
- ✅ Session length > 3 минуты
- ✅ Sessions per day > 2
- ✅ Retention D1 > 40%, D7 > 25%, D30 > 15%

**Monetization:**
- ✅ 5% конверсия Free → Premium
- ✅ LTV/CAC > 3
- ✅ Churn rate < 5%/месяц

**Quality:**
- ✅ App Store rating > 4.5 ⭐
- ✅ Google Play rating > 4.3 ⭐
- ✅ Crash-free rate > 99.5%
- ✅ ANR rate < 0.5%

**Performance:**
- ✅ Cold start < 2 секунд (p95)
- ✅ API response time < 500ms (p95)
- ✅ Frame rate > 55 fps
- ✅ Memory usage < 150MB

---

# 2. Анализ существующей системы

## 2.1. Текущая архитектура

### Backend Stack:

```
┌─────────────────────────────────────────────────┐
│           Production Environment                │
│         (REG.RU VPS - 91.229.8.221)            │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  Nginx (Reverse Proxy)                     │ │
│  │  - Port 80 → 443 redirect                  │ │
│  │  - SSL (Let's Encrypt)                     │ │
│  │  - Static files (WebApp)                   │ │
│  │  - Rate limiting (10 req/min per IP)       │ │
│  └───────────┬────────────────────────────────┘ │
│              │                                   │
│              ↓                                   │
│  ┌────────────────────────────────────────────┐ │
│  │  Docker: telegram-bot (FastAPI)            │ │
│  │  - Python 3.11                             │ │
│  │  - FastAPI 0.115+                          │ │
│  │  - Uvicorn ASGI server                     │ │
│  │  - Port 8000 (internal)                    │ │
│  │                                            │ │
│  │  Components:                               │ │
│  │  ├─ telegram_handler.py                    │ │
│  │  ├─ llm_agent_yandex.py (Yandex GPT)      │ │
│  │  ├─ calendar_radicale.py (CalDAV client)  │ │
│  │  ├─ stt_yandex.py (Speech-to-Text)        │ │
│  │  ├─ sms_service.py (SMS.ru)               │ │
│  │  ├─ analytics_service.py                  │ │
│  │  └─ admin_auth_service.py                 │ │
│  └───────────┬────────────────────────────────┘ │
│              │                                   │
│              ↓                                   │
│  ┌────────────────────────────────────────────┐ │
│  │  Docker: radicale (CalDAV server)          │ │
│  │  - Port 5232 (internal)                    │ │
│  │  - PostgreSQL backend                      │ │
│  │  - Multi-user support                      │ │
│  │  - htpasswd auth                           │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
└──────────────────────────────────────────────────┘
```

### Существующие API Endpoints:

**Telegram Bot API (не используем напрямую):**
```
/webhook              POST    # Telegram webhook (polling mode сейчас)
```

**Public API (используем в mobile app):**
```
GET    /health                            # Health check
GET    /api/events                        # Список событий
POST   /api/events                        # Создание события
GET    /api/events/{event_id}            # Детали события
PUT    /api/events/{event_id}            # Обновление события
DELETE /api/events/{event_id}            # Удаление события
GET    /api/events/today                 # События на сегодня
GET    /api/events/week                  # События на неделю
POST   /api/todos                         # Создание задачи
GET    /api/todos                         # Список задач
PUT    /api/todos/{todo_id}              # Обновление задачи
DELETE /api/todos/{todo_id}              # Удаление задачи
POST   /api/auth/sms/send                # Отправка SMS кода
POST   /api/auth/sms/verify              # Верификация кода
POST   /api/ai/parse                     # AI парсинг текста
```

**Admin API (не используем):**
```
POST   /api/admin/v2/login               # Админ логин
GET    /api/admin/v2/users               # Список пользователей
GET    /api/admin/v2/analytics           # Аналитика
```

### Ограничения текущей системы:

**Rate Limiting:**
- 10 запросов/минуту на пользователя
- 50 запросов/час на пользователя
- 429 Too Many Requests при превышении

**Yandex GPT лимиты:**
- ~20 запросов/минуту
- Иногда блокирует "небезопасные" запросы (ложные срабатывания)
- Timeout 30 секунд

**CalDAV (Radicale):**
- Поддерживает до 1000 событий на пользователя (можно расширить)
- WebDAV протокол (медленнее REST API)
- Требует BasicAuth

## 2.2. Что нужно изменить/добавить на Backend

### Новые API endpoints:

```typescript
// Push notifications
POST   /api/users/push-token              // Регистрация push токена
DELETE /api/users/push-token              // Удаление токена
GET    /api/notifications/settings        // Настройки уведомлений
PUT    /api/notifications/settings        // Обновление настроек

// Sync (для оффлайн режима)
POST   /api/sync                          // Batch синхронизация
GET    /api/sync/status                   // Статус синхронизации

// User profile
GET    /api/users/me                      // Профиль пользователя
PUT    /api/users/me                      // Обновление профиля
GET    /api/users/me/stats                // Статистика пользователя

// Export/Import
GET    /api/export/ical                   // Экспорт в iCal
POST   /api/import/ical                   // Импорт из iCal
GET    /api/export/google-calendar        // Интеграция с Google Calendar

// Premium features
POST   /api/subscription/checkout         // Создание подписки
GET    /api/subscription/status           // Статус подписки
POST   /api/subscription/cancel           // Отмена подписки

// Analytics (client-side events)
POST   /api/analytics/event               // Отправка события
```

### Изменения в существующих API:

**GET /api/events - добавить пагинацию:**
```typescript
GET /api/events?page=1&limit=50&start_date=...&end_date=...
Response: {
  events: Event[],
  total: number,
  page: number,
  pages: number
}
```

**POST /api/sync - новый endpoint для batch операций:**
```typescript
POST /api/sync
Body: {
  last_sync: "2025-12-22T10:00:00Z",
  client_version: "1.0.0",
  platform: "ios",
  changes: {
    events: {
      created: [{ id: "local-1", title: "...", ... }],
      updated: [{ id: "uuid", title: "...", ... }],
      deleted: ["uuid1", "uuid2"]
    },
    todos: {
      created: [...],
      updated: [...],
      deleted: [...]
    }
  }
}

Response: {
  sync_timestamp: "2025-12-22T10:05:30Z",
  server_changes: {
    events: [{ id: "uuid", title: "...", updated_at: "..." }],
    todos: [...]
  },
  conflicts: [
    {
      type: "event",
      client_id: "local-1",
      server_id: "uuid",
      resolution: "server_wins" | "client_wins" | "manual"
    }
  ],
  success: true
}
```

### Database изменения:

**Новые таблицы:**

```sql
-- Push tokens
CREATE TABLE push_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) NOT NULL,
  token TEXT NOT NULL,
  platform VARCHAR(20) NOT NULL, -- 'ios' | 'android'
  created_at TIMESTAMP DEFAULT NOW(),
  last_used_at TIMESTAMP,
  UNIQUE(user_id, token)
);

-- Subscriptions
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) NOT NULL UNIQUE,
  tier VARCHAR(50) NOT NULL, -- 'free' | 'premium' | 'team'
  status VARCHAR(50) NOT NULL, -- 'active' | 'cancelled' | 'expired'
  started_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP,
  payment_provider VARCHAR(50), -- 'apple' | 'google' | 'stripe'
  external_id VARCHAR(255), -- Receipt/Transaction ID
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Sync log (для отладки конфликтов)
CREATE TABLE sync_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) NOT NULL,
  platform VARCHAR(20),
  client_version VARCHAR(20),
  sync_type VARCHAR(50), -- 'full' | 'incremental'
  events_created INTEGER DEFAULT 0,
  events_updated INTEGER DEFAULT 0,
  events_deleted INTEGER DEFAULT 0,
  conflicts_count INTEGER DEFAULT 0,
  duration_ms INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Analytics events (client-side)
CREATE TABLE analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255),
  event_type VARCHAR(100) NOT NULL,
  properties JSONB,
  platform VARCHAR(20),
  app_version VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_analytics_events_user ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_events_created ON analytics_events(created_at);
```

---

# 3. Архитектура приложения

## 3.1. High-level Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Mobile Application                   │
│                  (React Native + Expo)                  │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Presentation Layer                  │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Screens (Calendar, Tasks, Create, etc.)   │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Components (EventCard, TodoItem, etc.)    │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                               │
│                         ↓                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │               Business Logic Layer               │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Redux Store (State Management)            │ │  │
│  │  │  ├─ authSlice                              │ │  │
│  │  │  ├─ eventsSlice                            │ │  │
│  │  │  ├─ todosSlice                             │ │  │
│  │  │  └─ settingsSlice                          │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Services                                  │ │  │
│  │  │  ├─ syncService (оффлайн sync)             │ │  │
│  │  │  ├─ notificationService (push)             │ │  │
│  │  │  ├─ voiceService (STT)                     │ │  │
│  │  │  ├─ biometricService (Face ID)             │ │  │
│  │  │  └─ analyticsService                       │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                               │
│                         ↓                               │
│  ┌──────────────────────────────────────────────────┐  │
│  │               Data Layer                         │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  API Client (RTK Query)                    │ │  │
│  │  │  ├─ authApi                                │ │  │
│  │  │  ├─ eventsApi                              │ │  │
│  │  │  ├─ todosApi                               │ │  │
│  │  │  └─ syncApi                                │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │  Local Storage                             │ │  │
│  │  │  ├─ AsyncStorage (settings, tokens)        │ │  │
│  │  │  ├─ SecureStore (JWT, sensitive data)      │ │  │
│  │  │  └─ SQLite (events, todos, sync queue)     │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ↓ HTTPS
              ┌───────────────────────┐
              │   Backend API Server  │
              │  (FastAPI + CalDAV)   │
              └───────────────────────┘
```

## 3.2. State Management Architecture

### Redux Toolkit структура:

```typescript
// store/index.ts
import { configureStore } from '@reduxjs/toolkit';
import { persistStore, persistReducer } from 'redux-persist';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authApi } from './api/authApi';
import { eventsApi } from './api/eventsApi';
import { todosApi } from './api/todosApi';
import authSlice from './slices/authSlice';
import eventsSlice from './slices/eventsSlice';
import todosSlice from './slices/todosSlice';
import settingsSlice from './slices/settingsSlice';
import syncSlice from './slices/syncSlice';

const persistConfig = {
  key: 'root',
  storage: AsyncStorage,
  whitelist: ['auth', 'settings'], // Persist only these slices
  blacklist: ['events', 'todos'], // Don't persist (use SQLite instead)
};

export const store = configureStore({
  reducer: {
    auth: persistReducer(persistConfig, authSlice),
    events: eventsSlice,
    todos: todosSlice,
    settings: settingsSlice,
    sync: syncSlice,
    [authApi.reducerPath]: authApi.reducer,
    [eventsApi.reducerPath]: eventsApi.reducer,
    [todosApi.reducerPath]: todosApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(
      authApi.middleware,
      eventsApi.middleware,
      todosApi.middleware
    ),
});

export const persistor = persistStore(store);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

### State slices структура:

```typescript
// store/slices/eventsSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Event } from '@/types/models';

interface EventsState {
  items: Event[];
  selectedDate: string; // ISO date
  viewMode: 'day' | 'week' | 'month';
  filters: {
    search: string;
    tags: string[];
  };
  loading: boolean;
  error: string | null;
  lastSync: string | null; // ISO timestamp
}

const initialState: EventsState = {
  items: [],
  selectedDate: new Date().toISOString().split('T')[0],
  viewMode: 'day',
  filters: { search: '', tags: [] },
  loading: false,
  error: null,
  lastSync: null,
};

const eventsSlice = createSlice({
  name: 'events',
  initialState,
  reducers: {
    setEvents: (state, action: PayloadAction<Event[]>) => {
      state.items = action.payload;
      state.lastSync = new Date().toISOString();
    },
    addEvent: (state, action: PayloadAction<Event>) => {
      state.items.push(action.payload);
    },
    updateEvent: (state, action: PayloadAction<Event>) => {
      const index = state.items.findIndex(e => e.id === action.payload.id);
      if (index !== -1) {
        state.items[index] = action.payload;
      }
    },
    deleteEvent: (state, action: PayloadAction<string>) => {
      state.items = state.items.filter(e => e.id !== action.payload);
    },
    setSelectedDate: (state, action: PayloadAction<string>) => {
      state.selectedDate = action.payload;
    },
    setViewMode: (state, action: PayloadAction<'day' | 'week' | 'month'>) => {
      state.viewMode = action.payload;
    },
    setFilters: (state, action: PayloadAction<Partial<EventsState['filters']>>) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
  },
});

export const {
  setEvents,
  addEvent,
  updateEvent,
  deleteEvent,
  setSelectedDate,
  setViewMode,
  setFilters,
  setLoading,
  setError,
} = eventsSlice.actions;

export default eventsSlice.reducer;
```

## 3.3. Data Flow Architecture

### Создание события (с оффлайн поддержкой):

```
┌────────────────────────────────────────────────────────┐
│                   User Action                           │
│         (Нажимает "Создать событие")                    │
└───────────────────┬────────────────────────────────────┘
                    │
                    ↓
┌────────────────────────────────────────────────────────┐
│              CreateEventScreen                          │
│         (Форма заполнения события)                      │
└───────────────────┬────────────────────────────────────┘
                    │
                    ↓
┌────────────────────────────────────────────────────────┐
│         Dispatch: createEvent(eventData)                │
└───────────────────┬────────────────────────────────────┘
                    │
                    ↓
            ┌───────┴────────┐
            │  Online?       │
            └───────┬────────┘
                    │
        ┌───────────┼───────────┐
        │ YES                   │ NO
        ↓                       ↓
┌──────────────────┐   ┌────────────────────┐
│ API Call         │   │ Save to SQLite     │
│ POST /api/events │   │ with pending=true  │
└─────┬────────────┘   └──────┬─────────────┘
      │                       │
      │                       ↓
      │              ┌────────────────────┐
      │              │ Add to sync queue  │
      │              └──────┬─────────────┘
      │                     │
      │                     ↓
      │              ┌────────────────────┐
      │              │ Dispatch:          │
      │              │ addLocalEvent()    │
      │              └──────┬─────────────┘
      │                     │
      ↓                     ↓
┌─────────────────────────────────────────┐
│         Update Redux State               │
│    events.items.push(newEvent)          │
└───────────────┬─────────────────────────┘
                │
                ↓
┌─────────────────────────────────────────┐
│         Re-render UI                     │
│   (EventCard появляется в списке)       │
└─────────────────────────────────────────┘
                │
                ↓ (when online)
┌─────────────────────────────────────────┐
│       syncService.syncPendingChanges()  │
│  - Отправляет все pending события       │
│  - Обновляет local IDs на server IDs    │
│  - Удаляет из sync queue                │
└─────────────────────────────────────────┘
```

### Синхронизация (периодическая):

```
┌────────────────────────────────────────┐
│        App становится active           │
│         (foreground state)             │
└──────────────┬─────────────────────────┘
               │
               ↓
┌────────────────────────────────────────┐
│   syncService.startPeriodicSync()      │
│         (каждые 30 секунд)             │
└──────────────┬─────────────────────────┘
               │
               ↓
       ┌───────┴────────┐
       │  Online?       │
       └───────┬────────┘
               │ YES
               ↓
┌────────────────────────────────────────┐
│   POST /api/sync                       │
│   Body: {                              │
│     last_sync: "2025-12-22T10:00:00Z", │
│     changes: {                         │
│       events: { created: [...], ... }  │
│     }                                  │
│   }                                    │
└──────────────┬─────────────────────────┘
               │
               ↓
┌────────────────────────────────────────┐
│   Response: {                          │
│     server_changes: [...],             │
│     conflicts: [...]                   │
│   }                                    │
└──────────────┬─────────────────────────┘
               │
               ↓
┌────────────────────────────────────────┐
│   Resolve conflicts:                   │
│   - Server wins (default)              │
│   - Client wins (if explicitly set)    │
│   - Show UI for manual resolution      │
└──────────────┬─────────────────────────┘
               │
               ↓
┌────────────────────────────────────────┐
│   Update SQLite + Redux                │
│   - Merge server changes               │
│   - Update local IDs                   │
│   - Clear sync queue                   │
└──────────────┬─────────────────────────┘
               │
               ↓
┌────────────────────────────────────────┐
│   Dispatch: setSyncStatus('synced')    │
└────────────────────────────────────────┘
```

---

# 4. Технический стек

## 4.1. Frontend (Mobile App)

### Core Framework:

**React Native 0.73.2**
- Причина выбора: Кросс-платформенность, большое комьюнити, mature экосистема
- Альтернативы рассмотрены: Flutter (отклонено из-за Dart), Native (отклонено из-за двойной разработки)

**Expo SDK 50**
- Managed workflow для быстрой разработки
- EAS Build для CI/CD
- Over-the-air updates (для hotfixes без app store ревью)
- Expo Application Services (EAS)

**TypeScript 5.3**
- Строгая типизация для предотвращения ошибок
- tsconfig.json с strict mode

### UI Framework:

**React Native Paper 5.11**
- Material Design 3 components
- Поддержка тёмной темы из коробки
- Customizable theme
- Accessibility support

**React Native Reanimated 3.6**
- Performant animations (60 fps)
- Shared values для smooth transitions
- Layout animations

**React Native Gesture Handler 2.14**
- Native gestures (swipe, pan, etc.)
- Лучше производительность чем PanResponder

### Navigation:

**React Navigation 6.1**
- Stack Navigator (для модальных экранов)
- Bottom Tab Navigator (главная навигация)
- Material Top Tabs (для переключения дней/недели/месяца)
- Deep linking support

### State Management:

**Redux Toolkit 2.0**
- Modern Redux с меньшим boilerplate
- createSlice, createAsyncThunk
- Immer для иммутабельности

**RTK Query 2.0**
- Data fetching и caching
- Automatic re-fetching
- Optimistic updates
- Cache invalidation

**Redux Persist 6.0**
- Персистентность state в AsyncStorage
- Миграции при изменении структуры

### API Client:

**Axios 1.6**
- HTTP client с interceptors
- Automatic retry
- Request/response transformers
- Timeout handling

### Local Database:

**expo-sqlite / react-native-sqlite-storage**
- SQLite для оффлайн хранения событий/задач
- Indexes для быстрого поиска
- Migrations support

**Watermelon DB (альтернатива):**
- Reactive database
- Lazy loading
- Better performance для больших датасетов
- Рассмотрим если SQLite станет узким местом

### Storage:

**@react-native-async-storage/async-storage**
- Key-value хранилище для settings
- ~6MB limit (достаточно)

**expo-secure-store**
- Encrypted storage для JWT tokens
- iOS Keychain / Android Keystore

### Calendar UI:

**react-native-calendars 1.1304**
- Calendar component с кастомизацией
- Agenda view
- Multi-day selection
- Mark dates

**@react-native-community/datetimepicker 7.6**
- Native date/time picker
- iOS wheel picker
- Android material picker

### Voice & AI:

**@react-native-voice/voice 3.2**
- Speech-to-Text (нативный)
- Continuous recognition
- Partial results

**expo-av (альтернатива)**
- Audio recording
- Отправка на Yandex STT API

### Push Notifications:

**expo-notifications 0.27**
- Local notifications
- Remote push (FCM для Android, APNS для iOS)
- Notification permissions
- Badge management

**@notifee/react-native (альтернатива)**
- Advanced notifications
- Custom layouts
- Actions buttons

### Biometric:

**expo-local-authentication**
- Face ID (iOS)
- Touch ID (iOS)
- Fingerprint (Android)
- Fallback на device passcode

### Analytics:

**expo-firebase-analytics (если используем Firebase)**
- Event tracking
- User properties
- Automatic screen tracking

**@amplitude/analytics-react-native (альтернатива)**
- Better analytics than Firebase
- Funnel analysis
- Retention reports

### Error Tracking:

**@sentry/react-native 5.15**
- Crash reporting
- Error tracking
- Performance monitoring
- Release health
- Breadcrumbs

### Testing:

**Jest 29.7**
- Unit tests
- Snapshot tests
- Mock functions

**@testing-library/react-native 12.4**
- Component testing
- User-centric queries
- Fire events

**Detox 20.15 (E2E)**
- End-to-end testing
- iOS Simulator / Android Emulator
- Runs on CI/CD

### Code Quality:

**ESLint 8.56**
- @react-native-community/eslint-config
- Custom rules

**Prettier 3.1**
- Code formatting
- Pre-commit hook (husky)

**TypeScript ESLint**
- Type-aware linting

### Development Tools:

**React Native Debugger**
- Redux DevTools
- React DevTools
- Network inspector

**Flipper 0.212**
- Performance monitoring
- Network inspector
- Layout inspector
- Crash reporter

**Reactotron 3.1**
- State inspection
- API monitoring
- Async storage viewer

## 4.2. Backend (что нужно добавить)

### Новые зависимости:

**python-push-notifications**
- Для отправки push через APNS/FCM

**stripe / yookassa**
- Обработка платежей для Premium подписки

**celery + redis**
- Для фоновых задач (отправка напоминаний)

**APScheduler (уже есть)**
- Cron tasks для периодических уведомлений

## 4.3. Infrastructure

### CI/CD:

**EAS Build (Expo Application Services)**
- Managed builds для iOS и Android
- Build на облаке (не нужен Mac для iOS build)
- Автоматическая подпись сертификатов

**GitHub Actions / GitLab CI**
- Automated testing
- Linting
- Build на каждый PR
- Deploy на internal distribution (TestFlight / Internal Testing)

### App Distribution:

**TestFlight (iOS)**
- Beta testing
- Internal и external testers
- Crash reports

**Google Play Internal Testing (Android)**
- Internal track для QA
- Alpha/Beta tracks для phased rollout

### Monitoring:

**Sentry**
- Crash reporting
- Performance monitoring
- Release health dashboard

**Firebase Crashlytics (альтернатива)**
- Crash-free statistics
- Custom logs

### Analytics:

**Amplitude / Mixpanel**
- User behavior tracking
- Funnel analysis
- Retention cohorts

---

# 5. Функциональные требования

## 5.1. User Stories (детально)

### Epic 1: Авторизация

#### Story 1.1: SMS авторизация

**Как** новый пользователь  
**Я хочу** войти в приложение используя номер телефона  
**Чтобы** получить доступ к календарю

**Acceptance Criteria:**
- ✅ Ввод номера телефона с форматированием (+7 (XXX) XXX-XX-XX)
- ✅ Валидация номера (российские номера: +7, длина 11 цифр)
- ✅ Кнопка "Получить код" активна только для валидного номера
- ✅ После отправки - таймер 60 секунд для повторной отправки
- ✅ Поле ввода кода (4 цифры, автофокус на следующее поле)
- ✅ Авто-подстановка кода из SMS (iOS Auto-fill)
- ✅ Показать ошибку если код неверный (3 попытки)
- ✅ После 3 неудачных попыток - блокировка на 5 минут
- ✅ После успешной авторизации - сохранить JWT в SecureStore
- ✅ Переход на главный экран календаря

**Technical Details:**
```typescript
// API calls
POST /api/auth/sms/send
Body: { phone: "+79001234567" }
Response: { 
  success: true, 
  expires_at: "2025-12-22T10:01:00Z" 
}

POST /api/auth/sms/verify
Body: { 
  phone: "+79001234567", 
  code: "1234" 
}
Response: { 
  access_token: "eyJ...", 
  refresh_token: "eyJ...",
  user_id: "uuid",
  expires_in: 3600 
}
```

**Edge Cases:**
- Пользователь закрыл приложение во время ожидания кода → восстановить state
- Нет интернета при отправке кода → показать error, кнопка "Повторить"
- SMS не пришла → показать "Отправить повторно" через 60 секунд
- Пользователь ввел чужой номер → можно вернуться назад и изменить

**UI Flow:**
```
[Экран 1: Ввод номера]
┌──────────────────────────────┐
│   AI Calendar Assistant      │
│                              │
│   Введите номер телефона     │
│                              │
│   ┌────────────────────────┐ │
│   │ +7 (900) 123-45-67     │ │
│   └────────────────────────┘ │
│                              │
│   [  Получить код  ]         │
│                              │
│   Нажимая кнопку, вы         │
│   принимаете условия...      │
└──────────────────────────────┘
         │
         ↓ (после отправки SMS)
[Экран 2: Ввод кода]
┌──────────────────────────────┐
│   Введите код из SMS         │
│                              │
│   Отправлен на               │
│   +7 (900) 123-45-67         │
│   [изменить]                 │
│                              │
│   ┌───┐ ┌───┐ ┌───┐ ┌───┐  │
│   │ 1 │ │ 2 │ │ 3 │ │ 4 │  │
│   └───┘ └───┘ └───┘ └───┘  │
│                              │
│   Не пришел код?             │
│   Отправить повторно (0:45)  │
└──────────────────────────────┘
```

#### Story 1.2: Biometric авторизация (Face ID / Touch ID)

**Как** постоянный пользователь  
**Я хочу** входить в приложение по отпечатку пальца или Face ID  
**Чтобы** не вводить код каждый раз

**Acceptance Criteria:**
- ✅ После первой SMS авторизации - предложить включить Biometric
- ✅ Запрос разрешения на использование Face ID / Touch ID
- ✅ Показать диалог с объяснением зачем нужно
- ✅ Можно пропустить (кнопка "Пропустить")
- ✅ Если включено - при следующем запуске сразу Face ID prompt
- ✅ Fallback на SMS код если Face ID failed 3 раза
- ✅ В настройках можно включить/выключить Biometric

**Technical Details:**
```typescript
import * as LocalAuthentication from 'expo-local-authentication';

// Проверка поддержки
const hasHardware = await LocalAuthentication.hasHardwareAsync();
const isEnrolled = await LocalAuthentication.isEnrolledAsync();

// Аутентификация
const result = await LocalAuthentication.authenticateAsync({
  promptMessage: 'Войдите с помощью Face ID',
  fallbackLabel: 'Использовать код',
  cancelLabel: 'Отмена',
});

if (result.success) {
  // Успех - загрузить JWT из SecureStore и войти
} else {
  // Ошибка - показать SMS авторизацию
}
```

### Epic 2: Календарь

#### Story 2.1: Просмотр событий на день

**Как** пользователь  
**Я хочу** видеть все события на текущий день  
**Чтобы** знать свой план на день

**Acceptance Criteria:**
- ✅ По умолчанию открывается сегодняшний день
- ✅ Календарь сверху (месячный view) с выделением сегодня
- ✅ Список событий снизу, отсортированных по времени
- ✅ Каждое событие показывает: время, название, место (если есть)
- ✅ Цветовая кодировка событий (можно настроить)
- ✅ Индикатор "сейчас" (красная линия на timeline)
- ✅ Свайп влево/вправо для переключения дней
- ✅ Pull-to-refresh для синхронизации с сервером
- ✅ Пустое состояние если нет событий: "Нет событий. Добавить?"
- ✅ Кнопка FAB (+) справа внизу для быстрого создания

**Technical Details:**
```typescript
// API call
GET /api/events?start_date=2025-12-22&end_date=2025-12-22
Response: {
  events: [
    {
      id: "uuid",
      title: "Встреча с клиентом",
      start_time: "2025-12-22T14:00:00+03:00",
      end_time: "2025-12-22T15:30:00+03:00",
      location: "Офис, ул. Ленина 15",
      description: null,
      all_day: false,
      recurrence: null,
      created_at: "2025-12-20T10:00:00Z",
      updated_at: "2025-12-20T10:00:00Z"
    },
    // ...
  ]
}
```

**Performance:**
- ✅ Load time: < 500ms (cached), < 1s (network)
- ✅ Smooth scroll: 60 fps
- ✅ Virtualized list для больших списков (>50 событий)

**UI Components:**
```typescript
<CalendarScreen>
  <CalendarHeader>
    <MonthYearTitle>Декабрь 2025</MonthYearTitle>
    <TodayButton />
  </CalendarHeader>
  
  <CalendarGrid
    markedDates={{
      '2025-12-22': { selected: true, marked: true },
      '2025-12-23': { marked: true },
    }}
    onDayPress={(day) => setSelectedDate(day.dateString)}
  />
  
  <EventsList>
    <EventCard
      event={event}
      onPress={() => navigation.navigate('EventDetails', { id: event.id })}
      onLongPress={() => showContextMenu(event)}
    />
  </EventsList>
  
  <FAB
    icon="plus"
    onPress={() => navigation.navigate('CreateEvent')}
  />
</CalendarScreen>
```

#### Story 2.2: Создание события через форму

**Как** пользователь  
**Я хочу** создать событие заполнив форму  
**Чтобы** добавить встречу в календарь

**Acceptance Criteria:**
- ✅ Обязательные поля: Название, Дата, Время начала
- ✅ Опциональные: Время окончания, Место, Описание, Напоминание
- ✅ Date picker: календарь с прокруткой месяцев
- ✅ Time picker: iOS wheel / Android material
- ✅ По умолчанию: сегодня, ближайший час (округление вверх)
- ✅ Время окончания автоматически = начало + 1 час
- ✅ Валидация: окончание > начала
- ✅ Поле "Повторять": Не повторять / Ежедневно / Еженедельно / Ежемесячно
- ✅ Поле "Напомнить": Не напоминать / За 15 мин / За 30 мин / За 1 час / За 1 день
- ✅ Кнопка "Создать" активна только если заполнены обязательные поля
- ✅ После создания - возврат на календарь с автоскроллом к новому событию
- ✅ Optimistic update: событие сразу показывается (pending state)
- ✅ Если оффлайн - сохранить локально и синхронизировать при подключении

**Edge Cases:**
- Пользователь выбрал прошедшую дату → предупреждение "Событие в прошлом"
- Пользователь создает событие на уже занятое время → предупреждение "Конфликт"
- Нет интернета → сохранить локально, показать индикатор "Ожидает синхронизации"
- API вернул ошибку → показать ошибку, не удалять из формы, кнопка "Повторить"

**UI Flow:**
```
[Форма создания]
┌─────────────────────────────────┐
│ ← Новое событие                 │
├─────────────────────────────────┤
│ Название *                      │
│ [Встреча с клиентом_______]     │
│                                 │
│ 📅 Дата *                       │
│ [22 декабря 2025         ▼]     │
│                                 │
│ 🕐 Начало *                     │
│ [14:00                   ▼]     │
│                                 │
│ 🕐 Окончание                    │
│ [15:30                   ▼]     │
│                                 │
│ 📍 Место                        │
│ [Офис, ул. Ленина 15_____]     │
│                                 │
│ 📝 Описание                     │
│ [________________________]     │
│ [________________________]     │
│                                 │
│ 🔔 Напомнить                    │
│ [За 30 минут             ▼]     │
│                                 │
│ 🔄 Повторять                    │
│ [Не повторять            ▼]     │
│                                 │
│        [Создать событие]        │
└─────────────────────────────────┘
```

**Technical Implementation:**
```typescript
// CreateEventScreen.tsx
const CreateEventScreen = ({ navigation }) => {
  const dispatch = useDispatch();
  const [createEvent, { isLoading }] = useCreateEventMutation();
  const isOnline = useNetInfo().isConnected;
  
  const [formData, setFormData] = useState({
    title: '',
    date: new Date(),
    startTime: roundToNextHour(new Date()),
    endTime: addHours(roundToNextHour(new Date()), 1),
    location: '',
    description: '',
    reminder: '30min',
    recurrence: null,
  });

  const handleSubmit = async () => {
    // Validation
    if (!formData.title.trim()) {
      showError('Введите название события');
      return;
    }
    
    if (formData.endTime <= formData.startTime) {
      showError('Окончание должно быть позже начала');
      return;
    }

    const event = {
      title: formData.title,
      start_time: combineDateAndTime(formData.date, formData.startTime),
      end_time: combineDateAndTime(formData.date, formData.endTime),
      location: formData.location || null,
      description: formData.description || null,
      recurrence: formData.recurrence,
    };

    if (isOnline) {
      // Online - отправить на сервер
      try {
        const result = await createEvent(event).unwrap();
        dispatch(addEvent(result.event));
        
        // Schedule local notification
        if (formData.reminder) {
          scheduleNotification(result.event, formData.reminder);
        }
        
        navigation.goBack();
        showSuccess('Событие создано');
      } catch (error) {
        showError('Не удалось создать событие');
      }
    } else {
      // Offline - сохранить локально
      const localEvent = {
        ...event,
        id: `local-${uuid()}`,
        pending: true,
      };
      
      await saveEventToSQLite(localEvent);
      dispatch(addEvent(localEvent));
      
      // Add to sync queue
      await addToSyncQueue('create', 'event', localEvent);
      
      navigation.goBack();
      showInfo('Событие сохранено. Синхронизируется при подключении');
    }
  };

  return (
    <Screen>
      <TextInput
        label="Название *"
        value={formData.title}
        onChangeText={(text) => setFormData({ ...formData, title: text })}
        autoFocus
      />
      
      <DatePickerField
        label="Дата *"
        value={formData.date}
        onChange={(date) => setFormData({ ...formData, date })}
      />
      
      {/* ... остальные поля */}
      
      <Button
        mode="contained"
        onPress={handleSubmit}
        loading={isLoading}
        disabled={!formData.title.trim()}
      >
        Создать событие
      </Button>
    </Screen>
  );
};
```

#### Story 2.3: Создание события через AI (текст)

**Как** пользователь  
**Я хочу** создать событие написав текст естественным языком  
**Чтобы** не заполнять форму вручную

**Acceptance Criteria:**
- ✅ Большое текстовое поле с примерами
- ✅ Кнопка "Создать" отправляет текст на AI парсинг
- ✅ Показать loading indicator во время обработки
- ✅ AI возвращает structured data (title, date, time, location)
- ✅ Показать превью события перед созданием
- ✅ Пользователь может отредактировать перед созданием
- ✅ Кнопки: "Создать" / "Изменить" / "Отмена"
- ✅ Если AI не смог распарсить - предложить форму

**Примеры текста:**
- "Встреча с клиентом завтра в 14:00"
- "Обед послезавтра в 13 часов"
- "Каждый понедельник зал в 18:00"
- "25 декабря день рождения мамы"
- "Созвон с командой через 2 часа"

**Technical Details:**
```typescript
POST /api/ai/parse
Body: {
  text: "Встреча с клиентом завтра в 14:00 в офисе"
}
Response: {
  intent: "create",
  title: "Встреча с клиентом",
  start_time: "2025-12-23T14:00:00+03:00",
  end_time: "2025-12-23T15:00:00+03:00", // авто +1 час
  location: "офис",
  description: null,
  recurrence: null,
  confidence: 0.95
}
```

**Edge Cases:**
- AI confidence < 0.7 → показать "Не уверен, уточните детали"
- Нет даты в тексте → использовать "сегодня"
- Нет времени в тексте → создать как задачу (todo) вместо события
- Ambiguous время ("утром", "вечером") → использовать разумные defaults (утро=9:00, вечер=18:00)
- Yandex GPT заблокировал запрос → fallback на форму, показать "Используйте форму"

**UI Flow:**
```
[AI Создание]
┌─────────────────────────────────┐
│ ← Создать с помощью AI          │
├─────────────────────────────────┤
│                                 │
│ 💬 Опишите событие              │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Встреча с клиентом завтра   │ │
│ │ в 14:00 в офисе             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Создать]                       │
│                                 │
│ Примеры:                        │
│ • Обед завтра в 13:00           │
│ • Каждый понедельник зал в 18   │
│ • Встреча через 2 часа          │
└─────────────────────────────────┘
         │
         ↓ (после AI обработки)
[Превью события]
┌─────────────────────────────────┐
│ Проверьте событие               │
├─────────────────────────────────┤
│ 📝 Встреча с клиентом           │
│ 📅 23 декабря 2025              │
│ 🕐 14:00 - 15:00                │
│ 📍 Офис                         │
│                                 │
│ [Создать] [Изменить] [Отмена]   │
└─────────────────────────────────┘
```

(Продолжение следует... это только ~20% документа. Хочешь чтобы я продолжил писать ВСЁ детально?)
