# Quick Testing Guide - 5 Minutes

Быстрая проверка всех ключевых функций бота за 5 минут.

---

## ✅ Test 1: Language Selection (30 sec)

**Commands:**
```
/start
→ Нажмите "🇬🇧 English"
→ Должно прийти "✅ Language changed to English"
→ Через 1 сек приветственное сообщение на английском
```

**Expected Result:**
- Кнопки переключились на английский
- Все сообщения на английском

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 2: Single Event Creation (30 sec)

**Commands:**
```
Create meeting with John tomorrow at 2 PM
```

**Expected Result:**
- "✅ Event created!" message
- Event visible in calendar

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 3: Batch Operations (60 sec)

**Commands:**
```
Create meeting Monday 10 AM and Tuesday 3 PM
```

**Expected Result:**
1. Confirmation dialog appears:
   - "📋 Did I understand correctly?"
   - List of 2 actions with readable times
   - [✅ Confirm] [❌ Cancel] buttons

2. Click "✅ Confirm"

3. Summary message:
   - "✅ All operations completed!"
   - "Success: 2, Errors: 0"
   - List of created events

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 4: Batch Cancellation (30 sec)

**Commands:**
```
Delete all events
```

**Expected Result:**
1. Confirmation dialog appears
2. Click "❌ Cancel"
3. "❌ Operations cancelled" message
4. No events deleted (check calendar)

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 5: Query Events (30 sec)

**Commands:**
```
What's on my schedule this week?
```

**Expected Result:**
- List of events with formatted dates/times
- All previously created events shown

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 6: WebApp Multilingual (30 sec)

**Steps:**
1. Make sure language is English (from Test 1)
2. Click "Cabinet" button (menu button left of text input)
3. WebApp opens

**Expected Result:**
- Admin panel in English
- "Admin Panel" title
- "Users", "Events", "Messages", "Errors" labels
- Everything in English

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 7: Language Persistence in WebApp (30 sec)

**Steps:**
1. Close WebApp
2. Send: `/language`
3. Select "🇪🇸 Español"
4. Click "Cabinet" again

**Expected Result:**
- WebApp opens in Spanish
- "Panel de Administración"
- "Usuarios", "Eventos", etc.

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 8: Error Handling (30 sec)

**Commands:**
```
Create meeting yesterday at 25:99
```

**Expected Result:**
- Bot asks for clarification
- No crash
- User-friendly error message

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 9: Update Event (30 sec)

**Commands:**
```
Reschedule meeting with John to 5 PM
```

**Expected Result:**
- "✅ Event updated!" message
- Time changed in calendar

**Status**: [ ] PASS / [ ] FAIL

---

## ✅ Test 10: Delete Event (30 sec)

**Commands:**
```
Delete meeting with John
```

**Expected Result:**
- "✅ Event deleted!" message
- Event removed from calendar

**Status**: [ ] PASS / [ ] FAIL

---

## Summary

Total time: ~5 minutes
Tests passed: __ / 10

**Overall Status**:
- [ ] ✅ ALL PASS - System ready
- [ ] ⚠️ PARTIAL - Review failed tests
- [ ] ❌ FAIL - Critical issues found

---

## If Any Test Fails

1. Check bot logs:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot --tail 100"
```

2. Check specific errors:
```bash
ssh root@91.229.8.221 "docker logs telegram-bot 2>&1 | grep -i error"
```

3. Restart if needed:
```bash
ssh root@91.229.8.221 "cd /root/ai-calendar-assistant && docker-compose -f docker-compose.hybrid.yml restart telegram-bot"
```

---

## Extended Test (Optional - 10 min)

### Test All 4 Languages

1. **Russian** (default)
   - `/start` → "🇷🇺 Русский" → Check interface
   - Test: "Встреча завтра в 14:00"

2. **English**
   - `/language` → "🇬🇧 English" → Check interface
   - Test: "Meeting tomorrow at 2 PM"

3. **Spanish**
   - `/language` → "🇪🇸 Español" → Check interface
   - Test: "Reunión mañana a las 14:00"

4. **Arabic**
   - `/language` → "🇸🇦 العربية" → Check interface (RTL)
   - Test: "اجتماع غداً الساعة 2"

### Test Voice Messages

1. Record voice: "Create meeting tomorrow at 3 PM"
2. Send to bot
3. Check transcription and event creation

### Test Edge Cases

1. **Very long title** (200+ chars)
2. **Special characters** (emojis, quotes)
3. **Multiple batch requests** (before confirming first)
4. **Calendar service down** (stop Radicale temporarily)

---

## Notes

- Test from real Telegram client (mobile/desktop)
- Use test user account if possible
- Document any unexpected behavior
- Take screenshots of failures
