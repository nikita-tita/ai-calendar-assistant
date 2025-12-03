# Инструкция по деплою бота на REG.RU VPS

## Шаг 1: Покупка VPS на REG.RU

1. Зайди на https://www.reg.ru/vps/
2. Выбери тариф **Start** (200₽/месяц):
   - 1 vCPU
   - 512 MB RAM
   - 10 GB SSD
   - Ubuntu 22.04

3. Нажми **"Заказать"**
4. Оплати российской картой

## Шаг 2: Получение доступа к VPS

После оплаты тебе на email придут:
- **IP-адрес сервера** (например: 185.123.45.67)
- **Пароль root**

## Шаг 3: Подключение к серверу

### Вариант A: Через терминал (Mac)

```bash
ssh root@ВАШ_IP_АДРЕС
```

Введи пароль из письма.

### Вариант B: Через веб-консоль REG.RU

1. Зайди в личный кабинет REG.RU
2. Раздел **"Серверы"** → **"VPS"**
3. Нажми на твой сервер
4. Кнопка **"Консоль"** (откроется терминал в браузере)

## Шаг 4: Установка бота (автоматически)

Скопируй и выполни эту команду в терминале сервера:

```bash
curl -fsSL https://raw.githubusercontent.com/nikita-tita/ai-calendar-bot/main/install.sh | bash
```

Скрипт автоматически:
- Установит Docker
- Скачает бота
- Запросит у тебя переменные окружения
- Запустит бота в фоне

## Шаг 5: Настройка переменных окружения

Скрипт запросит:

1. **TELEGRAM_BOT_TOKEN**: `8378762774:AAEYXYVmx84pgp2_sn_U7RXYTgfNJMY-Klk`
2. **OPENAI_API_KEY**: твой ключ OpenAI
3. **RADICALE_URL**: `https://calendar-bot-production-e1ac.up.railway.app`

## Шаг 6: Проверка работы

```bash
# Проверить, что бот запущен
docker ps

# Посмотреть логи бота
docker logs -f telegram-bot

# Перезапустить бота
docker restart telegram-bot
```

## Управление ботом

### Остановить бота
```bash
docker stop telegram-bot
```

### Запустить бота
```bash
docker start telegram-bot
```

### Обновить бота на новую версию
```bash
cd /root/ai-calendar-assistant
git pull
docker-compose down
docker-compose up -d --build
```

### Посмотреть логи
```bash
docker logs -f telegram-bot
```

## Автозапуск при перезагрузке сервера

Бот автоматически запустится при перезагрузке сервера благодаря `restart: always` в docker-compose.yml.

## Полезные команды

```bash
# Проверить использование ресурсов
docker stats

# Очистить старые Docker образы
docker system prune -a

# Проверить статус всех контейнеров
docker ps -a
```

## Стоимость

**200₽/месяц** — бот работает 24/7 без перерывов!

## Поддержка

Если что-то не работает:
1. Проверь логи: `docker logs telegram-bot`
2. Проверь, что контейнер запущен: `docker ps`
3. Перезапусти бота: `docker restart telegram-bot`
