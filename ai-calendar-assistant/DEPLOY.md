# Руководство по деплою

## Быстрый деплой

```bash
# 1. Закоммитить и запушить изменения
git add -A && git commit -m "fix: описание" && git push origin main

# 2. Задеплоить на сервер (одна команда)
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git pull origin main &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

## Структура на сервере

```
/root/ai-calendar-assistant/              # Git clone root
├── .git/                                 # Git данные
├── README.md                             # Корневой README
└── ai-calendar-assistant/                # ⭐ РАБОЧАЯ ДИРЕКТОРИЯ
    ├── .env                              # Конфигурация (НЕ в git!)
    ├── app/                              # Код приложения
    ├── data/                             # Данные (SQLite)
    ├── logs/                             # Логи
    ├── docker-compose.secure.yml         # Docker конфиг
    ├── Dockerfile.bot                    # Dockerfile
    ├── requirements.txt                  # Python зависимости
    ├── run_polling.py                    # Скрипт запуска бота
    └── start.sh                          # Entrypoint для Docker
```

**ВАЖНО:** Все docker команды выполняются из `/root/ai-calendar-assistant/ai-calendar-assistant/`

## Проверка деплоя

```bash
# Проверить здоровье API
curl https://calendar.housler.ru/health

# Проверить версию WebApp
curl -s https://calendar.housler.ru/static/index.html | grep "APP_VERSION"

# Проверить версию в контейнере
ssh -i ~/.ssh/id_housler root@91.229.8.221 \
  'docker exec telegram-bot cat /app/app/static/index.html | grep "APP_VERSION"'

# Посмотреть логи
ssh -i ~/.ssh/id_housler root@91.229.8.221 'docker logs telegram-bot --tail 50'

# Статус контейнеров
ssh -i ~/.ssh/id_housler root@91.229.8.221 'docker ps | grep -E "(telegram-bot|redis|radicale)"'
```

## Откат изменений

```bash
# На сервере - откатить к предыдущему коммиту
ssh -i ~/.ssh/id_housler root@91.229.8.221 '
  cd /root/ai-calendar-assistant/ai-calendar-assistant &&
  git log --oneline -5 &&
  git checkout HEAD~1 -- app/ &&
  docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot &&
  docker-compose -f docker-compose.secure.yml up -d telegram-bot
'
```

## Частые проблемы

### Контейнер не запускается

```bash
# Проверить логи
docker logs telegram-bot

# Проверить что порт свободен
docker ps -a | grep 8000

# Остановить конфликтующий контейнер
docker stop <container_name> && docker rm <container_name>
```

### Git pull конфликт

```bash
# Сбросить локальные изменения на сервере
cd /root/ai-calendar-assistant/ai-calendar-assistant
git fetch origin
git reset --hard origin/main
```

### .env не найден

```bash
# Скопировать из бэкапа
cp /root/backup_before_cleanup_20251204/.env \
   /root/ai-calendar-assistant/ai-calendar-assistant/.env
```

## Полезные команды

```bash
# SSH на сервер
ssh -i ~/.ssh/id_housler root@91.229.8.221

# Перейти в рабочую директорию
cd /root/ai-calendar-assistant/ai-calendar-assistant

# Пересобрать без кэша
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot

# Перезапустить
docker-compose -f docker-compose.secure.yml up -d telegram-bot

# Остановить все сервисы
docker-compose -f docker-compose.secure.yml down

# Запустить все сервисы
docker-compose -f docker-compose.secure.yml up -d
```

## Контакты

- **Сервер:** 91.229.8.221
- **SSH ключ:** `~/.ssh/id_housler`
- **Git:** https://github.com/nikita-tita/ai-calendar-assistant
- **Прод URL:** https://calendar.housler.ru
