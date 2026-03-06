"""Live LLM tests for template field extraction and refinement.

Run inside Docker: python /app/test_template_llm_live.py
"""

import asyncio
import json
import time
import httpx
from app.config import settings

API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
MODEL = f"gpt://{settings.yandex_gpt_folder_id}/yandexgpt-lite/latest"
HEADERS = {
    "Authorization": f"Api-Key {settings.yandex_gpt_api_key}",
    "Content-Type": "application/json"
}

# Cost tracking
total_input_tokens = 0
total_output_tokens = 0
total_requests = 0


async def call_llm(system_prompt: str, user_text: str) -> dict:
    """Call YandexGPT-Lite and return parsed result with token counts."""
    global total_input_tokens, total_output_tokens, total_requests
    payload = {
        "modelUri": MODEL,
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": 500},
        "messages": [
            {"role": "system", "text": system_prompt},
            {"role": "user", "text": user_text},
        ]
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(API_URL, headers=HEADERS, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw = data["result"]["alternatives"][0]["message"]["text"]
        usage = data["result"].get("usage", {})
    elapsed = round((time.perf_counter() - t0) * 1000)

    input_tokens = int(usage.get("inputTextTokens", 0))
    output_tokens = int(usage.get("completionTokens", 0))
    total_input_tokens += input_tokens
    total_output_tokens += output_tokens
    total_requests += 1

    # Parse JSON
    parsed = None
    start = raw.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == '{': depth += 1
            elif raw[i] == '}': depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(raw[start:i+1])
                except json.JSONDecodeError:
                    pass
                break

    return {
        "raw": raw, "parsed": parsed, "elapsed_ms": elapsed,
        "input_tokens": input_tokens, "output_tokens": output_tokens,
    }


# ==================== System Prompts (WITH dative case fix) ====================
# These match production prompts in telegram_handler.py

DATIVE_HINT = (
    "ВАЖНО: client_name — это имя/фамилия клиента. Может быть в любом падеже: "
    "\"Сидорову\" → client_name: \"Сидоров\", \"Козловой\" → client_name: \"Козлова\". "
    "Всегда приводи к именительному падежу.\n"
)

SHOWING_CONFIRM_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    'Нужные поля: "client_name": Имя клиента, "address": Адрес, "date": Дата, "time": Время\n'
    + DATIVE_HINT +
    "Если есть дополнительные пожелания/заметки не из полей — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON, без пояснений. Пример:\n"
    '{"client_name": "Иванов Пётр", "address": "ул. Пионерская 12", "date": "завтра", "time": "14:00", "extra": null}\n'
    "Если какое-то поле не удалось определить — поставь null."
)

DOC_REMINDER_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    'Нужные поля: "client_name": Имя клиента, "doc_list": Список документов\n'
    + DATIVE_HINT +
    "Если поле doc_list — верни как массив строк.\n"
    "Если есть дополнительные пожелания/заметки не из полей — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON, без пояснений. Пример:\n"
    '{"client_name": "Иванов Пётр", "doc_list": ["паспорт", "справка НДФЛ"], "extra": "срок до пятницы"}\n'
    "Если какое-то поле не удалось определить — поставь null."
)

MEETING_REMINDER_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    'Нужные поля: "client_name": Имя клиента, "date": Дата, "time": Время, "address": Адрес\n'
    + DATIVE_HINT +
    "Если есть дополнительные пожелания/заметки не из полей — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON, без пояснений. Пример:\n"
    '{"client_name": "Иванов", "date": "завтра", "time": "14:00", "address": "ул. Ленина 5", "extra": null}\n'
    "Если какое-то поле не удалось определить — поставь null."
)

THANK_YOU_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    'Нужные поля: "client_name": Имя клиента\n'
    + DATIVE_HINT +
    "Если есть дополнительные пожелания/заметки не из полей — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON, без пояснений. Пример:\n"
    '{"client_name": "Иванов Пётр", "extra": null}\n'
    "Если какое-то поле не удалось определить — поставь null."
)

EVENT_SHOWING_PROMPT = (
    "Ты помощник риелтора. Из сообщения извлеки поля для создания события.\n"
    "Тип события: 🏠 Показ квартиры\n"
    'Нужные поля: "address": Адрес, "client_name": Имя клиента, "time_text": Время\n'
    + DATIVE_HINT +
    "Верни ТОЛЬКО JSON. Пример:\n"
    '{"address": "ул. Пионерская 12", "client_name": "Иванов", "time_text": "завтра в 14:00"}\n'
    "Если поле не удалось определить — поставь null."
)

EVENT_CALL_PROMPT = (
    "Ты помощник риелтора. Из сообщения извлеки поля для создания события.\n"
    "Тип события: 📞 Звонок клиенту\n"
    'Нужные поля: "client_name": Имя клиента, "time_text": Время, "topic": Тема звонка\n'
    + DATIVE_HINT +
    "Верни ТОЛЬКО JSON. Пример:\n"
    '{"client_name": "Иванов", "time_text": "сегодня в 10:00", "topic": "обсудить условия"}\n'
    "Если поле не удалось определить — поставь null."
)

REFINE_PROMPT_TPL = (
    "Ты помощник риелтора. Есть готовое сообщение для клиента:\n\n"
    "{current_text}\n\n"
    "Пользователь хочет его дополнить или изменить. "
    "Верни ТОЛЬКО обновлённый текст сообщения целиком, без пояснений. "
    "Сохрани стиль и тон оригинала. Добавь/измени только то, что просит пользователь."
)


# ==================== Test Cases ====================

TESTS = [
    # ===== ГРУППА 1: Базовые сценарии (все поля на месте) =====
    {
        "name": "1.1 Показ — все поля чётко",
        "prompt": SHOWING_CONFIRM_PROMPT,
        "input": "Иванов Пётр, ул. Пионерская 12, завтра в 14:00",
        "expect_fields": ["client_name", "address", "date", "time"],
    },
    {
        "name": "1.2 Документы — Сидорову (дат. падеж)",
        "prompt": DOC_REMINDER_PROMPT,
        "input": "Сидорову напомнить: паспорт, справка 2-НДФЛ, выписка из ЕГРН",
        "expect_fields": ["client_name", "doc_list"],
    },
    {
        "name": "1.3 Встреча — все 4 поля",
        "prompt": MEETING_REMINDER_PROMPT,
        "input": "Антон, Новочеркасская 10к4, завтра в 16",
        "expect_fields": ["client_name", "date", "time", "address"],
    },
    {
        "name": "1.4 Благодарность — только имя",
        "prompt": THANK_YOU_PROMPT,
        "input": "Марина Сергеевна",
        "expect_fields": ["client_name"],
    },

    # ===== ГРУППА 2: Доп пожелания (extra) =====
    {
        "name": "2.1 Документы — Петрову + extra",
        "prompt": DOC_REMINDER_PROMPT,
        "input": "Петрову: паспорт и свидетельство о браке, и скажи что срок до пятницы",
        "expect_fields": ["client_name", "doc_list"],
        "expect_extra": True,
    },
    {
        "name": "2.2 Показ — Козлова + extra парковка",
        "prompt": SHOWING_CONFIRM_PROMPT,
        "input": "Козлова, Литейный 30, послезавтра в 11:00, и напиши что парковка во дворе",
        "expect_fields": ["client_name", "address", "date", "time"],
        "expect_extra": True,
    },
    {
        "name": "2.3 Встреча + extra про паспорт",
        "prompt": MEETING_REMINDER_PROMPT,
        "input": "Антон, Новочеркасская 10к4 завтра в 16, и напиши чтобы паспорт не забыл",
        "expect_fields": ["client_name", "date", "time", "address"],
        "expect_extra": True,
    },

    # ===== ГРУППА 3: Нечёткие / разговорные формулировки =====
    {
        "name": "3.1 Разговорный стиль — показ",
        "prompt": SHOWING_CONFIRM_PROMPT,
        "input": "ну короче завтра в два часа покажу квартиру на проспекте Мира 15 Семёнову",
        "expect_fields": ["client_name", "address", "date", "time"],
    },
    {
        "name": "3.2 Голосовая расшифровка — документы",
        "prompt": DOC_REMINDER_PROMPT,
        "input": "надо напомнить Ивановой что нужен паспорт выписка из домовой книги и справка об отсутствии задолженности",
        "expect_fields": ["client_name", "doc_list"],
    },
    {
        "name": "3.3 Без запятых — встреча",
        "prompt": MEETING_REMINDER_PROMPT,
        "input": "Марина завтра в три на Невском 100",
        "expect_fields": ["client_name", "date", "time", "address"],
    },

    # ===== ГРУППА 4: Частичные данные =====
    {
        "name": "4.1 Показ — Васильев без даты",
        "prompt": SHOWING_CONFIRM_PROMPT,
        "input": "Васильев, Гагарина 5, в 15:00",
        "expect_fields": ["client_name", "address", "time"],
        "expect_null": ["date"],
    },
    {
        "name": "4.2 Документы — Козлову, без списка",
        "prompt": DOC_REMINDER_PROMPT,
        "input": "Козлову",
        "expect_fields": ["client_name"],
        "expect_null": ["doc_list"],
    },

    # ===== ГРУППА 5: Шаблоны событий =====
    {
        "name": "5.1 Показ квартиры — событие (Иванову)",
        "prompt": EVENT_SHOWING_PROMPT,
        "input": "Иванову на Пионерской 12 завтра в 14:00",
        "expect_fields": ["address", "client_name", "time_text"],
    },
    {
        "name": "5.2 Звонок — Сидорову",
        "prompt": EVENT_CALL_PROMPT,
        "input": "позвонить Сидорову сегодня в 10 обсудить ипотеку",
        "expect_fields": ["client_name", "time_text", "topic"],
    },
    {
        "name": "5.3 Показ — длинное описание",
        "prompt": EVENT_SHOWING_PROMPT,
        "input": "нужно показать трёшку на улице Маршала Жукова дом 15 корпус 2 квартира 45 клиенту Николаю Петровичу в пятницу в 18 30",
        "expect_fields": ["address", "client_name", "time_text"],
    },

    # ===== ГРУППА 6: Мусор / пустые / невалидные =====
    {
        "name": "6.1 Полный мусор",
        "prompt": SHOWING_CONFIRM_PROMPT,
        "input": "ааааа бббб ввввв",
        "expect_fields": [],
        "expect_all_null": True,
    },
    {
        "name": "6.2 Только эмодзи",
        "prompt": DOC_REMINDER_PROMPT,
        "input": "😊👍🏠",
        "expect_fields": [],
        "expect_all_null": True,
    },
    {
        "name": "6.3 Слишком короткое",
        "prompt": MEETING_REMINDER_PROMPT,
        "input": "да",
        "expect_fields": [],
        "expect_all_null": True,
    },
]

# ===== ГРУППА 7: Цепочка редактирования =====
REFINE_CHAIN = [
    {
        "name": "7.1 Начальный рендер встречи",
        "prompt": MEETING_REMINDER_PROMPT,
        "input": "Антон, Новочеркасская 10к4 завтра в 16",
    },
    {
        "name": "7.2 Добавить про паспорт",
        "refine": "и напиши чтобы паспорт не забыл",
    },
    {
        "name": "7.3 Добавить номер телефона",
        "refine": "добавь мой номер +7-999-123-45-67 на случай если заблудится",
    },
    {
        "name": "7.4 Сменить тон на более формальный",
        "refine": "сделай более официальным тоном",
    },
]


async def run_tests():
    print("=" * 70)
    print("LIVE LLM TEMPLATE TESTS (with dative case fix + cost tracking)")
    print(f"Model: {MODEL}")
    print("=" * 70)

    passed = 0
    failed = 0
    errors = 0
    times = []

    for test in TESTS:
        print(f"\n{'─' * 60}")
        print(f"TEST: {test['name']}")
        print(f"INPUT: {test['input'][:80]}")

        try:
            result = await call_llm(test["prompt"], test["input"])
            parsed = result["parsed"]
            times.append(result["elapsed_ms"])

            print(f"TIME: {result['elapsed_ms']}ms | tokens: {result['input_tokens']}→{result['output_tokens']}")
            print(f"PARSED: {json.dumps(parsed, ensure_ascii=False, indent=2) if parsed else 'NONE'}")

            # Validate
            ok = True
            issues = []

            if test.get("expect_all_null"):
                if parsed:
                    non_null = [k for k, v in parsed.items() if v is not None and k != "extra"]
                    if non_null:
                        issues.append(f"Expected all null but got: {non_null}")
                        ok = False
            elif parsed is None:
                issues.append("Failed to parse JSON from response")
                ok = False
            else:
                for field in test.get("expect_fields", []):
                    val = parsed.get(field)
                    if val is None or val == "null":
                        issues.append(f"Missing field: {field}")
                        ok = False

                for field in test.get("expect_null", []):
                    val = parsed.get(field)
                    if val is not None and val != "null":
                        issues.append(f"Expected null for {field}, got: {val}")

                if test.get("expect_extra"):
                    extra = parsed.get("extra")
                    if not extra or extra == "null":
                        issues.append("Expected extra field but got null")
                        ok = False

            if ok:
                print("RESULT: ✅ PASS")
                passed += 1
            else:
                print(f"RESULT: ❌ FAIL — {'; '.join(issues)}")
                failed += 1

        except Exception as e:
            print(f"RESULT: 💥 ERROR — {e}")
            errors += 1

    # ===== Refine chain =====
    print(f"\n{'=' * 60}")
    print("REFINE CHAIN TEST")
    print(f"{'=' * 60}")

    current_text = None
    for step in REFINE_CHAIN:
        print(f"\n{'─' * 50}")
        print(f"STEP: {step['name']}")

        try:
            if "prompt" in step:
                print(f"INPUT: {step['input']}")
                result = await call_llm(step["prompt"], step["input"])
                parsed = result["parsed"]
                times.append(result["elapsed_ms"])

                print(f"TIME: {result['elapsed_ms']}ms | tokens: {result['input_tokens']}→{result['output_tokens']}")
                print(f"PARSED: {json.dumps(parsed, ensure_ascii=False, indent=2) if parsed else 'NONE'}")

                if parsed:
                    name = parsed.get("client_name", "[Имя]")
                    date = parsed.get("date", "[Дата]")
                    time_ = parsed.get("time", "[Время]")
                    addr = parsed.get("address", "[Адрес]")
                    current_text = (
                        f"{name}, напоминаю о нашей встрече {date} в {time_}.\n"
                        f"Адрес: {addr}\nДо встречи!"
                    )
                    print(f"RENDERED:\n{current_text}")
                    passed += 1
                else:
                    print("RESULT: ❌ FAIL — no parsed data")
                    failed += 1
            else:
                print(f"REFINE: {step['refine']}")
                refine_prompt = REFINE_PROMPT_TPL.format(current_text=current_text)

                result = await call_llm(refine_prompt, step["refine"])
                refined = result["raw"].strip()
                times.append(result["elapsed_ms"])

                print(f"TIME: {result['elapsed_ms']}ms | tokens: {result['input_tokens']}→{result['output_tokens']}")
                print(f"REFINED:\n{refined}")

                if len(refined) > 10 and refined != current_text:
                    current_text = refined
                    print("RESULT: ✅ PASS — text updated")
                    passed += 1
                else:
                    print("RESULT: ❌ FAIL — text not changed")
                    failed += 1

        except Exception as e:
            print(f"RESULT: 💥 ERROR — {e}")
            errors += 1

    # ===== Summary & Cost =====
    total = passed + failed + errors
    avg_time = round(sum(times) / len(times)) if times else 0

    # YandexGPT Lite pricing (as of 2026):
    # Input:  0.20 ₽ / 1000 tokens
    # Output: 0.40 ₽ / 1000 tokens
    input_cost = total_input_tokens * 0.20 / 1000
    output_cost = total_output_tokens * 0.40 / 1000
    total_cost = input_cost + output_cost
    cost_per_request = total_cost / total_requests if total_requests else 0

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed, {errors} errors")
    print(f"{'─' * 70}")
    print(f"PERFORMANCE:")
    print(f"  Avg latency:    {avg_time}ms")
    print(f"  Total requests: {total_requests}")
    print(f"{'─' * 70}")
    print(f"TOKEN USAGE:")
    print(f"  Input tokens:   {total_input_tokens}")
    print(f"  Output tokens:  {total_output_tokens}")
    print(f"  Total tokens:   {total_input_tokens + total_output_tokens}")
    print(f"{'─' * 70}")
    print(f"COST (YandexGPT Lite: 0.20₽/1K input, 0.40₽/1K output):")
    print(f"  Input cost:     {input_cost:.4f} ₽")
    print(f"  Output cost:    {output_cost:.4f} ₽")
    print(f"  Total cost:     {total_cost:.4f} ₽")
    print(f"  Per request:    {cost_per_request:.4f} ₽ (~{cost_per_request*100:.2f} коп.)")
    print(f"{'─' * 70}")
    print(f"DIALOG COST ESTIMATE (typical 3-5 LLM calls per dialog):")
    print(f"  1 template fill:           ~{cost_per_request:.4f} ₽")
    print(f"  Fill + 1 edit:             ~{cost_per_request*2:.4f} ₽")
    print(f"  Fill + 3 edits:            ~{cost_per_request*4:.4f} ₽")
    print(f"  10 dialogs/day:            ~{cost_per_request*2*10:.4f} ₽")
    print(f"  100 dialogs/day:           ~{cost_per_request*2*100:.3f} ₽")
    print(f"  1000 dialogs/day:          ~{cost_per_request*2*1000:.2f} ₽")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(run_tests())
