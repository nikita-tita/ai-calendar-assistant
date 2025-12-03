# 🚀 Manual Deployment Instructions - Security Fixes

## Quick Commands (Copy & Paste)

### Option 1: One Command (Recommended)

```bash
ssh root@91.229.8.221
# Password: upvzrr3LH4pxsaqs
```

Then paste this entire block:

```bash
cd /root/ai-calendar-assistant && \
echo "📦 Pulling latest code..." && \
git fetch origin && \
git checkout main && \
git pull origin main && \
echo "" && \
echo "🔧 Checking .env configuration..." && \
if ! grep -q "TELEGRAM_WEBAPP_URL" .env; then
  echo "TELEGRAM_WEBAPP_URL=https://calendar-webapp-beige.vercel.app" >> .env
fi && \
echo "" && \
echo "🐳 Rebuilding containers..." && \
docker-compose down && \
docker-compose build --no-cache telegram-bot-polling && \
docker-compose up -d && \
echo "" && \
echo "⏳ Waiting for containers to start..." && \
sleep 5 && \
echo "" && \
echo "📊 Container Status:" && \
docker-compose ps && \
echo "" && \
echo "📋 Recent Logs:" && \
docker-compose logs --tail=30 telegram-bot-polling && \
echo "" && \
echo "✅ Deployment complete!"
```

### Option 2: Step by Step

If you prefer to run commands one by one:

```bash
# 1. Connect to server
ssh root@91.229.8.221
# Password: upvzrr3LH4pxsaqs

# 2. Navigate to project
cd /root/ai-calendar-assistant

# 3. Pull latest code
git fetch origin
git checkout main
git pull origin main

# 4. Add TELEGRAM_WEBAPP_URL if missing
if ! grep -q "TELEGRAM_WEBAPP_URL" .env; then
  echo "TELEGRAM_WEBAPP_URL=https://calendar-webapp-beige.vercel.app" >> .env
fi

# 5. Stop containers
docker-compose down

# 6. Rebuild with latest code
docker-compose build --no-cache telegram-bot-polling

# 7. Start containers
docker-compose up -d

# 8. Check status
docker-compose ps

# 9. View logs
docker-compose logs -f telegram-bot-polling
```

## What Will Be Deployed

### Security Fixes
- ✅ Removed hardcoded SECRET_KEY
- ✅ Removed hardcoded RADICALE_BOT_PASSWORD
- ✅ Set DEBUG=False by default
- ✅ Excluded .env from Docker images
- ✅ Added secret validation (min 32 chars)
- ✅ Removed hardcoded webapp domain

### Modified Files
- `app/config.py` - Security validators
- `app/services/telegram_handler.py` - Configurable webapp URL
- `Dockerfile` - No .env COPY
- `.dockerignore` - Exclude .env

### New Documentation
- `SECURITY.md` - Complete security guide
- `CODE_REVIEW.md` - Detailed review
- `QUICKSTART_SECURITY.md` - Quick reference

## Verification Steps

After deployment, verify:

```bash
# 1. Check container is running
docker-compose ps
# Should show: telegram-bot-polling | Up

# 2. Check for validation errors
docker-compose logs telegram-bot-polling | grep "CRITICAL"
# Should return nothing (no critical errors)

# 3. Check for successful startup
docker-compose logs telegram-bot-polling | grep "Configuration validated"
# Should show: "✅ Configuration validated successfully"

# 4. Test bot
# Send /start to your Telegram bot
# You should see "🗓 Кабинет" menu button
```

## Troubleshooting

### Issue: "CRITICAL: SECRET_KEY must be at least 32 characters"

**Solution:**
```bash
cd /root/ai-calendar-assistant

# Generate new SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Copy the output and update .env
nano .env
# Replace old SECRET_KEY with new one

# Restart
docker-compose restart telegram-bot-polling
```

### Issue: "CRITICAL: RADICALE_BOT_PASSWORD is not set"

**Solution:**
```bash
cd /root/ai-calendar-assistant

# Generate password
python3 -c "import secrets; print('RADICALE_BOT_PASSWORD=' + secrets.token_urlsafe(24))"

# Update .env
nano .env
# Add the RADICALE_BOT_PASSWORD line

# Restart
docker-compose restart telegram-bot-polling
```

### Issue: Container keeps restarting

**Solution:**
```bash
# Check full logs
docker-compose logs --tail=100 telegram-bot-polling

# If .env related, verify all required fields:
cat .env | grep -E "(SECRET_KEY|RADICALE_BOT_PASSWORD|TELEGRAM_BOT_TOKEN)"
```

### Issue: "Permission denied" when pulling code

**Solution:**
```bash
# Reset git permissions
cd /root/ai-calendar-assistant
git config --global --add safe.directory /root/ai-calendar-assistant
git pull origin main
```

## Monitoring

### Watch Logs Live
```bash
docker-compose logs -f telegram-bot-polling
```

### Check Resource Usage
```bash
docker stats
```

### Verify Health
```bash
docker inspect telegram-bot-polling | grep -A10 Health
```

## Rollback (if needed)

If something goes wrong:

```bash
cd /root/ai-calendar-assistant

# 1. Checkout previous commit
git log --oneline -5
# Find the commit hash before security fixes

# 2. Checkout that commit
git checkout <previous-commit-hash>

# 3. Rebuild and restart
docker-compose down
docker-compose up -d --build

# 4. Check logs
docker-compose logs -f telegram-bot-polling
```

## Success Indicators

You'll know deployment succeeded when:

1. ✅ Container status shows "Up" (not "Restarting")
2. ✅ Logs show "Configuration validated successfully"
3. ✅ No "CRITICAL" errors in logs
4. ✅ Bot responds to /start command
5. ✅ "🗓 Кабинет" menu button appears

## Next Steps

After successful deployment:

1. **Test the bot**
   - Send /start
   - Try adding an event
   - Check calendar interface

2. **Monitor for 24 hours**
   - Check logs periodically
   - Watch for errors
   - Monitor resource usage

3. **Update secrets on schedule**
   - Rotate SECRET_KEY every 90 days
   - Update API keys as needed
   - See SECURITY.md for details

## Support

If you encounter issues:

1. Check logs: `docker-compose logs telegram-bot-polling`
2. Review SECURITY.md troubleshooting section
3. Verify .env has all required fields
4. Check disk space: `df -h`
5. Check memory: `free -h`

---

**Deploy Date:** 2025-11-11
**Branch:** main
**Security Rating:** 🟢 Production Ready
