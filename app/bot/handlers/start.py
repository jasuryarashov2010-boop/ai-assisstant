from __future__ import annotations

import logging
from sqlalchemy import select
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.keyboards.common import LABELS, ai_menu, main_reply, plan_menu, support_menu
from app.bot.states import AIChat
from app.config import get_settings
from app.core.texts import TEXT
from app.db.models import Channel, Referral, User
from app.services.usage import get_or_create_usage, get_plan

router = Router(name="start")
settings = get_settings()
log = logging.getLogger(__name__)


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:uz"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
    ])


async def home_text(user: User, db) -> str:
    plan = await get_plan(db, user.plan_code if user.plan_code in {"free", "pro", "comfort"} else "free")
    usage = await get_or_create_usage(db, user.id)
    lang = user.language or "uz"
    plan_name = {"uz": plan.name_uz, "en": plan.name_en, "ru": plan.name_ru}[lang]
    return TEXT[lang]["home"].format(plan=plan_name, used=usage.ai_requests, limit=plan.daily_ai_limit, tickets=usage.tickets_created, ticket_limit=plan.daily_ticket_limit)


async def register_referral(message: Message, user: User, db) -> None:
    payload = (message.text or "").split(" ", 1)[1].strip() if " " in (message.text or "") else ""
    if not payload.startswith("ref_") or not payload[4:].isdigit():
        return
    inviter_id = int(payload[4:])
    if inviter_id == user.telegram_id:
        return
    inviter = await db.scalar(select(User).where(User.telegram_id == inviter_id))
    if inviter is None:
        return
    existing = await db.scalar(select(Referral).where(Referral.inviter_id == inviter.id, Referral.invited_id == user.id))
    if existing is None:
        db.add(Referral(inviter_id=inviter.id, invited_id=user.id))
        inviter.referrals_count += 1
        await db.commit()


@router.message(CommandStart())
async def start(message: Message, user: User, db, state: FSMContext):
    await state.clear()
    await register_referral(message, user, db)
    if not user.language:
        await message.answer(TEXT["uz"]["choose_lang"], reply_markup=lang_kb(), parse_mode="HTML")
        return
    await message.answer(await home_text(user, db), reply_markup=main_reply(message.from_user.id in settings.admin_id_set, user.language), parse_mode="HTML")


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, user: User, db, state: FSMContext):
    language = callback.data.split(":", 1)[1]
    if language not in {"uz", "en", "ru"}:
        return await callback.answer("Invalid language", show_alert=True)
    await state.clear()
    user.language = language
    await db.commit()
    await callback.message.edit_text(await home_text(user, db), parse_mode="HTML", reply_markup=__import__("app.bot.keyboards.common", fromlist=["back_menu"]).back_menu("nav:main", language))
    await callback.message.answer(TEXT[language]["language_saved"], reply_markup=main_reply(callback.from_user.id in settings.admin_id_set, language), parse_mode="HTML")
    await callback.answer()


@router.message(Command("language"))
async def language_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXT["uz"]["choose_lang"], reply_markup=lang_kb(), parse_mode="HTML")


@router.message(F.text.in_({v for labels in LABELS.values() for v in labels.values()}))
async def reply_navigation(message: Message, user: User, db, state: FSMContext):
    text = message.text or ""
    await state.clear()
    for lang, labels in LABELS.items():
        if text == labels["ai"]:
            await message.answer(TEXT[lang if user.language == lang else user.language]["ai_menu"], reply_markup=ai_menu(user.language), parse_mode="HTML")
            return
        if text == labels["support"]:
            await message.answer(TEXT[user.language]["support_menu"], reply_markup=support_menu(user.language), parse_mode="HTML")
            return
        if text == labels["profile"]:
            from app.bot.handlers.user import profile_screen
            await profile_screen(message, user, db)
            return
        if text == labels["plans"]:
            from app.bot.handlers.user import plans_screen
            await plans_screen(message, user, db)
            return
        if text == labels["settings"]:
            await message.answer(TEXT[user.language]["settings"], reply_markup=__import__("app.bot.keyboards.common", fromlist=["back_menu"]).back_menu("nav:main", user.language), parse_mode="HTML")
            return
        if text == labels["ref"]:
            from app.bot.handlers.user import referral_screen
            await referral_screen(message, user, db)
            return
        if text == labels["refresh"]:
            await message.answer(await home_text(user, db), reply_markup=main_reply(message.from_user.id in settings.admin_id_set, user.language), parse_mode="HTML")
            return
        if text == labels["admin"] and message.from_user.id in settings.admin_id_set:
            from app.admin.handlers import show_admin_menu
            await show_admin_menu(message)
            return


@router.callback_query(F.data == "nav:main")
async def nav_main(callback: CallbackQuery, user: User, db, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(await home_text(user, db), parse_mode="HTML")
    await callback.message.answer(TEXT[user.language]["main_ready"], reply_markup=main_reply(callback.from_user.id in settings.admin_id_set, user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "nav:ai")
async def nav_ai(callback: CallbackQuery, user: User, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(TEXT[user.language]["ai_menu"], reply_markup=ai_menu(user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "nav:support")
async def nav_support(callback: CallbackQuery, user: User, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(TEXT[user.language]["support_menu"], reply_markup=support_menu(user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "nav:profile")
async def nav_profile(callback: CallbackQuery, user: User, db, state: FSMContext):
    await state.clear()
    from app.bot.handlers.user import render_profile_text
    await callback.message.edit_text(await render_profile_text(user, db), parse_mode="HTML", reply_markup=__import__("app.bot.keyboards.common", fromlist=["back_menu"]).back_menu("nav:main", user.language))
    await callback.answer()


@router.callback_query(F.data == "check:sub")
async def check_subscription(callback: CallbackQuery, user: User, db, state: FSMContext):
    await state.clear()
    channels = (await db.scalars(select(Channel).where(Channel.is_active))).all()
    missing = []
    for channel in channels:
        try:
            member = await callback.bot.get_chat_member(channel.chat_id, callback.from_user.id)
            if member.status in {"left", "kicked"}:
                missing.append(channel)
        except Exception:
            missing.append(channel)
    if missing:
        await callback.answer("❌ Hali barcha kanallarga obuna bo‘lmagansiz.", show_alert=True)
        return
    if not user.language:
        await callback.message.answer(TEXT["uz"]["choose_lang"], reply_markup=lang_kb(), parse_mode="HTML")
    else:
        await callback.message.answer(await home_text(user, db), reply_markup=main_reply(callback.from_user.id in settings.admin_id_set, user.language), parse_mode="HTML")
    await callback.answer("✅ Obuna tasdiqlandi")
