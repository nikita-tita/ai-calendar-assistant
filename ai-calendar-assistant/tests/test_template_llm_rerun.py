"""Rerun only the failed tests with fixed prompt."""

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


async def call_llm(system_prompt: str, user_text: str) -> dict:
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
        raw = resp.json()["result"]["alternatives"][0]["message"]["text"]
    elapsed = round((time.perf_counter() - t0) * 1000)
    parsed = None
    start = raw.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == '{': depth += 1
            elif raw[i] == '}': depth -= 1
            if depth == 0:
                try: parsed = json.loads(raw[start:i+1])
                except: pass
                break
    return {"raw": raw, "parsed": parsed, "elapsed_ms": elapsed}


# Fixed prompt with dative case hint
DOC_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    '"client_name": Имя клиента, "doc_list": Список документов\n'
    "ВАЖНО: client_name — это имя/фамилия клиента. Может быть в любом падеже: "
    '"Сидорову" → client_name: "Сидоров", "Козловой" → client_name: "Козлова". '
    "Всегда приводи к именительному падежу.\n"
    "Если поле doc_list — верни как массив строк.\n"
    "Если есть дополнительные пожелания — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON. Если поле не найдено — null."
)

SHOWING_PROMPT = (
    "Ты помощник риелтора. Из сообщения пользователя извлеки поля для шаблона.\n"
    '"client_name": Имя клиента, "address": Адрес, "date": Дата, "time": Время\n'
    "ВАЖНО: client_name — это имя/фамилия клиента. Может быть в любом падеже: "
    '"Сидорову" → client_name: "Сидоров", "Козловой" → client_name: "Козлова". '
    "Всегда приводи к именительному падежу.\n"
    "Если есть дополнительные пожелания — верни в поле \"extra\".\n"
    "Верни ТОЛЬКО JSON. Если поле не найдено — null."
)

TESTS = [
    {
        "name": "FIX 1.2 Документы — Сидорову (дат. падеж)",
        "prompt": DOC_PROMPT,
        "input": "Сидорову напомнить: паспорт, справка 2-НДФЛ, выписка из ЕГРН",
    },
    {
        "name": "FIX 2.1 Документы — Петрову + extra",
        "prompt": DOC_PROMPT,
        "input": "Петрову: паспорт и свидетельство о браке, и скажи что срок до пятницы",
    },
    {
        "name": "FIX 2.2 Показ — Козлова + extra",
        "prompt": SHOWING_PROMPT,
        "input": "Козлова, Литейный 30, послезавтра в 11:00, и напиши что парковка во дворе",
    },
    {
        "name": "FIX 4.1 Показ — Васильев без даты",
        "prompt": SHOWING_PROMPT,
        "input": "Васильев, Гагарина 5, в 15:00",
    },
    # Extra edge cases
    {
        "name": "EDGE: двойная фамилия",
        "prompt": DOC_PROMPT,
        "input": "Ивановой-Петровой нужен паспорт и СНИЛС",
    },
    {
        "name": "EDGE: имя + отчество в дательном",
        "prompt": SHOWING_PROMPT,
        "input": "Николаю Петровичу показ на Ленина 5 в среду в 12",
    },
    {
        "name": "EDGE: только имя без фамилии",
        "prompt": DOC_PROMPT,
        "input": "Маше надо собрать справку из банка и выписку",
    },
]


async def run():
    print("=" * 60)
    print("RERUN FAILED TESTS (with fixed prompt)")
    print("=" * 60)

    for test in TESTS:
        print(f"\n{'─' * 50}")
        print(f"TEST: {test['name']}")
        print(f"INPUT: {test['input']}")

        result = await call_llm(test["prompt"], test["input"])
        parsed = result["parsed"]

        print(f"TIME: {result['elapsed_ms']}ms")
        print(f"PARSED: {json.dumps(parsed, ensure_ascii=False, indent=2) if parsed else 'NONE'}")

        if parsed and parsed.get("client_name"):
            print(f"✅ client_name = {parsed['client_name']}")
        else:
            print("❌ client_name MISSING")

        if parsed and parsed.get("extra"):
            print(f"📝 extra = {parsed['extra']}")


if __name__ == "__main__":
    asyncio.run(run())
