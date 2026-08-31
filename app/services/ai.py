from io import BytesIO
from typing import Any
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def chat(self, messages: list[dict[str, str]], knowledge: str = '') -> str:
        if not self.client:
            return '⚠️ <b>AI API sozlanmagan.</b> Admin <code>OPENAI_API_KEY</code> ni Render Environment Variables orqali kiritsin.'
        system = (
            'You are a helpful multilingual Telegram AI assistant. Answer in the user\'s language. '
            'Be concise unless detail is requested. Do not invent facts. Use HTML-safe plain text; avoid raw Telegram HTML unless asked.'
        )
        if knowledge:
            system += '\nKnowledge base context:\n' + knowledge[:12000]
        response = await self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[{'role':'system','content':system}, *messages[-20:]],
            temperature=0.4,
        )
        return response.choices[0].message.content or 'Javob olinmadi.'

    async def transcribe(self, filename: str, data: bytes) -> str:
        if not self.client:
            return 'AI API sozlanmagan.'
        file_obj = BytesIO(data); file_obj.name = filename
        result = await self.client.audio.transcriptions.create(model=settings.openai_transcribe_model, file=file_obj)
        return result.text

    async def generate_image(self, prompt: str):
        if not self.client:
            return None
        result = await self.client.images.generate(model=settings.openai_image_model, prompt=prompt, size='1024x1024')
        item = result.data[0]
        if getattr(item, 'b64_json', None):
            return BytesIO(__import__('base64').b64decode(item.b64_json))
        return None

    async def learning(self, task: str, language: str='uz') -> str:
        prompt = f'''You are an AI tutor for a Telegram bot administrator. Language: {language}.\nTask: {task}\nReturn practical, structured content with examples. If code is requested, make it complete and explain dependencies. Include useful tags.'''
        return await self.chat([{'role':'user','content':prompt}])

ai_service = AIService()
