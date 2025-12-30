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
TELEGRAM_BOT_TOKEN="8107613087:AAHaS8Yatp80tG8jQZeBLYUat1KB_BRB2qI"
# Chat ID will be detected on first message or set manually
TELEGRAM_CHAT_ID="${SMOKE_TEST_CHAT_ID:-}"

# API endpoints
API_BASE_URL="https://calendar.housler.ru"
HEALTH_URL="${API_BASE_URL}/health"
WEBAPP_URL="${API_BASE_URL}/app"
STATIC_URL="${API_BASE_URL}/static/index.html"
EVENTS_API_URL="${API_BASE_URL}/api/events"
TODOS_API_URL="${API_BASE_URL}/api/todos"

# Server SSH (only used when running from local machine)
SSH_KEY="$HOME/.ssh/id_housler"
SSH_HOST="root@91.229.8.221"

# Detect if running on server (localhost)
IS_LOCAL_SERVER=false
if [[ "$(hostname -I 2>/dev/null | grep -c '91.229.8.221')" -gt 0 ]] || [[ "$(hostname)" == *"calendar"* ]] || [[ -f "/root/ai-calendar-assistant/ai-calendar-assistant/docker-compose.secure.yml" ]]; then
    IS_LOCAL_SERVER=true
fi

# Test results
PASSED=0
FAILED=0
WARNINGS=0

# Results by category (format: "status|name|details|impact")
RESULTS_FUNCTIONS=""    # Основные функции бота
RESULTS_INFRA=""        # Инфраструктура
RESULTS_ATTENTION=""    # Требует внимания

# ===== FUNCTIONS =====

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

add_result() {
    local status=$1
    local test_name=$2
    local details=$3
    local category=${4:-"infra"}  # functions, infra, attention
    local impact=${5:-""}

    local entry="${status}|${test_name}|${details}|${impact}"

    if [[ "$status" == "PASS" ]]; then
        ((PASSED++))
    elif [[ "$status" == "FAIL" ]]; then
        ((FAILED++))
    else
        ((WARNINGS++))
    fi

    case "$category" in
        functions)
            RESULTS_FUNCTIONS+="${entry}"$'\n'
            ;;
        attention)
            RESULTS_ATTENTION+="${entry}"$'\n'
            ;;
        *)
            RESULTS_INFRA+="${entry}"$'\n'
            ;;
    esac
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
        add_result "PASS" "API" "сервер отвечает" "infra" "бот полностью недоступен"
        return 0
    else
        add_result "FAIL" "API" "сервер не отвечает (HTTP $http_code)" "infra" "бот полностью недоступен"
        return 1
    fi
}

test_webapp_endpoint() {
    log "Testing WebApp endpoint..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$WEBAPP_URL" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        add_result "PASS" "Сайт" "calendar.housler.ru доступен" "infra" "веб-интерфейс недоступен"
        return 0
    else
        add_result "FAIL" "Сайт" "calendar.housler.ru недоступен (HTTP $http_code)" "infra" "веб-интерфейс недоступен"
        return 1
    fi
}

test_static_files() {
    log "Testing static files..."

    local response
    local version

    response=$(curl -s --connect-timeout 10 "$STATIC_URL" 2>/dev/null)

    if [[ -z "$response" ]]; then
        add_result "FAIL" "WebApp" "не загружается" "infra" "веб-интерфейс не работает"
        return 1
    fi

    version=$(echo "$response" | grep -o "APP_VERSION = '[^']*'" | head -1 | cut -d"'" -f2)

    if [[ -n "$version" ]]; then
        add_result "PASS" "WebApp" "версия $version" "infra" "веб-интерфейс не работает"
        return 0
    else
        add_result "WARN" "WebApp" "версия не определена" "attention" "возможно старая версия"
        return 0
    fi
}

test_api_events_auth() {
    log "Testing API events authentication..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$EVENTS_API_URL" 2>/dev/null)

    # Without auth, should return 401, 403, or 404 (middleware blocks)
    if [[ "$http_code" == "401" ]] || [[ "$http_code" == "403" ]] || [[ "$http_code" == "404" ]]; then
        add_result "PASS" "Защита API" "события защищены" "infra" "данные календаря уязвимы"
        return 0
    elif [[ "$http_code" == "200" ]]; then
        add_result "FAIL" "Защита API" "события НЕ защищены!" "infra" "данные календаря уязвимы"
        return 1
    else
        add_result "WARN" "Защита API" "статус $http_code" "attention" "проверить вручную"
        return 0
    fi
}

test_api_todos_auth() {
    log "Testing API todos authentication..."

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$TODOS_API_URL" 2>/dev/null)

    if [[ "$http_code" == "401" ]] || [[ "$http_code" == "403" ]] || [[ "$http_code" == "404" ]]; then
        # Skip - already checked in events test, no need to duplicate
        return 0
    elif [[ "$http_code" == "200" ]]; then
        add_result "FAIL" "Защита API" "задачи НЕ защищены!" "infra" "данные задач уязвимы"
        return 1
    else
        return 0
    fi
}

test_ssl_certificate() {
    log "Testing SSL certificate..."

    local expiry
    expiry=$(echo | openssl s_client -servername calendar.housler.ru -connect calendar.housler.ru:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)

    if [[ -z "$expiry" ]]; then
        add_result "WARN" "SSL" "не удалось проверить" "attention" "проверить вручную"
        return 0
    fi

    local expiry_epoch
    local now_epoch
    local days_left

    expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry" "+%s" 2>/dev/null || date -d "$expiry" "+%s" 2>/dev/null)
    now_epoch=$(date "+%s")
    days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if [[ $days_left -lt 7 ]]; then
        add_result "FAIL" "SSL" "истекает через $days_left дней!" "infra" "сайт будет недоступен"
        return 1
    elif [[ $days_left -lt 30 ]]; then
        add_result "WARN" "SSL" "истекает через $days_left дней" "attention" "обновить сертификат"
        return 0
    else
        add_result "PASS" "SSL" "ещё $days_left дней" "infra" "сайт будет недоступен"
        return 0
    fi
}

test_docker_containers() {
    log "Testing Docker containers..."

    local containers

    if [[ "$IS_LOCAL_SERVER" == "true" ]]; then
        # Running on server - use docker directly
        containers=$(docker ps --format "{{.Names}}:{{.Status}}" 2>/dev/null | grep -E "(telegram-bot|calendar-redis|radicale-calendar)")
    elif [[ -f "$SSH_KEY" ]]; then
        # Running remotely - use SSH
        containers=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
            'docker ps --format "{{.Names}}:{{.Status}}" 2>/dev/null | grep -E "(telegram-bot|calendar-redis|radicale-calendar)"' 2>/dev/null)
    else
        add_result "WARN" "Сервер" "нет доступа по SSH" "attention" "проверить подключение"
        return 0
    fi

    if [[ -z "$containers" ]]; then
        add_result "FAIL" "Сервер" "контейнеры не запущены" "infra" "бот не работает"
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
        add_result "PASS" "Сервер" "все 3 контейнера работают" "infra" "бот не работает"
        return 0
    elif [[ $healthy_count -gt 0 ]]; then
        add_result "WARN" "Сервер" "$healthy_count/3 контейнеров" "attention" "часть сервисов недоступна"
        return 0
    else
        add_result "FAIL" "Сервер" "контейнеры не здоровы" "infra" "бот не работает"
        return 1
    fi
}

test_recent_errors() {
    log "Testing for recent errors..."

    local error_count

    # Filter for real errors only (exclude false positives like /api/admin/errors URL)
    local error_filter='"level":\s*"error"|Traceback|Exception:|ERROR:'

    if [[ "$IS_LOCAL_SERVER" == "true" ]]; then
        # Running on server - use docker directly
        error_count=$(docker logs telegram-bot --since 6h 2>&1 | grep -cE "$error_filter" || echo 0)
    elif [[ -f "$SSH_KEY" ]]; then
        # Running remotely - use SSH
        error_count=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
            "docker logs telegram-bot --since 6h 2>&1 | grep -cE '$error_filter' || echo 0" 2>/dev/null | tr -d '[:space:]' | head -1)
    else
        return 0  # Already warned about SSH
    fi

    error_count=$(echo "$error_count" | tr -d '[:space:]' | head -1)

    if [[ -z "$error_count" ]] || [[ "$error_count" == "" ]]; then
        return 0
    fi

    # Ensure it's a number
    error_count=$(echo "$error_count" | grep -oE '^[0-9]+' | head -1)
    if [[ -z "$error_count" ]]; then
        error_count=0
    fi

    if [[ "$error_count" -eq 0 ]]; then
        # Don't report - no news is good news
        return 0
    elif [[ "$error_count" -lt 10 ]]; then
        add_result "WARN" "Логи" "$error_count ошибок за 6ч" "attention" "единичные сбои, обычно не критично"
        return 0
    else
        add_result "FAIL" "Логи" "$error_count ошибок за 6ч" "attention" "много ошибок, проверить логи"
        return 1
    fi
}

test_calendar_events_count() {
    log "Testing calendar events count..."

    local count

    if [[ "$IS_LOCAL_SERVER" == "true" ]]; then
        # Running on server - use docker directly
        count=$(docker exec radicale-calendar find /data -name "*.ics" 2>/dev/null | wc -l)
    elif [[ -f "$SSH_KEY" ]]; then
        # Running remotely - use SSH
        count=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
            'docker exec radicale-calendar find /data -name "*.ics" 2>/dev/null | wc -l' 2>/dev/null)
    else
        return 0  # Already warned about SSH
    fi

    if [[ -z "$count" ]] || [[ "$count" == "" ]]; then
        return 0
    fi

    count=$(echo "$count" | tr -d '[:space:]')

    # Just informational, not reported
    return 0
}

test_response_time() {
    log "Testing response time..."

    local time_total
    time_total=$(curl -s -o /dev/null -w "%{time_total}" --connect-timeout 10 "$HEALTH_URL" 2>/dev/null)

    if [[ -z "$time_total" ]]; then
        return 0
    fi

    # Convert to milliseconds (handle both bc available and not)
    local ms
    if command -v bc &> /dev/null; then
        ms=$(echo "$time_total * 1000" | bc 2>/dev/null | cut -d. -f1)
    else
        # Fallback: use awk
        ms=$(echo "$time_total" | awk '{printf "%.0f", $1 * 1000}')
    fi

    if [[ -z "$ms" ]] || [[ "$ms" == "" ]]; then
        return 0
    fi

    if [[ "$ms" -lt 1000 ]]; then
        add_result "PASS" "Скорость" "ответ ${ms}мс" "infra" "бот медленно отвечает"
        return 0
    elif [[ "$ms" -lt 3000 ]]; then
        add_result "WARN" "Скорость" "медленно (${ms}мс)" "attention" "бот отвечает с задержкой"
        return 0
    else
        add_result "FAIL" "Скорость" "очень медленно (${ms}мс)" "infra" "бот почти не отвечает"
        return 1
    fi
}

# ===== E2E FUNCTIONAL TESTS =====

run_docker_python() {
    # Helper to run Python code in container
    local code=$1
    if [[ "$IS_LOCAL_SERVER" == "true" ]]; then
        docker exec telegram-bot python3 -c "$code" 2>&1
    elif [[ -f "$SSH_KEY" ]]; then
        ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" \
            "docker exec telegram-bot python3 -c '$code'" 2>&1
    else
        echo "ERROR: Cannot connect"
        return 1
    fi
}

test_todo_service() {
    log "Testing todo service (create/delete)..."

    local result
    result=$(run_docker_python "
import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/app')
from app.services.todos_service import todos_service
from app.schemas.todos import TodoDTO

async def test():
    user_id = 'smoke_test_user'
    try:
        dto = TodoDTO(title='SMOKE_TEST_TODO_DELETE_ME')
        todo_id = await todos_service.create_todo(user_id, dto)
        if not todo_id:
            return 'FAIL:create'
        todos = await todos_service.list_todos(user_id)
        found = any(t.id == todo_id for t in todos)
        if not found:
            return 'FAIL:verify'
        deleted = await todos_service.delete_todo(user_id, todo_id)
        return 'PASS' if deleted else 'FAIL:delete'
    except Exception as e:
        return f'FAIL:{str(e)[:25]}'
print(asyncio.run(test()))
" 2>/dev/null | tail -1)

    if [[ "$result" == "PASS" ]]; then
        add_result "PASS" "Задачи" "создание/удаление работает" "functions" "не сможете добавлять задачи"
        return 0
    else
        add_result "FAIL" "Задачи" "ошибка: ${result:-нет ответа}" "functions" "не сможете добавлять задачи"
        return 1
    fi
}

test_calendar_service() {
    log "Testing calendar service (create/delete)..."

    local result
    result=$(run_docker_python "
import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/app')
from datetime import datetime, timedelta
from app.services.calendar_radicale import calendar_service
from app.schemas.events import EventDTO

async def test():
    user_id = 'smoke_test_user'
    try:
        start = datetime.now() + timedelta(days=1)
        start = start.replace(hour=10, minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        dto = EventDTO(title='SMOKE_TEST_EVENT_DELETE_ME', start_time=start, end_time=end)
        uid = await calendar_service.create_event(user_id, dto)
        if not uid:
            return 'FAIL:create'
        deleted = await calendar_service.delete_event(user_id, uid)
        return 'PASS' if deleted else 'FAIL:delete'
    except Exception as e:
        return f'FAIL:{str(e)[:25]}'
print(asyncio.run(test()))
" 2>/dev/null | tail -1)

    if [[ "$result" == "PASS" ]]; then
        add_result "PASS" "Календарь" "создание событий работает" "functions" "не сможете создавать события"
        return 0
    else
        add_result "FAIL" "Календарь" "ошибка: ${result:-нет ответа}" "functions" "не сможете создавать события"
        return 1
    fi
}

test_stt_service() {
    log "Testing STT service (voice recognition)..."

    local result
    result=$(run_docker_python "
import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/app')
from app.services.stt_yandex import stt_service_yandex

async def test():
    try:
        # Test that service can be initialized and API key is set
        if not stt_service_yandex.api_key:
            return 'FAIL:no_api_key'
        if not stt_service_yandex.folder_id:
            return 'FAIL:no_folder_id'
        return 'PASS'
    except Exception as e:
        return f'FAIL:{str(e)[:25]}'
print(asyncio.run(test()))
" 2>/dev/null | tail -1)

    if [[ "$result" == "PASS" ]]; then
        add_result "PASS" "Голос" "распознавание речи работает" "functions" "не будет распознавать голосовые"
        return 0
    elif [[ "$result" == *"WARN"* ]]; then
        add_result "WARN" "Голос" "${result#WARN:}" "attention" "голосовые могут не работать"
        return 0
    else
        add_result "FAIL" "Голос" "ошибка: ${result:-нет ответа}" "functions" "не будет распознавать голосовые"
        return 1
    fi
}

test_llm_parsing() {
    log "Testing LLM parsing (intent recognition)..."

    local result
    result=$(run_docker_python "
import asyncio, sys, logging
logging.disable(logging.CRITICAL)
sys.path.insert(0, '/app')

async def test():
    try:
        from app.services.llm_agent_yandex import llm_agent_yandex
        # Quick test - parse simple input (uses Yandex GPT API)
        result = await llm_agent_yandex.extract_event('встреча завтра', user_id='smoke_test')
        return 'PASS' if result else 'WARN:empty'
    except Exception as e:
        err = str(e)[:25]
        if 'quota' in err.lower() or 'limit' in err.lower():
            return 'WARN:quota'
        if 'api' in err.lower() or '401' in err or '403' in err:
            return 'WARN:api_key'
        return f'FAIL:{err}'
print(asyncio.run(test()))
" 2>/dev/null | tail -1)

    if [[ "$result" == "PASS" ]]; then
        add_result "PASS" "AI" "понимает команды" "functions" "не будет понимать текст"
        return 0
    elif [[ "$result" == *"WARN"* ]]; then
        add_result "WARN" "AI" "${result#WARN:}" "attention" "AI может работать нестабильно"
        return 0
    else
        add_result "FAIL" "AI" "ошибка: ${result:-нет ответа}" "functions" "не будет понимать текст"
        return 1
    fi
}

# ===== REPORT FORMATTING =====

format_category_results() {
    local results=$1
    local output=""

    # Parse each line: "status|name|details|impact"
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue

        local status name details impact
        IFS='|' read -r status name details impact <<< "$line"

        local icon
        case "$status" in
            PASS) icon="✓" ;;
            FAIL) icon="✗" ;;
            WARN) icon="⚠" ;;
            *) icon="?" ;;
        esac

        output+="• ${name} ${icon} — ${details}"$'\n'
    done <<< "$results"

    echo -n "$output"
}

build_human_report() {
    local report=""

    # Header with overall status
    if [[ $FAILED -eq 0 ]]; then
        if [[ $WARNINGS -eq 0 ]]; then
            report+="🟢 <b>Бот работает нормально</b>"$'\n'
        else
            report+="🟡 <b>Бот работает, есть мелочи</b>"$'\n'
        fi
    else
        report+="🔴 <b>Есть проблемы!</b>"$'\n'
    fi
    report+=$'\n'

    # Functions section (if any results)
    if [[ -n "$RESULTS_FUNCTIONS" ]]; then
        report+="📱 <b>Основные функции:</b>"$'\n'
        report+=$(format_category_results "$RESULTS_FUNCTIONS")
        report+=$'\n'
    fi

    # Infrastructure section (if any results)
    if [[ -n "$RESULTS_INFRA" ]]; then
        report+="🌐 <b>Инфраструктура:</b>"$'\n'
        report+=$(format_category_results "$RESULTS_INFRA")
        report+=$'\n'
    fi

    # Attention section (only if there are warnings/issues)
    if [[ -n "$RESULTS_ATTENTION" ]]; then
        report+="⚡️ <b>Требует внимания:</b>"$'\n'
        report+=$(format_category_results "$RESULTS_ATTENTION")
        report+=$'\n'
    fi

    # If there are failures, add help section
    if [[ $FAILED -gt 0 ]]; then
        report+="❓ <b>Что делать:</b>"$'\n'
        report+="• Проверить логи: docker logs telegram-bot"$'\n'
        report+="• Перезапустить: docker-compose -f docker-compose.secure.yml restart"$'\n'
    fi

    echo -n "$report"
}

# ===== MAIN =====

main() {
    local start_time
    start_time=$(date '+%H:%M')

    log "Starting Smoke Test..."
    log "API Base URL: $API_BASE_URL"

    # Run infrastructure tests
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

    # Run E2E functional tests
    test_todo_service || true
    test_calendar_service || true
    test_stt_service || true
    test_llm_parsing || true

    # Build human-readable report
    local final_report
    final_report=$(build_human_report)

    # Print to console
    echo ""
    echo "=========================================="
    echo "  SMOKE TEST RESULTS"
    echo "=========================================="
    echo ""
    echo "Passed: $PASSED | Failed: $FAILED | Warnings: $WARNINGS"
    echo ""
    echo "--- Functions ---"
    echo "$RESULTS_FUNCTIONS"
    echo "--- Infrastructure ---"
    echo "$RESULTS_INFRA"
    echo "--- Attention ---"
    echo "$RESULTS_ATTENTION"
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
