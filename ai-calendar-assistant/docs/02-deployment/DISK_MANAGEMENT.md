# Управление диском на сервере

## Проблема 20 декабря 2025

Диск заполнился на 100%, что привело к ошибке `507 Insufficient Storage` при создании событий в календаре.

### Причины заполнения

| Источник | Проблема |
|----------|----------|
| Docker overlay2 | Слои образов накапливаются при каждом `docker-compose build` |
| Docker container logs | **Логи контейнеров росли бесконечно** (не было лимита) |
| Docker build cache | Кэш сборки не очищался |
| Systemd journal | Логи journald не были ограничены |

## Настроенные решения

### 1. Лимит логов Docker

Файл `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
```

Каждый контейнер хранит максимум 3 файла по 50MB = 150MB логов на контейнер.

### 2. Лимит systemd journal

Файл `/etc/systemd/journald.conf`:
```ini
[Journal]
SystemMaxUse=500M
SystemKeepFree=1G
MaxFileSec=1week
```

### 3. Ежедневная автоочистка Docker

Файл `/etc/cron.daily/docker-cleanup`:
```bash
#!/bin/bash
docker container prune -f --filter "until=24h"
docker image prune -f
docker builder prune -f --filter "until=168h"
```

Удаляет:
- Остановленные контейнеры старше 24ч
- Образы без тегов (dangling)
- Build cache старше 7 дней

### 4. Мониторинг диска

Скрипт `/root/check-disk.sh` запускается каждые 6 часов:
```bash
#!/bin/bash
THRESHOLD=80
USAGE=$(df / | tail -1 | awk '{print int($5)}')

if [ "$USAGE" -ge "$THRESHOLD" ]; then
    docker system prune -f --filter "until=12h"
fi
```

При заполнении >80% автоматически очищает Docker.

## Ручные команды

### Проверка состояния
```bash
# Использование диска
df -h /

# Docker использование
docker system df -v

# Топ директорий
du -h --max-depth=2 /var/lib/docker | sort -hr | head -10
```

### Очистка (экстренная)
```bash
# Удалить всё неиспользуемое (осторожно!)
docker system prune -af --volumes

# Очистить только build cache
docker builder prune -af

# Очистить старые образы (старше 7 дней)
docker image prune -af --filter "until=168h"
```

## Рекомендуемые пороги

| Метрика | Норма | Внимание | Критично |
|---------|-------|----------|----------|
| Диск | <50% | 50-80% | >80% |
| Docker images | <10GB | 10-20GB | >20GB |
| Container logs | <1GB | 1-3GB | >3GB |

## Что делать при 100% диске

1. **Очистить Docker:**
   ```bash
   docker system prune -af --volumes
   docker builder prune -af
   ```

2. **Очистить логи journald:**
   ```bash
   journalctl --vacuum-size=200M
   ```

3. **Перезапустить контейнеры:**
   ```bash
   docker-compose -f docker-compose.secure.yml restart
   ```

---

**Дата настройки:** 2025-12-20
