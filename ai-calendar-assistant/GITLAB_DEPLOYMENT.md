# Развертывание AI Calendar Assistant на GitLab

Пошаговая инструкция по развертыванию проекта AI Calendar Assistant на GitLab с использованием CI/CD.

## 📋 Оглавление

1. [Подготовка проекта](#подготовка-проекта)
2. [Создание репозитория на GitLab](#создание-репозитория-на-gitlab)
3. [Настройка CI/CD переменных](#настройка-cicd-переменных)
4. [Настройка сервера для деплоя](#настройка-сервера-для-деплоя)
5. [Запуск CI/CD пайплайна](#запуск-cicd-пайплайна)
6. [Проверка и мониторинг](#проверка-и-мониторинг)

---

## 1. Подготовка проекта

### Проверка структуры проекта

Убедитесь, что в проекте есть следующие файлы:

```
AI-Calendar-Project/
├── .gitlab-ci.yml                    # ✅ CI/CD конфигурация
├── ai-calendar-assistant/
│   ├── .dockerignore                 # ✅ Исключения для Docker
│   ├── .env.example                  # ✅ Пример переменных окружения
│   ├── Dockerfile                    # ✅ Существует
│   ├── docker-compose.yml            # ✅ Существует
│   ├── requirements.txt              # ✅ Зависимости Python
│   └── app/                          # Код приложения
```

### Проверка файлов

```bash
cd ~/Desktop/AI-Calendar-Project

# Проверяем наличие всех необходимых файлов
ls -la .gitlab-ci.yml
ls -la ai-calendar-assistant/.dockerignore
ls -la ai-calendar-assistant/.env.example
ls -la ai-calendar-assistant/Dockerfile
ls -la ai-calendar-assistant/docker-compose.yml
```

---

## 2. Создание репозитория на GitLab

### Вариант A: Через веб-интерфейс GitLab

1. Откройте [GitLab](https://gitlab.com)
2. Нажмите **New Project** → **Create blank project**
3. Укажите:
   - **Project name**: `ai-calendar-assistant`
   - **Visibility Level**: `Private` (или `Public`)
4. **НЕ** ставьте галочку "Initialize repository with a README"
5. Нажмите **Create project**

### Вариант B: Через командную строку

```bash
# Перейти в директорию проекта
cd ~/Desktop/AI-Calendar-Project

# Инициализировать Git (если еще не инициализирован)
git init

# Добавить все файлы
git add .

# Создать первый коммит
git commit -m "Initial commit: AI Calendar Assistant with GitLab CI/CD"

# Добавить GitLab remote (замените YOUR_USERNAME на ваше имя пользователя)
git remote add gitlab git@gitlab.com:YOUR_USERNAME/ai-calendar-assistant.git

# Или через HTTPS
git remote add gitlab https://gitlab.com/YOUR_USERNAME/ai-calendar-assistant.git

# Отправить код на GitLab
git push -u gitlab main
```

**Примечание**: Если ваша основная ветка называется `master`, используйте:
```bash
git branch -M main
git push -u gitlab main
```

---

## 3. Настройка CI/CD переменных

### Обязательные переменные

В GitLab перейдите в **Settings** → **CI/CD** → **Variables** и добавьте следующие переменные:

#### 3.1 Telegram Bot

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `TELEGRAM_BOT_TOKEN` | Ваш токен от @BotFather | ✅ | ✅ |
| `TELEGRAM_WEBHOOK_SECRET` | Случайная строка (32+ символа) | ✅ | ✅ |

#### 3.2 API Keys

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `YANDEX_GPT_API_KEY` | Ваш Yandex GPT API ключ | ✅ | ✅ |
| `YANDEX_GPT_FOLDER_ID` | Ваш Yandex Folder ID | ✅ | ❌ |

#### 3.3 Deployment (SSH)

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `SSH_PRIVATE_KEY` | Приватный SSH ключ для доступа к серверу | ✅ | ✅ |
| `DEPLOY_SERVER` | IP или домен вашего сервера | ✅ | ❌ |
| `DEPLOY_USER` | root (или другой пользователь) | ✅ | ❌ |

#### 3.4 Database

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `DB_PASSWORD` | Пароль для PostgreSQL | ✅ | ✅ |

#### 3.5 GitLab Container Registry

| Variable | Value | Protected | Masked |
|----------|-------|-----------|--------|
| `CI_REGISTRY_USER` | Ваш GitLab username | ✅ | ❌ |
| `CI_REGISTRY_PASSWORD` | Personal Access Token с правами `read_registry`, `write_registry` | ✅ | ✅ |

### Генерация SSH ключа для деплоя

Если у вас еще нет SSH ключа для деплоя:

```bash
# Создать новый SSH ключ
ssh-keygen -t ed25519 -C "gitlab-ci@ai-calendar-assistant" -f ~/.ssh/gitlab_deploy_key

# Показать приватный ключ (добавить в GitLab как SSH_PRIVATE_KEY)
cat ~/.ssh/gitlab_deploy_key

# Показать публичный ключ (добавить на сервер)
cat ~/.ssh/gitlab_deploy_key.pub
```

Добавьте публичный ключ на сервер:

```bash
# На вашем сервере
mkdir -p ~/.ssh
echo "ВАШИ_ПУБЛИЧНЫЙ_КЛЮЧ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

---

## 4. Настройка сервера для деплоя

### 4.1 Подключение к серверу

```bash
ssh root@91.229.8.221
# или
ssh root@your-server-ip
```

### 4.2 Установка зависимостей на сервере

```bash
# Обновить систему
apt-get update && apt-get upgrade -y

# Установить Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Установить Docker Compose
apt-get install docker-compose-plugin -y

# Установить Git
apt-get install git -y

# Проверить установку
docker --version
docker compose version
git --version
```

### 4.3 Клонирование репозитория на сервер

```bash
# Создать директорию для проекта
cd /root
git clone https://gitlab.com/YOUR_USERNAME/ai-calendar-assistant.git

# Перейти в директорию
cd ai-calendar-assistant/ai-calendar-assistant
```

### 4.4 Настройка .env файла на сервере

```bash
# Создать .env из примера
cp .env.example .env

# Редактировать .env
nano .env
```

Заполните все необходимые переменные из раздела 3.

### 4.5 Создание необходимых директорий

```bash
# В директории проекта
mkdir -p credentials logs radicale_data

# Установить правильные права
chmod 755 credentials logs radicale_data
```

---

## 5. Запуск CI/CD пайплайна

### 5.1 Структура пайплайна

Ваш `.gitlab-ci.yml` включает 3 стадии:

1. **test** - Запуск тестов, проверка кода, сканирование безопасности
2. **build** - Сборка Docker образов и push в GitLab Container Registry
3. **deploy** - Деплой на production/staging сервер

### 5.2 Автоматический запуск

Пайплайн запускается автоматически при:

- Push в любую ветку (стадия `test`)
- Push в `main` или `develop` (стадии `test` + `build`)
- Создании merge request
- Создании тега

### 5.3 Ручной деплой

Деплой выполняется **вручную** для безопасности:

1. Откройте ваш проект на GitLab
2. Перейдите в **CI/CD** → **Pipelines**
3. Выберите нужный пайплайн
4. В стадии `deploy` нажмите на кнопку **Play** (▶️) рядом с `deploy_production` или `deploy_staging`

### 5.4 Мониторинг выполнения

```bash
# На сервере проверить статус контейнеров
docker-compose ps

# Просмотреть логи
docker-compose logs -f calendar-assistant
docker-compose logs -f radicale
docker-compose logs -f property-bot

# Проверить health status
docker-compose ps | grep healthy
```

---

## 6. Проверка и мониторинг

### 6.1 Проверка работы приложения

```bash
# Проверить health endpoint
curl http://localhost:8000/health

# Или с внешнего адреса
curl https://your-domain.com/health
```

### 6.2 Проверка Telegram бота

Отправьте сообщение вашему боту в Telegram:

```
/start
```

### 6.3 Настройка webhook

```bash
# На сервере или локально
python3 << EOF
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN"
WEBHOOK_URL = "https://your-domain.com/webhook/telegram"
WEBHOOK_SECRET = "YOUR_WEBHOOK_SECRET"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
data = {
    "url": WEBHOOK_URL,
    "secret_token": WEBHOOK_SECRET
}

response = requests.post(url, json=data)
print(response.json())
EOF
```

### 6.4 Мониторинг логов

```bash
# Логи всех сервисов
docker-compose logs -f

# Только calendar-assistant
docker-compose logs -f calendar-assistant

# Последние 100 строк
docker-compose logs --tail=100 calendar-assistant
```

### 6.5 Перезапуск сервисов

```bash
# Перезапустить все сервисы
docker-compose restart

# Перезапустить конкретный сервис
docker-compose restart calendar-assistant

# Полная пересборка и перезапуск
docker-compose down
docker-compose up -d --build
```

---

## 🔧 Дополнительные настройки

### Автоматический деплой (опционально)

Если хотите автоматический деплой без ручного подтверждения, удалите строку `when: manual` из `.gitlab-ci.yml`:

```yaml
deploy_production:
  stage: deploy
  # ... другие настройки ...
  only:
    - main
  # when: manual  # <-- Закомментировать или удалить эту строку
```

### Настройка Nginx (если используете)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Настройка SSL с Certbot

```bash
apt-get install certbot python3-certbot-nginx -y
certbot --nginx -d your-domain.com
```

---

## 🚨 Troubleshooting

### Проблема: Pipeline fails на stage build

**Решение**: Проверьте, что GitLab Runner имеет доступ к Docker:

```bash
# На сервере с Runner
docker ps
```

### Проблема: SSH connection refused во время deploy

**Решение**:
1. Проверьте SSH ключ в GitLab CI/CD Variables
2. Убедитесь, что публичный ключ добавлен на сервер
3. Проверьте firewall:

```bash
ufw allow 22/tcp
ufw enable
```

### Проблема: Docker image pull fails

**Решение**: Проверьте, что на сервере выполнен login в GitLab registry:

```bash
echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin registry.gitlab.com
```

### Проблема: Telegram webhook не работает

**Решение**:
1. Проверьте, что webhook URL доступен извне
2. Проверьте SSL сертификат (Telegram требует HTTPS)
3. Проверьте логи:

```bash
docker-compose logs calendar-assistant | grep webhook
```

---

## 📚 Дополнительные ресурсы

- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Docker Documentation](https://docs.docker.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## ✅ Чеклист развертывания

- [ ] Создан репозиторий на GitLab
- [ ] Код загружен в репозиторий
- [ ] Добавлены все CI/CD переменные
- [ ] Сгенерирован и добавлен SSH ключ
- [ ] Установлен Docker на сервере
- [ ] Клонирован репозиторий на сервер
- [ ] Создан и настроен .env файл
- [ ] Запущен первый pipeline
- [ ] Выполнен manual deploy
- [ ] Проверен health endpoint
- [ ] Настроен Telegram webhook
- [ ] Протестирован бот в Telegram
- [ ] Настроен Nginx (если нужно)
- [ ] Настроен SSL сертификат (если нужно)

---

**Готово!** Ваш AI Calendar Assistant развернут на GitLab! 🚀

Для обновления кода просто делайте `git push gitlab main`, и GitLab автоматически запустит тесты и сборку. Деплой запускайте вручную через веб-интерфейс GitLab.
