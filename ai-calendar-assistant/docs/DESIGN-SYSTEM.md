# Housler Design System

Строгие правила визуального оформления. Каждый компонент должен следовать этому документу.

---

## Принципы

1. **Только черный и белый.** Никаких цветных акцентов, если явно не согласовано.
2. **Никаких эмоджи.** Ни в коде, ни в интерфейсе, ни в комментариях.
3. **Минимализм.** Меньше элементов — лучше. Каждый пиксель должен быть обоснован.
4. **Консистентность.** Одинаковые задачи решаются одинаковыми компонентами.
5. **Переиспользование.** Не дублируй — используй готовое.

---

## 1. Токены

### 1.1 Цвета

```css
:root {
  /* Основа */
  --black: #000000;
  --white: #FFFFFF;

  /* Серая шкала (единственные допустимые оттенки) */
  --gray-900: #181A20;  /* Основной текст, primary кнопки */
  --gray-800: #333333;
  --gray-700: #4A4A4A;
  --gray-600: #6B7280;  /* Вторичный текст */
  --gray-500: #9CA3AF;
  --gray-400: #D1D5DB;
  --gray-300: #E5E7EB;  /* Границы, разделители */
  --gray-200: #F3F4F6;  /* Hover фон */
  --gray-100: #F9FAFB;  /* Фоны секций */

  /* Семантические алиасы — использовать ЭТИ, не сырые значения */
  --color-text: var(--gray-900);
  --color-text-secondary: var(--gray-600);
  --color-border: var(--gray-300);
  --color-bg: var(--white);
  --color-bg-secondary: var(--gray-100);
  --color-bg-hover: var(--gray-200);
  --color-accent: var(--black);
}
```

**Запрещено:**
- Любые цвета за пределами серой шкалы
- Использование `red-*`, `green-*`, `blue-*`, `purple-*`, `yellow-*`, `orange-*`
- Цветовое кодирование статусов (использовать текст и иконки)

### 1.2 Типографика

**Шрифт:** Inter (Google Fonts)

```tsx
// layout.tsx
import { Inter } from "next/font/google";

const inter = Inter({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600"],
});
```

**Веса:**
- `400` — обычный текст
- `500` — акценты, кнопки, навигация
- `600` — заголовки, цены

**Размеры:**

| Токен | Размер | Применение |
|-------|--------|------------|
| `text-xs` | 12px | Подписи, счетчики, метаданные |
| `text-sm` | 14px | Вторичный текст, кнопки sm |
| `text-base` | 16px | Основной текст, инпуты |
| `text-lg` | 18px | Подзаголовки |
| `text-xl` | 20px | Заголовки карточек |
| `text-2xl` | 24px | Заголовки блоков |
| `text-3xl` | 32px | Заголовки страниц |

### 1.3 Отступы

Используй кратные 4px:

| Токен | Значение | Применение |
|-------|----------|------------|
| `1` | 4px | Микроотступы |
| `2` | 8px | Между связанными элементами |
| `3` | 12px | Внутри компонентов |
| `4` | 16px | Стандартный gap |
| `5` | 20px | Padding карточек |
| `6` | 24px | Между секциями |
| `8` | 32px | Крупные отступы |
| `10` | 40px | Между блоками |
| `12` | 48px | Padding секций |
| `16` | 64px | Большие секции |

### 1.4 Скругления

| Токен | Значение | Применение |
|-------|----------|------------|
| `rounded` | 4px | Badges, мелкие элементы |
| `rounded-lg` | 8px | Кнопки, инпуты |
| `rounded-xl` | 12px | Карточки, модалки |
| `rounded-full` | 50% | Аватары, круглые кнопки |

### 1.5 Тени

```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.07);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
```

Тени используются только для:
- Модальных окон
- Dropdown меню
- Floating элементов (FAB, toast)

### 1.6 Анимации

```css
--transition-fast: 150ms ease;
--transition-base: 200ms ease;
```

Анимируем только:
- `opacity`
- `transform`
- `background-color`
- `border-color`

---

## 2. Компоненты

### 2.1 Кнопки

**Три варианта. Больше не нужно.**

```tsx
// Primary — основное действие (одна на экран)
<button className="btn btn-primary">Найти</button>

// Secondary — вторичные действия
<button className="btn btn-secondary">Фильтры</button>

// Ghost — минимальные действия
<button className="btn btn-ghost">Отмена</button>
```

**CSS:**

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 150ms ease;
  cursor: pointer;
  border: none;
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--gray-900);
  color: var(--white);
}
.btn-primary:hover:not(:disabled) {
  background: var(--black);
}

.btn-secondary {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--color-bg-hover);
  border-color: var(--gray-400);
}

.btn-ghost {
  background: transparent;
  color: var(--color-text);
}
.btn-ghost:hover:not(:disabled) {
  background: var(--color-bg-secondary);
}
```

**Размеры:**

```css
.btn-sm { padding: 8px 16px; font-size: 14px; }
.btn-lg { padding: 16px 32px; font-size: 16px; }
.btn-block { width: 100%; }
```

**Запрещено:**
- `btn-danger` с красным фоном — используй текст "Удалить" + модалку подтверждения
- `btn-accent` — дублирует primary
- Inline стили типа `px-4 py-2 border border-[var(--color-border)] rounded-lg`

### 2.2 Инпуты

**Единый стиль для всех полей ввода:**

```css
.input {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--white);
  color: var(--color-text);
  transition: border-color 150ms ease;
}

.input:focus {
  outline: none;
  border-color: var(--color-text);
}

.input::placeholder {
  color: var(--color-text-secondary);
}

.input:disabled {
  background: var(--color-bg-secondary);
  cursor: not-allowed;
}

.input-error {
  border-color: var(--gray-900);
}
```

**Применяется к:**
- `<input>`
- `<textarea>`
- `<select>`

**Компонент Field:**

```tsx
<Field label="Email" required error={errors.email}>
  <input className="input" type="email" />
</Field>
```

### 2.3 Карточки

```css
.card {
  background: var(--white);
  border: 1px solid var(--color-border);
  border-radius: 12px;
}

.card-interactive {
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.card-interactive:hover {
  border-color: var(--gray-400);
  box-shadow: var(--shadow-sm);
}

.card-body {
  padding: 20px;
}
```

### 2.4 Модальные окна

```tsx
<Modal isOpen={isOpen} onClose={onClose} title="Заголовок" size="md">
  <p>Контент</p>
  <Modal.Footer>
    <button className="btn btn-secondary flex-1">Отмена</button>
    <button className="btn btn-primary flex-1">Подтвердить</button>
  </Modal.Footer>
</Modal>
```

**Размеры:** `sm` (384px), `md` (448px), `lg` (512px)

**Структура:**
- Заголовок: `text-xl font-semibold`
- Backdrop: `bg-black/50`
- Анимация: slide-in 200ms

### 2.5 Badges / Tags

**Только черно-белые:**

```tsx
// Стандартный badge
<span className="badge">Студия</span>

// Инвертированный (для выделения)
<span className="badge badge-filled">Сдан</span>
```

```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  background: var(--color-bg-secondary);
  color: var(--color-text);
}

.badge-filled {
  background: var(--gray-900);
  color: var(--white);
}
```

**Статусы через текст, не цвет:**
- "Сдан" — badge-filled
- "Строится" — badge (обычный)
- "Сдача: Q4 2025" — badge (обычный)

### 2.6 Табы

**Единый паттерн:**

```tsx
<Tabs value={activeTab} onChange={setActiveTab}>
  <Tab value="offers">Квартиры</Tab>
  <Tab value="plans">Планировки</Tab>
</Tabs>
```

```css
.tabs {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--color-border);
}

.tab {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 150ms ease;
}

.tab:hover {
  color: var(--color-text);
}

.tab-active {
  color: var(--color-text);
  border-bottom-color: var(--color-accent);
}
```

### 2.7 Таблицы

```css
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  padding: 12px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.table td {
  padding: 12px;
  font-size: 14px;
  border-bottom: 1px solid var(--color-border);
}

.table tr:hover {
  background: var(--color-bg-secondary);
}
```

### 2.8 Иконки-кнопки (Action Buttons)

Для избранного, сравнения и т.д.:

```tsx
<IconButton size="md" active={isFavorite} onClick={toggle}>
  <HeartIcon />
</IconButton>
```

```css
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--white);
  border: 1px solid var(--color-border);
  transition: all 150ms ease;
}

.icon-btn:hover {
  background: var(--color-bg-secondary);
  border-color: var(--gray-400);
}

.icon-btn-active {
  background: var(--gray-900);
  border-color: var(--gray-900);
  color: var(--white);
}

.icon-btn-sm { width: 32px; height: 32px; }
.icon-btn-md { width: 40px; height: 40px; }
.icon-btn-lg { width: 48px; height: 48px; }
```

### 2.9 Пагинация

```tsx
<Pagination
  current={page}
  total={totalPages}
  onChange={setPage}
/>
```

Кнопки страниц используют `.btn .btn-sm`:
- Текущая: `.btn-primary`
- Остальные: `.btn-secondary`

### 2.10 Loading / Skeleton

```css
.skeleton {
  background: var(--color-bg-secondary);
  border-radius: 4px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

```tsx
// Skeleton для карточки
<div className="card">
  <div className="skeleton h-48 rounded-t-xl" />
  <div className="card-body space-y-3">
    <div className="skeleton h-6 w-3/4" />
    <div className="skeleton h-4 w-1/2" />
  </div>
</div>
```

---

## 3. Паттерны

### 3.1 Лейблы полей

```tsx
<label className="block text-sm font-medium mb-1.5">
  Название
  {required && <span className="text-[var(--color-text-secondary)] ml-0.5">*</span>}
</label>
```

### 3.2 Ошибки форм

```tsx
{error && (
  <p className="text-sm text-[var(--color-text)] mt-1.5">{error}</p>
)}
```

Не используем красный цвет. Текст ошибки достаточно информативен.

### 3.3 Пустые состояния

```tsx
<div className="text-center py-12">
  <div className="text-[var(--color-text-secondary)] mb-4">
    Нет результатов
  </div>
  <button className="btn btn-secondary">
    Сбросить фильтры
  </button>
</div>
```

### 3.4 Секции страницы

```tsx
<section className="py-12 md:py-16">
  <div className="container">
    <h2 className="text-2xl md:text-3xl font-semibold mb-8">
      Заголовок секции
    </h2>
    {/* content */}
  </div>
</section>
```

### 3.5 Разделители в карточках

```tsx
<div className="pt-4 mt-4 border-t border-[var(--color-border)]">
  {/* footer content */}
</div>
```

### 3.6 Hover на кликабельных элементах

Все кликабельные элементы должны иметь визуальный feedback:

```css
/* Текстовые ссылки */
.link:hover {
  color: var(--color-text-secondary);
}

/* Карточки */
.card-interactive:hover {
  border-color: var(--gray-400);
}

/* Строки таблиц */
.table tr:hover {
  background: var(--color-bg-secondary);
}
```

---

## 4. Layout

### 4.1 Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
}

@media (min-width: 640px) {
  .container { padding: 0 24px; }
}

@media (min-width: 1024px) {
  .container { padding: 0 32px; }
}
```

### 4.2 Грид для карточек

```tsx
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
  {offers.map(offer => <OfferCard key={offer.id} offer={offer} />)}
</div>
```

### 4.3 Header

- Высота: auto с padding `py-6`
- Border: `border-b border-[var(--color-border)]`
- Лого: `text-xl font-semibold tracking-tight`
- Навигация: `text-[15px] font-medium`

### 4.4 Footer

- Padding: `py-12 md:py-16`
- Border: `border-t border-[var(--color-border)]`
- Текст копирайта: `text-sm text-[var(--color-text-secondary)]`

---

## 5. Иконки

Используем inline SVG. Стандартный размер: 20x20 (`w-5 h-5`).

**Правила:**
- `stroke="currentColor"` — цвет наследуется
- `strokeWidth={2}` или `strokeWidth={1.5}`
- `fill="none"` для outline иконок

```tsx
// Шаблон иконки
<svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
  <path strokeLinecap="round" strokeLinejoin="round" d="..." />
</svg>
```

**Размеры иконок:**
- `w-4 h-4` — в кнопках sm, badges
- `w-5 h-5` — стандартный
- `w-6 h-6` — в заголовках, крупных кнопках

---

## 6. Доступность

### 6.1 Focus states

```css
.btn:focus-visible,
.input:focus-visible,
.icon-btn:focus-visible {
  outline: 2px solid var(--color-text);
  outline-offset: 2px;
}
```

### 6.2 Обязательные атрибуты

```tsx
// Иконки-кнопки
<button aria-label="Добавить в избранное">
  <HeartIcon />
</button>

// Модалки
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">

// Скрытый текст для скринридеров
<span className="sr-only">Загрузка...</span>
```

---

## 7. Чеклист для нового компонента

Перед созданием нового компонента проверь:

- [ ] Нет ли уже готового компонента для этой задачи?
- [ ] Используются ли только CSS-переменные из токенов?
- [ ] Нет ли цветов кроме черно-белой палитры?
- [ ] Нет ли эмоджи?
- [ ] Есть ли hover/focus состояния?
- [ ] Есть ли disabled состояние (если применимо)?
- [ ] Добавлены ли aria-атрибуты?
- [ ] Соответствует ли размер типографики токенам?
- [ ] Соответствуют ли отступы шкале (кратные 4px)?

---

## 8. Антипаттерны

**Не делай так:**

```tsx
// Плохо: inline стили дублируют btn
<button className="px-4 py-2 bg-gray-900 text-white rounded-lg">

// Хорошо:
<button className="btn btn-primary">
```

```tsx
// Плохо: цветной badge
<span className="bg-green-100 text-green-700">Сдан</span>

// Хорошо:
<span className="badge badge-filled">Сдан</span>
```

```tsx
// Плохо: разные стили для одинаковых инпутов
<input className="w-full px-4 py-2.5 border border-gray-300 rounded-lg" />
<input className="w-full px-3 py-2 border border-[var(--color-border)] rounded-md" />

// Хорошо:
<input className="input" />
```

```tsx
// Плохо: эмоджи
<span>Сдан ✓</span>

// Хорошо:
<span className="badge badge-filled">Сдан</span>
```

---

## 9. Файловая структура компонентов

```
frontend/src/
├── components/
│   ├── ui/                    # Базовые UI-примитивы
│   │   ├── Button.tsx         # (если нужен компонент, а не только CSS)
│   │   ├── Input.tsx
│   │   ├── Modal.tsx
│   │   ├── Tabs.tsx
│   │   ├── Badge.tsx
│   │   ├── IconButton.tsx
│   │   ├── Pagination.tsx
│   │   └── index.ts           # реэкспорт
│   │
│   ├── layout/                # Структурные компоненты
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Container.tsx
│   │
│   └── [feature]/             # Бизнес-компоненты
│       ├── OfferCard.tsx
│       ├── OfferTable.tsx
│       └── ...
```

---

## 10. Миграция существующих компонентов

Компоненты, требующие обновления для соответствия Design System:

| Компонент | Проблема | Решение |
|-----------|----------|---------|
| `CompareButton` | `purple-500`, `purple-600` | Заменить на `gray-900` / `black` |
| `StageBadge` | Цветные bg (`yellow-100`, `green-100`) | Перейти на `.badge` / `.badge-filled` |
| `PriorityBadge` | Цветной текст + символы | Текстовые метки без цвета |
| `StatusBadge` | `green-100`, `orange-100` | `.badge` / `.badge-filled` |
| `BookingForm` | `green-50`, `green-600` | Обычный текст + border |
| `OffersTable` | `blue-50` для выделения | `var(--color-bg-secondary)` |
| `BulkActionsBar` | Inline button стили | Использовать `.btn .btn-secondary` |

---

Этот документ — источник истины. При сомнениях — сверяйся с ним.
