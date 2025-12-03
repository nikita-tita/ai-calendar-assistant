# Deprecated OpenAI & Anthropic Services

This folder contains old service files that used OpenAI and Anthropic APIs.

**Status**: DEPRECATED (not used in production)

## Files

- `llm_agent.py` - Old LLM agent using Anthropic Claude
- `llm_agent_openai.py` - OpenAI-based LLM agent
- `stt.py` - Speech-to-Text using OpenAI Whisper

## Current Services (Yandex-based)

The project now uses Yandex services instead:

- **LLM**: `app/services/llm_agent_yandex.py` - Yandex GPT for NLP
- **STT**: `app/services/stt_yandex.py` - Yandex SpeechKit for voice

## Why Deprecated?

OpenAI and Anthropic APIs:
- Don't work well from Russia (VPN required)
- More expensive for Russian language
- Yandex services are better optimized for Russian

## Migration Date

- Deprecated: 2025-10-15
- Replaced with Yandex services

---

**Note**: These files are kept for reference only. Do NOT use in production.
