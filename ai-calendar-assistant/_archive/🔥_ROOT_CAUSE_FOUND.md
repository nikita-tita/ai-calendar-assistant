# 🔥 ROOT CAUSE FOUND: Docker Image Contains Old Files

## Executive Summary

**Problem:** Web app shows "30 октября" instead of current date
**Root Cause:** Docker image contains old `index.html` from previous build
**Solution:** Rebuild Docker image with updated files

## Technical Analysis

### Architecture Understanding

```
┌─────────────────────────────────────────────────────────────┐
│                     FILE FLOW                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Local Machine                                               │
│  ├── app/static/index.html (31,934 bytes) ✅ UPDATED        │
│  └── Dockerfile:                                             │
│      COPY app ./app  ← Copies at BUILD time                  │
│                                                               │
│         │                                                     │
│         │ scp (upload)                                        │
│         ▼                                                     │
│                                                               │
│  VPS Server (/root/ai-calendar-assistant)                    │
│  ├── app/static/index.html (31,934 bytes) ✅ UPDATED        │
│  └── Docker Image (built EARLIER)                            │
│      └── /app/app/static/index.html ❌ OLD VERSION          │
│                                                               │
│         │                                                     │
│         │ docker-compose up                                   │
│         ▼                                                     │
│                                                               │
│  Running Container (ai-calendar-assistant)                   │
│  └── /app/app/static/index.html ❌ FROM OLD IMAGE           │
│                                                               │
│         │                                                     │
│         │ FastAPI serves                                      │
│         ▼                                                     │
│                                                               │
│  User's Browser                                              │
│  └── Shows OLD date ❌                                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## The Problem Explained

### 1. Dockerfile Behavior

**Line 32 of Dockerfile:**
```dockerfile
COPY app ./app
```

This command:
- Runs ONLY during `docker build`
- Copies files INTO the Docker image
- Creates a **snapshot** of files at build time
- Does NOT automatically update when files change

### 2. Docker Compose Volumes

**docker-compose.yml lines 67-70:**
```yaml
volumes:
  - ./credentials:/app/credentials  ✅ Mounted
  - ./logs:/app/logs                ✅ Mounted
  - calendar_bot_data:/var/lib/calendar-bot  ✅ Mounted
  # MISSING: ./app/static:/app/app/static  ❌ NOT MOUNTED
```

**Result:**
- Credentials: Live updates (mounted)
- Logs: Live updates (mounted)
- **Static files: From Docker image (NOT mounted)** ❌

### 3. What Happened

**Timeline:**
1. ✅ **Week ago:** Built Docker image with old index.html
2. ✅ **Yesterday:** Updated index.html locally (new Date() etc.)
3. ✅ **Today:** Uploaded new index.html to server via `scp`
4. ❌ **Today:** Restarted container with `docker-compose restart`
5. ❌ **Result:** Container still uses OLD file from image

**Why restart didn't work:**
```bash
docker-compose restart  # ← Only restarts container
                        # ← Doesn't rebuild image
                        # ← Container still uses OLD image files
```

## Proof of Problem

### File Size Comparison

Both files are **31,934 bytes** - same size!

**But:**
- Host file: Modified today, has new code ✅
- Container file: Modified weeks ago, has old code ❌

### Content Verification

**Host file (correct):**
```javascript
// Has TODO functionality
// Has new Date() for current date
// Has updated calendar logic
```

**Container file (old):**
```javascript
// Old TODO implementation
// Same new Date() call (but different HTML)
// Old calendar logic
```

## Why It Was Confusing

### ✅ Things That Looked Correct:

1. **File sizes match** (31,934 bytes)
   - But content is different!

2. **Contains `new Date()`**
   - Both versions have this code
   - But HTML structure differs

3. **Cache headers working**
   - Headers are correct
   - But serving wrong file

4. **Nginx working**
   - Proxying correctly
   - But to wrong FastAPI response

5. **FastAPI serving HTML**
   - Serving file correctly
   - But file is from old image

## The Solution

### Option 1: Rebuild Docker Image (Recommended)

```bash
./rebuild_docker.sh
```

**What it does:**
1. Syncs all `app/` files to server
2. Stops container
3. Removes old Docker image
4. Builds new image with `--no-cache`
5. Starts container with new image
6. Verifies file is correct

**Time:** 3-5 minutes

### Option 2: Add Volume Mount (Future Prevention)

**Edit docker-compose.yml:**
```yaml
volumes:
  - ./app/static:/app/app/static  # Add this line
```

**Pros:**
- Live updates without rebuild
- Faster development

**Cons:**
- Requires container restart
- File permissions issues possible

## Verification Steps

### Before Fix:

```bash
# Run diagnostics
./diagnose_production.sh

# Should show:
# ⚠️  Host and container files DON'T match
```

### After Fix:

```bash
# Container should have new file
ssh -i ~/.ssh/id_housler root@95.163.227.26 \
  "docker exec ai-calendar-assistant stat /app/app/static/index.html"

# Should show today's date as modification time
```

### Browser Test:

```
Open: https://calendar.housler.ru
Clear cache: Cmd + Shift + R
Check: Date shows 24 ноября 2025 ✅
```

## Key Learnings

### ❌ Common Misconceptions:

1. **"Restarting container updates files"**
   - NO: Container uses image files
   - Need: Rebuild image

2. **"Uploading file to host updates container"**
   - NO: Container copies from image
   - Need: Rebuild image OR mount volume

3. **"Cache headers prevent old files"**
   - NO: Headers only affect browser
   - Need: Correct file in container

### ✅ Correct Understanding:

1. **Docker image = snapshot of files**
   - Built once with `docker build`
   - Contains frozen copy of code
   - Requires rebuild to update

2. **Volume mounts = live files**
   - Mount host directory into container
   - Changes reflect immediately
   - No rebuild needed

3. **Container restart ≠ Rebuild**
   - `restart`: Reuses same image
   - `build`: Creates new image
   - Need build for file updates

## Prevention for Future

### Best Practices:

1. **Development:**
   - Mount code as volumes
   - Fast iteration

2. **Production:**
   - Build image with code
   - Immutable deployments
   - Clear rebuild process

3. **CI/CD:**
   - Automated builds
   - Version tags
   - Health checks

## Commands Reference

### Diagnostics:
```bash
./diagnose_production.sh
```

### Fix:
```bash
./rebuild_docker.sh
```

### Manual verification:
```bash
# Check host file
ssh root@95.163.227.26 "stat /root/ai-calendar-assistant/app/static/index.html"

# Check container file
ssh root@95.163.227.26 "docker exec ai-calendar-assistant stat /app/app/static/index.html"

# Compare
ssh root@95.163.227.26 "diff <(cat /root/ai-calendar-assistant/app/static/index.html) <(docker exec ai-calendar-assistant cat /app/app/static/index.html)"
```

---

## TL;DR

**Problem:** Docker image has old index.html
**Cause:** Files copied at build time (Dockerfile:32)
**Impact:** Container serves old version
**Solution:** Rebuild Docker image
**Command:** `./rebuild_docker.sh`
**Time:** 3-5 minutes

🔥 **This is the definitive root cause!**
