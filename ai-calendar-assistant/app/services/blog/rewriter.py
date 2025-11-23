"""Article rewriting service using Yandex GPT."""

import json
import re
from typing import Optional
import requests
import structlog

from app.config import settings
from app.schemas.blog import RewriteRequest, RewriteResponse

logger = structlog.get_logger()


class YandexGPTRewriter:
    """Rewrite articles using Yandex GPT."""

    def __init__(self):
        """Initialize Yandex GPT rewriter."""
        self.api_key = settings.yandex_gpt_api_key
        self.folder_id = settings.yandex_gpt_folder_id
        self.model = "yandexgpt"  # or "yandexgpt-lite" for faster
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

        self.system_prompt = """Ты - профессиональный копирайтер и рерайтер статей для недвижимости.

Твоя задача:
1. Перепиши статью своими словами, сохраняя ключевые факты и информацию
2. Сделай текст уникальным (не копируй фразы напрямую из оригинала)
3. Сохрани структуру статьи с заголовками и подзаголовками
4. Используй markdown разметку для форматирования:
   - # для главного заголовка
   - ## для подзаголовков
   - ### для подподзаголовков
   - Обычные параграфы разделяй пустой строкой
   - **жирный текст** для акцентов
   - Списки с - или 1., 2., 3.
5. Пиши живым, понятным языком
6. Сохрани тему недвижимости (квартиры, дома, аренда, покупка, рынок)
7. НЕ пиши текст одним сплошным абзацем - обязательно разбивай на параграфы
8. Идеальный размер параграфа - 3-5 предложений

ВАЖНО:
- НЕ добавляй свои комментарии и пояснения
- Верни ТОЛЬКО переписанный текст в markdown формате
- НЕ используй фразы типа "Вот переписанная статья", "Ниже представлен текст" и т.п.
- Начни сразу с содержания статьи

Пример правильного форматирования:

# Заголовок статьи

Первый параграф вводной части статьи. Здесь несколько предложений о теме.

Второй параграф с продолжением мысли. Еще немного информации.

## Подзаголовок раздела

Параграф с раскрытием темы раздела. **Важный момент** можно выделить.

Следующий параграф этого раздела.

## Второй раздел

И так далее...

### Подраздел

Текст подраздела.

Помни: каждый параграф - отдельная мысль или аспект темы!
"""

    async def rewrite_article(
        self,
        original_content: str,
        title: str,
        preserve_structure: bool = True,
        target_length: Optional[int] = None
    ) -> RewriteResponse:
        """Rewrite article using Yandex GPT.

        Args:
            original_content: Original article text
            title: Original article title
            preserve_structure: Whether to preserve article structure
            target_length: Target word count (optional)

        Returns:
            RewriteResponse with rewritten content and metadata
        """
        try:
            logger.info("rewriting_article", title=title, original_length=len(original_content))

            # Build user prompt
            user_prompt = f"""Оригинальный заголовок: {title}

Оригинальная статья:
{original_content}

---

Перепиши эту статью своими словами, сохраняя структуру и ключевую информацию."""

            if target_length:
                user_prompt += f"\n\nЦелевой объем: примерно {target_length} слов."

            if not preserve_structure:
                user_prompt += "\n\nМожешь изменить структуру статьи для лучшей читаемости."

            # Call Yandex GPT API
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.7,  # Higher temperature for more creative rewriting
                    "maxTokens": 4000  # Enough for long articles
                },
                "messages": [
                    {
                        "role": "system",
                        "text": self.system_prompt
                    },
                    {
                        "role": "user",
                        "text": user_prompt
                    }
                ]
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60  # Longer timeout for article rewriting
            )

            if response.status_code != 200:
                logger.error("yandex_gpt_rewrite_error",
                           status_code=response.status_code,
                           response=response.text)
                raise Exception(f"Yandex GPT API error: {response.status_code} - {response.text}")

            response_data = response.json()
            rewritten_text = response_data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")

            if not rewritten_text:
                raise Exception("Empty response from Yandex GPT")

            # Clean up the response (remove any meta comments)
            rewritten_text = self._clean_response(rewritten_text)

            logger.info("article_rewritten",
                       original_length=len(original_content),
                       rewritten_length=len(rewritten_text))

            # Generate summary and meta description
            summary = await self._generate_summary(rewritten_text, title)
            meta_description = await self._generate_meta_description(rewritten_text, title)
            suggested_title = await self._generate_title(rewritten_text, title)

            return RewriteResponse(
                rewritten_content=rewritten_text,
                summary=summary,
                suggested_title=suggested_title,
                meta_description=meta_description
            )

        except Exception as e:
            logger.error("rewrite_article_error", error=str(e), title=title)
            raise

    def _clean_response(self, text: str) -> str:
        """Clean up GPT response from meta comments.

        Args:
            text: Raw response text

        Returns:
            Cleaned text
        """
        # Remove common meta phrases
        meta_phrases = [
            r'^вот переписанная статья:?\s*\n*',
            r'^переписанная статья:?\s*\n*',
            r'^ниже представлен.*?:?\s*\n*',
            r'^вот текст.*?:?\s*\n*',
            r'^готовая статья:?\s*\n*',
        ]

        cleaned = text.strip()
        for pattern in meta_phrases:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        return cleaned.strip()

    async def _generate_summary(self, content: str, original_title: str) -> str:
        """Generate article summary.

        Args:
            content: Article content
            original_title: Original article title

        Returns:
            Article summary (2-3 sentences)
        """
        try:
            prompt = f"""Напиши краткое описание этой статьи (2-3 предложения) для превью:

Заголовок: {original_title}

Статья:
{content[:1000]}...

Верни ТОЛЬКО описание без лишних фраз."""

            response = await self._call_yandex_gpt(prompt, temperature=0.5, max_tokens=200)
            return response.strip()

        except Exception as e:
            logger.error("generate_summary_error", error=str(e))
            # Fallback: first paragraph
            paragraphs = content.split('\n\n')
            for p in paragraphs:
                if len(p) > 50 and not p.startswith('#'):
                    return p[:300] + '...'
            return original_title

    async def _generate_meta_description(self, content: str, original_title: str) -> str:
        """Generate SEO meta description.

        Args:
            content: Article content
            original_title: Original article title

        Returns:
            Meta description (up to 160 characters)
        """
        try:
            prompt = f"""Напиши SEO meta description для этой статьи (максимум 160 символов):

Заголовок: {original_title}

Статья:
{content[:1000]}...

Верни ТОЛЬКО meta description без кавычек и лишних слов."""

            response = await self._call_yandex_gpt(prompt, temperature=0.5, max_tokens=100)
            description = response.strip()

            # Ensure it's not too long
            if len(description) > 160:
                description = description[:157] + '...'

            return description

        except Exception as e:
            logger.error("generate_meta_description_error", error=str(e))
            return original_title[:160]

    async def _generate_title(self, content: str, original_title: str) -> str:
        """Generate alternative article title.

        Args:
            content: Article content
            original_title: Original article title

        Returns:
            Alternative title
        """
        try:
            prompt = f"""Предложи улучшенный заголовок для этой статьи:

Оригинальный заголовок: {original_title}

Начало статьи:
{content[:500]}...

Требования к заголовку:
- Цепляющий и информативный
- Не более 10 слов
- Отражает суть статьи

Верни ТОЛЬКО новый заголовок без кавычек."""

            response = await self._call_yandex_gpt(prompt, temperature=0.6, max_tokens=100)
            return response.strip()

        except Exception as e:
            logger.error("generate_title_error", error=str(e))
            return original_title

    async def _call_yandex_gpt(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Make a simple call to Yandex GPT.

        Args:
            prompt: User prompt
            temperature: Model temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}/latest",
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": max_tokens
            },
            "messages": [
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Yandex GPT API error: {response.status_code}")

        response_data = response.json()
        return response_data.get("result", {}).get("alternatives", [{}])[0].get("message", {}).get("text", "")


# Global instance
yandex_gpt_rewriter = YandexGPTRewriter()
