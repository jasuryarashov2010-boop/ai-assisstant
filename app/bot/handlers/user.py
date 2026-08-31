from __future__ import annotations

import asyncio
import html as pyhtml
import logging
from io import BytesIO
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func

from app.bot.keyboards.common import ai_chat_menu, ai_menu, back_menu, chat_history, plan_menu, rating_kb, ticket_list, ticket_view
from app.bot.keyboards.common import support_menu as support_kb
from app.bot.states import AIChat, Feedback, File, Image, Rating as RatingState, Ticket, Vision, Voice
from app.core.texts import TEXT
from app.db.models import AIConversation, AIMessage, Feedback as FeedbackModel, Rating, Ticket as TicketModel, TicketMessage, User
from app.services.ai import ai_service
from app.services.files import extract_text
from app.services.knowledge import relevant_knowledge
from app.services.tickets import add_message, create_ticket, find_active_ticket, get_ticket_by_public
from app.services.usage import ai_allowed, consume_ai, consume_ticket, effective_plan, get_or_create_usage, get_plan, ticket_allowed

router = Router(name="user")
log = logging.getLogger(__name__)


def esc(value: str) -> str:
    return pyhtml.escape(str(value), quote=False)


async def split_text(text: str, limit: int = 3900):
    text = text or "(bo‘sh javob)"
    while text:
        yield text[:limit]
        text = text[limit:]


async def render_profile_text(user: User, db) -> str:
    tickets = await db.scalar(select(func.count()).select_from(TicketModel).where(TicketModel.user_id == user.id)) or 0
    avg = await db.scalar(select(func.avg(Rating.score)).where(Rating.user_id == user.id))
    usage = await get_or_create_usage(db, user.id)
    plan = await effective_plan(db, user)
    rating = f"{float(avg):.1f}/5" if avg else "—"
    return (
        f"<b>👤 PROFIL</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: @{esc(user.username or '—')}\n"
        f"💎 Tarif: <b>{esc(plan.name_uz if user.language == 'uz' else plan.name_en if user.language == 'en' else plan.name_ru)}</b>\n"
        f"🎫 Ticketlar: <b>{tickets}</b>\n"
        f"👥 Referral: <b>{user.referrals_count}</b>\n"
        f"⭐ Reyting: <b>{rating}</b>\n"
        f"⚡ AI today: <b>{usage.ai_requests}/{plan.daily_ai_limit}</b>"
    )


async def profile_screen(message: Message, user: User, db) -> None:
    await message.answer(await render_profile_text(user, db), reply_markup=back_menu("nav:main", user.language), parse_mode="HTML")


async def plans_screen(message: Message, user: User, db) -> None:
    free = await get_plan(db, "free"); pro = await get_plan(db, "pro"); comfort = await get_plan(db, "comfort")
    await message.answer(
        f"<b>⭐ TARIFLAR</b>\n\n"
        f"🆓 <b>Free</b> — {free.daily_ai_limit} AI/kun\n"
        f"⭐ <b>Pro</b> — {pro.daily_ai_limit} AI/kun · {pro.daily_ticket_limit} ticket/kun\n"
        f"💎 <b>Comfort</b> — {comfort.daily_ai_limit} AI/kun · {comfort.daily_ticket_limit} ticket/kun\n\n"
        f"💬 Upgrade uchun admin bilan bog‘laning.",
        reply_markup=plan_menu(user.language), parse_mode="HTML"
    )


async def referral_screen(message: Message, user: User, db) -> None:
    me = await message.bot.me()
    username = me.username or "your_bot"
    await message.answer(
        f"<b>🔗 REFERRAL</b>\n\n👥 Taklif qilingan: <b>{user.referrals_count}</b>\n\n"
        f"Sizning linkingiz:\n<code>https://t.me/{username}?start=ref_{user.telegram_id}</code>",
        reply_markup=back_menu("nav:main", user.language), parse_mode="HTML"
    )


@router.callback_query(F.data == "ai:chat")
async def enter_chat(callback: CallbackQuery, user: User, state: FSMContext, db):
    await state.clear()
    conversation = AIConversation(user_id=user.id, title="Yangi chat")
    db.add(conversation); await db.flush(); await db.commit()
    await state.set_state(AIChat.active)
    await state.update_data(conversation_id=conversation.id, mode="chat")
    await callback.message.edit_text(
        "<b>💬 AI CHAT</b>\n\n<blockquote>Endi yozavering. Har bir savol shu chat kontekstida davom etadi.</blockquote>\n\n"
        "🧠 Tarix saqlanadi\n⚡ Javob kelganda shu oynada ko‘rinadi\n\n❌ Chiqish: /cancel",
        reply_markup=ai_chat_menu(user.language), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ai:new")
async def new_chat(callback: CallbackQuery, user: User, state: FSMContext, db):
    await state.clear()
    conversation = AIConversation(user_id=user.id, title="Yangi chat")
    db.add(conversation); await db.flush(); await db.commit()
    await state.set_state(AIChat.active); await state.update_data(conversation_id=conversation.id, mode="chat")
    await callback.message.edit_text("<b>🆕 YANGI CHAT</b>\n\nSavolingizni yuboring.", reply_markup=ai_chat_menu(user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ai:history")
async def chat_history_screen(callback: CallbackQuery, user: User, db, state: FSMContext):
    await state.clear()
    rows = (await db.scalars(select(AIConversation).where(AIConversation.user_id == user.id).order_by(AIConversation.updated_at.desc()).limit(15))).all()
    text = "<b>📂 CHAT TARIXI</b>\n\n" + ("\n".join(f"💬 <b>{esc(x.title)}</b>" for x in rows) if rows else "Hozircha chat yo‘q.")
    await callback.message.edit_text(text, reply_markup=chat_history(rows, user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("ai:open:"))
async def open_chat(callback: CallbackQuery, user: User, db, state: FSMContext):
    cid = callback.data.rsplit(":", 1)[1]
    if not cid.isdigit(): return await callback.answer("Invalid chat", show_alert=True)
    conversation = await db.scalar(select(AIConversation).where(AIConversation.id == int(cid), AIConversation.user_id == user.id))
    if not conversation: return await callback.answer("Chat topilmadi", show_alert=True)
    await state.set_state(AIChat.active); await state.update_data(conversation_id=conversation.id, mode="chat")
    messages = (await db.scalars(select(AIMessage).where(AIMessage.conversation_id == conversation.id).order_by(AIMessage.created_at.desc()).limit(6))).all()[::-1]
    preview = "\n\n".join(f"<b>{'Siz' if m.role == 'user' else 'AI'}:</b> {esc(m.content[:700])}" for m in messages)
    await callback.message.edit_text(f"<b>💬 {esc(conversation.title)}</b>\n\n{preview or 'Bu chat hali bo‘sh.'}", reply_markup=ai_chat_menu(user.language), parse_mode="HTML")
    await callback.answer()


@router.message(F.text, AIChat.active)
async def ai_chat(message: Message, user: User, db, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        return
    allowed, remaining, _ = await ai_allowed(db, user)
    if not allowed:
        await message.answer(TEXT[user.language]["limit"], parse_mode="HTML", reply_markup=back_menu("nav:ai", user.language)); return
    if not ai_service.configured:
        await message.answer("⚠️ <b>AI hozir sozlanmagan.</b> Admin <code>OPENAI_API_KEY</code> ni Render Environment Variables'ga qo‘shishi kerak.", parse_mode="HTML", reply_markup=back_menu("nav:ai", user.language)); return

    data = await state.get_data(); cid = data.get("conversation_id"); mode = data.get("mode", "chat")
    conversation = await db.scalar(select(AIConversation).where(AIConversation.id == cid, AIConversation.user_id == user.id)) if cid else None
    if conversation is None:
        conversation = AIConversation(user_id=user.id, title=text[:60]); db.add(conversation); await db.flush(); await state.update_data(conversation_id=conversation.id)

    knowledge = await relevant_knowledge(db, text)
    history = (await db.scalars(select(AIMessage).where(AIMessage.conversation_id == conversation.id).order_by(AIMessage.created_at.desc()).limit(18))).all()[::-1]
    messages = [{"role": x.role, "content": x.content} for x in history]
    messages.append({"role": "user", "content": text})

    waiting = await message.answer("⏳ <b>AI o‘ylayapti…</b>", parse_mode="HTML", reply_markup=ai_chat_menu(user.language))
    try:
        answer = await asyncio.wait_for(ai_service.chat(messages, knowledge=knowledge, mode=mode), timeout=100)
    except asyncio.TimeoutError:
        await waiting.edit_text("⚠️ AI javobi juda uzoq davom etdi. Qayta urinib ko‘ring.", reply_markup=ai_chat_menu(user.language), parse_mode="HTML"); return
    except Exception as exc:
        log.exception("AI user request failed")
        err = str(exc)
        friendly = "⚠️ AI xizmatiga ulanib bo‘lmadi. API kalit/model/limitni tekshiring." if "OPENAI" not in err else "⚠️ AI API sozlamalarida muammo bor."
        await waiting.edit_text(friendly, reply_markup=ai_chat_menu(user.language), parse_mode="HTML"); return

    db.add(AIMessage(conversation_id=conversation.id, role="user", content=text, model=__import__("app.config", fromlist=["get_settings"]).get_settings().openai_chat_model))
    db.add(AIMessage(conversation_id=conversation.id, role="assistant", content=answer, model=__import__("app.config", fromlist=["get_settings"]).get_settings().openai_chat_model))
    conversation.title = conversation.title if conversation.title != "Yangi chat" else text[:60]
    await consume_ai(db, user)
    await waiting.delete()
    parts = [x async for x in split_text(answer)]
    for index, part in enumerate(parts):
        suffix = f"\n\n<tg-spoiler>⚡ Qolgan limit: {max(0, remaining-1)}</tg-spoiler>" if index == len(parts)-1 else ""
        await message.answer(esc(part) + suffix, parse_mode="HTML", reply_markup=ai_chat_menu(user.language) if index == len(parts)-1 else None)


@router.callback_query(F.data.in_({"ai:translate", "ai:study", "ai:coding", "ai:data"}))
async def ai_mode(callback: CallbackQuery, user: User, state: FSMContext):
    mode = callback.data.split(":", 1)[1]
    labels = {"translate": "🌐 Tarjima", "study": "📚 Study Mode", "coding": "💻 Coding", "data": "📊 Data Analysis"}
    await state.clear(); await state.set_state(AIChat.active); await state.update_data(mode=mode)
    await callback.message.edit_text(f"<b>{labels[mode]}</b>\n\nTopshiriqni yuboring. Har bir so‘rovda maxsus rejim ishlaydi.\n\n❌ Chiqish: /cancel", reply_markup=ai_chat_menu(user.language), parse_mode="HTML")
    await callback.answer()


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear(); await message.answer("✅ Rejim bekor qilindi.\n\nBosh menyudan istalgan bo‘limni tanlang.")


@router.callback_query(F.data == "ai:voice")
async def voice_prompt(callback: CallbackQuery, user: User, state: FSMContext, db):
    plan = await effective_plan(db, user)
    if not plan.voice_enabled:
        await callback.answer("🔒 Voice Pro/Comfort tarifida mavjud.", show_alert=True); return
    await state.clear(); await state.set_state(Voice.active)
    await callback.message.edit_text("<b>🎙 VOICE SUPPORT</b>\n\nOvozli xabar yuboring. AI uni matnga aylantirib, javob beradi.", reply_markup=back_menu("nav:ai", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.voice, Voice.active)
async def voice(message: Message, user: User, db, state: FSMContext):
    allowed, _, _ = await ai_allowed(db, user)
    if not allowed: return await message.answer(TEXT[user.language]["limit"], parse_mode="HTML")
    if not ai_service.configured: return await message.answer("⚠️ OPENAI_API_KEY sozlanmagan.")
    info = await message.bot.get_file(message.voice.file_id); content = await message.bot.download_file(info.file_path)
    try:
        transcript = await ai_service.transcribe("voice.ogg", content.read())
        answer = await ai_service.chat([{"role": "user", "content": transcript}])
    except Exception:
        log.exception("Voice request failed"); return await message.answer("⚠️ Voice/AI ishlashida xatolik yuz berdi.")
    await consume_ai(db, user); await state.clear()
    await message.answer(f"<b>📝 Matn</b>\n{esc(transcript)}\n\n<b>🤖 AI</b>\n{esc(answer)}", parse_mode="HTML", reply_markup=back_menu("nav:ai", user.language))


@router.callback_query(F.data == "ai:file")
async def file_prompt(callback: CallbackQuery, user: User, state: FSMContext, db):
    plan = await effective_plan(db, user)
    if not plan.file_enabled: return await callback.answer("🔒 Fayl tahlili Pro/Comfort tarifida mavjud.", show_alert=True)
    await state.clear(); await state.set_state(File.active)
    await callback.message.edit_text("<b>📎 FAYL TAHLILI</b>\n\nPDF, DOCX, XLSX, TXT, CSV, MD, JSON yoki PY yuboring. Caption yozsangiz, AI aynan shu topshiriqni bajaradi.", reply_markup=back_menu("nav:ai", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.document, File.active)
async def document(message: Message, user: User, db, state: FSMContext):
    allowed, _, _ = await ai_allowed(db, user)
    if not allowed: return await message.answer(TEXT[user.language]["limit"], parse_mode="HTML")
    size = message.document.file_size or 0
    if size > 20 * 1024 * 1024: return await message.answer("⚠️ Maksimal fayl hajmi 20 MB.")
    info = await message.bot.get_file(message.document.file_id); raw = await message.bot.download_file(info.file_path)
    name = message.document.file_name or "document"
    try: extracted = await extract_text(name, raw.read())
    except Exception: extracted = ""
    if not extracted: return await message.answer("⚠️ Fayl matnini o‘qib bo‘lmadi.")
    task = message.caption or "Faylni tahlil qiling va asosiy xulosalarni bering."
    try: answer = await ai_service.chat([{"role": "user", "content": f"Fayl: {name}\nTopshiriq: {task}\n\n{extracted[:30000]}"}], mode="data")
    except Exception: log.exception("File AI failed"); return await message.answer("⚠️ Faylni AI tahlil qilishida xatolik yuz berdi.")
    await consume_ai(db, user); await state.clear()
    for part in [x async for x in split_text(answer)]: await message.answer(f"📄 <b>{esc(name)}</b>\n\n{esc(part)}", parse_mode="HTML")
    await message.answer("✅ Fayl tahlili tugadi.", reply_markup=back_menu("nav:ai", user.language))


@router.callback_query(F.data == "ai:vision")
async def vision_prompt(callback: CallbackQuery, state: FSMContext, user: User):
    await state.clear(); await state.set_state(Vision.active)
    await callback.message.edit_text("<b>📷 RASM TAHLILI</b>\n\nRasmni yuboring. Caption orqali savolingizni yozishingiz mumkin.", reply_markup=back_menu("nav:ai", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.photo, Vision.active)
async def vision(message: Message, user: User, db, state: FSMContext):
    allowed, _, _ = await ai_allowed(db, user)
    if not allowed: return await message.answer(TEXT[user.language]["limit"], parse_mode="HTML")
    photo = message.photo[-1]; info = await message.bot.get_file(photo.file_id); data = await message.bot.download_file(info.file_path)
    try: answer = await ai_service.vision(message.caption or "Analyze this image accurately.", data.read())
    except Exception: log.exception("Vision failed"); return await message.answer("⚠️ Rasm tahlilida xatolik yuz berdi.")
    await consume_ai(db, user); await state.clear(); await message.answer(esc(answer), parse_mode="HTML", reply_markup=back_menu("nav:ai", user.language))


@router.callback_query(F.data == "ai:image")
async def image_prompt(callback: CallbackQuery, user: User, state: FSMContext, db):
    plan = await effective_plan(db, user)
    if not plan.image_enabled: return await callback.answer("🔒 Rasm yaratish Pro/Comfort tarifida mavjud.", show_alert=True)
    await state.clear(); await state.set_state(Image.active)
    await callback.message.edit_text("<b>🖼 RASM YARATISH</b>\n\nTasvirni imkon qadar aniq tasvirlab bering. Stil, rang, kompozitsiya va formatni yozishingiz mumkin.", reply_markup=back_menu("nav:ai", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.text, Image.active)
async def image_gen(message: Message, user: User, db, state: FSMContext):
    allowed, _, _ = await ai_allowed(db, user)
    if not allowed: return await message.answer(TEXT[user.language]["limit"], parse_mode="HTML")
    try: img = await ai_service.generate_image(message.text)
    except Exception: log.exception("Image generation failed"); return await message.answer("⚠️ Rasm yaratish ishlamadi. Image API modelini va API keyni tekshiring.")
    if img is None: return await message.answer("⚠️ Rasm javobi bo‘sh keldi.")
    await consume_ai(db, user); await state.clear(); await message.answer_photo(img, caption="🖼 <b>Tayyor.</b>", parse_mode="HTML", reply_markup=back_menu("nav:ai", user.language))


@router.callback_query(F.data == "ticket:list")
async def ticket_list_screen(callback: CallbackQuery, user: User, db, state: FSMContext):
    await state.clear()
    rows = (await db.scalars(select(TicketModel).where(TicketModel.user_id == user.id).order_by(TicketModel.created_at.desc()).limit(20))).all()
    await callback.message.edit_text("<b>🎫 MENING MUROJAATLARIM</b>\n\n" + ("Ticket tanlang:" if rows else "Hozircha ticket yo‘q."), reply_markup=ticket_list(rows, user.language), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "ticket:new")
async def ticket_new(callback: CallbackQuery, user: User, db, state: FSMContext):
    if not await ticket_allowed(db, user): return await callback.answer("⛔ Bugungi ticket limiti tugagan.", show_alert=True)
    existing = await find_active_ticket(db, user)
    if existing: return await callback.answer("Sizda allaqachon ochiq ticket bor. Avval uni davom ettiring.", show_alert=True)
    ticket = await create_ticket(db, user, "Support")
    await consume_ticket(db, user); await state.clear(); await state.set_state(Ticket.active); await state.update_data(ticket_id=ticket.id)
    await callback.message.edit_text(f"<b>🎫 #{ticket.public_id}</b>\n\nMuammo yoki savolingizni yozing.", reply_markup=back_menu("nav:support", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.text, Ticket.active)
async def ticket_message(message: Message, user: User, db, state: FSMContext):
    data = await state.get_data(); ticket = await db.get(TicketModel, data.get("ticket_id"))
    if not ticket or ticket.user_id != user.id: await state.clear(); return
    await add_message(db, ticket.id, "user", user.telegram_id, message.text)
    ticket.status = "pending"; await db.commit(); await state.clear()
    await message.answer(f"✅ <b>#{ticket.public_id}</b> murojaatingiz qabul qilindi.\n\nOperator javobini shu ticketda davom ettirishingiz mumkin.", reply_markup=ticket_view(ticket, user.language), parse_mode="HTML")


@router.callback_query(F.data.startswith("ticket:open:"))
async def ticket_open(callback: CallbackQuery, user: User, db, state: FSMContext):
    public_id = callback.data.rsplit(":", 1)[1]; ticket = await get_ticket_by_public(db, public_id)
    if not ticket or ticket.user_id != user.id: return await callback.answer("Ticket topilmadi", show_alert=True)
    messages = (await db.scalars(select(TicketMessage).where(TicketMessage.ticket_id == ticket.id).order_by(TicketMessage.created_at.desc()).limit(8))).all()[::-1]
    body = "\n\n".join(f"<b>{'👤 Siz' if m.sender_type == 'user' else '👨‍💻 Operator'}:</b> {esc(m.content)}" for m in messages)
    await state.clear(); await callback.message.edit_text(f"<b>🎫 #{ticket.public_id}</b>\n\nStatus: <b>{esc(ticket.status)}</b>\n\n{body or 'Xabarlar yo‘q.'}", reply_markup=ticket_view(ticket, user.language), parse_mode="HTML"); await callback.answer()


@router.callback_query(F.data.startswith("ticket:continue:"))
async def ticket_continue(callback: CallbackQuery, user: User, db, state: FSMContext):
    public_id = callback.data.rsplit(":", 1)[1]; ticket = await get_ticket_by_public(db, public_id)
    if not ticket or ticket.user_id != user.id or ticket.status == "closed": return await callback.answer("Ticket faol emas.", show_alert=True)
    await state.clear(); await state.set_state(Ticket.active); await state.update_data(ticket_id=ticket.id)
    await callback.message.edit_text(f"<b>🎫 #{ticket.public_id}</b>\n\nYangi xabaringizni yuboring.", reply_markup=back_menu("ticket:list", user.language), parse_mode="HTML"); await callback.answer()


@router.callback_query(F.data.startswith("ticket:close:"))
async def ticket_close(callback: CallbackQuery, user: User, db, state: FSMContext):
    public_id = callback.data.rsplit(":", 1)[1]; ticket = await get_ticket_by_public(db, public_id)
    if not ticket or ticket.user_id != user.id: return await callback.answer("Ticket topilmadi", show_alert=True)
    ticket.status = "closed"; await db.commit(); await state.clear()
    await callback.message.edit_text(f"✅ <b>Ticket #{ticket.public_id} yopildi.</b>\n\nXizmatni 1–5 yulduz bilan baholashingiz mumkin.", reply_markup=rating_kb(ticket.id), parse_mode="HTML"); await callback.answer()


@router.callback_query(F.data == "support:new")
async def support_new(callback: CallbackQuery, user: User, db, state: FSMContext):
    await ticket_new(callback, user, db, state)


@router.callback_query(F.data == "support:rate")
async def rate_pick(callback: CallbackQuery, user: User, db):
    ticket = await db.scalar(select(TicketModel).where(TicketModel.user_id == user.id, TicketModel.status == "closed").order_by(TicketModel.updated_at.desc()))
    if not ticket: return await callback.answer("Baholash uchun yopilgan ticket topilmadi.", show_alert=True)
    await callback.message.edit_text(f"⭐ <b>Ticket #{ticket.public_id}</b>\n\nSupport xizmatini baholang:", reply_markup=rating_kb(ticket.id), parse_mode="HTML"); await callback.answer()


@router.callback_query(F.data.startswith("rate:"))
async def rate(callback: CallbackQuery, user: User, db, state: FSMContext):
    _, ticket_id, score = callback.data.split(":")
    ticket = await db.get(TicketModel, int(ticket_id))
    if not ticket or ticket.user_id != user.id: return await callback.answer("Ruxsat yo‘q.", show_alert=True)
    existing = await db.scalar(select(Rating).where(Rating.ticket_id == ticket.id))
    if existing: existing.score = int(score)
    else: db.add(Rating(ticket_id=ticket.id, user_id=user.id, score=int(score)))
    await db.commit(); await state.clear(); await callback.message.edit_text(f"⭐ Rahmat! Siz <b>{score}/5</b> baho berdingiz.", reply_markup=back_menu("nav:support", user.language), parse_mode="HTML"); await callback.answer()


@router.callback_query(F.data == "support:feedback")
async def feedback_prompt(callback: CallbackQuery, user: User, state: FSMContext):
    await state.clear(); await state.set_state(Feedback.active)
    await callback.message.edit_text("<b>📝 FEEDBACK</b>\n\nXizmat haqida fikringizni yozing.", reply_markup=back_menu("nav:support", user.language), parse_mode="HTML"); await callback.answer()


@router.message(F.text, Feedback.active)
async def feedback(message: Message, user: User, db, state: FSMContext):
    db.add(FeedbackModel(user_id=user.id, text=message.text)); await db.commit(); await state.clear(); await message.answer("✅ Feedback qabul qilindi. Rahmat!", reply_markup=back_menu("nav:support", user.language))


@router.callback_query(F.data.startswith("plan:"))
async def plan_interest(callback: CallbackQuery, user: User):
    await callback.answer("💬 Tarifni ulash uchun admin bilan bog‘laning.", show_alert=True)
