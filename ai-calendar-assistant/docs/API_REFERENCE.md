# API Reference

> **Version:** 0.1.0
> **Base URL:** `https://calendar.housler.ru`
> **Last Updated:** 2026-01-11

API для AI Calendar Assistant - интеллектуального календарного ассистента с поддержкой естественного языка.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Codes](#error-codes)
5. [Endpoints](#endpoints)
   - [Root Endpoints](#root-endpoints)
   - [Events API](#events-api)
   - [Todos API](#todos-api)
   - [Admin API v1](#admin-api-v1)
   - [Admin API v2](#admin-api-v2)
   - [Telegram API](#telegram-api)
   - [Logs API](#logs-api)

---

## Overview

### Base URLs

| Environment | URL |
|------------|-----|
| Production | `https://calendar.housler.ru` |
| Direct API | `http://95.163.227.26:8000` |

### Response Format

Все ответы возвращаются в формате JSON:

```json
{
  "field1": "value1",
  "field2": "value2"
}
```

### Content-Type

- Request: `application/json`
- Response: `application/json`

### Allowed HTTP Methods

- `GET` - Получение данных
- `POST` - Создание ресурсов
- `PUT` - Обновление ресурсов
- `DELETE` - Удаление ресурсов
- `OPTIONS` - CORS preflight

---

## Authentication

API использует два типа аутентификации:

### 1. Telegram WebApp HMAC (для Events/Todos API)

Для доступа к `/api/events/*` и `/api/todos/*` требуется валидный Telegram WebApp initData.

**Header:**
```
X-Telegram-Init-Data: <telegram_init_data>
```

**Формат initData:**
```
query_id=xxx&user={"id":123,"username":"user"}&auth_date=1234567890&hash=xxx
```

**Процесс валидации:**
1. Парсинг initData как query string
2. Извлечение `hash` параметра
3. Сортировка оставшихся параметров по алфавиту
4. Создание data_check_string (параметры через `\n`)
5. Создание secret_key: `HMAC-SHA256("WebAppData", bot_token)`
6. Вычисление hash: `HMAC-SHA256(secret_key, data_check_string)`
7. Сравнение хэшей
8. Проверка `auth_date` (не старше 5 минут, не в будущем)

**Пример curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/events/123456" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: query_id=xxx&user=%7B%22id%22%3A123456%7D&auth_date=1234567890&hash=abc123"
```

### 2. Admin Authentication (для Admin API)

#### Admin API v1 (3-password system)

Требуется три пароля для входа:
- `password1` + `password2` + `password3` = "real" mode (полный доступ)
- `password1` + `password2` + wrong password3 = "fake" mode (пустые данные)
- Любая другая комбинация = "invalid"

После успешного логина возвращается JWT токен.

**Header:**
```
Authorization: Bearer <jwt_token>
```

#### Admin API v2 (Login + 2FA)

Использует login/password с опциональным TOTP 2FA. Токены хранятся в httpOnly cookies:
- `admin_access_token` - access token (1 час)
- `admin_refresh_token` - refresh token (7 дней)

---

## Rate Limiting

### Общие лимиты

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/admin/verify` | 5 requests | per minute |
| `/api/admin/broadcast` | 1 request | per minute |
| `/api/admin/v2/login` | 5 requests | per minute |
| `/api/admin/v2/broadcast` | 1 request | per minute |
| `/telegram/webhook` | 50 concurrent | - |

### Rate Limit Headers

При превышении лимита возвращается:
- Status: `429 Too Many Requests`
- Header: `Retry-After: <seconds>`

### Реализация

Rate limiting использует slowapi с Redis backend (или in-memory fallback):
```
storage_uri: redis://localhost:6379 или memory://
```

---

## Error Codes

### HTTP Status Codes

| Code | Description | Когда возникает |
|------|-------------|-----------------|
| `200` | OK | Успешный запрос |
| `400` | Bad Request | Невалидные параметры запроса |
| `401` | Unauthorized | Отсутствует или невалидная аутентификация |
| `403` | Forbidden | Нет прав на операцию (попытка доступа к чужим данным) |
| `404` | Not Found | Ресурс не найден |
| `422` | Validation Error | Ошибка валидации Pydantic |
| `429` | Too Many Requests | Превышен rate limit |
| `500` | Internal Server Error | Внутренняя ошибка сервера |
| `501` | Not Implemented | Endpoint требует дополнительных параметров |

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

Для validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Endpoints

### Root Endpoints

#### GET /

Корневой endpoint API.

**Response:**
```json
{
  "message": "AI Calendar Assistant API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

**curl:**
```bash
curl https://calendar.housler.ru/
```

---

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

**curl:**
```bash
curl https://calendar.housler.ru/health
```

---

#### GET /metrics

Prometheus metrics endpoint.

**Response:** `text/plain` - Prometheus metrics format

**curl:**
```bash
curl https://calendar.housler.ru/metrics
```

---

#### GET /app

Возвращает WebApp интерфейс (index.html).

**Headers:**
```
Cache-Control: no-cache, no-store, must-revalidate
```

---

#### GET /admin

Возвращает Admin Panel интерфейс (admin.html).

**Headers:**
```
Cache-Control: no-cache, no-store, must-revalidate
```

---

### Events API

**Base Path:** `/api`
**Authentication:** Telegram WebApp HMAC

#### GET /api/events/{user_id}

Получить все события пользователя за указанный период.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start` | datetime | No | Начало периода (ISO 8601). Default: now |
| `end` | datetime | No | Конец периода (ISO 8601). Default: now + 30 days |

**Response:**
```json
[
  {
    "id": "event-uuid-123",
    "title": "Meeting",
    "start": "2026-01-11T10:00:00",
    "end": "2026-01-11T11:00:00",
    "location": "Office",
    "description": "Weekly sync",
    "color": "blue"
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/events/123456?start=2026-01-01T00:00:00&end=2026-01-31T23:59:59" \
  -H "X-Telegram-Init-Data: <telegram_init_data>"
```

**Errors:**
- `401` - Missing or invalid Telegram authentication
- `403` - Cannot access other user's events
- `500` - Failed to fetch events

---

#### POST /api/events/{user_id}

Создать новое событие.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |

**Request Body:**
```json
{
  "title": "Meeting with team",
  "start": "2026-01-15T14:00:00",
  "end": "2026-01-15T15:00:00",
  "location": "Conference Room A",
  "description": "Quarterly review",
  "color": "blue"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Название события |
| `start` | datetime | Yes | Время начала (ISO 8601) |
| `end` | datetime | Yes | Время окончания (ISO 8601) |
| `location` | string | No | Место проведения |
| `description` | string | No | Описание |
| `color` | string | No | Цвет (default: "blue") |

**Validation:**
- `end` должен быть после `start`

**Response:**
```json
{
  "id": "generated-event-uid",
  "title": "Meeting with team",
  "start": "2026-01-15T14:00:00",
  "end": "2026-01-15T15:00:00",
  "location": "Conference Room A",
  "description": "Quarterly review",
  "color": "blue"
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/events/123456" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: <telegram_init_data>" \
  -d '{
    "title": "Meeting with team",
    "start": "2026-01-15T14:00:00",
    "end": "2026-01-15T15:00:00",
    "location": "Conference Room A"
  }'
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot create events for other users
- `422` - Validation error (end time must be after start time)
- `500` - Failed to create event

---

#### PUT /api/events/{user_id}/{event_id}

Обновить существующее событие.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |
| `event_id` | string | Yes | Event UID |

**Request Body:**
```json
{
  "title": "Updated title",
  "start": "2026-01-15T15:00:00",
  "end": "2026-01-15T16:00:00",
  "location": "New location",
  "description": "Updated description",
  "color": "red"
}
```

Все поля опциональны - передавайте только те, которые нужно обновить.

**Response:**
```json
{
  "id": "event-uid",
  "title": "Updated title",
  "start": "2026-01-15T15:00:00",
  "end": "2026-01-15T16:00:00",
  "location": "New location",
  "description": "Updated description",
  "color": "red"
}
```

**curl:**
```bash
curl -X PUT "https://calendar.housler.ru/api/events/123456/event-uid-123" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: <telegram_init_data>" \
  -d '{"title": "Updated meeting title"}'
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot update other user's events
- `404` - Event not found
- `422` - Validation error
- `500` - Failed to update event

---

#### DELETE /api/events/{user_id}/{event_id}

Удалить событие.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |
| `event_id` | string | Yes | Event UID |

**Response:**
```json
{
  "status": "deleted",
  "id": "event-uid"
}
```

**curl:**
```bash
curl -X DELETE "https://calendar.housler.ru/api/events/123456/event-uid-123" \
  -H "X-Telegram-Init-Data: <telegram_init_data>"
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot delete other user's events
- `404` - Event not found
- `500` - Failed to delete event

---

#### GET /api/health

Health check для Events API.

**Response:**
```json
{
  "status": "ok",
  "radicale_connected": true
}
```

**curl:**
```bash
curl https://calendar.housler.ru/api/health
```

---

### Todos API

**Base Path:** `/api`
**Authentication:** Telegram WebApp HMAC

#### GET /api/todos/{user_id}

Получить все задачи пользователя.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `completed` | boolean | No | Фильтр по статусу выполнения |
| `priority` | string | No | Фильтр по приоритету: "low", "medium", "high" |

**Response:**
```json
[
  {
    "id": "todo-uuid-123",
    "title": "Buy groceries",
    "completed": false,
    "priority": "medium",
    "due_date": "2026-01-15T18:00:00",
    "notes": "Don't forget milk",
    "created_at": "2026-01-10T10:00:00",
    "updated_at": "2026-01-10T10:00:00"
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/todos/123456?completed=false&priority=high" \
  -H "X-Telegram-Init-Data: <telegram_init_data>"
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot access other user's todos
- `500` - Failed to fetch todos

---

#### POST /api/todos/{user_id}

Создать новую задачу.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |

**Request Body:**
```json
{
  "title": "Complete project report",
  "completed": false,
  "priority": "high",
  "due_date": "2026-01-20T17:00:00",
  "notes": "Include Q4 metrics"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Название задачи |
| `completed` | boolean | No | Статус выполнения (default: false) |
| `priority` | string | No | Приоритет: "low", "medium", "high" (default: "medium") |
| `due_date` | datetime | No | Срок выполнения (ISO 8601) |
| `notes` | string | No | Дополнительные заметки |

**Response:**
```json
{
  "id": "generated-todo-uid",
  "title": "Complete project report",
  "completed": false,
  "priority": "high",
  "due_date": "2026-01-20T17:00:00",
  "notes": "Include Q4 metrics",
  "created_at": "2026-01-11T12:00:00",
  "updated_at": "2026-01-11T12:00:00"
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/todos/123456" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: <telegram_init_data>" \
  -d '{
    "title": "Complete project report",
    "priority": "high",
    "due_date": "2026-01-20T17:00:00"
  }'
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot create todos for other users
- `500` - Failed to create todo

---

#### PUT /api/todos/{user_id}/{todo_id}

Обновить существующую задачу.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |
| `todo_id` | string | Yes | Todo UID |

**Request Body:**
```json
{
  "title": "Updated title",
  "completed": true,
  "priority": "low",
  "due_date": "2026-01-25T17:00:00",
  "notes": "Updated notes"
}
```

Все поля опциональны.

**Response:**
```json
{
  "id": "todo-uid",
  "title": "Updated title",
  "completed": true,
  "priority": "low",
  "due_date": "2026-01-25T17:00:00",
  "notes": "Updated notes",
  "created_at": "2026-01-10T10:00:00",
  "updated_at": "2026-01-11T14:00:00"
}
```

**curl:**
```bash
curl -X PUT "https://calendar.housler.ru/api/todos/123456/todo-uid-123" \
  -H "Content-Type: application/json" \
  -H "X-Telegram-Init-Data: <telegram_init_data>" \
  -d '{"completed": true}'
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot update other user's todos
- `404` - Todo not found
- `500` - Failed to update todo

---

#### POST /api/todos/{user_id}/{todo_id}/toggle

Переключить статус выполнения задачи.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |
| `todo_id` | string | Yes | Todo UID |

**Response:**
```json
{
  "id": "todo-uid",
  "title": "Task title",
  "completed": true,
  "priority": "medium",
  "due_date": null,
  "notes": null,
  "created_at": "2026-01-10T10:00:00",
  "updated_at": "2026-01-11T14:00:00"
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/todos/123456/todo-uid-123/toggle" \
  -H "X-Telegram-Init-Data: <telegram_init_data>"
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot toggle other user's todos
- `404` - Todo not found
- `500` - Failed to toggle todo

---

#### DELETE /api/todos/{user_id}/{todo_id}

Удалить задачу.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |
| `todo_id` | string | Yes | Todo UID |

**Response:**
```json
{
  "status": "deleted",
  "id": "todo-uid"
}
```

**curl:**
```bash
curl -X DELETE "https://calendar.housler.ru/api/todos/123456/todo-uid-123" \
  -H "X-Telegram-Init-Data: <telegram_init_data>"
```

**Errors:**
- `401` - Unauthorized
- `403` - Cannot delete other user's todos
- `404` - Todo not found
- `500` - Failed to delete todo

---

### Admin API v1

**Base Path:** `/api/admin`
**Authentication:** JWT Bearer Token (3-password system)

#### POST /api/admin/verify

Аутентификация с тремя паролями.

**Request Body:**
```json
{
  "password1": "first_password",
  "password2": "second_password",
  "password3": "third_password"
}
```

**Response (success - all 3 correct):**
```json
{
  "valid": true,
  "mode": "real",
  "token": "jwt_token_here"
}
```

**Response (panic mode - pwd1&2 correct, pwd3 wrong):**
```json
{
  "valid": true,
  "mode": "fake",
  "token": "jwt_token_here"
}
```

**Response (failure):**
```json
{
  "valid": false,
  "error": "invalid_credentials"
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/verify" \
  -H "Content-Type: application/json" \
  -d '{"password1": "xxx", "password2": "yyy", "password3": "zzz"}'
```

**Rate Limit:** 5 requests per minute per IP

---

#### GET /api/admin/stats

Получить статистику дашборда.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "total_logins": 150,
  "active_users_today": 25,
  "active_users_week": 78,
  "active_users_month": 120,
  "total_users": 200,
  "total_actions": 5000,
  "total_events_created": 350,
  "total_messages": 2500
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/stats" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/users

Получить список всех пользователей.

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Response:**
```json
[
  {
    "user_id": "123456",
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe",
    "first_seen": "2026-01-01T10:00:00",
    "last_seen": "2026-01-11T14:00:00",
    "total_actions": 150,
    "is_hidden": false
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/users" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/users/{user_id}/dialog

Получить историю диалогов пользователя.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Telegram user ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 1000, max: 10000) |

**Response:**
```json
[
  {
    "timestamp": "2026-01-11T10:00:00",
    "role": "user",
    "content": "Create meeting tomorrow at 3pm"
  },
  {
    "timestamp": "2026-01-11T10:00:01",
    "role": "assistant",
    "content": "Created event 'Meeting' for tomorrow at 3:00 PM"
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/users/123456/dialog?limit=100" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/users/{user_id}/events

Получить события пользователя (90 дней назад и вперед).

**Response:**
```json
[
  {
    "id": "event-uid",
    "title": "Meeting",
    "start": "2026-01-15T14:00:00",
    "end": "2026-01-15T15:00:00",
    "location": "Office",
    "description": "Weekly sync"
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/users/123456/events" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/users/{user_id}/todos

Получить задачи пользователя.

**Response:**
```json
[
  {
    "id": "todo-uid",
    "title": "Buy groceries",
    "completed": false,
    "priority": "medium",
    "due_date": "2026-01-15T18:00:00",
    "created_at": "2026-01-10T10:00:00"
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/users/123456/todos" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### POST /api/admin/users/{user_id}/toggle-hidden

Переключить статус скрытия пользователя в дашборде.

**Response:**
```json
{
  "user_id": "123456",
  "is_hidden": true
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/users/123456/toggle-hidden" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/timeline

Получить таймлайн активности.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hours` | integer | No | Период в часах (default: 24, max: 168) |

**Response:**
```json
[
  {
    "timestamp": "2026-01-11T10:00:00",
    "value": 15
  },
  {
    "timestamp": "2026-01-11T11:00:00",
    "value": 22
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/timeline?hours=48" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/actions

Получить последние действия пользователей.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 100, max: 1000) |

**Response:**
```json
[
  {
    "user_id": "123456",
    "action_type": "event_create",
    "timestamp": "2026-01-11T14:00:00",
    "details": "Created event: Meeting",
    "success": true,
    "username": "john_doe",
    "first_name": "John",
    "last_name": "Doe",
    "is_test": false
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/actions?limit=50" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/errors

Получить ошибки за период.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hours` | integer | No | Период в часах (default: 24, max: 2160) |
| `limit` | integer | No | Максимум записей (default: 100, max: 500) |

**Response:**
```json
{
  "errors": [
    {
      "user_id": "123456",
      "action_type": "llm_error",
      "timestamp": "2026-01-11T14:00:00",
      "details": "API timeout",
      "error_message": "Connection timeout after 30s",
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe"
    }
  ],
  "stats": {
    "total": 5,
    "by_type": {
      "llm_error": 3,
      "calendar_error": 2
    },
    "period_hours": 24
  }
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/errors?hours=48&limit=100" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### GET /api/admin/report

Получить отчет по пользователям (lightweight).

**Response:**
```json
{
  "users": [
    {
      "user_id": "123456",
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "first_seen": "2026-01-01T10:00:00",
      "last_seen": "2026-01-11T14:00:00",
      "todos": null,
      "events": null,
      "todos_count": null,
      "events_count": null
    }
  ],
  "summary": {
    "total_users": 150
  }
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/report" \
  -H "Authorization: Bearer <jwt_token>"
```

---

#### POST /api/admin/broadcast

Отправить broadcast сообщение всем пользователям.

**Request Body:**
```json
{
  "message": "Important update!",
  "button_text": "Open App",
  "button_action": "start",
  "test_only": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | Текст сообщения (HTML) |
| `button_text` | string | No | Текст кнопки |
| `button_action` | string | No | "start" для добавления кнопки с callback |
| `test_only` | boolean | No | Отправить только тестовым пользователям |

**Response:**
```json
{
  "status": "completed",
  "sent": 145,
  "failed": 5,
  "total": 150,
  "failed_users": [
    {"user_id": "111", "error": "User blocked bot"}
  ]
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/broadcast" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '{"message": "New features available!", "test_only": true}'
```

**Rate Limit:** 1 request per minute per IP

---

#### GET /api/admin/health

Health check для Admin API.

**Response:**
```json
{
  "status": "ok"
}
```

**curl:**
```bash
curl https://calendar.housler.ru/api/admin/health
```

---

### Admin API v2

**Base Path:** `/api/admin/v2`
**Authentication:** httpOnly cookies (admin_access_token)

#### POST /api/admin/v2/login

Вход в админ панель.

**Request Body:**
```json
{
  "username": "admin",
  "password": "password123",
  "totp_code": "123456"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | Имя пользователя |
| `password` | string | Yes | Пароль |
| `totp_code` | string | No | 2FA код (если включен) |

**Response (success):**
```json
{
  "success": true,
  "mode": "real",
  "message": "Login successful",
  "totp_required": false
}
```

**Cookies set:**
- `admin_access_token` - httpOnly, secure, 1 hour
- `admin_refresh_token` - httpOnly, secure, 7 days

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/v2/login" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username": "admin", "password": "secret"}'
```

**Rate Limit:** 5 requests per minute per IP

---

#### POST /api/admin/v2/logout

Выход из системы.

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

Удаляет cookies `admin_access_token` и `admin_refresh_token`.

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/v2/logout" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/me

Получить информацию о текущем админе.

**Response:**
```json
{
  "user_id": "admin-uuid",
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "last_login_at": "2026-01-11T10:00:00",
  "last_login_ip": "1.2.3.4",
  "totp_enabled": true
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/me" \
  -b cookies.txt
```

---

#### POST /api/admin/v2/setup-2fa

Настроить двухфакторную аутентификацию.

**Response:**
```json
{
  "success": true,
  "qr_code": "data:image/png;base64,...",
  "manual_entry_key": "JBSWY3DPEHPK3PXP",
  "issuer": "AI Calendar Admin"
}
```

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/v2/setup-2fa" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/stats

Статистика дашборда (аналогично v1).

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/stats" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users

Список пользователей (аналогично v1).

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users/{user_id}/dialog

История диалогов пользователя.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 1000, max: 10000) |

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users/123456/dialog?limit=100" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users/{user_id}/events

События пользователя.

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users/123456/events" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users/{user_id}/todos

Задачи пользователя.

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users/123456/todos" \
  -b cookies.txt
```

---

#### POST /api/admin/v2/users/{user_id}/toggle-hidden

Переключить скрытие пользователя.

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/v2/users/123456/toggle-hidden" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/timeline

Таймлайн активности.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hours` | integer | No | Период в часах (default: 24, max: 168) |

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/timeline?hours=48" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/timeline/daily

Ежедневная статистика.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | No | Период в днях (default: 30, max: 90) |

**Response:**
```json
{
  "data": [
    {
      "date": "2026-01-11",
      "actions": 150,
      "users": 25,
      "events": 30,
      "messages": 100,
      "errors": 2
    }
  ],
  "period_days": 30
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/timeline/daily?days=30" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/actions

Последние действия пользователей.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 100, max: 1000) |

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/actions?limit=50" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/actions/summary

Сводка по типам действий.

**Response:**
```json
{
  "summary": [
    {
      "action_type": "event_create",
      "today": 15,
      "week": 78,
      "month": 250,
      "unique_users": 45,
      "trend": "up"
    }
  ],
  "totals": {
    "today": 150,
    "week": 890,
    "month": 3500
  }
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/actions/summary" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/actions/by-type/{action_type}

Пользователи с определенным типом действий.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `action_type` | string | Yes | Тип действия |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 50, max: 200) |

**Response:**
```json
{
  "users": [
    {
      "user_id": "123456",
      "username": "john_doe",
      "first_name": "John",
      "action_count": 25,
      "last_action": "2026-01-11T14:00:00"
    }
  ],
  "action_type": "event_create"
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/actions/by-type/event_create?limit=20" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/errors

Ошибки за период.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hours` | integer | No | Период в часах (default: 24, max: 168) |
| `limit` | integer | No | Максимум записей (default: 100, max: 500) |

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/errors?hours=48" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/llm/costs

Расходы на LLM.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | No | Период в днях (default: 30, max: 90) |

**Response:**
```json
{
  "daily_costs": [
    {"date": "2026-01-11", "cost_rub": 15.50, "tokens": 5000, "requests": 50}
  ],
  "by_model": {
    "yandexgpt": {"cost_rub": 100, "tokens": 50000, "requests": 500}
  },
  "by_user": [
    {"user_id": "123456", "username": "john", "cost_rub": 5.25, "tokens": 2500}
  ],
  "totals": {
    "cost_rub": 150.00,
    "tokens": 75000,
    "requests": 750,
    "unique_users": 45,
    "avg_cost_per_user": 3.33,
    "avg_cost_per_request": 0.20
  },
  "period_days": 30
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/llm/costs?days=30" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users/metrics

Метрики вовлеченности пользователей.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `days` | integer | No | Период в днях (default: 30, max: 90) |

**Response:**
```json
{
  "dau": [
    {"date": "2026-01-11", "count": 25}
  ],
  "mau": 120,
  "avg_dau": 22.5,
  "dau_mau_ratio": 0.188,
  "segments": {
    "power_users": 15,
    "regular_users": 45,
    "casual_users": 40,
    "dormant_users": 20
  },
  "retention": {
    "day_1": 0.65,
    "day_7": 0.45
  },
  "new_users": {
    "today": 3,
    "this_week": 12,
    "this_month": 35
  },
  "period_days": 30
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users/metrics?days=30" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/users/top

Топ активных пользователей.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Количество пользователей (default: 10, max: 50) |
| `days` | integer | No | Период в днях (default: 30, max: 90) |

**Response:**
```json
{
  "users": [
    {
      "user_id": "123456",
      "username": "john_doe",
      "first_name": "John",
      "total_actions": 250,
      "events": 45,
      "messages": 180,
      "llm_cost": 12.50,
      "last_seen": "2026-01-11T14:00:00"
    }
  ],
  "limit": 10,
  "period_days": 30
}
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/users/top?limit=10&days=30" \
  -b cookies.txt
```

---

#### GET /api/admin/v2/audit-logs

Аудит-логи админ действий.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 100, max: 500) |

**Response:**
```json
[
  {
    "id": "log-uuid",
    "admin_user_id": "admin-uuid",
    "username": "admin",
    "action_type": "login",
    "timestamp": "2026-01-11T10:00:00",
    "details": "Successful login",
    "ip_address": "1.2.3.4",
    "success": true
  }
]
```

**curl:**
```bash
curl -X GET "https://calendar.housler.ru/api/admin/v2/audit-logs?limit=50" \
  -b cookies.txt
```

---

#### POST /api/admin/v2/broadcast

Broadcast сообщение (аналогично v1).

**Rate Limit:** 1 request per minute per IP

**curl:**
```bash
curl -X POST "https://calendar.housler.ru/api/admin/v2/broadcast" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"message": "Important update!", "test_only": true}'
```

---

#### GET /api/admin/v2/health

Health check для Admin API v2.

**Response:**
```json
{
  "status": "ok",
  "version": "v2"
}
```

**curl:**
```bash
curl https://calendar.housler.ru/api/admin/v2/health
```

---

### Telegram API

**Base Path:** `/telegram`
**Authentication:** Webhook Secret Token

#### POST /telegram/webhook

Обработка входящих Telegram webhook.

**Headers:**
```
X-Telegram-Bot-Api-Secret-Token: <webhook_secret>
```

**Security:**
- В production `TELEGRAM_WEBHOOK_SECRET` обязателен
- Без секрета в production возвращается 500

**Request Body:** Telegram Update object

**Response:**
```json
{
  "status": "ok"
}
```

**Errors:**
- `401` - Invalid webhook secret
- `500` - Webhook not configured securely (production) / Internal error

---

#### GET /telegram/status

Статус Telegram бота.

**Response:**
```json
{
  "status": "ok",
  "bot_username": "calendar_assistant_bot",
  "bot_id": 123456789
}
```

**curl:**
```bash
curl https://calendar.housler.ru/telegram/status
```

---

### Logs API

**Base Path:** `/api/logs`
**Authentication:** None (development/testing)

#### GET /api/logs/user/{user_id}

Получить логи пользователя.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | Telegram user ID |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 50) |
| `log_type` | string | No | Фильтр по типу лога |

**Response:**
```json
{
  "user_id": 123456,
  "logs": [
    {
      "timestamp": "2026-01-11T10:00:00",
      "type": "message",
      "data": {"text": "Hello"}
    }
  ],
  "total": 25
}
```

**curl:**
```bash
curl "https://calendar.housler.ru/api/logs/user/123456?limit=20&log_type=message"
```

---

#### GET /api/logs/recent

Получить последние логи всех пользователей.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Максимум записей (default: 100) |

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-01-11T10:00:00",
      "type": "message",
      "data": {"text": "Hello"},
      "user_id": 123456
    }
  ],
  "total": 150
}
```

**curl:**
```bash
curl "https://calendar.housler.ru/api/logs/recent?limit=50"
```

---

#### DELETE /api/logs/user/{user_id}

Удалить логи пользователя.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | integer | Yes | Telegram user ID |

**Response:**
```json
{
  "user_id": 123456,
  "cleared": 50,
  "status": "success"
}
```

**curl:**
```bash
curl -X DELETE "https://calendar.housler.ru/api/logs/user/123456"
```

---

#### GET /api/logs/stats

Статистика логирования.

**Response:**
```json
{
  "total_users": 25,
  "total_logs": 1500,
  "type_counts": {
    "message": 1000,
    "callback": 300,
    "error": 200
  }
}
```

**curl:**
```bash
curl "https://calendar.housler.ru/api/logs/stats"
```

---

## CORS

API поддерживает CORS для следующих origins:
- Production: настраивается через `CORS_ORIGINS` env variable
- Development: `localhost:3000`, `localhost:8000`, `127.0.0.1:3000`, `127.0.0.1:8000`

**Allowed Headers:**
- `Content-Type`
- `Authorization`
- `X-Telegram-Init-Data`

---

## Security Headers

API добавляет security headers (SEC-005):
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security` (только production)

---

## Appendix

### Data Types

#### TodoPriority
```
"low" | "medium" | "high"
```

#### DateTime Format
```
ISO 8601: "2026-01-11T14:00:00"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret (required in production) |
| `ADMIN_PASSWORD_1` | First admin password |
| `ADMIN_PASSWORD_2` | Second admin password |
| `ADMIN_PASSWORD_3` | Third admin password |
| `JWT_SECRET` | JWT signing secret |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `REDIS_URL` | Redis URL for rate limiting |

---

**Generated:** 2026-01-11
**Author:** DEV-7 (QA/Tech Writer)
**Task:** DOC-001
