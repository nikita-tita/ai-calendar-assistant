#!/bin/bash
#
# AI Calendar Assistant - Automated Smoke Test
# Runs twice daily (10:00 and 17:00) via cron
# Sends results to Telegram bot @dogovorarenda_bot
#
# Usage: ./smoke_test.sh
# Cron:  0 10,17 * * * /path/to/smoke_test.sh
#

set -e

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN="***REMOVED***"
# Chat ID will be detected on first message or set manually
TELEGRAM_CHAT_ID="${SMOKE_TEST_CHAT_ID:-}"

# API endpoints
API_BASE_URL="https://calendar.housler.ru"
HEALTH_URL="${API_BASE_URL}/health"
WEBAPP_URL="${API_BASE_URL}/app"
STATIC_URL="${API_BASE_URL}/static/index.html"
EVENTS_API_URL="${API_BASE_URL}/api/events"
TODOS_API_URL="${API_BASE_URL}/api/todos"

# Server SSH
SSH_KEY="$HOME/.ssh/id_housler"
SSH_HOST="root@91.229.8.221"

# Test results
PASSED=0
FAILED=0
WARNINGS=0
REPORT=""

# ===== FUNCTIONS =====

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

add_result() {
    local status=$1
    local test_name=$2
    local details=$3

    if [[ "$status" == "PASS" ]]; then
        REPORT+="✅ $test_name"
        ((PASSED++))
    elif [[ "$status" == "FAIL" ]]; then
        REPORT+="❌ $test_name"
        ((FAILED++))
    else
        REPORT+="⚠️ $test_name"
        ((WARNINGS++))
    fi

    if [[ -n "$details" ]]; then
        REPORT+=" — $details"
    fi
    REPORT+=$'\n'
}

send_telegram() {
    local message=$1
    local parse_mode=${2:-"HTML"}

    if [[ -z "$TELEGRAM_CHAT_ID" ]]; then
        log "ERROR: TELEGRAM_CHAT_ID not set. Set SMOKE_TEST_CHAT_ID environment variable."
        log "To get your chat ID, send any message to the bot and check:"
        log "curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
        return 1
    fi

    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "text=${message}" \
        -d "parse_mode=${parse_mode}" \
        > /dev/null 2>&1
}

# ===== TESTS =====

test_health_endpoint() {
    log "Testing health endpoint..."

    local body
    local http_code

    body=$(curl -s --connect-timeout 10 "$HEALTH_URL" 2>/dev/null)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$HEALTH_URL" 2>/dev/null)

    if [[ "$http_code" == "200" ]] && [[ "$body" == *"ok"* ]]; then
        add_result "PASS" "Health endpoint" "HTTP 200"
        return 0
    else
        add_result "FAIL" "Health endpoint" "HTTP $http_code"
        return 1
    fi
}

test_webapp_endpoint() {
    log "Testing WebApp endpoint..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$WEBAPP_URL" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        add_result "PASS" "WebApp endpoint" "HTTP 200"
        return 0
    else
        add_result "FAIL" "WebApp endpoint" "HTTP $http_code"
        return 1
    fi
}

test_static_files() {
    log "Testing static files..."

    local response
    local version

    response=$(curl -s --connect-timeout 10 "$STATIC_URL" 2>/dev/null)

    if [[ -z "$response" ]]; then
        add_result "FAIL" "Static files" "No response"
        return 1
    fi

    version=$(echo "$response" | grep -o "APP_VERSION = '[^']*'" | head -1 | cut -d"'" -f2)

    if [[ -n "$version" ]]; then
        add_result "PASS" "Static files" "v$version"
        return 0
    else
        add_result "WARN" "Static files" "Version not found"
        return 0
    fi
}

test_api_events_auth() {
    log "Testing API events authentication..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$EVENTS_API_URL" 2>/dev/null)

    # Without auth, should return 401, 403, or 404 (middleware blocks)
    if [[ "$http_code" == "401" ]] || [[ "$http_code" == "403" ]] || [[ "$http_code" == "404" ]]; then
        add_result "PASS" "Events API auth" "Protected (HTTP $http_code)"
        return 0
    elif [[ "$http_code" == "200" ]]; then
        add_result "FAIL" "Events API auth" "NOT PROTECTED!"
        return 1
    else
        add_result "WARN" "Events API auth" "HTTP $http_code"
        return 0
    fi
}

test_api_todos_auth() {
    log "Testing API todos authentication..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$TODOS_API_URL" 2>/dev/null)

    if [[ "$http_code" == "401" ]] || [[ "$http_code" == "403" ]] || [[ "$http_code" == "404" ]]; then
        add_result "PASS" "Todos API auth" "Protected (HTTP $http_code)"
        return 0
    elif [[ "$http_code" == "200" ]]; then
        add_result "FAIL" "Todos API auth" "NOT PROTECTED!"
        return 1
    else
        add_result "WARN" "Todos API auth" "HTTP $http_code"
        return 0
    fi
}

test_ssl_certificate() {
    log "Testing SSL certificate..."

    local expiry
    expiry=$(echo | openssl s_client -servername calendar.housler.ru -connect calendar.housler.ru:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)

    if [[ -z "$expiry" ]]; then
        add_result "WARN" "SSL certificate" "Could not check"
        return 0
    fi

    local expiry_epoch
    local now_epoch
    local days_left

    expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry" "+%s" 2>/dev/null || date -d "$expiry" "+%s" 2>/dev/null)
    now_epoch=$(date "+%s")
    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if [[ $days_left -lt 7 ]]; then
        add_result "FAIL" "SSL certificate" "Expires in $days_left days!"
        return 1
    elif [[ $days_left -lt 30 ]]; then
        add_result "WARN" "SSL certificate" "Expires in $days_left days"
        return 0
    else
        add_result "PASS" "SSL certificate" "Valid ($days_left days)"
        return 0
    fi
}

test_docker_containers() {
    log "Testing Docker containers..."

    if [[ ! -f "$SSH_KEY" ]]; then
        add_result "WARN" "Docker containers" "SSH key not found"
        return 0
    fi

    local containers
    containers=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
        'docker ps --format "{{.Names}}:{{.Status}}" 2>/dev/null | grep -E "(telegram-bot|calendar-redis|radicale-calendar)"' 2>/dev/null)

    if [[ -z "$containers" ]]; then
        add_result "FAIL" "Docker containers" "Cannot connect or no containers"
        return 1
    fi

    local healthy_count=0
    local total_count=0

    while IFS= read -r line; do
        ((total_count++))
        if [[ "$line" == *"healthy"* ]]; then
            ((healthy_count++))
        fi
    done <<< "$containers"

    if [[ $healthy_count -eq 3 ]]; then
        add_result "PASS" "Docker containers" "3/3 healthy"
        return 0
    elif [[ $healthy_count -gt 0 ]]; then
        add_result "WARN" "Docker containers" "$healthy_count/3 healthy"
        return 0
    else
        add_result "FAIL" "Docker containers" "0/3 healthy"
        return 1
    fi
}

test_recent_errors() {
    log "Testing for recent errors..."

    if [[ ! -f "$SSH_KEY" ]]; then
        add_result "WARN" "Recent errors" "SSH key not found"
        return 0
    fi

    local error_count
    error_count=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
        'docker logs telegram-bot --since 6h 2>&1 | grep -ciE "error|exception|traceback" || echo 0' 2>/dev/null | tr -d '[:space:]' | head -1)

    if [[ -z "$error_count" ]] || [[ "$error_count" == "" ]]; then
        add_result "WARN" "Recent errors" "Cannot check logs"
        return 0
    fi

    # Ensure it's a number
    error_count=$(echo "$error_count" | grep -oE '^[0-9]+' | head -1)
    if [[ -z "$error_count" ]]; then
        error_count=0
    fi

    if [[ "$error_count" -eq 0 ]]; then
        add_result "PASS" "Recent errors" "No errors (6h)"
        return 0
    elif [[ "$error_count" -lt 10 ]]; then
        add_result "WARN" "Recent errors" "$error_count errors (6h)"
        return 0
    else
        add_result "FAIL" "Recent errors" "$error_count errors (6h)"
        return 1
    fi
}

test_calendar_events_count() {
    log "Testing calendar events count..."

    if [[ ! -f "$SSH_KEY" ]]; then
        add_result "WARN" "Calendar events" "SSH key not found"
        return 0
    fi

    local count
    count=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
        'docker exec radicale-calendar find /data -name "*.ics" 2>/dev/null | wc -l' 2>/dev/null)

    if [[ -z "$count" ]] || [[ "$count" == "" ]]; then
        add_result "WARN" "Calendar events" "Cannot count"
        return 0
    fi

    count=$(echo "$count" | tr -d '[:space:]')

    if [[ "$count" -gt 0 ]]; then
        add_result "PASS" "Calendar events" "$count events"
        return 0
    else
        add_result "WARN" "Calendar events" "0 events"
        return 0
    fi
}

test_response_time() {
    log "Testing response time..."

    local time_total
    time_total=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 10 "$HEALTH_URL" 2>/dev/null)

    if [[ -z "$time_total" ]]; then
        add_result "WARN" "Response time" "Cannot measure"
        return 0
    fi

    # Convert to milliseconds
    local ms
    ms=$(echo "$time_total * 1000" | bc 2>/dev/null | cut -d. -f1)

    if [[ -z "$ms" ]]; then
        add_result "WARN" "Response time" "${time_total}s"
        return 0
    fi

    if [[ "$ms" -lt 500 ]]; then
        add_result "PASS" "Response time" "${ms}ms"
        return 0
    elif [[ "$ms" -lt 2000 ]]; then
        add_result "WARN" "Response time" "${ms}ms (slow)"
        return 0
    else
        add_result "FAIL" "Response time" "${ms}ms (very slow)"
        return 1
    fi
}

# ===== MAIN =====

main() {
    local start_time
    start_time=$(date '+%Y-%m-%d %H:%M:%S')

    log "Starting Smoke Test..."
    log "API Base URL: $API_BASE_URL"

    # Run all tests
    test_health_endpoint || true
    test_webapp_endpoint || true
    test_static_files || true
    test_api_events_auth || true
    test_api_todos_auth || true
    test_ssl_certificate || true
    test_response_time || true
    test_docker_containers || true
    test_recent_errors || true
    test_calendar_events_count || true

    # Build final report
    local total=$((PASSED + FAILED + WARNINGS))
    local status_emoji
    local status_text

    if [[ $FAILED -eq 0 ]]; then
        if [[ $WARNINGS -eq 0 ]]; then
            status_emoji="✅"
            status_text="ALL TESTS PASSED"
        else
            status_emoji="⚠️"
            status_text="PASSED WITH WARNINGS"
        fi
    else
        status_emoji="🔴"
        status_text="TESTS FAILED"
    fi

    local final_report="<b>${status_emoji} AI Calendar Assistant</b>
<b>${status_text}</b>

<b>📊 Results:</b> ✅${PASSED} ❌${FAILED} ⚠️${WARNINGS}

<b>🔍 Details:</b>
${REPORT}
<b>🕐 Time:</b> ${start_time}
<b>🌐 URL:</b> ${API_BASE_URL}"

    # Print to console
    echo ""
    echo "=========================================="
    echo "  SMOKE TEST RESULTS"
    echo "=========================================="
    echo ""
    echo "Status: $status_text"
    echo "Passed: $PASSED"
    echo "Failed: $FAILED"
    echo "Warnings: $WARNINGS"
    echo ""
    echo "$REPORT"
    echo "=========================================="

    # Send to Telegram
    if [[ -n "$TELEGRAM_CHAT_ID" ]]; then
        log "Sending report to Telegram..."
        send_telegram "$final_report" "HTML"
        log "Report sent!"
    else
        log "TELEGRAM_CHAT_ID not set. Report not sent to Telegram."
        log "Set environment variable: export SMOKE_TEST_CHAT_ID=your_chat_id"
        log "Get chat ID: curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates"
    fi

    # Exit with appropriate code
    if [[ $FAILED -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main "$@"
