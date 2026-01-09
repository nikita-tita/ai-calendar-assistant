#!/bin/bash
#
# КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ - НЕМЕДЛЕННОЕ ПРИМЕНЕНИЕ
#
# Этот скрипт исправляет 3 критические уязвимости:
# 1. Закрывает Radicale публичный порт (CVSS 9.1)
# 2. Исправляет права .env файла (CVSS 8.8)
# 3. Создает первый backup
#
# Время выполнения: ~5 минут
# Downtime: ~30 секунд

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${RED}=================================================="
echo "  ⚠️  КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ БЕЗОПАСНОСТИ"
echo "==================================================${NC}"
echo ""

SERVER="root@95.163.227.26"
SERVER_PASS="$SERVER_PASSWORD"

# Function to run commands on server
run_remote() {
    sshpass -p "$SERVER_PASS" ssh -o StrictHostKeyChecking=no $SERVER "$1"
}

echo -e "${YELLOW}[ПРОВЕРКА 1/3] Radicale публичный доступ...${NC}"
if curl -s -m 5 http://95.163.227.26:5232 > /dev/null 2>&1; then
    echo -e "${RED}❌ УЯЗВИМОСТЬ: Radicale доступен публично на порту 5232${NC}"
    echo "   CVSS Score: 9.1 (Critical)"
    echo "   Злоумышленники могут получить доступ ко всем календарям!"
    NEED_FIX_RADICALE=true
else
    echo -e "${GREEN}✅ Radicale недоступен публично${NC}"
    NEED_FIX_RADICALE=false
fi
echo ""

echo -e "${YELLOW}[ПРОВЕРКА 2/3] Права .env файла...${NC}"
ENV_PERMS=$(run_remote "stat -c '%a' /root/ai-calendar-assistant/.env 2>/dev/null || echo '000'")
if [ "$ENV_PERMS" != "600" ]; then
    echo -e "${RED}❌ УЯЗВИМОСТЬ: .env файл readable ($ENV_PERMS)${NC}"
    echo "   CVSS Score: 8.8 (High)"
    echo "   Содержит все API keys, пароли, токены!"
    NEED_FIX_ENV=true
else
    echo -e "${GREEN}✅ .env права правильные (600)${NC}"
    NEED_FIX_ENV=false
fi
echo ""

echo -e "${YELLOW}[ПРОВЕРКА 3/3] Наличие бэкапов...${NC}"
BACKUP_COUNT=$(run_remote "ls /root/backups/calendar-assistant/ 2>/dev/null | wc -l || echo 0")
if [ "$BACKUP_COUNT" -eq 0 ]; then
    echo -e "${RED}❌ КРИТИЧНО: Бэкапов НЕТ${NC}"
    echo "   При сбое - ПОЛНАЯ ПОТЕРЯ ДАННЫХ"
    NEED_BACKUP=true
else
    echo -e "${GREEN}✅ Найдено бэкапов: $BACKUP_COUNT${NC}"
    NEED_BACKUP=false
fi
echo ""

# Summary
if [ "$NEED_FIX_RADICALE" = false ] && [ "$NEED_FIX_ENV" = false ] && [ "$NEED_BACKUP" = false ]; then
    echo -e "${GREEN}=========================================="
    echo "  ✅ ВСЕ КРИТИЧЕСКИЕ ПРОВЕРКИ ПРОЙДЕНЫ"
    echo "==========================================${NC}"
    exit 0
fi

echo -e "${RED}=========================================="
echo "  ТРЕБУЮТСЯ ИСПРАВЛЕНИЯ"
echo "==========================================${NC}"
echo ""
echo "Будут применены следующие исправления:"
[ "$NEED_FIX_RADICALE" = true ] && echo "  🔒 Закрыть Radicale порт 5232"
[ "$NEED_FIX_ENV" = true ] && echo "  🔒 Установить права .env → 600"
[ "$NEED_BACKUP" = true ] && echo "  💾 Создать первый backup"
echo ""
read -p "Продолжить? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Отменено."
    exit 1
fi
echo ""

# FIX 1: Close Radicale port
if [ "$NEED_FIX_RADICALE" = true ]; then
    echo -e "${YELLOW}[ИСПРАВЛЕНИЕ 1/3] Закрытие Radicale порта...${NC}"

    # Backup docker-compose.yml
    run_remote "cp /root/ai-calendar-assistant/docker-compose.yml /root/ai-calendar-assistant/docker-compose.yml.backup-$(date +%Y%m%d-%H%M%S)"

    # Comment out public port
    run_remote "cd /root/ai-calendar-assistant && \
        sed -i 's/^    - \"5232:5232\"/    # - \"5232:5232\"  # Closed for security/' docker-compose.yml && \
        docker-compose up -d"

    echo "   Ожидание перезапуска контейнеров..."
    sleep 10

    # Verify
    if curl -s -m 5 http://95.163.227.26:5232 > /dev/null 2>&1; then
        echo -e "${RED}   ❌ ОШИБКА: Radicale все еще доступен!${NC}"
        echo "   Проверьте docker-compose.yml вручную"
    else
        echo -e "${GREEN}   ✅ Radicale порт закрыт${NC}"
    fi
    echo ""
fi

# FIX 2: Fix .env permissions
if [ "$NEED_FIX_ENV" = true ]; then
    echo -e "${YELLOW}[ИСПРАВЛЕНИЕ 2/3] Исправление прав .env...${NC}"

    run_remote "chmod 600 /root/ai-calendar-assistant/.env"

    # Verify
    NEW_PERMS=$(run_remote "stat -c '%a' /root/ai-calendar-assistant/.env")
    if [ "$NEW_PERMS" = "600" ]; then
        echo -e "${GREEN}   ✅ Права .env установлены: 600${NC}"
    else
        echo -e "${RED}   ❌ ОШИБКА: Права = $NEW_PERMS${NC}"
    fi
    echo ""
fi

# FIX 3: Create first backup
if [ "$NEED_BACKUP" = true ]; then
    echo -e "${YELLOW}[ИСПРАВЛЕНИЕ 3/3] Создание первого backup...${NC}"

    # Upload backup script if not exists
    if ! run_remote "test -f /root/ai-calendar-assistant/backup-calendar.sh"; then
        echo "   Загрузка backup скрипта..."
        sshpass -p "$SERVER_PASS" scp -o StrictHostKeyChecking=no \
            backup-calendar.sh $SERVER:/root/ai-calendar-assistant/
        run_remote "chmod +x /root/ai-calendar-assistant/backup-calendar.sh"
    fi

    # Run backup
    echo "   Запуск backup (может занять несколько минут)..."
    run_remote "cd /root/ai-calendar-assistant && ./backup-calendar.sh" || true

    # Verify
    BACKUP_COUNT=$(run_remote "ls /root/backups/calendar-assistant/ 2>/dev/null | wc -l || echo 0")
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        BACKUP_SIZE=$(run_remote "du -sh /root/backups/calendar-assistant/ | cut -f1")
        echo -e "${GREEN}   ✅ Backup создан: $BACKUP_SIZE${NC}"
        run_remote "ls -lh /root/backups/calendar-assistant/"
    else
        echo -e "${RED}   ❌ ОШИБКА: Backup не создан${NC}"
    fi
    echo ""
fi

# Final verification
echo -e "${GREEN}=========================================="
echo "  ПРОВЕРКА ПОСЛЕ ИСПРАВЛЕНИЙ"
echo "==========================================${NC}"
echo ""

echo "🔒 Radicale доступность:"
if curl -s -m 5 http://95.163.227.26:5232 > /dev/null 2>&1; then
    echo -e "   ${RED}❌ ВСЕ ЕЩЕ ДОСТУПЕН (требуется ручное исправление)${NC}"
else
    echo -e "   ${GREEN}✅ Недоступен публично${NC}"
fi

echo "🔒 .env права:"
ENV_PERMS=$(run_remote "stat -c '%a' /root/ai-calendar-assistant/.env")
if [ "$ENV_PERMS" = "600" ]; then
    echo -e "   ${GREEN}✅ 600 (правильно)${NC}"
else
    echo -e "   ${RED}❌ $ENV_PERMS (неправильно)${NC}"
fi

echo "💾 Бэкапы:"
BACKUP_COUNT=$(run_remote "ls /root/backups/calendar-assistant/ 2>/dev/null | wc -l || echo 0")
if [ "$BACKUP_COUNT" -gt 0 ]; then
    echo -e "   ${GREEN}✅ Найдено: $BACKUP_COUNT${NC}"
else
    echo -e "   ${RED}❌ Отсутствуют${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "  КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ ЗАВЕРШЕНЫ"
echo "==========================================${NC}"
echo ""
echo "⚠️  Следующие шаги:"
echo "   1. Проверить работу бота в Telegram"
echo "   2. Проверить работу webapp"
echo "   3. Запустить полное развертывание: ./deploy-security-improvements.sh"
echo "   4. Настроить cron для ежедневных бэкапов"
echo ""
echo "📋 Логи:"
echo "   docker-compose logs -f"
echo ""

exit 0
