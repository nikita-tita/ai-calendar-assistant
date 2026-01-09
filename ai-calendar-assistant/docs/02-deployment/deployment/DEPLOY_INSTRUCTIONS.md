# Инструкция по деплою обновлений

## Быстрый деплой (рекомендуется)

Используйте скрипт для полного обновления всех файлов:

```bash
./deploy-full-update.sh
```

Этот скрипт:
- ✅ Загружает ВСЕ файлы на сервер
- ✅ Копирует их в Docker контейнер
- ✅ Перезапускает бот
- ✅ Сохраняет все данные пользователей
- ✅ Проверяет статус

## Ручной деплой отдельных файлов

### 1. Обновление Python кода

```bash
# Загрузить на сервер
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/services/telegram_handler.py \
  root@95.163.227.26:/root/ai-calendar-assistant/app/services/

# Скопировать в контейнер и перезапустить
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker cp /root/ai-calendar-assistant/app/services/telegram_handler.py telegram-bot:/app/app/services/ && \
   docker restart telegram-bot"
```

### 2. Обновление WebApp

```bash
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  webapp_server.html \
  root@95.163.227.26:/var/www/calendar/index.html

# Перезапуск не требуется - статический файл
```

### 3. Обновление админ-панели

```bash
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  admin_server.html \
  root@95.163.227.26:/var/www/calendar/admin_fbc36dd546d7746b862e45a7.html

# Перезапуск не требуется
```

## Критически важно! ⚠️

### При обновлении кода ВСЕГДА обновляйте связанные файлы:

**Если меняете analytics_service.py:**
```bash
# Обновите также:
- app/models/analytics.py (модели данных)
- app/routers/admin.py (API endpoints)
- app/services/telegram_handler.py (логирование)
```

**Если меняете telegram_handler.py:**
```bash
# Обновите также:
- app/services/llm_agent_yandex.py (если изменён LLM)
- app/services/user_preferences.py (если изменены настройки)
- app/services/analytics_service.py (если изменено логирование)
```

**Если меняете config.py:**
```bash
# Обновите также:
- app/main.py (использует settings)
- .env файл на сервере (если добавлены новые переменные)
```

## Проверка после деплоя

### 1. Проверить статус бота
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker ps | grep telegram-bot"
```

### 2. Проверить логи
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker logs --tail 50 telegram-bot"
```

### 3. Проверить аналитику
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker exec telegram-bot cat /var/lib/calendar-bot/analytics_data.json"
```

### 4. Тест админ-панели
- Открыть: https://этонесамыйдлинныйдомен.рф/admin_fbc36dd546d7746b862e45a7.html
- Войти с 3 паролями
- Проверить статистику и список пользователей

### 5. Тест бота
- Отправить `/start` в Telegram
- Создать тестовое событие
- Проверить, что оно появилось в календаре

## Восстановление после сбоя

### Если бот не запускается:

1. **Проверить логи:**
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker logs telegram-bot 2>&1 | tail -50"
```

2. **Типичные ошибки:**

**ModuleNotFoundError:**
- Не загружена вся папка (например, `app/models/`)
- Решение: используйте `deploy-full-update.sh`

**AttributeError в Settings:**
- Не обновлён `app/config.py` или `.env`
- Решение: проверьте все поля в config.py

**ValidationError в аналитике:**
- Формат данных в `analytics_data.json` устарел
- Решение: очистите файл `{"actions":[]}`

### Если админка пустая:

1. **Проверить файл аналитики:**
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker exec telegram-bot cat /var/lib/calendar-bot/analytics_data.json"
```

2. **Если файл пустой - это нормально!**
   - Данные начнут собираться при использовании бота
   - Отправьте `/start` нескольким пользователям
   - Создайте несколько событий
   - Обновите страницу админки

3. **Создать тестовые данные:**
```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker exec telegram-bot python3 -c \"
from app.services.analytics_service import analytics_service
from app.models.analytics import ActionType

analytics_service.log_action('2296243', ActionType.USER_START, 'Test', username='test1', first_name='Test', last_name='User')
analytics_service.log_action('5602113922', ActionType.USER_START, 'Test', username='test2', first_name='Test', last_name='User')
print('Done')
\" && docker restart telegram-bot"
```

## Резервное копирование

### Перед критическими обновлениями:

```bash
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "tar -czf /root/backup-$(date +%Y%m%d-%H%M).tar.gz /var/lib/calendar-bot/"

# Скачать бэкап локально
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  root@95.163.227.26:/root/backup-*.tar.gz ./backups/
```

## Откат изменений

Если что-то пошло не так:

```bash
# 1. Остановить текущий бот
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker stop telegram-bot"

# 2. Восстановить из бэкапа
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "tar -xzf /root/backup-YYYYMMDD-HHMM.tar.gz -C /"

# 3. Перезапустить
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 \
  "docker start telegram-bot"
```

---

## Контрольный список перед деплоем ✅

- [ ] Все файлы сохранены локально
- [ ] Протестировано локально (если возможно)
- [ ] Создан бэкап данных
- [ ] Используется скрипт `deploy-full-update.sh` ИЛИ обновлены ВСЕ связанные файлы
- [ ] После деплоя проверены логи
- [ ] Протестирован бот в Telegram
- [ ] Проверена админ-панель

---

**Последнее обновление:** 27 октября 2025
