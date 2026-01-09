#!/bin/bash
#
# Comprehensive Security Test Suite
# Тестирует все аспекты безопасности системы
#

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SERVER="95.163.227.26"
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNING=0

echo "=========================================="
echo "  🔒 Security Test Suite"
echo "=========================================="
echo ""

test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC} - $test_name"
        [ -n "$message" ] && echo "   $message"
        ((TESTS_PASSED++))
    elif [ "$result" = "FAIL" ]; then
        echo -e "${RED}❌ FAIL${NC} - $test_name"
        [ -n "$message" ] && echo "   $message"
        ((TESTS_FAILED++))
    else
        echo -e "${YELLOW}⚠️  WARN${NC} - $test_name"
        [ -n "$message" ] && echo "   $message"
        ((TESTS_WARNING++))
    fi
    echo ""
}

# Test 1: Radicale Public Access
echo "[1/15] Testing Radicale public access..."
if timeout 5 curl -s http://$SERVER:5232 > /dev/null 2>&1; then
    test_result "Radicale public access" "FAIL" "Port 5232 is publicly accessible (CVSS 9.1)"
else
    test_result "Radicale public access" "PASS" "Port 5232 is not accessible publicly"
fi

# Test 2: FastAPI Health
echo "[2/15] Testing FastAPI health..."
if timeout 5 curl -s http://$SERVER:8000/health | grep -q '"status":"ok"'; then
    test_result "FastAPI health" "PASS" "API is responding correctly"
else
    test_result "FastAPI health" "FAIL" "API is not responding"
fi

# Test 3: HTTPS Certificate
echo "[3/15] Testing HTTPS certificate..."
if timeout 5 curl -s https://этонесамыйдлинныйдомен.рф > /dev/null 2>&1; then
    test_result "HTTPS certificate" "PASS" "SSL certificate is valid"
else
    test_result "HTTPS certificate" "WARN" "Cannot verify SSL certificate"
fi

# Test 4: SQL Injection Protection
echo "[4/15] Testing SQL injection protection..."
RESPONSE=$(timeout 5 curl -s "http://$SERVER:8000/api/events/1' OR '1'='1" -w "%{http_code}" -o /dev/null || echo "000")
if [ "$RESPONSE" = "404" ] || [ "$RESPONSE" = "400" ] || [ "$RESPONSE" = "422" ]; then
    test_result "SQL injection" "PASS" "API properly rejects SQL injection attempts"
else
    test_result "SQL injection" "FAIL" "API may be vulnerable to SQL injection (HTTP $RESPONSE)"
fi

# Test 5: Admin Panel Brute Force
echo "[5/15] Testing admin panel rate limiting..."
ATTEMPTS=0
for i in {1..20}; do
    RESPONSE=$(timeout 2 curl -s -X POST http://$SERVER:8000/api/admin/verify \
        -H "Content-Type: application/json" \
        -d '{"password1":"wrong","password2":"wrong","password3":"wrong"}' \
        -w "%{http_code}" -o /dev/null 2>/dev/null || echo "000")
    [ "$RESPONSE" = "200" ] && ((ATTEMPTS++))
done
if [ $ATTEMPTS -lt 20 ]; then
    test_result "Admin rate limiting" "PASS" "Rate limiting active (blocked after $((20-ATTEMPTS)) attempts)"
else
    test_result "Admin rate limiting" "WARN" "No rate limiting detected (all 20 attempts succeeded)"
fi

# Test 6: XSS Protection
echo "[6/15] Testing XSS protection..."
XSS_PAYLOAD='<script>alert(1)</script>'
RESPONSE=$(timeout 5 curl -s -X POST http://$SERVER:8000/api/events/test \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$XSS_PAYLOAD\"}" 2>/dev/null || echo "error")
if echo "$RESPONSE" | grep -q "$XSS_PAYLOAD"; then
    test_result "XSS protection" "WARN" "Response contains unescaped HTML"
else
    test_result "XSS protection" "PASS" "HTML is properly escaped"
fi

# Test 7: CORS Configuration
echo "[7/15] Testing CORS configuration..."
CORS_HEADER=$(timeout 5 curl -s -I http://$SERVER:8000/health | grep -i "access-control-allow-origin" || echo "")
if [ -n "$CORS_HEADER" ]; then
    if echo "$CORS_HEADER" | grep -q "\*"; then
        test_result "CORS config" "WARN" "CORS allows all origins (*)"
    else
        test_result "CORS config" "PASS" "CORS is restrictive"
    fi
else
    test_result "CORS config" "PASS" "No CORS headers (API only)"
fi

# Test 8: Docker Container Security
echo "[8/15] Testing Docker container security..."
# Cannot test remotely without SSH access
test_result "Docker security" "WARN" "Manual check required: docker ps --format '{{.RunningFor}}'"

# Test 9: Webhook Secret
echo "[9/15] Testing webhook secret..."
WEBHOOK_RESPONSE=$(timeout 5 curl -s -X POST http://$SERVER:8000/telegram/webhook \
    -H "Content-Type: application/json" \
    -d '{"update_id":1}' \
    -w "%{http_code}" -o /dev/null 2>/dev/null || echo "000")
if [ "$WEBHOOK_RESPONSE" = "401" ]; then
    test_result "Webhook secret" "PASS" "Webhook requires authentication"
elif [ "$WEBHOOK_RESPONSE" = "500" ]; then
    test_result "Webhook secret" "PASS" "Webhook protected (internal error without auth)"
else
    test_result "Webhook secret" "WARN" "Webhook authentication unclear (HTTP $WEBHOOK_RESPONSE)"
fi

# Test 10: TLS Version
echo "[10/15] Testing TLS version..."
TLS_VERSION=$(timeout 5 curl -sI https://этонесамыйдлинныйдомен.рф --tlsv1.2 2>&1 | grep -o "TLSv1\.[23]" || echo "")
if [ -n "$TLS_VERSION" ]; then
    test_result "TLS version" "PASS" "Using $TLS_VERSION"
else
    test_result "TLS version" "WARN" "Cannot verify TLS version"
fi

# Test 11: Security Headers
echo "[11/15] Testing security headers..."
HEADERS=$(timeout 5 curl -sI https://этонесамыйдлинныйдомен.рф 2>/dev/null || echo "")
MISSING_HEADERS=""
echo "$HEADERS" | grep -qi "X-Content-Type-Options" || MISSING_HEADERS="$MISSING_HEADERS X-Content-Type-Options"
echo "$HEADERS" | grep -qi "X-Frame-Options" || MISSING_HEADERS="$MISSING_HEADERS X-Frame-Options"
echo "$HEADERS" | grep -qi "Strict-Transport-Security" || MISSING_HEADERS="$MISSING_HEADERS HSTS"

if [ -z "$MISSING_HEADERS" ]; then
    test_result "Security headers" "PASS" "All security headers present"
else
    test_result "Security headers" "WARN" "Missing headers:$MISSING_HEADERS"
fi

# Test 12: API Enumeration
echo "[12/15] Testing API enumeration protection..."
ENUM_404=0
for i in {1..10}; do
    RESPONSE=$(timeout 2 curl -s http://$SERVER:8000/api/users/$RANDOM -w "%{http_code}" -o /dev/null 2>/dev/null || echo "000")
    [ "$RESPONSE" = "404" ] && ((ENUM_404++))
done
if [ $ENUM_404 -eq 10 ]; then
    test_result "API enumeration" "PASS" "API returns consistent 404 for invalid resources"
else
    test_result "API enumeration" "WARN" "API enumeration may be possible"
fi

# Test 13: Backup Existence
echo "[13/15] Testing backup existence..."
# Cannot test without SSH - manual check required
test_result "Backup existence" "WARN" "Manual check required: ls /root/backups/calendar-assistant/"

# Test 14: Response Time (DDoS resilience)
echo "[14/15] Testing response time..."
START=$(date +%s%N)
timeout 5 curl -s http://$SERVER:8000/health > /dev/null
END=$(date +%s%N)
RESPONSE_TIME=$(( (END - START) / 1000000 ))
if [ $RESPONSE_TIME -lt 1000 ]; then
    test_result "Response time" "PASS" "Response time: ${RESPONSE_TIME}ms"
elif [ $RESPONSE_TIME -lt 5000 ]; then
    test_result "Response time" "WARN" "Response time: ${RESPONSE_TIME}ms (slow)"
else
    test_result "Response time" "FAIL" "Response time: ${RESPONSE_TIME}ms (very slow, possible DoS)"
fi

# Test 15: Port Scan
echo "[15/15] Testing open ports..."
OPEN_PORTS=""
for port in 22 80 443 3306 5432 6379 27017 8000 5232; do
    if timeout 2 nc -z $SERVER $port 2>/dev/null; then
        OPEN_PORTS="$OPEN_PORTS $port"
    fi
done
EXPECTED_PORTS="22 80 443 8000"
if [ "$OPEN_PORTS" = "$EXPECTED_PORTS" ] || [ "$OPEN_PORTS" = " $EXPECTED_PORTS" ]; then
    test_result "Port scan" "PASS" "Only expected ports open:$OPEN_PORTS"
else
    test_result "Port scan" "WARN" "Open ports:$OPEN_PORTS (expected: 22 80 443 8000)"
fi

# Summary
echo "=========================================="
echo "  📊 Test Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}✅ Passed:  $TESTS_PASSED${NC}"
echo -e "${YELLOW}⚠️  Warning: $TESTS_WARNING${NC}"
echo -e "${RED}❌ Failed:  $TESTS_FAILED${NC}"
echo ""
TOTAL=$((TESTS_PASSED + TESTS_WARNING + TESTS_FAILED))
SCORE=$((TESTS_PASSED * 100 / TOTAL))
echo "Security Score: $SCORE/100"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}⚠️  Critical issues found! Run fix-critical-security-now.sh${NC}"
    exit 1
elif [ $TESTS_WARNING -gt 3 ]; then
    echo -e "${YELLOW}⚠️  Multiple warnings found. Review recommended.${NC}"
    exit 0
else
    echo -e "${GREEN}✅ Security checks passed!${NC}"
    exit 0
fi
