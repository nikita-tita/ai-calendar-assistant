# Restore Instructions

## Quick Restore from Local Backup

### 1. Restore from Local Backup Directory
```bash
# Copy files back to project
cp backups/working-state-20251030-185404/*.py app/services/
cp backups/working-state-20251030-185404/datetime_parser.py app/utils/
```

### 2. Deploy to Server
```bash
# Copy to server
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/services/telegram_handler.py \
  app/services/llm_agent_yandex.py \
  app/services/calendar_radicale.py \
  app/services/daily_reminders.py \
  app/services/user_preferences.py \
  root@95.163.227.26:/root/ai-calendar-assistant/app/services/

sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  app/utils/datetime_parser.py \
  root@95.163.227.26:/root/ai-calendar-assistant/app/utils/

# Deploy to container and restart
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 "\
  docker cp /root/ai-calendar-assistant/app/services/telegram_handler.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/llm_agent_yandex.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/calendar_radicale.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/daily_reminders.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/services/user_preferences.py telegram-bot-polling:/app/app/services/ && \
  docker cp /root/ai-calendar-assistant/app/utils/datetime_parser.py telegram-bot-polling:/app/app/utils/ && \
  docker restart telegram-bot-polling"
```

## Restore from Git

```bash
# Reset to this commit
git reset --hard 6a05189

# Or checkout specific commit
git checkout 6a05189

# Then deploy as above
```

## Restore from Server Backup

```bash
# Extract server backup
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  root@95.163.227.26:/root/backups/working-state-20251030-190733.tar.gz \
  ./restore-backup.tar.gz

tar -xzf restore-backup.tar.gz

# Deploy extracted files (same commands as above)
```

## Restore from Container Backup

```bash
# Download container backup
sshpass -p '$SERVER_PASSWORD' scp -o StrictHostKeyChecking=no \
  root@95.163.227.26:/root/backups/container-working-state-20251030-190733.tar.gz \
  ./container-backup.tar.gz

# Extract on server and copy to container
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 "\
  cd /tmp && \
  tar -xzf /root/backups/container-working-state-20251030-190733.tar.gz && \
  docker cp /tmp/app/services/telegram_handler.py telegram-bot-polling:/app/app/services/ && \
  docker cp /tmp/app/services/llm_agent_yandex.py telegram-bot-polling:/app/app/services/ && \
  docker cp /tmp/app/services/calendar_radicale.py telegram-bot-polling:/app/app/services/ && \
  docker cp /tmp/app/services/daily_reminders.py telegram-bot-polling:/app/app/services/ && \
  docker cp /tmp/app/services/user_preferences.py telegram-bot-polling:/app/app/services/ && \
  docker cp /tmp/app/utils/datetime_parser.py telegram-bot-polling:/app/app/utils/ && \
  docker restart telegram-bot-polling"
```

## Verify Restoration

```bash
# Check bot is running
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 "\
  docker ps | grep telegram-bot-polling && \
  docker logs --tail 20 telegram-bot-polling"

# Test in Telegram:
# 1. Press "🛠 Сервисы" button
# 2. Check all 5 service buttons work
# 3. Test "🏢 Подбор новостроек" button
# 4. Create an event and verify time display
```

## Backup Locations

1. **Local**: `backups/working-state-20251030-185404/`
2. **Server Files**: `/root/backups/working-state-20251030-190733/`
3. **Server Archive**: `/root/backups/working-state-20251030-190733.tar.gz`
4. **Container Archive**: `/root/backups/container-working-state-20251030-190733.tar.gz`
5. **Git Commit**: `6a05189`

## Emergency Rollback

If something breaks and you need immediate rollback:

```bash
# Option 1: Use git (fastest for local dev)
git reset --hard 6a05189

# Option 2: Copy from local backup (fastest for local files)
cp backups/working-state-20251030-185404/*.py app/services/
cp backups/working-state-20251030-185404/datetime_parser.py app/utils/

# Option 3: Restore container from backup (fastest for production)
sshpass -p '$SERVER_PASSWORD' ssh -o StrictHostKeyChecking=no root@95.163.227.26 "\
  cd /tmp && tar -xzf /root/backups/container-working-state-20251030-190733.tar.gz && \
  docker cp /tmp/app telegram-bot-polling:/app/ && \
  docker restart telegram-bot-polling"
```
