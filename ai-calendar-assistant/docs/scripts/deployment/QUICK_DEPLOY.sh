#!/bin/bash

# Быстрый деплой через создание файлов напрямую на сервере
# Запустить: bash QUICK_DEPLOY.sh

echo "=== Быстрый деплой Yandex GPT на сервер ==="
echo ""
echo "Скопируй и выполни следующие команды на сервере:"
echo ""
echo "ssh root@95.163.227.26"
echo ""
echo "# ============================================"
echo "# 1. Создаём llm_agent_yandex.py"
echo "# ============================================"
echo ""
cat << 'EOF'
cat > /root/ai-calendar-assistant/app/services/llm_agent_yandex.py << 'ENDOFFILE'
EOF

cat app/services/llm_agent_yandex.py

cat << 'EOF'
ENDOFFILE
EOF

echo ""
echo "# ============================================"
echo "# 2. Обновляем telegram_handler.py (строка 9)"
echo "# ============================================"
echo ""
cat << 'EOF'
sed -i 's/from app.services.llm_agent_openai import llm_agent_openai as llm_agent/from app.services.llm_agent_yandex import llm_agent_yandex as llm_agent/' /root/ai-calendar-assistant/app/services/telegram_handler.py
EOF

echo ""
echo "# ============================================"
echo "# 3. Обновляем config.py"
echo "# ============================================"
echo ""
cat << 'EOF'
sed -i '/# OpenAI (for Whisper)/a\    \n    # Yandex GPT (for regions where Claude/OpenAI are blocked)\n    yandex_gpt_api_key: Optional[str] = None\n    yandex_gpt_folder_id: Optional[str] = None' /root/ai-calendar-assistant/app/config.py
EOF

echo ""
echo "# ============================================"
echo "# 4. Обновляем requirements.txt"
echo "# ============================================"
echo ""
cat << 'EOF'
sed -i '/aiohttp>=3.9.0/a requests>=2.31.0' /root/ai-calendar-assistant/requirements.txt
EOF

echo ""
echo "# ============================================"
echo "# 5. Добавляем Yandex GPT ключи в .env"
echo "# ============================================"
echo ""
cat << 'EOF'
cat >> /root/ai-calendar-assistant/.env << 'ENDOFENV'

# Yandex GPT (работает из России без VPN)
YANDEX_GPT_API_KEY=YOUR_KEY_HERE
YANDEX_GPT_FOLDER_ID=YOUR_FOLDER_HERE
ENDOFENV
EOF

echo ""
echo "# ============================================"
echo "# 6. Перезапускаем бота"
echo "# ============================================"
echo ""
cat << 'EOF'
cd /root/ai-calendar-assistant
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d --build
sleep 5
docker logs telegram-bot --tail 50
EOF

echo ""
echo "=== Готово! ==="
