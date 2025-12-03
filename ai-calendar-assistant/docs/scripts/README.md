# Скрипты проекта

Эта папка содержит копии всех скриптов автоматизации для документации и истории изменений.

**Важно**: Рабочие версии скриптов находятся в корне проекта. Здесь хранятся копии для справки.

## Структура

```
scripts/
├── deployment/        # Скрипты развертывания
├── security/         # Скрипты безопасности
├── maintenance/      # Обслуживание и бэкапы
└── property-bot/     # Скрипты Property Bot
```

## Категории скриптов

### deployment/

Скрипты для развертывания проекта на различных платформах:

- `deploy-to-regru.sh` - Основной деплой на REG.RU VPS
- `deploy-safe.sh` - Безопасный деплой с проверками
- `deploy-auto.sh` - Автоматический деплой
- `QUICK_DEPLOY.sh` - Быстрое развертывание
- `deploy-yandex-gpt.sh` - Деплой с Yandex GPT
- `deploy-webapp-safe.sh` - Безопасный деплой webapp
- `deploy-fix-dates.sh` - Деплой с фиксами дат
- `deploy-full-update.sh` - Полное обновление системы

**Использование**:
```bash
# Из корня проекта
./deploy-to-regru.sh
```

### security/

Скрипты для проверки и улучшения безопасности:

- `deploy-security-improvements.sh` - Развертывание улучшений безопасности
- `test-security.sh` - Тестирование безопасности
- `final_security_check.sh` - Финальная проверка безопасности
- `fix-critical-security-now.sh` - Срочное исправление критических уязвимостей

**Использование**:
```bash
# Проверка безопасности перед деплоем
./test-security.sh

# Деплой security фиксов
./deploy-security-improvements.sh
```

### maintenance/

Скрипты для обслуживания и резервного копирования:

- `backup-calendar.sh` - Резервное копирование данных календаря
- `restore-from-backup.sh` - Восстановление из резервной копии

**Использование**:
```bash
# Создать бэкап
./backup-calendar.sh

# Восстановить из бэкапа
./restore-from-backup.sh [backup_file]
```

### property-bot/

Скрипты для развертывания Property Bot:

- `deploy-property-bot.sh` - Базовое развертывание Property Bot
- `deploy-property-bot-complete.sh` - Полное развертывание со всеми зависимостями

**Использование**:
```bash
# Полный деплой Property Bot
./deploy-property-bot-complete.sh
```

## Общие принципы использования

### Перед запуском любого скрипта:

1. **Проверьте права**:
   ```bash
   chmod +x script-name.sh
   ```

2. **Прочитайте комментарии в начале скрипта**:
   ```bash
   head -20 script-name.sh
   ```

3. **Проверьте переменные окружения** (если требуются):
   ```bash
   cat .env
   ```

4. **Сделайте бэкап** (для продакшн):
   ```bash
   ./backup-calendar.sh
   ```

### Логирование

Все скрипты пишут логи. Просмотр логов:

```bash
# Логи деплоя
tail -f /var/log/calendar-deploy.log

# Логи приложения
docker logs telegram-bot -f
```

### Безопасность

- Никогда не коммитьте скрипты с паролями или токенами
- Используйте `.env` файлы для конфиденциальных данных
- Проверяйте скрипты на уязвимости перед использованием

## Создание нового скрипта

Шаблон для нового скрипта:

```bash
#!/bin/bash

# Script: script-name.sh
# Description: Краткое описание что делает скрипт
# Author: Ваше имя
# Date: 2025-10-29
# Version: 1.0

set -e  # Остановить при ошибке
set -u  # Ошибка при использовании неопределенных переменных

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Проверка зависимостей
command -v docker >/dev/null 2>&1 || error "Docker не установлен"

# Основная логика
main() {
    log "Начало выполнения скрипта"

    # Ваш код здесь

    log "Скрипт выполнен успешно"
}

# Запуск
main "$@"
```

После создания:

1. Сохраните в корне проекта
2. Сделайте исполняемым: `chmod +x script-name.sh`
3. Протестируйте на staging
4. Скопируйте в `docs/scripts/[category]/`
5. Обновите этот README

## Troubleshooting

### Скрипт не запускается

```bash
# Проверьте права
ls -l script-name.sh

# Добавьте права на выполнение
chmod +x script-name.sh
```

### Ошибки с переменными окружения

```bash
# Проверьте .env файл
cat .env

# Загрузите переменные
source .env
```

### Ошибки Docker

```bash
# Проверьте Docker
docker ps

# Перезапустите Docker
sudo systemctl restart docker
```

---

**Последнее обновление**: 2025-10-29
