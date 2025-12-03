# 🏢 Property Search Bot - Separate Bot Architecture

## Overview

Property search functionality has been moved to a separate Telegram bot:
- **Bot Username**: @aipropertyfinder_bot
- **Bot Token**: `***REMOVED***`
- **Link**: https://t.me/aipropertyfinder_bot

## Architecture

### Before (Monolithic)
```
Calendar Bot (telegram-bot-polling)
├── Calendar Mode
└── Property Mode  ← Mixed in same bot
```

### After (Microservices)
```
Calendar Bot (telegram-bot-polling)
└── "🏢 Поиск новостроек" button → Links to Property Bot

Property Bot (property-bot) - Separate container
└── Full property search functionality
```

## Benefits

1. **Separation of Concerns** - Each bot has single responsibility
2. **Independent Scaling** - Can scale property bot separately
3. **Better User Experience** - Clear separation, dedicated bot for property search
4. **Easier Maintenance** - Changes to property features don't affect calendar bot

## Deployment

### Deploy Property Bot
```bash
./deploy-property-bot.sh
```

This script will:
1. Copy all property bot files to server
2. Build property-bot Docker image
3. Start property-bot container
4. Update calendar bot with link to property bot
5. Restart calendar bot

### Manual Deployment
```bash
# Build property bot
docker-compose build property-bot

# Start property bot
docker-compose up -d property-bot

# Check logs
docker logs property-bot --tail 50
```

## Files Structure

```
ai-calendar-assistant/
├── run_property_bot.py           # Property bot entry point
├── Dockerfile.property-bot        # Property bot dockerfile
├── docker-compose.yml             # Updated with property-bot service
├── app/
│   ├── services/
│   │   ├── telegram_handler.py   # Updated to link to property bot
│   │   └── property/             # Property bot modules
│   │       ├── property_handler.py
│   │       ├── property_service.py
│   │       ├── property_scoring.py
│   │       └── llm_agent_property.py
│   └── models/
│       └── property.py           # Property database models
└── deploy-property-bot.sh        # Deployment script
```

## Testing

### Test Calendar Bot Link
1. Open calendar bot
2. Click "🏢 Поиск новостроек" button
3. Should see message with link to @aipropertyfinder_bot
4. Click "🔍 Открыть бота поиска"
5. Opens @aipropertyfinder_bot

### Test Property Bot
1. Open @aipropertyfinder_bot
2. Send /start
3. Send search query: "Квартиру на васке за 15 млн"
4. Should receive search results

## Configuration

### Environment Variables
Property bot uses same `.env` as calendar bot:
- `YANDEX_GPT_API_KEY` - For LLM agent
- `DATABASE_URL` - PostgreSQL connection (property-bot-db)
- `TELEGRAM_BOT_TOKEN` - Automatically set to property bot token

### Database
Property bot uses separate PostgreSQL database:
- **Container**: property-bot-db
- **Database**: property_bot
- **User**: property_user
- **Shared with**: Calendar bot (for user management)

## Monitoring

### Check Property Bot Status
```bash
docker-compose ps property-bot
docker logs property-bot --tail 50 -f
```

### Check Calendar Bot Status
```bash
docker-compose ps telegram-bot-polling
docker logs telegram-bot-polling --tail 50 -f
```

### Check Database
```bash
docker exec -it property-bot-db psql -U property_user -d property_bot
\dt  # List tables
SELECT COUNT(*) FROM property_listings;
```

## Troubleshooting

### Property Bot Not Starting
```bash
# Check logs
docker logs property-bot

# Rebuild image
docker-compose build property-bot --no-cache
docker-compose up -d property-bot
```

### Link Not Working from Calendar Bot
```bash
# Restart calendar bot
docker restart telegram-bot-polling

# Check telegram_handler.py was updated
docker exec telegram-bot-polling grep -A 5 "aipropertyfinder_bot" /app/app/services/telegram_handler.py
```

### Database Connection Issues
```bash
# Check property-bot-db is running
docker-compose ps property-bot-db

# Test connection
docker exec property-bot-db psql -U property_user -d property_bot -c "SELECT 1;"
```

## Future Improvements

1. **Shared Session Management** - Use Redis for cross-bot sessions
2. **Analytics** - Track user flow from calendar bot to property bot
3. **Deep Linking** - Pass search context from calendar bot to property bot
4. **Unified User Profile** - Share user preferences across bots

---

**Last Updated**: 2025-10-30
**Status**: ✅ Deployed and operational
