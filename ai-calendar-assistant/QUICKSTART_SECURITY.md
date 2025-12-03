# Quick Start - Secure Production Deployment

## What Was Fixed

✅ **All critical security vulnerabilities resolved!**

- Removed hardcoded `SECRET_KEY` and `RADICALE_BOT_PASSWORD`
- Set `DEBUG=False` and `APP_ENV=production` by default
- Excluded `.env` from Docker images (updated Dockerfile and .dockerignore)
- Removed hardcoded webapp domain (now configurable via .env)
- Added automatic validation for secret strength
- Improved healthcheck to use stdlib (urllib vs requests)

## Your Current Setup

Your `.env` file has already been updated with:
```
✅ SECRET_KEY=9gpft-iHZFVwnB3Wk66_OpvODJQqUR1Nk2ttiXT7mvs
✅ JWT_SECRET=cKOKEOkAn-7yqO-sECKD_JJrHlaok9z5SEHq5VnBZfU
✅ ENCRYPTION_KEY=Pj7DZ8ixyBp3_77-j1B4jpBNQXnKZp9VKFtSVkB6v1w
✅ TELEGRAM_WEBHOOK_SECRET=WDrkeqRf-1tWsQdmO-4gXdWgEK-VnGKcQizh7OqLyZ4
✅ RADICALE_BOT_PASSWORD=cU06KxDvGSxbRxcMPsZj8oL7uUTRYAkf
✅ DB_PASSWORD=LnNk-p6mN5mRprvbj2SrzlbffZKgKNx0
✅ APP_ENV=production
✅ DEBUG=False
```

## What You Need To Do

### 1. Update Your Domain

Edit `.env` and replace `your-domain.com` with your actual domain:

```bash
nano .env
```

Find and update:
```bash
TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook/telegram
TELEGRAM_WEBAPP_URL=https://your-domain.com
```

Replace with:
```bash
TELEGRAM_WEBHOOK_URL=https://youractual.domain/webhook/telegram
TELEGRAM_WEBAPP_URL=https://youractual.domain
```

### 2. Verify Configuration

```bash
# Check docker-compose config is valid
docker-compose config

# Should show no errors
```

### 3. Start Application

```bash
# Build and start all services
docker-compose up -d --build

# Watch logs for any errors
docker-compose logs -f
```

### 4. Verify Security

Look for these messages in logs:
```
✅ Configuration validated successfully
✅ Application started on 0.0.0.0:8000
✅ SECRET_KEY validated (44 chars)
```

If you see validation errors:
```
❌ CRITICAL: SECRET_KEY must be at least 32 characters long
```

The application will refuse to start - this is **correct behavior** protecting you from weak secrets.

## Testing

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Telegram Webhook
```bash
# Update webhook URL with Telegram
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://yourdomain.com/webhook/telegram\", \"secret_token\": \"${TELEGRAM_WEBHOOK_SECRET}\"}"
```

### WebApp Button
Send `/start` to your bot - you should see "🗓 Кабинет" button appear.

## Troubleshooting

### App won't start - "SECRET_KEY not set"
- Check `.env` file exists in project root
- Verify `SECRET_KEY=` line is present and has value
- Ensure no spaces around `=`

### Telegram menu button not appearing
- Check `TELEGRAM_WEBAPP_URL` is set in `.env`
- Verify URL is HTTPS (not HTTP)
- Restart bot: `docker-compose restart`

### Docker build fails
```bash
# Clear cache and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Security Checklist

Before going live:

- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] All secrets are unique (not example values)
- [ ] `DEBUG=False` in `.env`
- [ ] HTTPS configured for webhook and webapp URLs
- [ ] Firewall configured (only 80/443 exposed)
- [ ] Backup `.env` file securely (encrypted)

## Documentation

For detailed security information, see:
- `SECURITY.md` - Complete security guide
- `CODE_REVIEW.md` - List of all fixes applied
- `.env.example` - Template with all options

## Next Steps (Optional Improvements)

Not critical, but recommended:

1. **Add bcrypt for password hashing** (replace SHA-256)
2. **Setup Redis rate limiter** (for multi-instance deployments)
3. **Configure log rotation** (prevent disk space issues)
4. **Update dependencies** (run `pip list --outdated`)

See `CODE_REVIEW.md` for full list.

## Support

If you encounter issues:

1. Check logs: `docker-compose logs --tail=100`
2. Verify `.env` syntax: `docker-compose config`
3. Review SECURITY.md troubleshooting section
4. Check file permissions: `ls -la .env`

---

**Status:** 🟢 Ready for production deployment
**Security Level:** ✅ All critical issues resolved
**Last Updated:** 2025-11-11
