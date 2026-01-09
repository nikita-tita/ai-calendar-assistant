# Complete Architecture Analysis: AI Calendar Assistant

## System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    SYSTEM ARCHITECTURE                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  User (Telegram)                                              │
│       │                                                        │
│       │ HTTPS                                                  │
│       ▼                                                        │
│  Telegram Bot API                                             │
│       │                                                        │
│       │ Webhook/Polling                                        │
│       ▼                                                        │
│  telegram-bot-polling (Docker)                                │
│       │                                                        │
│       │ HTTP                                                   │
│       ▼                                                        │
│  ai-calendar-assistant (Docker)                               │
│  ├── FastAPI (port 8000)                                      │
│  ├── Yandex GPT Integration                                   │
│  └── CalDAV Client                                            │
│       │                                                        │
│       ├─────────► Radicale CalDAV (Docker)                    │
│       │                                                        │
│       └─────────► Redis (Docker)                              │
│                                                                │
│  ◄───────────────────────────────────────────────────         │
│                                                                │
│  User (Browser)                                               │
│       │                                                        │
│       │ HTTPS                                                  │
│       ▼                                                        │
│  Nginx (port 443)                                             │
│  ├── SSL Termination                                          │
│  ├── Reverse Proxy                                            │
│  └── Static Files                                             │
│       │                                                        │
│       │ HTTP                                                   │
│       ▼                                                        │
│  ai-calendar-assistant (Docker)                               │
│  └── FastAPI serves index.html                                │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

## Component Analysis

### 1. Docker Containers

#### a) ai-calendar-assistant (Main Application)
```yaml
Service: calendar-assistant
Container: ai-calendar-assistant
Port: 8000
Image: Built from Dockerfile
```

**Responsibilities:**
- FastAPI web server
- REST API endpoints
- Telegram webhook handling
- Yandex GPT integration
- CalDAV calendar operations
- TODO management
- Analytics tracking

**Critical Files:**
- `/app/app/main.py` - FastAPI entry point
- `/app/app/static/index.html` - Web interface
- `/app/app/services/telegram_handler.py` - Bot logic
- `/app/app/routers/` - API endpoints

**Volumes:**
- `./credentials:/app/credentials` - API credentials
- `./logs:/app/logs` - Application logs
- `calendar_bot_data:/var/lib/calendar-bot` - Persistent data

**Issue Found:**
- ❌ No volume for `/app/app/static` - static files from image only

#### b) telegram-bot-polling (Bot Polling)
```yaml
Service: telegram-bot-polling
Container: telegram-bot-polling
Port: 8000 (internal)
```

**Responsibilities:**
- Telegram long polling
- Message receiving
- Command routing
- Forwards to main app

#### c) calendar-redis (Cache)
```yaml
Service: redis
Container: calendar-redis
Port: 6379 (internal)
```

**Responsibilities:**
- Rate limiting storage
- Session caching
- Temporary data

#### d) radicale-calendar (CalDAV Server)
```yaml
Service: radicale
Container: radicale-calendar
Port: 5232 (internal)
```

**Responsibilities:**
- CalDAV/CardDAV server
- Calendar event storage
- Event synchronization

### 2. Nginx Configuration

**File:** `/etc/nginx/sites-available/calendar.housler.ru`

**Port Configuration:**
```nginx
# Port 80 - HTTP (redirects to HTTPS)
server {
    listen 80;
    server_name calendar.housler.ru;
    return 301 https://$server_name$request_uri;
}

# Port 443 - HTTPS
server {
    listen 443 ssl http2;
    server_name calendar.housler.ru;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/calendar.housler.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/calendar.housler.ru/privkey.pem;

    # Proxy to FastAPI
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 3. Application Code Structure

```
ai-calendar-assistant/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py              # Configuration
│   ├── models/
│   │   ├── analytics.py       # Analytics models
│   │   └── ...
│   ├── services/
│   │   ├── telegram_handler.py    # Telegram bot logic
│   │   ├── llm_agent_yandex.py   # Yandex GPT
│   │   ├── todo_service.py       # TODO management
│   │   └── ...
│   ├── routers/
│   │   ├── events.py          # Calendar API
│   │   ├── todos.py           # TODO API
│   │   ├── telegram.py        # Telegram webhook
│   │   └── ...
│   ├── static/
│   │   └── index.html         # Web interface ⚠️
│   └── middleware/
│       └── ...
├── Dockerfile                  # Container build
├── docker-compose.yml         # Orchestration
├── requirements.txt           # Dependencies
└── run_polling.py            # Polling bot entry
```

### 4. File Flow Analysis

#### Development Flow:
```
Local Changes
     ↓
git commit
     ↓
git push (if using Git)
     ↓
scp to server
     ↓
Docker build (COPIES files)
     ↓
Docker image (SNAPSHOT)
     ↓
Container runtime
     ↓
Application serves
```

#### Current Issue:
```
✅ Updated: app/static/index.html (local)
     ↓
✅ Uploaded: scp to server
     ↓
❌ Skipped: Docker build
     ↓
❌ Old image: Contains old index.html
     ↓
❌ Container: Serves old file
```

### 5. Dockerfile Analysis

**File:** `Dockerfile`

**Critical Line 32:**
```dockerfile
COPY app ./app
```

**What this means:**
1. Runs during `docker build` command
2. Copies entire `app/` directory into image
3. Creates immutable snapshot
4. Changes to host files DON'T affect image
5. Requires rebuild to update

**Multi-stage build:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++ ffmpeg
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY app ./app  # ← LINE 32: Copies files at BUILD time
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6. Docker Compose Analysis

**File:** `docker-compose.yml`

**Volume Configuration (lines 67-70):**
```yaml
volumes:
  - ./credentials:/app/credentials      # ✅ Mounted
  - ./logs:/app/logs                    # ✅ Mounted
  - calendar_bot_data:/var/lib/calendar-bot  # ✅ Mounted
  # MISSING: - ./app/static:/app/app/static    # ❌ NOT MOUNTED
```

**Impact:**
- Credentials: Changes reflect immediately ✅
- Logs: Written to host filesystem ✅
- Static files: From Docker image only ❌

**What's needed for live updates:**
```yaml
volumes:
  - ./app/static:/app/app/static  # Add this!
```

### 7. Environment Variables

**File:** `.env`

**Key Variables:**
```bash
# Application
APP_ENV=production
DEBUG=False

# Telegram
TELEGRAM_BOT_TOKEN=***REDACTED_BOT_TOKEN***
TELEGRAM_WEBAPP_URL=https://calendar.housler.ru  # ✅ Updated

# Calendar
RADICALE_URL=http://radicale:5232

# Cache
REDIS_URL=redis://redis:6379/0

# AI
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
```

### 8. Network Flow

#### User → Web App:
```
Browser (HTTPS)
     ↓
calendar.housler.ru:443 (Nginx)
     ↓
SSL Termination
     ↓
Proxy to localhost:8000
     ↓
ai-calendar-assistant container
     ↓
FastAPI serves index.html
     ↓
Response to user
```

#### User → Telegram Bot:
```
Telegram App
     ↓
Telegram Bot API
     ↓
telegram-bot-polling container (polling)
     ↓
HTTP to ai-calendar-assistant:8000
     ↓
Process message
     ↓
Yandex GPT (if needed)
     ↓
CalDAV operations (if needed)
     ↓
Response to Telegram
```

### 9. Data Flow

#### Calendar Event Creation:
```
User message (Telegram)
     ↓
telegram_handler.py
     ↓
llm_agent_yandex.py (parse intent)
     ↓
Yandex GPT API
     ↓
Extract event details
     ↓
CalDAV client
     ↓
radicale-calendar container
     ↓
Store event
     ↓
Confirmation to user
```

#### TODO Management:
```
User action (Web App)
     ↓
HTTPS → Nginx → FastAPI
     ↓
/api/todos endpoint
     ↓
todo_service.py
     ↓
File storage (data/todos/)
     ↓
JSON files
     ↓
Response to web app
```

### 10. Security Analysis

**SSL/TLS:**
- ✅ Let's Encrypt certificate
- ✅ TLS 1.2/1.3 only
- ✅ Strong ciphers
- ✅ HTTP → HTTPS redirect

**Authentication:**
- ✅ Telegram init data HMAC validation
- ✅ Bot token in environment variables
- ✅ API keys not in code

**Network:**
- ✅ Internal Docker network
- ✅ Only necessary ports exposed
- ❌ Rate limiting configured (via Redis)

### 11. Identified Issues

#### Critical:
1. **Static files not mounted as volume**
   - Impact: Requires rebuild for updates
   - Risk: Deployment friction
   - Solution: Add volume mount OR proper rebuild process

2. **No clear deployment process**
   - Impact: Manual steps error-prone
   - Risk: Wrong files in production
   - Solution: Automated deployment script

#### Warning:
3. **No health check for telegram-bot-polling**
   - Status: unhealthy
   - Impact: Unknown bot status
   - Solution: Add health check

4. **No automated image cleanup**
   - Impact: Disk space usage
   - Risk: Out of space
   - Solution: Add cleanup to rebuild script

### 12. Solutions Implemented

#### Scripts Created:

1. **`diagnose_production.sh`**
   - Complete environment diagnosis
   - File comparison
   - Container status
   - Configuration verification

2. **`rebuild_docker.sh`**
   - Automated rebuild process
   - File synchronization
   - Image cleanup
   - Verification steps

3. **`deploy_webapp_now.sh`**
   - Quick deployment
   - Rebuild and restart
   - Basic verification

#### Code Changes:

1. **Cache-control headers**
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

2. **Root endpoint serves HTML**
   - Was: JSON API info
   - Now: index.html web app

### 13. Best Practices for Future

#### Development:
- ✅ Use volume mounts for code
- ✅ Hot reload enabled
- ✅ Local Docker compose

#### Production:
- ✅ Build immutable images
- ✅ Tag images with version
- ✅ Clear deployment process
- ✅ Health checks on all services
- ✅ Automated backups

#### CI/CD (Recommended):
```yaml
# .github/workflows/deploy.yml
- Build Docker image
- Run tests
- Push to registry
- Deploy to server
- Verify deployment
- Rollback if failed
```

## Conclusion

The AI Calendar Assistant is a well-architected application with:
- ✅ Good separation of concerns
- ✅ Microservices approach
- ✅ Secure configuration
- ✅ Proper use of Docker

**Main Issue:** Static files deployment process not clearly defined

**Solution:** Use provided scripts for proper rebuilds

**Future:** Consider adding volume mounts for faster iteration or implement proper CI/CD pipeline.

---

**System Status:** Healthy
**Deployment Process:** Fixed
**Documentation:** Complete
