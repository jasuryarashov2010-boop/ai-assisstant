from __future__ import annotations

from datetime import datetime, timezone
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from app.config import get_settings
from app.db.models import User
from app.db.session import SessionLocal

settings = get_settings()

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        tg = data.get("event_from_user")
        if not tg:
            return await handler(event, data)
        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.telegram_id == tg.id))
            if user is None:
                user = User(telegram_id=tg.id, username=tg.username, full_name=tg.full_name, language="")
                session.add(user)
                await session.flush()
            user.username = tg.username
            user.full_name = tg.full_name
            user.last_active_at = datetime.now(timezone.utc)
            await session.commit()
            data["db"] = session
            data["user"] = user
            if user.is_banned and tg.id not in settings.admin_id_set:
                return
            return await handler(event, data)
