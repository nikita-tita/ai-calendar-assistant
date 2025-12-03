#!/bin/bash

# Start script for running both Telegram bot and FastAPI server

echo "Starting AI Calendar Assistant..."

# Start FastAPI server in background
echo "Starting FastAPI server on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to start
sleep 3

# Start Telegram bot in foreground
echo "Starting Telegram bot (polling mode)..."
python run_polling.py &
BOT_PID=$!

# Function to handle shutdown
shutdown() {
    echo "Shutting down services..."
    kill $BOT_PID 2>/dev/null
    kill $FASTAPI_PID 2>/dev/null
    exit 0
}

# Trap signals for graceful shutdown
trap shutdown SIGTERM SIGINT

# Wait for both processes
wait
