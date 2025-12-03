# 🧪 Manual Testing Guide - AI Calendar Assistant

## ✅ Fixed Issues

### 1. **CRITICAL FIX:** `LLMAgentYandex.process_message` AttributeError
- **Status:** ✅ FIXED
- **What was wrong:** telegram_handler was calling non-existent `llm_agent.process_message()` method
- **Fix:** Updated to call `llm_agent.extract_event()` with proper parameters
- **Location:** [app/services/telegram_handler.py:310](app/services/telegram_handler.py#L310)

---

## 📋 Test Scenarios

### 🗓️ Calendar Bot - Text Messages

#### Test 1: Simple Event Creation
**Send to bot:**
```
Завтра в 15:00 встреча с командой
```

**Expected behavior:**
1. Bot responds: "⏳ Обрабатываю..."
2. Bot creates event
3. Bot responds: "✅ Создано: Встреча с командой"
4. Event appears in calendar for tomorrow at 15:00

**Check logs for:**
```bash
docker logs telegram-bot-polling 2>&1 | grep "text_message_received\|event_created" | tail -5
```

---

#### Test 2: Event with Multiple Details
**Send to bot:**
```
Послезавтра в 10:00 встреча с нотариусом Новиковым по адресу улица Ленина 5
```

**Expected behavior:**
1. Bot processes message
2. Creates event with:
   - Title: "Встреча с нотариусом Новиковым"
   - Location: "улица Ленина 5"
   - Time: Day after tomorrow at 10:00

---

#### Test 3: Clarification Request
**Send to bot:**
```
Встреча с Андреем
```

**Expected behavior:**
1. Bot asks: "Когда планируется встреча с Андреем?"
2. You reply: "Завтра в 14:00"
3. Bot creates event

---

### 🎤 Calendar Bot - Voice Messages

#### Test 4: Voice Event Creation
**Record and send voice:**
> "Завтра у нотариуса Новикова в 12 надо быть"

**Expected behavior:**
1. Bot responds: "🎤 Распознаю голос..."
2. Bot shows: "Вы сказали: Завтра у нотариуса Новикова в 12 надо быть"
3. Bot responds: "⏳ Обрабатываю..."
4. Bot creates event: "✅ Создано: У нотариуса Новикова" with date/time shown

**Check logs for:**
```bash
docker logs telegram-bot-polling 2>&1 | grep "voice_message\|transcribed\|event_created" | tail -10
```

---

#### Test 5: Long Voice Message (>1 minute)
**Record long voice message (>1 minute):**
> "Нужно записать встречу на послезавтра в 10 утра с нотариусом Новиковым по адресу улица Ленина дом 5 квартира 10, взять с собой паспорт и документы на квартиру"

**Expected behavior:**
1. Bot chunks audio into 25-second segments
2. Successfully transcribes entire message
3. Creates event with all details

---

### 📋 Quick Buttons

#### Test 6: "📋 Сегодня" Button
**Click:** "📋 Сегодня"

**Expected behavior:**
- Shows today's events with times
- OR "📅 На сегодня событий не запланировано."

**Check logs for:**
```bash
docker logs telegram-bot-polling 2>&1 | grep "today_events" | tail -3
```

---

#### Test 7: "📋 Завтра" Button
**Click:** "📋 Завтра"

**Expected behavior:**
- Shows tomorrow's events
- OR "📅 На завтра событий не запланировано."

---

#### Test 8: "📋 Неделя" Button
**Click:** "📋 Неделя"

**Expected behavior:**
- Shows all events for next 7 days grouped by date

---

### 🏠 Property Bot

#### Test 9: Property Search Request (Voice)
**Record and send:**
> "Найди квартиру до 18000000 в ипотеку двухкомнатную север города не дальше 20 минут от метро"

**Expected behavior:**
1. Bot transcribes voice
2. Bot extracts parameters:
   - budget: 18000000
   - rooms: 2
   - district: "север города"
   - mortgage: true
   - metro_distance: 20 minutes
3. Bot shows confirmation with inline button "✅ Подтвердить"
4. Click "✅ Подтвердить"
5. Bot performs search

**Known issues:**
- ⚠️ Currently missing `mortgage` and `metro_distance` extraction (needs LLM prompt fix)

---

#### Test 10: Property Search Request (Text)
**Send to bot:**
```
Ищу трёшку в центре до 20 миллионов
```

**Expected behavior:**
1. Bot enters property mode
2. Extracts: rooms=3, district="центр", budget=20000000
3. Shows confirmation
4. Performs search after confirmation

---

### 🔄 Mode Switching

#### Test 11: Calendar ↔️ Property Mode
**Steps:**
1. Start in calendar mode (default)
2. Click "📋 Меню"
3. Click "🏠 Поиск новостройки"
4. Bot enters property mode
5. Send property search request
6. Click "📋 Меню" again
7. Click "📅 Календарь"
8. Bot returns to calendar mode

**Expected behavior:**
- Buttons change correctly
- Bot context switches properly
- No errors in logs

---

### ⚙️ Settings

#### Test 12: Timezone Change
**Steps:**
1. Click "📋 Меню"
2. Click "⚙️ Настройки"
3. Select different timezone
4. Create event

**Expected behavior:**
- Event created in selected timezone
- Times shown correctly

---

## 🐛 Known Issues to Monitor

### High Priority
1. ~~`LLMAgentYandex.process_message` AttributeError~~ ✅ FIXED
2. Property Bot not extracting mortgage and metro parameters
3. "❌ Ошибка при загрузке событий" in quick buttons - need to verify fixed

### Medium Priority
4. Property Bot "❌ Данные поиска не найдены" - state management issue

---

## 📊 Log Monitoring Commands

### Watch all events in real-time:
```bash
ssh root@91.229.8.221 "docker logs -f telegram-bot-polling 2>&1" | grep -v "getUpdates"
```

### Check for errors:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot-polling 2>&1 | grep -i error | tail -20"
```

### Check voice processing:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot-polling 2>&1 | grep 'voice_message\|transcribed\|stt' | tail -20"
```

### Check event creation:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot-polling 2>&1 | grep 'event_created\|event_create_error' | tail -20"
```

### Check property bot:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot-polling 2>&1 | grep 'property\|search_criteria' | tail -20"
```

---

## ✅ Success Criteria

### Calendar Bot
- ✅ Text messages create events correctly
- ✅ Voice messages transcribe and create events
- ✅ Long voice messages (>1 min) work
- ✅ Quick buttons show events without errors
- ✅ Clarification flow works
- ✅ Events saved to Radicale

### Property Bot
- ✅ Voice search requests transcribe
- ✅ Parameters extracted (at least basic: budget, rooms, district)
- ✅ Confirmation button works
- ✅ Search executes without errors

### General
- ✅ Mode switching works
- ✅ No AttributeErrors in logs
- ✅ No file corruption errors
- ✅ Bot responds to all messages

---

## 🆘 If Something Fails

### 1. Check bot is running:
```bash
ssh root@91.229.8.221 "docker ps | grep telegram-bot-polling"
```

### 2. Check recent errors:
```bash
ssh root@91.229.8.221 "docker logs --tail 50 telegram-bot-polling 2>&1 | grep -i error"
```

### 3. Restart bot:
```bash
ssh root@91.229.8.221 "cd /root/ai-calendar-assistant && docker-compose -f docker-compose.polling.yml restart telegram-bot"
```

### 4. Check API keys still present:
```bash
ssh root@91.229.8.221 "docker exec telegram-bot-polling printenv | grep YANDEX"
```

---

## 📝 Testing Checklist

Mark off as you test:

### Calendar - Text
- [ ] Test 1: Simple event creation
- [ ] Test 2: Event with details
- [ ] Test 3: Clarification flow

### Calendar - Voice
- [ ] Test 4: Basic voice event
- [ ] Test 5: Long voice message

### Quick Buttons
- [ ] Test 6: Today button
- [ ] Test 7: Tomorrow button
- [ ] Test 8: Week button

### Property Bot
- [ ] Test 9: Voice property search
- [ ] Test 10: Text property search

### General
- [ ] Test 11: Mode switching
- [ ] Test 12: Timezone settings

---

## 🎯 Priority Order

1. **FIRST:** Test calendar text message (Test 1)
2. **SECOND:** Test calendar voice message (Test 4)
3. **THIRD:** Test quick buttons (Tests 6, 7, 8)
4. **FOURTH:** Test property bot (Tests 9, 10)
5. **FIFTH:** Test mode switching (Test 11)

---

## 📞 Server Access

**SSH:** `root@91.229.8.221`
**Password:** `upvzrr3LH4pxsaqs`
**Container:** `telegram-bot-polling`
**Bot:** @aibroker_bot
**Test User ID:** 2296243

---

## 🔍 Quick Verification

Run this command to verify bot health:
```bash
ssh root@91.229.8.221 "
echo '=== Bot Status ===' &&
docker ps | grep telegram-bot-polling &&
echo '' &&
echo '=== Recent Activity ===' &&
docker logs --tail 10 telegram-bot-polling 2>&1 | grep -v getUpdates &&
echo '' &&
echo '=== API Keys Present ===' &&
docker exec telegram-bot-polling printenv | grep YANDEX_GPT_API_KEY | cut -d= -f1 &&
echo '' &&
echo '=== No Recent Errors ===' &&
docker logs --tail 50 telegram-bot-polling 2>&1 | grep -i error | tail -3
"
```
