# Руководство по деплою

## Быстрый деплой (рекомендуется)

```bash
# 1. Закоммитить и запушить изменения локально
git add -A && git commit -m "fix: описание" && git push

# 2. Запустить скрипт деплоя на сервере
ssh -i ~/.ssh/id_housler root@91.229.8.221 '/root/ai-calendar-assistant/deploy_sync.sh'
```

## Структура на сервере

```
/root/ai-calendar-assistant/           # Docker build context
├── app/                               # ← Копируется из git
├── docker-compose.secure.yml          # Docker конфиг
├── Dockerfile.bot                     # Dockerfile для бота
├── .env                               # Переменные окружения
├── deploy_sync.sh                     # Скрипт синхронизации
└── ai-calendar-assistant/             # Git репозиторий
    ├── app/                           # Исходный код (актуальный)
    ├── docs/                          # Документация
    └── scripts/                       # Скрипты
```

**Важно:** Docker билдит из `/root/ai-calendar-assistant/`, а git репозиторий находится в подпапке `ai-calendar-assistant/`. Скрипт `deploy_sync.sh` синхронизирует их.

## Ручной деплой

Если скрипт не работает:

```bash
# SSH на сервер
ssh -i ~/.ssh/id_housler root@91.229.8.221

# Перейти в git директорию и обновить
cd /root/ai-calendar-assistant/ai-calendar-assistant
git pull origin main

# Скопировать файлы в docker context
rsync -av --delete app/ /root/ai-calendar-assistant/app/
cp requirements.txt /root/ai-calendar-assistant/
cp run_polling.py /root/ai-calendar-assistant/ 2>/dev/null || true
cp start.sh /root/ai-calendar-assistant/ 2>/dev/null || true

# Пересобрать и перезапустить
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot
docker-compose -f docker-compose.secure.yml up -d telegram-bot
```

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
```

## Откат изменений

```bash
# На сервере
cd /root/ai-calendar-assistant/ai-calendar-assistant
git log --oneline -10  # Найти нужный коммит
git checkout <commit_hash> -- app/  # Откатить только app/

# Синхронизировать и пересобрать
rsync -av --delete app/ /root/ai-calendar-assistant/app/
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot
docker-compose -f docker-compose.secure.yml up -d telegram-bot
```

## Частые проблемы

### Контейнер показывает старую версию после деплоя

**Причина:** Файлы не скопированы из git в docker context.

**Решение:**
```bash
rsync -av --delete /root/ai-calendar-assistant/ai-calendar-assistant/app/ \
  /root/ai-calendar-assistant/app/
docker-compose -f docker-compose.secure.yml build --no-cache telegram-bot
docker-compose -f docker-compose.secure.yml up -d telegram-bot
```

### Порт 8000 занят

**Причина:** Старый контейнер не остановлен.

**Решение:**
```bash
docker ps -a | grep 8000
docker stop <container_name>
docker rm <container_name>
docker-compose -f docker-compose.secure.yml up -d telegram-bot
```

### Git pull не работает

**Причина:** Локальные изменения конфликтуют.

**Решение:**
```bash
cd /root/ai-calendar-assistant/ai-calendar-assistant
git stash
git pull origin main
git stash pop  # Если нужно вернуть локальные изменения
```

## Обновление версии WebApp

При изменении `app/static/index.html` обязательно обновите `APP_VERSION`:

```javascript
const APP_VERSION = 'YYYY-MM-DD-vN';  // Например: 2025-12-04-v2
```

Это позволяет:
- Отслеживать какая версия на проде
- Форсировать обновление кэша в браузере
- Быстро диагностировать проблемы

## Контакты

- Сервер: 91.229.8.221
- SSH ключ: `~/.ssh/id_housler`
- Git: https://github.com/nikita-tita/ai-calendar-assistant
