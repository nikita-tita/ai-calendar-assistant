#!/bin/bash
set -e

echo "🚀 DEPLOYING TODOS FIX - Comprehensive Review"
echo "=============================================="
echo ""

SERVER="root@95.163.227.26"
PROJECT_DIR="/root/ai-calendar-assistant"
KEY="~/.ssh/id_housler"

echo "📋 Files to deploy:"
echo "  1. app/routers/todos.py (updated endpoints)"
echo "  2. app/static/index.html (edit/delete UI)"
echo ""

# Check SSH connection
echo "🔌 Testing SSH connection..."
if ! ssh -i ~/.ssh/id_housler "$SERVER" 'echo "✅ SSH OK"' 2>/dev/null; then
    echo "❌ SSH connection failed!"
    echo "Please check your SSH key and server access."
    exit 1
fi
echo ""

# Upload files
echo "📤 Step 1/4: Uploading files to server..."
scp -i ~/.ssh/id_housler app/routers/todos.py "$SERVER:$PROJECT_DIR/app/routers/todos.py" || {
    echo "❌ Failed to upload todos.py"
    exit 1
}
echo "  ✅ todos.py uploaded"

scp -i ~/.ssh/id_housler app/static/index.html "$SERVER:$PROJECT_DIR/app/static/index.html" || {
    echo "❌ Failed to upload index.html"
    exit 1
}
echo "  ✅ index.html uploaded"
echo ""

# Copy to containers
echo "📦 Step 2/4: Copying files to containers..."
ssh -i ~/.ssh/id_housler "$SERVER" '
docker cp /root/ai-calendar-assistant/app/routers/todos.py ai-calendar-assistant:/app/app/routers/todos.py
docker cp /root/ai-calendar-assistant/app/static/index.html ai-calendar-assistant:/app/app/static/index.html
docker cp /root/ai-calendar-assistant/app/static/index.html telegram-bot-polling:/app/app/static/index.html
echo "✅ Files copied to containers"
'
echo ""

# Restart main container to reload routes
echo "🔄 Step 3/4: Restarting ai-calendar-assistant container..."
ssh -i ~/.ssh/id_housler "$SERVER" 'docker restart ai-calendar-assistant' > /dev/null
echo "  ✅ Container restarted"
echo ""

# Wait for container to start
echo "⏳ Waiting for container to be ready..."
sleep 5
echo ""

# Verify deployment
echo "🔍 Step 4/4: Verifying deployment..."
ssh -i ~/.ssh/id_housler "$SERVER" '
echo "  📊 Container status:"
docker ps --filter "name=ai-calendar-assistant" --format "    {{.Names}}: {{.Status}}"

echo ""
echo "  📄 File verification:"
echo "    todos.py lines: $(docker exec ai-calendar-assistant wc -l /app/app/routers/todos.py | cut -d" " -f1)"
echo "    index.html lines: $(docker exec ai-calendar-assistant wc -l /app/app/static/index.html | cut -d" " -f1)"

echo ""
echo "  ✅ todos_service import: $(docker exec ai-calendar-assistant grep -c "from app.services.todos_service" /app/app/routers/todos.py || echo 0) occurrences"
echo "  ✅ editTodo function: $(docker exec ai-calendar-assistant grep -c "window.editTodo" /app/app/static/index.html || echo 0) occurrences"
echo "  ✅ PUT endpoint: $(docker exec ai-calendar-assistant grep -c "@router.put" /app/app/routers/todos.py || echo 0) occurrences"
'
echo ""

echo "🎉 DEPLOYMENT COMPLETE!"
echo "======================="
echo ""
echo "📱 TESTING INSTRUCTIONS:"
echo "  1. Open Telegram bot"
echo "  2. /start → \"🗓 Кабинет\""
echo "  3. Click \"✓ Задачи\" tab"
echo "  4. Your tasks should appear (including \"позвонить бабушке\")"
echo "  5. Click on a task to edit it"
echo "  6. Try editing and saving"
echo "  7. Try deleting a task"
echo ""
echo "📖 Full documentation: 🔥_COMPREHENSIVE_TODOS_REVIEW.md"
echo ""
echo "💬 Report back:"
echo "  ✅ Tasks visible from bot?"
echo "  ✅ Edit works (click on task)?"
echo "  ✅ Delete works?"
echo "  ✅ Save works?"
echo ""
