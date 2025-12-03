# 🔐 Security Guide

## Generating Secure Secrets

Before deploying to production, you **MUST** generate secure secrets for all sensitive environment variables.

### Quick Setup

Run this command to generate all required secrets:

```bash
cd ai-calendar-assistant

# Generate secrets and save to .env
cat > .env << 'EOF'
# Copy from .env.example and replace placeholders below

# Generate SECRET_KEY (32+ characters)
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Generate Radicale password
RADICALE_BOT_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(24))")

# Generate DB password
DB_PASSWORD=$(python -c "import secrets; print(secrets.token_urlsafe(24))")

# Generate other secrets
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
EOF
```

Or generate them manually:

```bash
# SECRET_KEY (minimum 32 characters)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# RADICALE_BOT_PASSWORD
python -c "import secrets; print('RADICALE_BOT_PASSWORD=' + secrets.token_urlsafe(24))"

# DB_PASSWORD
python -c "import secrets; print('DB_PASSWORD=' + secrets.token_urlsafe(24))"

# JWT_SECRET
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))"

# ENCRYPTION_KEY
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(32))"
```

## Security Checklist

Before deploying to production, verify:

### Critical

- [ ] `SECRET_KEY` is set to a unique value (minimum 32 characters)
- [ ] `RADICALE_BOT_PASSWORD` is set (no default password used)
- [ ] `DB_PASSWORD` is set to a strong password
- [ ] `DEBUG=False` in production
- [ ] `.env` file is NOT committed to git (check `.gitignore`)
- [ ] `.env` is NOT copied to Docker image (check `Dockerfile`)

### Important

- [ ] `CORS_ORIGINS` is set to your actual domain(s)
- [ ] `TELEGRAM_WEBAPP_URL` is set to your webapp URL
- [ ] HTTPS is configured (use Let's Encrypt/Certbot)
- [ ] Firewall allows only ports 80, 443, 22
- [ ] Radicale is NOT exposed publicly (internal Docker network only)
- [ ] PostgreSQL is NOT exposed publicly (internal Docker network only)

### Recommended

- [ ] Sentry DSN is configured for error tracking
- [ ] Backups are automated (calendar data)
- [ ] Logs are rotated (Docker logging config)
- [ ] Rate limits are tested
- [ ] Different secrets for dev/staging/production
- [ ] Admin passwords use bcrypt (not SHA-256)
- [ ] Redis is configured for rate limiter persistence

## Security Best Practices

### 1. Never Hardcode Secrets

❌ **Bad:**
```python
SECRET_KEY = "my-secret-key"
api_key = "1234567890abcdef"
```

✅ **Good:**
```python
from app.config import settings

SECRET_KEY = settings.secret_key
api_key = settings.yandex_gpt_api_key
```

### 2. Use Strong Passwords

Minimum requirements:
- `SECRET_KEY`: 32+ characters
- Database passwords: 24+ characters
- API keys: Use service-generated keys

### 3. Rotate Secrets Regularly

Schedule:
- Production secrets: Every 90 days
- Staging secrets: Every 180 days
- Development secrets: As needed

### 4. Separate Environments

Use different `.env` files for:
- `.env.development` (local development)
- `.env.staging` (staging server)
- `.env.production` (production server)

Never copy production secrets to development!

### 5. Secure Docker Images

Our Dockerfile:
- ✅ Does NOT copy `.env` file
- ✅ Uses multi-stage build
- ✅ Runs as non-root user (TODO)
- ✅ Has health checks

### 6. Network Isolation

Docker Compose setup:
- `internal` network: Radicale, PostgreSQL (not exposed)
- `external` network: calendar-assistant (exposed via port 8000)

### 7. Logging

- ✅ Use structured logging (structlog)
- ✅ Never log secrets or API keys
- ❌ Never log full request bodies (may contain tokens)
- ✅ Log authentication attempts (security audit)

## Vulnerability Reporting

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email: [your-security-email@example.com]
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours.

## Security Updates

Stay informed:
- Watch this repository for security advisories
- Subscribe to Python security mailing list
- Check for dependency updates weekly

Run security audit:
```bash
# Check for known vulnerabilities in dependencies
pip install safety
safety check -r requirements.txt

# Run bandit security scanner
pip install bandit
bandit -r app/ -f json -o security-report.json
```

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [Docker Security](https://docs.docker.com/engine/security/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Last updated:** 2025-11-10
**Version:** 1.0.0
