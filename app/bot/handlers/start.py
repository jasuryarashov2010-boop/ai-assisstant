from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func
from app.bot.keyboards.common import main_reply
from app.core.texts import TEXT
from app.db.models import Channel, Ticket, Rating
from app.db.session import SessionLocal
from app.services.usage import get_plan, get_or_create_usage
from app.config import get_settings

router=Router(); settings=get_settings()

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='🇺🇿 O‘zbekcha',callback_data='lang:uz'),InlineKeyboardButton(text='🇬🇧 English',callback_data='lang:en')],[InlineKeyboardButton(text='🇷🇺 Русский',callback_data='lang:ru')]])

async def welcome_text(user, db):
    plan=await get_plan(db,user.plan_code if user.plan_code in ('free','pro','comfort') else 'free')
    usage=await get_or_create_usage(db,user.id)
    return TEXT[user.language]['welcome'].format(plan=plan.name_uz if user.language=='uz' else plan.name_en if user.language=='en' else plan.name_ru,used=usage.ai_requests,limit=plan.daily_ai_limit)

@router.message(CommandStart())
async def start(message:Message,user,db):
    if message.text and ' ' in message.text:
        payload=message.text.split(' ',1)[1].strip()
        if payload.startswith('ref_') and payload[4:].isdigit() and int(payload[4:]) != user.telegram_id:
            from app.db.models import Referral, User
            inviter=await db.scalar(select(User).where(User.telegram_id==int(payload[4:])))
            if inviter and not await db.scalar(select(Referral).where(Referral.inviter_id==inviter.id,Referral.invited_id==user.id)):
                db.add(Referral(inviter_id=inviter.id,invited_id=user.id)); inviter.referrals_count += 1; await db.commit()
    if user.language not in ('uz','en','ru'):
        await message.answer(TEXT['uz']['choose_lang'],reply_markup=lang_kb(),parse_mode='HTML'); return
    await message.answer(await welcome_text(user,db),reply_markup=main_reply(message.from_user.id in settings.admin_id_set,user.language or 'uz'),parse_mode='HTML')

@router.callback_query(F.data.startswith('lang:'))
async def set_lang(c:CallbackQuery,user,db):
    user.language=c.data.split(':')[1]; await db.commit()
    await c.message.edit_text(await welcome_text(user,db),parse_mode='HTML')
    await c.message.answer('✅ Til saqlandi.',reply_markup=main_reply(c.from_user.id in settings.admin_id_set,user.language or 'uz'))
    await c.answer()


@router.message(F.text=='/language')
async def language_command(message:Message): await message.answer(TEXT['uz']['choose_lang'],reply_markup=lang_kb(),parse_mode='HTML')

@router.message(F.text.in_({'🔄 Yangilash','🔄 Refresh','🔄 Обновить'}))
async def refresh(message:Message,user,db): await message.answer(await welcome_text(user,db),reply_markup=main_reply(message.from_user.id in settings.admin_id_set,user.language or 'uz'),parse_mode='HTML')


@router.callback_query(F.data=='check:sub')
async def check_subscription(c:CallbackQuery, user, db):
    from app.db.models import Channel
    channels=(await db.scalars(select(Channel).where(Channel.is_active))).all()
    missing=[]
    for ch in channels:
        try:
            member=await c.bot.get_chat_member(ch.chat_id,c.from_user.id)
            if member.status in ('left','kicked'): missing.append(ch)
        except Exception: missing.append(ch)
    if missing:
        await c.answer('❌ Hali barcha kanallarga obuna bo‘lmagansiz.',show_alert=True); return
    await c.answer('✅ Obuna tasdiqlandi.')
    if not user.language:
        await c.message.answer(TEXT['uz']['choose_lang'],reply_markup=lang_kb(),parse_mode='HTML')
    else:
        await c.message.answer(await welcome_text(user,db),reply_markup=main_reply(c.from_user.id in settings.admin_id_set,user.language or 'uz'),parse_mode='HTML')
