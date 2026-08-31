from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery
from sqlalchemy import select
from app.db.models import Channel
from app.db.session import SessionLocal
from app.bot.keyboards.common import subscription_kb

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data):
        user=data.get('user')
        if not user: return await handler(event,data)
        tg=data.get('event_from_user')
        if tg and tg.id in __import__('app.config',fromlist=['get_settings']).get_settings().admin_id_set:
            return await handler(event,data)
        if isinstance(event, CallbackQuery) and event.data == 'check:sub':
            return await handler(event,data)
        async with SessionLocal() as session:
            channels=(await session.scalars(select(Channel).where(Channel.is_active))).all()
            missing=[]
            for c in channels:
                try:
                    member=await data['bot'].get_chat_member(c.chat_id,tg.id)
                    if member.status in ('left','kicked'): missing.append(c)
                except Exception: missing.append(c)
            if missing:
                msg=getattr(event,'message',None)
                if msg: await msg.answer('📢 <b>Botdan foydalanish uchun kanallarga obuna bo‘ling.</b>\n\nObuna bo‘lgach, <b>✅ Obunani tekshirish</b> tugmasini bosing.',reply_markup=subscription_kb(missing),parse_mode='HTML')
                elif getattr(event,'callback_query',None): await event.callback_query.answer('Avval majburiy kanallarga obuna bo‘ling.',show_alert=True)
                return
        return await handler(event,data)
