# Web App Deployment Instructions

## Problem Description

**Issue:** Old web application showing on server
- Shows "30 октября" instead of current date
- TODO functionality not working
- Browser cache serving old version

**Root Cause:** Browser caching of static files

## Quick Solution

### Run Deployment Script

```bash
cd ~/Desktop/AI-Calendar-Project/ai-calendar-assistant
./deploy_webapp_now.sh
```

The script will:
1. ✅ Create backup of old version
2. ✅ Upload new `index.html` to server
3. ✅ Rebuild Docker container
4. ✅ Restart container with new version
5. ✅ Verify deployment

**Time:** ~2 minutes

## Clear Browser Cache

After deployment, you MUST clear browser cache:

### Chrome / Firefox / Edge
- **Windows:** `Ctrl + Shift + R` or `Ctrl + F5`
- **Mac:** `Cmd + Shift + R`

### Safari
- **Mac:** `Cmd + Option + R`
- Or: Safari → Clear History → All History

### Telegram WebApp
1. Close and reopen Telegram
2. Clear Telegram cache: Settings → Data and Storage → Clear Cache
3. Reopen bot and web app

## Verification Steps

1. **Open Web App**
   ```
   https://calendar.housler.ru
   ```

2. **Check Date**
   - Should show: **24 ноября 2025** (current date)
   - NOT: 30 октября 2025 (old date)

3. **Check TODO Tab**
   - Click "Дела" tab
   - Should show TODO list
   - Can add/complete/delete tasks

4. **Check Calendar Range**
   - Should show events from 90 days ago to 90 days forward
   - Total range: 180 days

## Technical Details

### What Was Fixed

1. **Cache-Control Headers Added**
   ```python
   return FileResponse(
       static_path,
       headers={
           "Cache-Control": "no-cache, no-store, must-revalidate",
           "Pragma": "no-cache",
           "Expires": "0"
       }
   )
   ```

2. **Container Rebuilt**
   - Old container had old code baked in
   - New container has latest `index.html` and `main.py`

3. **Deployment Process**
   - Upload → Build → Restart → Verify
   - Ensures all changes are applied

### File Locations

**Local:**
- `~/Desktop/AI-Calendar-Project/ai-calendar-assistant/app/static/index.html`

**Server (Host):**
- `/root/ai-calendar-assistant/app/static/index.html`

**Container:**
- `/app/app/static/index.html`

### Verify Deployment

```bash
# Check file on server
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "ls -lh /root/ai-calendar-assistant/app/static/index.html"

# Check file in container
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "docker exec ai-calendar-assistant ls -lh /app/app/static/index.html"

# Test web app response
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "curl -s http://localhost:8000/ | head -20"
```

## Troubleshooting

### Issue: Still shows old date

**Solution:**
1. Hard refresh: `Cmd + Shift + R`
2. Clear browser cache completely
3. Try incognito/private window
4. Try different browser

### Issue: TODO tab empty

**Check:**
1. Browser console for errors (F12)
2. Check API connection:
   ```bash
   curl -k https://calendar.housler.ru/api/health
   ```
3. Verify Telegram authentication

### Issue: Container not starting

**Check logs:**
```bash
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "docker logs ai-calendar-assistant --tail 50"
```

**Restart manually:**
```bash
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "cd /root/ai-calendar-assistant && docker-compose restart calendar-assistant"
```

## Rerun Deployment

If needed, you can rerun the deployment script multiple times:

```bash
./deploy_webapp_now.sh
```

It's safe to run multiple times - old versions are backed up.

## Backup Files

Each deployment creates a timestamped backup:
```
/root/ai-calendar-assistant/app/static/index.html.backup-20251124-225215
```

To restore from backup:
```bash
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "cd /root/ai-calendar-assistant && \
   cp app/static/index.html.backup-YYYYMMDD-HHMMSS app/static/index.html"
```

## Support

If issues persist:
1. Check Nginx logs: `/var/log/nginx/calendar.housler.ru.error.log`
2. Check application logs: `docker logs ai-calendar-assistant`
3. Verify SSL certificate: `https://www.ssllabs.com/ssltest/analyze.html?d=calendar.housler.ru`

---

**Last Updated:** 2025-11-24
**Deployment URL:** https://calendar.housler.ru
**Server IP:** 95.163.227.26
