from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Any

from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)


class AIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=90.0, max_retries=2) if settings.openai_api_key else None

    @property
    def configured(self) -> bool:
        return self.client is not None

    @staticmethod
    def _system(knowledge: str = "", mode: str = "chat") -> str:
        mode_rules = {
            "translate": "Act as a precise translator. Preserve meaning, tone and formatting. Do not add commentary unless useful.",
            "study": "Act as a patient tutor. Explain step-by-step, use examples, and check understanding.",
            "coding": "Act as a senior software engineer. Give runnable code, explain dependencies, detect edge cases and avoid invented APIs.",
            "data": "Act as a careful data analyst. State assumptions and distinguish observed facts from guesses.",
        }
        text = (
            "You are a helpful multilingual Telegram AI assistant. Answer in the user's language. "
            "Prefer clear sections, concise paragraphs and practical examples. "
            "Return plain text/Markdown-like text; the application will escape Telegram HTML.\n\n"
            + mode_rules.get(mode, "For normal chat, be direct, friendly and useful.")
        )
        if knowledge:
            text += "\n\nRelevant knowledge base context:\n" + knowledge[:10000]
        return text

    async def chat(self, messages: list[dict[str, Any]], knowledge: str = "", mode: str = "chat") -> str:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        try:
            if hasattr(self.client, "responses"):
                response = await self.client.responses.create(
                    model=settings.openai_chat_model,
                    instructions=self._system(knowledge, mode),
                    input=messages[-24:],
                )
                text = getattr(response, "output_text", None)
                if text:
                    return text.strip()

            response = await self.client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=[{"role": "system", "content": self._system(knowledge, mode)}, *messages[-24:]],
            )
            text = response.choices[0].message.content or ""
            if not text.strip():
                raise RuntimeError("AI returned an empty response")
            return text.strip()
        except Exception:
            log.exception("AI chat request failed")
            raise

    async def transcribe(self, filename: str, data: bytes) -> str:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        file_obj = BytesIO(data)
        file_obj.name = filename
        result = await self.client.audio.transcriptions.create(model=settings.openai_transcribe_model, file=file_obj)
        return (result.text or "").strip()

    async def vision(self, prompt: str, data: bytes, mime: str = "image/jpeg") -> str:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        b64 = base64.b64encode(data).decode("ascii")
        if hasattr(self.client, "responses"):
            response = await self.client.responses.create(
                model=settings.openai_chat_model,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                    ],
                }],
            )
            text = getattr(response, "output_text", None)
            if text:
                return text.strip()
        response = await self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]}],
        )
        return (response.choices[0].message.content or "").strip()

    async def generate_image(self, prompt: str) -> BytesIO | None:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        result = await self.client.images.generate(model=settings.openai_image_model, prompt=prompt, size="1024x1024")
        item = result.data[0]
        if getattr(item, "b64_json", None):
            return BytesIO(base64.b64decode(item.b64_json))
        return None

    async def learning(self, task: str, language: str = "uz") -> str:
        return await self.chat([{"role": "user", "content": task}], mode="coding" if "cod" in task.lower() else "chat")


ai_service = AIService()
