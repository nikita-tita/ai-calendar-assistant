# Быстрый старт: Развертывание на GitLab

## Шаг 1: Создайте репозиторий на GitLab

1. Откройте https://gitlab.com
2. Нажмите **New Project** → **Create blank project**
3. Укажите имя: `ai-calendar-assistant`
4. Выберите видимость: **Private** или **Public**
5. НЕ ставьте галочку "Initialize repository with a README"
6. Нажмите **Create project**

## Шаг 2: Добавьте GitLab remote и загрузите код

```bash
# Перейдите в директорию проекта
cd ~/Desktop/AI-Calendar-Project

# Добавьте GitLab remote (замените YOUR_USERNAME на ваше имя пользователя)
git remote add gitlab https://gitlab.com/YOUR_USERNAME/ai-calendar-assistant.git

# Загрузите код
git push -u gitlab main
```

## Шаг 3: Настройте CI/CD переменные

В GitLab перейдите в **Settings** → **CI/CD** → **Variables** и добавьте:

### Обязательные переменные:

| Variable | Value | Masked | Protected |
|----------|-------|--------|-----------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather | ✅ | ✅ |
| `YANDEX_GPT_API_KEY` | Ваш Yandex GPT API ключ | ✅ | ✅ |
| `YANDEX_GPT_FOLDER_ID` | Ваш Yandex Folder ID | ❌ | ✅ |
| `DB_PASSWORD` | Пароль для БД | ✅ | ✅ |

### Для деплоя на сервер:

| Variable | Value | Masked | Protected |
|----------|-------|--------|-----------|
| `SSH_PRIVATE_KEY` | Приватный SSH ключ | ✅ | ✅ |
| `DEPLOY_SERVER` | 91.229.8.221 (или ваш IP) | ❌ | ✅ |
| `DEPLOY_USER` | root | ❌ | ✅ |

### Для GitLab Container Registry:

| Variable | Value | Masked | Protected |
|----------|-------|--------|-----------|
| `CI_REGISTRY_USER` | Ваш GitLab username | ❌ | ✅ |
| `CI_REGISTRY_PASSWORD` | Personal Access Token | ✅ | ✅ |

## Шаг 4: Создайте Personal Access Token

1. В GitLab перейдите в **User Settings** → **Access Tokens**
2. Создайте новый токен с правами:
   - `read_registry`
   - `write_registry`
3. Скопируйте токен и добавьте как `CI_REGISTRY_PASSWORD`

## Шаг 5: Настройте SSH ключ для деплоя

```bash
# Создайте SSH ключ
ssh-keygen -t ed25519 -C "gitlab-ci" -f ~/.ssh/gitlab_deploy

# Покажите приватный ключ (добавьте в GitLab как SSH_PRIVATE_KEY)
cat ~/.ssh/gitlab_deploy

# Покажите публичный ключ (добавьте на сервер)
cat ~/.ssh/gitlab_deploy.pub
```

На вашем сервере:
```bash
ssh root@91.229.8.221
mkdir -p ~/.ssh
echo "ПУБЛИЧНЫЙ_КЛЮЧ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## Шаг 6: Запустите Pipeline

1. После push кода, pipeline запустится автоматически
2. Откройте **CI/CD** → **Pipelines**
3. Дождитесь прохождения стадий `test` и `build`
4. Для деплоя нажмите кнопку **Play** (▶️) на стадии `deploy_production`

## Шаг 7: Проверьте деплой

```bash
# Подключитесь к серверу
ssh root@91.229.8.221

# Проверьте статус контейнеров
cd /root/ai-calendar-assistant
docker-compose ps

# Просмотрите логи
docker-compose logs -f calendar-assistant
```

## Шаг 8: Настройте Telegram Webhook

```bash
# Выполните на сервере или локально
python3 << 'EOF'
import requests

BOT_TOKEN = "ВАШ_ТОКЕН"
WEBHOOK_URL = "https://ваш-домен.com/webhook/telegram"
WEBHOOK_SECRET = "ВАШ_СЕКРЕТ"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
data = {"url": WEBHOOK_URL, "secret_token": WEBHOOK_SECRET}

response = requests.post(url, json=data)
print(response.json())
EOF
```

## Готово!

Ваш AI Calendar Assistant развернут и работает!

**Полезные команды:**

```bash
# Перезапуск сервисов
docker-compose restart

# Просмотр логов
docker-compose logs -f

# Обновление кода
git pull
docker-compose up -d --build

# Очистка старых образов
docker image prune -af
```

## Troubleshooting

Если что-то пошло не так, смотрите подробную инструкцию в [GITLAB_DEPLOYMENT.md](GITLAB_DEPLOYMENT.md)

---

**Поддержка:** Создавайте Issues в GitLab репозитории
