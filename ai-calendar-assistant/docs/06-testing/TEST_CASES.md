# Comprehensive Test Cases - AI Calendar Assistant Bot

## 1. Language Selection Tests

### 1.1 Initial Language Selection
**Test Case ID**: LANG-001
**Priority**: High
**Steps**:
1. Send `/start` command to bot
2. Bot should show language selection buttons (4 languages)
3. Click on "🇬🇧 English" button
4. Verify confirmation message appears in English
5. Verify welcome message appears in English after 1 second
6. Verify keyboard buttons are in English

**Expected Result**:
- Language changes to English
- All UI elements are in English
- User preferences saved

### 1.2 Change Language via /language Command
**Test Case ID**: LANG-002
**Priority**: High
**Steps**:
1. User already has language set to Russian
2. Send `/language` command
3. Select "🇪🇸 Español"
4. Verify all messages switch to Spanish

**Expected Result**: Language changes successfully, all subsequent messages in Spanish

### 1.3 Language Persistence
**Test Case ID**: LANG-003
**Priority**: Medium
**Steps**:
1. Set language to English
2. Restart bot (or wait 24 hours)
3. Send any message
4. Verify bot responds in English

**Expected Result**: Language preference persists across sessions

---

## 2. Batch Operations Tests

### 2.1 Multiple Event Creation
**Test Case ID**: BATCH-001
**Priority**: High
**Steps**:
1. Send message: "Создай встречу с Ивановым в понедельник в 10:00 и встречу с Петровым во вторник в 14:00"
2. Bot should show confirmation dialog with:
   - Header explaining what will be done
   - List of 2 actions with formatted times
   - Confirm/Cancel buttons
3. Click "✅ Подтвердить"
4. Wait for execution
5. Check summary message

**Expected Result**:
- Confirmation dialog appears with readable dates/times
- Both events created successfully
- Summary shows: "Выполнено: 2, Ошибки: 0"
- Both events visible in calendar

### 2.2 Batch Operations Cancellation
**Test Case ID**: BATCH-002
**Priority**: High
**Steps**:
1. Send message requesting multiple operations
2. Confirmation dialog appears
3. Click "❌ Отменить"
4. Verify cancellation message appears
5. Verify no events were created

**Expected Result**:
- Cancellation successful
- No changes to calendar
- Clear feedback to user

### 2.3 Mixed Batch Operations (Create + Delete)
**Test Case ID**: BATCH-003
**Priority**: Medium
**Steps**:
1. Create event "Test Event 1"
2. Send: "Создай встречу Test Event 2 завтра в 15:00 и удали Test Event 1"
3. Verify confirmation shows both create and delete actions
4. Confirm execution
5. Verify final state

**Expected Result**:
- Confirmation clearly shows different action types
- Both operations execute successfully
- Event 1 deleted, Event 2 created

### 2.4 Batch Operations Error Handling
**Test Case ID**: BATCH-004
**Priority**: High
**Steps**:
1. Send request to create 3 events, one with invalid data
2. Confirm execution
3. Check summary

**Expected Result**:
- Summary shows partial success (e.g., "Выполнено: 2, Ошибки: 1")
- Detailed list shows which operations succeeded/failed
- No system crash or undefined behavior

### 2.5 Multilingual Batch Confirmation
**Test Case ID**: BATCH-005
**Priority**: Medium
**Steps**:
1. Set language to English
2. Request multiple operations in English
3. Verify confirmation dialog in English
4. Set language to Arabic
5. Request multiple operations in Arabic
6. Verify confirmation dialog in Arabic (RTL layout)

**Expected Result**: All batch UI elements properly translated

---

## 3. WebApp Multilingual Tests

### 3.1 WebApp Opens with User Language
**Test Case ID**: WEBAPP-001
**Priority**: High
**Steps**:
1. Set bot language to English
2. Click "Cabinet" button (menu button)
3. WebApp opens
4. Verify admin panel interface is in English

**Expected Result**:
- URL contains `?lang=en&user_id=...`
- All UI elements in English ("Admin Panel", "Users", "Events", etc.)

### 3.2 WebApp Language Switching
**Test Case ID**: WEBAPP-002
**Priority**: Medium
**Steps**:
1. Open WebApp with Russian language
2. Note all texts are in Russian
3. Go back to bot, change language to Spanish
4. Reopen WebApp
5. Verify interface is now in Spanish

**Expected Result**: WebApp language dynamically matches bot language

### 3.3 WebApp URL Parameter Validation
**Test Case ID**: WEBAPP-003
**Priority**: Medium
**Steps**:
1. Open WebApp normally
2. Check browser console for URL
3. Manually modify `?lang=invalid`
4. Reload page

**Expected Result**: Falls back to Russian (default) without errors

### 3.4 All Languages in WebApp
**Test Case ID**: WEBAPP-004
**Priority**: High
**Test Matrix**:
- Russian: Verify all labels (Пользователей, Событий, etc.)
- English: Verify all labels (Users, Events, etc.)
- Spanish: Verify all labels (Usuarios, Eventos, etc.)
- Arabic: Verify RTL layout + labels (المستخدمون, الأحداث, etc.)

**Expected Result**: Complete translation coverage for all 4 languages

---

## 4. Single Event Operations Tests

### 4.1 Create Event with Natural Language
**Test Case ID**: EVENT-001
**Priority**: High
**Steps**:
1. Send: "Встреча с Андреем завтра в 14:00"
2. Verify success message
3. Check calendar for event

**Expected Result**: Event created with correct time, title, and user

### 4.2 Update Existing Event
**Test Case ID**: EVENT-002
**Priority**: High
**Steps**:
1. Create event "Meeting A" tomorrow at 10:00
2. Send: "Перенеси встречу с Андреем на 15:00"
3. Verify update confirmation
4. Check event time changed

**Expected Result**: Event time updated successfully

### 4.3 Delete Event
**Test Case ID**: EVENT-003
**Priority**: High
**Steps**:
1. Create event "Delete Test"
2. Send: "Удали Delete Test"
3. Verify deletion confirmation
4. Check event no longer exists

**Expected Result**: Event deleted successfully

### 4.4 Query Events for Day/Week
**Test Case ID**: EVENT-004
**Priority**: High
**Steps**:
1. Create 3 events this week
2. Send: "Что у меня на неделю?"
3. Verify list of events appears

**Expected Result**: All events listed with formatted times

---

## 5. Voice Message Tests

### 5.1 Voice Recognition (Russian)
**Test Case ID**: VOICE-001
**Priority**: Medium
**Steps**:
1. Record voice: "Создай встречу завтра в два часа"
2. Send to bot
3. Verify transcription appears
4. Verify event created

**Expected Result**: Voice correctly transcribed and processed

### 5.2 Voice Recognition (Other Languages)
**Test Case ID**: VOICE-002
**Priority**: Low
**Test Matrix**: English, Spanish, Arabic voice messages

**Expected Result**: Transcription works for all supported languages

---

## 6. Error Handling Tests

### 6.1 Invalid Date/Time
**Test Case ID**: ERROR-001
**Priority**: High
**Steps**:
1. Send: "Встреча вчера в 25:99"
2. Verify error message or clarification request

**Expected Result**: Bot asks for clarification, doesn't crash

### 6.2 Calendar Service Unavailable
**Test Case ID**: ERROR-002
**Priority**: High
**Steps**:
1. Stop CalDAV service
2. Try to create event
3. Check error message

**Expected Result**: User-friendly error message displayed

### 6.3 Malformed LLM Response
**Test Case ID**: ERROR-003
**Priority**: Medium
**Steps**:
1. Send ambiguous/nonsense message
2. Verify bot handles gracefully

**Expected Result**: Clarification request, no crash

---

## 7. Edge Cases Tests

### 7.1 Empty Batch Array
**Test Case ID**: EDGE-001
**Priority**: Low
**Scenario**: Yandex GPT returns empty array `[]`
**Expected Result**: Error handled gracefully, user informed

### 7.2 Very Long Event Title
**Test Case ID**: EDGE-002
**Priority**: Low
**Steps**:
1. Create event with 500+ character title
2. Verify truncation or proper handling

**Expected Result**: No UI breaking, proper ellipsis or truncation

### 7.3 Concurrent Batch Operations
**Test Case ID**: EDGE-003
**Priority**: Medium
**Steps**:
1. User requests batch operation
2. Before confirming, user sends another batch request
3. Verify correct handling

**Expected Result**: New request replaces old, or proper queue management

### 7.4 Special Characters in Event Titles
**Test Case ID**: EDGE-004
**Priority**: Low
**Test**: Emojis, quotes, apostrophes, Cyrillic, Arabic
**Expected Result**: All characters handled correctly

---

## 8. Performance Tests

### 8.1 Large Batch Operations
**Test Case ID**: PERF-001
**Priority**: Medium
**Steps**:
1. Request creation of 10+ events in one message
2. Confirm execution
3. Measure time to complete

**Expected Result**:
- All operations complete within 30 seconds
- UI remains responsive
- Clear progress indication

### 8.2 High User Load
**Test Case ID**: PERF-002
**Priority**: Low
**Scenario**: 10+ users simultaneously creating batch operations
**Expected Result**: No conflicts, each user's operations isolated

---

## 9. Integration Tests

### 9.1 End-to-End Workflow (Russian User)
**Test Case ID**: INT-001
**Priority**: High
**Complete User Journey**:
1. User starts bot → selects Russian
2. Creates 3 events for next week
3. Queries "Дела на неделю"
4. Updates one event time
5. Deletes one event
6. Opens WebApp (in Russian)
7. Views statistics

**Expected Result**: Smooth workflow, no errors, consistent language

### 9.2 End-to-End Workflow (English User)
**Test Case ID**: INT-002
**Priority**: High
**Same as INT-001 but in English**

---

## 10. Regression Tests

### 10.1 Previous Single Command Functionality
**Test Case ID**: REG-001
**Priority**: High
**Verify**: All previous single-command features still work after batch implementation

### 10.2 Language Selection Still Works
**Test Case ID**: REG-002
**Priority**: High
**Verify**: Language selection wasn't broken by WebApp changes

---

## Test Execution Priority

**Critical (Must Pass)**:
- LANG-001, LANG-002
- BATCH-001, BATCH-002, BATCH-004
- WEBAPP-001, WEBAPP-004
- EVENT-001, EVENT-002, EVENT-003
- ERROR-001, ERROR-002
- INT-001

**High Priority**:
- All other BATCH-* tests
- All ERROR-* tests
- REG-001, REG-002

**Medium Priority**:
- VOICE-*, EDGE-*, PERF-001

**Low Priority**:
- EDGE-002, EDGE-004, PERF-002

---

## Automated Testing Recommendations

1. **Unit Tests**: Test individual functions (datetime parsing, translation lookup)
2. **Integration Tests**: Test bot handlers with mock Telegram updates
3. **E2E Tests**: Use Telegram Bot API test environment
4. **Load Tests**: Simulate multiple concurrent users

## Bug Reporting Template

```
Bug ID: [AUTO]
Test Case: [TEST-ID]
Severity: [Critical/High/Medium/Low]
Language: [ru/en/es/ar]
Steps to Reproduce:
1. ...
Expected: ...
Actual: ...
Screenshots: [if applicable]
Logs: [relevant logs]
```
