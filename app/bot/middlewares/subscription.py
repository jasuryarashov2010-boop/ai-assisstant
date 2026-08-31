from __future__ import annotations
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject
from sqlalchemy import select
from app.bot.keyboards.common import subscription_kb
from app.config import get_settings
from app.db.models import Channel
from app.db.session import SessionLocal

settings = get_settings()

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user = data.get("user"); tg = data.get("event_from_user")
        if not user or not tg or tg.id in settings.admin_id_set:
            return await handler(event, data)
        if isinstance(event, CallbackQuery) and event.data == "check:sub":
            return await handler(event, data)
        async with SessionLocal() as session:
            channels = (await session.scalars(select(Channel).where(Channel.is_active))).all()
            missing = []
            for channel in channels:
                try:
                    member = await data["bot"].get_chat_member(channel.chat_id, tg.id)
                    if member.status in {"left", "kicked"}:
                        missing.append(channel)
                except Exception:
                    missing.append(channel)
        if missing:
            if hasattr(event, "answer"):
                try:
                    await event.answer("📢 Avval majburiy kanallarga obuna bo‘ling.", show_alert=False)
                except Exception:
                    pass
            if getattr(event, "message", None):
                await event.message.answer("<b>📢 Majburiy obuna</b>\n\nBotdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=subscription_kb(missing, user.language or "uz"), parse_mode="HTML")
            return
        return await handler(event, data)
