from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from app.bot.keyboards.common import ai_menu, plan_menu, back_menu, LABELS
from app.bot.keyboards.support import support_menu, rating_kb
from app.core.texts import TEXT
from app.db.models import Ticket, Rating
from app.services.usage import get_plan, get_or_create_usage, ai_allowed, consume_ai, ticket_allowed, consume_ticket
from app.services.files import extract_text
from app.services.ai import ai_service
from app.services.knowledge import relevant_knowledge
from app.services.tickets import create_ticket, add_message, find_active_ticket
from app.bot.states import AIChat, Voice, File, Image, Vision, Ticket, Rating as RatingState, Feedback
import html as pyhtml

router=Router()

async def profile_data(user,db):
    tickets=await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.user_id==user.id)) or 0
    avg=await db.scalar(select(func.avg(Rating.score)).where(Rating.user_id==user.id))
    return tickets, (round(float(avg),1) if avg else '—')

@router.message(F.text.in_({'🤖 AI Yordamchi','🤖 AI Assistant','🤖 AI Помощник'}))
async def ai_home(message:Message,user,db): await message.answer(TEXT[user.language]['ai_menu'],reply_markup=ai_menu(user.language),parse_mode='HTML')

@router.callback_query(F.data=='ai:chat')
async def ai_chat_prompt(c:CallbackQuery,state):
    await state.set_state(AIChat.text); await state.update_data(mode='chat'); await c.message.answer('💬 <b>Chat</b>\nSavolingizni yuboring. Chiqish uchun /cancel.',parse_mode='HTML'); await c.answer()

@router.message(F.text=='/cancel')
async def cancel(message:Message,state): await state.clear(); await message.answer('✅ Bekor qilindi.')

@router.message(F.content_type.in_({'text'}), AIChat.text)
async def ai_chat(message:Message,user,db,state):
    allowed,remaining,_=await ai_allowed(db,user)
    if not allowed: await message.answer('⛔ <b>Bugungi AI limiti tugadi.</b>\n⭐ Tarifni oshirish uchun admin bilan bog‘laning.',parse_mode='HTML'); return
    from app.db.models import AIConversation, AIMessage
    from sqlalchemy import select
    data=await state.get_data(); mode=data.get('mode','chat')
    conv=await db.scalar(select(AIConversation).where(AIConversation.user_id==user.id,AIConversation.is_closed==False).order_by(AIConversation.updated_at.desc()))
    if not conv:
        conv=AIConversation(user_id=user.id,title=message.text[:60]); db.add(conv); await db.flush()
    k=await relevant_knowledge(db,message.text)
    prefix={'translate':'Act as a precise translator. Preserve meaning and formatting.', 'study':'Act as a patient study tutor. Explain step-by-step and check understanding.', 'coding':'Act as a senior software engineer. Give safe, complete and tested coding guidance.'}.get(mode,'')
    prompt=(prefix+'\n' if prefix else '')+message.text
    history=(await db.scalars(select(AIMessage).where(AIMessage.conversation_id==conv.id).order_by(AIMessage.created_at.desc()).limit(12))).all()[::-1]
    messages=[{'role':x.role,'content':x.content} for x in history] + [{'role':'user','content':prompt}]
    answer=await ai_service.chat(messages,k)
    db.add(AIMessage(conversation_id=conv.id,role='user',content=message.text,model=None)); db.add(AIMessage(conversation_id=conv.id,role='assistant',content=answer,model=None)); await consume_ai(db,user)
    await message.answer(f'{pyhtml.escape(answer)}\n\n<tg-spoiler>⚡ Qolgan limit: {max(0,remaining-1)}</tg-spoiler>',parse_mode='HTML')

@router.callback_query(F.data.in_({'ai:translate','ai:study','ai:coding'}))
async def ai_modes(c:CallbackQuery,state):
    mode=c.data.split(':')[1]; labels={'translate':'🌐 Tarjima','study':'📚 Study Mode','coding':'💻 Coding'}
    await state.set_state(AIChat.text); await state.update_data(mode=mode); await c.message.answer(f'<b>{labels[mode]}</b>\nTopshiriqni yuboring. /cancel',parse_mode='HTML'); await c.answer()

@router.callback_query(F.data=='ai:voice')
async def voice_help(c:CallbackQuery,state): await state.set_state(Voice.voice); await c.message.answer('🎙 <b>Voice Support</b>\nOvozli xabar yuboring.',parse_mode='HTML'); await c.answer()

@router.message(F.voice, Voice.voice)
async def voice(message:Message,user,db,state):
    allowed,_,_=await ai_allowed(db,user)
    if not allowed: await message.answer('⛔ Bugungi AI limiti tugadi.'); return
    file=await message.bot.get_file(message.voice.file_id); data=await message.bot.download_file(file.file_path)
    transcript=await ai_service.transcribe('voice.ogg',data.read())
    answer=await ai_service.chat([{'role':'user','content':transcript}])
    await consume_ai(db,user); await state.clear()
    await message.answer(f'<b>📝 Matn:</b> {pyhtml.escape(transcript)}\n\n<b>🤖 AI:</b> {pyhtml.escape(answer)}',parse_mode='HTML')

@router.callback_query(F.data=='ai:file')
async def file_help(c:CallbackQuery,state): await state.set_state(File.file); await c.message.answer('📎 <b>Fayl tahlili</b>\nHozircha fayl nomi va metadata asosida ishlaydigan qabul qila olish oqimi tayyor. Fayl yuboring.',parse_mode='HTML'); await c.answer()

@router.message(F.document, File.file)
async def document(message:Message,user,db,state):
    plan=await get_plan(db,user.plan_code)
    if not plan.file_enabled: await message.answer('🔒 Fayl tahlili Pro/Comfort tarifida mavjud.'); return
    allowed,_,_=await ai_allowed(db,user)
    if not allowed: await message.answer('⛔ Bugungi AI limiti tugadi.'); return
    name=message.document.file_name or 'document'; size=message.document.file_size or 0
    answer=await ai_service.chat([{'role':'user','content':f'File received: {name}, size: {size} bytes. Explain what analysis workflow should be used and ask the user what they want extracted.'}])
    await consume_ai(db,user); await state.clear(); await message.answer(f'📄 <b>{pyhtml.escape(name)}</b>\n\n{pyhtml.escape(answer)}',parse_mode='HTML')

@router.callback_query(F.data=='ai:vision')
async def vision_help(c:CallbackQuery,state):
    await state.set_state(Vision.photo); await c.message.answer('📷 <b>Rasm tahlili</b>\nRasmni yuboring.',parse_mode='HTML'); await c.answer()

@router.message(F.photo, Vision.photo)
async def vision(message:Message,user,db,state):
    allowed,_,_=await ai_allowed(db,user)
    if not allowed: await message.answer('⛔ Bugungi AI limiti tugadi.'); return
    photo=message.photo[-1]; file=await message.bot.get_file(photo.file_id); data=await message.bot.download_file(file.file_path)
    import base64
    b64=base64.b64encode(data.read()).decode()
    prompt=message.caption or 'Describe and analyze this image accurately.'
    if not ai_service.client: await message.answer('⚠️ AI API sozlanmagan.'); return
    r=await ai_service.client.chat.completions.create(model=__import__('app.config',fromlist=['get_settings']).get_settings().openai_chat_model,messages=[{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+b64}}]}])
    answer=r.choices[0].message.content or 'Tahlil olinmadi.'
    await consume_ai(db,user); await state.clear(); await message.answer(pyhtml.escape(answer),parse_mode='HTML')

@router.callback_query(F.data=='ai:image')
async def image_prompt(c:CallbackQuery,state): await state.set_state(Image.prompt); await c.message.answer('🖼 Rasm uchun tavsifni yuboring.',parse_mode='HTML'); await c.answer()

@router.message(F.text, Image.prompt)
async def image_gen(message:Message,user,db,state):
    plan=await get_plan(db,user.plan_code)
    if not plan.image_enabled: await message.answer('🔒 Rasm yaratish Pro/Comfort tarifida mavjud.'); return
    allowed,_,_=await ai_allowed(db,user)
    if not allowed: await message.answer('⛔ Bugungi AI limiti tugadi.'); return
    img=await ai_service.generate_image(message.text)
    await consume_ai(db,user); await state.clear()
    if img: await message.answer_photo(img,caption='🖼 <b>Rasm tayyor.</b>',parse_mode='HTML')
    else: await message.answer('⚠️ Rasm API hozir sozlanmagan yoki javob qaytarmadi.')

@router.callback_query(F.data=='ticket:list')
async def ticket_list(c:CallbackQuery,user,db):
    from app.bot.keyboards.common import ticket_list
    rows=(await db.scalars(select(Ticket).where(Ticket.user_id==user.id).order_by(Ticket.created_at.desc()).limit(10))).all()
    if not rows: await c.message.answer('📂 <b>Mening murojaatlarim</b>\nHozircha ticketlar yo‘q.',reply_markup=ticket_list([]),parse_mode='HTML')
    else: await c.message.answer('📂 <b>Mening murojaatlarim</b>',reply_markup=ticket_list(rows),parse_mode='HTML')
    await c.answer()

@router.callback_query(F.data=='ticket:new')
async def ticket_new(c:CallbackQuery,user,db,state):
    if not await ticket_allowed(db,user): await c.answer('⛔ Bugungi ticket limiti tugagan.',show_alert=True); return
    ticket=await create_ticket(db,user); await add_message(db,ticket.id,'user',user.telegram_id,'Ticket created'); await db.commit(); await consume_ticket(db,user); await state.set_state(Ticket.message); await state.update_data(ticket_id=ticket.id); await c.message.answer(f'🎫 <b>Ticket #{ticket.public_id}</b> yaratildi.\nMuammoingizni yuboring. /cancel',parse_mode='HTML'); await c.answer()

@router.callback_query(F.data.startswith('ticket:open:'))
async def ticket_open(c:CallbackQuery,user,db):
    public_id=c.data.rsplit(':',1)[1]; t=await db.scalar(select(Ticket).where(Ticket.public_id==public_id,Ticket.user_id==user.id))
    if not t: await c.answer('Ticket topilmadi.',show_alert=True); return
    await c.message.answer(f'🎫 <b>#{t.public_id}</b>\nHolat: <b>{t.status}</b>\nUstuvorlik: <b>{t.priority}</b>\n\nYozishni davom ettirishingiz mumkin.',parse_mode='HTML'); await c.answer()

@router.message(F.text.in_({'💬 Support','💬 Поддержка'}))
async def support(message:Message): await message.answer('💬 <b>Support</b>\nMuammo yoki savolingizni operatorga yuboring.',reply_markup=support_menu(),parse_mode='HTML')

@router.callback_query(F.data=='support:new')
async def support_new(c:CallbackQuery,user,db,state):
    if not await ticket_allowed(db,user): await c.answer('⛔ Bugungi ticket limiti tugagan.',show_alert=True); return
    ticket=await create_ticket(db,user); await consume_ticket(db,user); await state.set_state(Ticket.message); await state.update_data(ticket_id=ticket.id); await db.commit(); await c.message.answer(f'🎫 <b>#{ticket.public_id}</b>\nMuammoingizni yuboring. /cancel',parse_mode='HTML'); await c.answer()

@router.message(Ticket.message)
async def ticket_message(message:Message,user,db,state):
    data=await state.get_data(); tid=data.get('ticket_id')
    if not tid: await state.clear(); return
    await add_message(db,int(tid),'user',user.telegram_id,message.text or '[attachment]');
    ticket=await db.get(Ticket,int(tid)); ticket.status='processing'; await db.commit()
    await message.answer('✅ <b>Xabaringiz ticketga qo‘shildi.</b>\nOperator javobini kuting.',parse_mode='HTML')

@router.callback_query(F.data=='support:feedback')
async def feedback_prompt(c:CallbackQuery,state): await state.set_state(Feedback.text); await c.message.answer('📝 Xizmatingiz haqidagi fikringizni yozing.'); await c.answer()

@router.message(Feedback.text)
async def feedback_save(m:Message,user,db,state):
    from app.db.models import Feedback as FeedbackModel
    db.add(FeedbackModel(user_id=user.id,text=m.text or '')); await db.commit(); await state.clear(); await m.answer('✅ Feedback qabul qilindi. Rahmat!')

@router.callback_query(F.data=='support:rate')
async def rate_prompt(c:CallbackQuery,user,db):
    t=await db.scalar(select(Ticket).where(Ticket.user_id==user.id,Ticket.status=='closed').order_by(Ticket.updated_at.desc()))
    if not t: await c.answer('⭐ Baholash uchun yopilgan ticket kerak.',show_alert=True); return
    await c.message.answer(f'⭐ Ticket #{t.public_id} xizmatini baholang:',reply_markup=rating_kb(t.id)); await c.answer()

@router.callback_query(F.data.startswith('rate:'))
async def rate_save(c:CallbackQuery,user,db):
    _,tid,score=c.data.split(':'); db.add(Rating(ticket_id=int(tid),user_id=user.id,score=int(score))); await db.commit(); await c.answer('✅ Bahongiz saqlandi.',show_alert=True)

@router.message(F.text.in_({'👤 Profil','👤 Profile','👤 Профиль'}))
async def profile(message:Message,user,db):
    tickets,rating=await profile_data(user,db); text=TEXT[user.language]['profile'].format(id=user.telegram_id,username=user.username or 'none',plan=user.plan_code.title(),tickets=tickets,refs=user.referrals_count,rating=rating)
    await message.answer(text,parse_mode='HTML')

@router.message(F.text.in_({'⭐ Tariflar','⭐ Plans','⭐ Тарифы'}))
async def plans(message:Message,user,db):
    free=await get_plan(db,'free'); pro=await get_plan(db,'pro'); comfort=await get_plan(db,'comfort'); await message.answer(TEXT[user.language]['plan'].format(free=free.daily_ai_limit,pro=pro.daily_ai_limit,comfort=comfort.daily_ai_limit),reply_markup=plan_menu(),parse_mode='HTML')

@router.callback_query(F.data.startswith('plan:'))
async def plan_request(c:CallbackQuery): await c.message.answer('⭐ Tarifni ulash uchun <b>admin bilan bog‘laning</b> va Telegram ID’ingizni yuboring.',parse_mode='HTML'); await c.answer()

@router.message(F.text.in_({'🔗 Referral','🔗 Реферал'}))
async def referral(message:Message,user,db):
    username=(await message.bot.me()).username or 'your_bot'; await message.answer(f'<b>🔗 Referral</b>\n\n👥 Taklif qilingan: <b>{user.referrals_count}</b>\n\nSizning linkingiz:\n<code>https://t.me/{username}?start=ref_{user.telegram_id}</code>',parse_mode='HTML')

@router.message(F.text.in_({'⚙️ Sozlamalar','⚙️ Settings','⚙️ Настройки'}))
async def settings(message:Message,user): await message.answer('⚙️ <b>Sozlamalar</b>\n\n🌐 Tilni o‘zgartirish uchun /language buyrug‘ini ishlating.\n🔔 Bildirishnomalar: yoqilgan\n🛡 Privacy: standart.',parse_mode='HTML')
