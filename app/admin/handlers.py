from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from app.config import get_settings
from app.bot.keyboards.admin import admin_menu, admin_back, learning_menu
from app.bot.states import Admin
from app.db.models import User, Ticket, Operator, Channel, KnowledgeItem, LearningItem, Rating, AuditLog, Broadcast
from app.services.usage import get_plan
from app.services.ai import ai_service
from app.db.session import SessionLocal

router=Router(); settings=get_settings()

def show_admin_menu(message):
    return message.answer("<b>🛠 ADMIN PANEL</b>\n\nBoshqaruv markaziga xush kelibsiz.", reply_markup=admin_menu(), parse_mode="HTML")

def is_admin(uid:int)->bool: return uid in settings.admin_id_set
async def log(session, uid, action, target_type=None, target_id=None, payload=None):
    session.add(AuditLog(admin_id=uid,action=action,target_type=target_type,target_id=str(target_id) if target_id is not None else None,payload=payload or {})); await session.flush()

def deny(c): return c.answer('⛔ Ruxsat yo‘q.',show_alert=True)

@router.message(Command('admin'))
async def admin_cmd(message:Message):
    if not is_admin(message.from_user.id): return
    await message.answer('<b>🛠 ADMIN PANEL</b>\n\nBoshqaruv markaziga xush kelibsiz.',reply_markup=admin_menu(),parse_mode='HTML')

@router.message(F.text=='🛠 Admin Panel')
async def admin_btn(message:Message):
    if is_admin(message.from_user.id): await admin_cmd(message)

@router.callback_query(F.data=='adm:home')
async def admin_home(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    await c.message.edit_text('<b>🛠 ADMIN PANEL</b>\n\nBo‘limni tanlang:',reply_markup=admin_menu(),parse_mode='HTML'); await c.answer()

@router.callback_query(F.data=='adm:dashboard')
async def dashboard(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    async with SessionLocal() as s:
        users=await s.scalar(select(func.count()).select_from(User)) or 0
        tickets=await s.scalar(select(func.count()).select_from(Ticket)) or 0
        pending=await s.scalar(select(func.count()).select_from(Ticket).where(Ticket.status=='pending')) or 0
        ai=await s.scalar(select(func.sum(__import__('app.db.models',fromlist=['UsageDaily']).UsageDaily.ai_requests))) or 0
        ops=await s.scalar(select(func.count()).select_from(Operator).where(Operator.is_active)) or 0
    await c.message.edit_text(f'<b>📊 Dashboard</b>\n\n👥 Users: <b>{users}</b>\n🎫 Tickets: <b>{tickets}</b>\n🟡 Pending: <b>{pending}</b>\n🤖 AI requests: <b>{ai}</b>\n👨‍💻 Operators: <b>{ops}</b>',reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.callback_query(F.data=='adm:users')
async def users(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await deny(c)
    await state.set_state(Admin.user_id); await c.message.edit_text('<b>👥 Users</b>\n\nTelegram ID yoki username yuboring.',reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Admin.user_id)
async def user_lookup(m:Message,state:FSMContext):
    if not is_admin(m.from_user.id): return
    q=m.text.strip().lstrip('@');
    async with SessionLocal() as s:
        user=await s.scalar(select(User).where(User.telegram_id==int(q)) if q.isdigit() else select(User).where(User.username.ilike(q)))
        if not user: await m.answer('❌ User topilmadi.'); return
        await state.clear(); await m.answer(f'<b>👤 User</b>\n\nID: <code>{user.telegram_id}</code>\nUsername: @{user.username or "—"}\nPlan: <b>{user.plan_code}</b>\nBanned: <b>{user.is_banned}</b>\nReferrals: <b>{user.referrals_count}</b>\n\nPlan o‘zgartirish: <code>/setplan {user.telegram_id} pro</code>\nBan: <code>/ban {user.telegram_id}</code>\nUnban: <code>/unban {user.telegram_id}</code>',parse_mode='HTML')

@router.message(Command('setplan'))
async def setplan(m:Message):
    if not is_admin(m.from_user.id): return
    parts=m.text.split();
    if len(parts)!=3 or not parts[1].isdigit() or parts[2] not in ('free','pro','comfort'): return await m.answer('Format: /setplan USER_ID free|pro|comfort')
    async with SessionLocal() as s:
        user=await s.scalar(select(User).where(User.telegram_id==int(parts[1])))
        if not user:return await m.answer('User topilmadi.')
        old=user.plan_code; user.plan_code=parts[2]; await log(s,m.from_user.id,'CHANGE_PLAN','user',user.telegram_id,{'old':old,'new':parts[2]}); await s.commit()
    await m.answer(f'✅ {parts[1]} → {parts[2]}')
    try: await m.bot.send_message(int(parts[1]),f'🎉 <b>Tarifingiz yangilandi:</b> {parts[2].upper()}',parse_mode='HTML')
    except Exception: pass

@router.message(Command('ban'))
async def ban(m:Message): await _ban(m,True)
@router.message(Command('unban'))
async def unban(m:Message): await _ban(m,False)
async def _ban(m,flag):
    if not is_admin(m.from_user.id): return
    parts=m.text.split();
    if len(parts)!=2 or not parts[1].isdigit(): return await m.answer('Format: /ban USER_ID')
    async with SessionLocal() as s:
        u=await s.scalar(select(User).where(User.telegram_id==int(parts[1]))); 
        if not u:return await m.answer('User topilmadi.')
        u.is_banned=flag; await log(s,m.from_user.id,'BAN' if flag else 'UNBAN','user',u.telegram_id); await s.commit()
    await m.answer('✅ Bajarildi.')

@router.callback_query(F.data=='adm:tickets')
async def tickets(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    async with SessionLocal() as s:
        rows=(await s.scalars(select(Ticket).order_by(Ticket.updated_at.desc()).limit(15))).all()
    text='<b>🎫 Tickets</b>\n\n'+('\n'.join(f'#{x.public_id} • {x.status} • priority={x.priority}' for x in rows) or 'Hozircha ticket yo‘q.')
    await c.message.edit_text(text,reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.callback_query(F.data=='adm:operators')
async def operators(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    async with SessionLocal() as s: rows=(await s.scalars(select(Operator).order_by(Operator.id.desc()).limit(20))).all()
    text='<b>👨‍💻 Operators</b>\n\n'+('\n'.join(f'👤 {x.telegram_id} • {x.role} • {"ON" if x.is_active else "OFF"}' for x in rows) or 'Operatorlar yo‘q.')+'\n\nQo‘shish: <code>/addop USER_ID ROLE</code>'
    await c.message.edit_text(text,reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Command('addop'))
async def addop(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split();
    if len(p)!=3 or not p[1].isdigit() or p[2] not in ('admin','operator','ai_manager','analyst'): return await m.answer('Format: /addop USER_ID operator')
    async with SessionLocal() as s: s.add(Operator(telegram_id=int(p[1]),role=p[2])); await log(s,m.from_user.id,'ADD_OPERATOR','operator',p[1],{'role':p[2]}); await s.commit()
    await m.answer('✅ Operator qo‘shildi.')

@router.callback_query(F.data=='adm:channels')
async def channels(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    async with SessionLocal() as s: rows=(await s.scalars(select(Channel).order_by(Channel.id))).all()
    text='<b>📢 Mandatory Channels</b>\n\n'+('\n'.join(f'{x.id}. {x.title} — <code>{x.chat_id}</code>' for x in rows) or 'Kanallar yo‘q.')+'\n\nQo‘shish: <code>/addchannel CHAT_ID | TITLE | INVITE_URL</code>\nO‘chirish: <code>/delchannel ID</code>'
    await c.message.edit_text(text,reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Command('addchannel'))
async def addchannel(m:Message):
    if not is_admin(m.from_user.id): return
    raw=m.text[len('/addchannel'):].strip(); p=[x.strip() for x in raw.split('|')]
    if len(p)!=3 or not p[0].lstrip('-').isdigit(): return await m.answer('Format: /addchannel CHAT_ID | TITLE | INVITE_URL')
    async with SessionLocal() as s: s.add(Channel(chat_id=int(p[0]),title=p[1],invite_url=p[2])); await log(s,m.from_user.id,'ADD_CHANNEL','channel',p[0]); await s.commit()
    await m.answer('✅ Kanal qo‘shildi.')

@router.message(Command('delchannel'))
async def delchannel(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split();
    if len(p)!=2 or not p[1].isdigit(): return await m.answer('Format: /delchannel ID')
    async with SessionLocal() as s:
        c=await s.get(Channel,int(p[1]));
        if not c:return await m.answer('Topilmadi.')
        await s.delete(c); await log(s,m.from_user.id,'DELETE_CHANNEL','channel',p[1]); await s.commit()
    await m.answer('✅ O‘chirildi.')

@router.callback_query(F.data=='adm:kb')
async def kb(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await deny(c)
    await state.set_state(Admin.kb_title); await c.message.edit_text('<b>📚 Knowledge Base</b>\n\nYangi maqola nomini yuboring. Keyin matnini yuborasiz.',reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Admin.kb_title)
async def kb_title(m:Message,state:FSMContext): await state.update_data(title=m.text); await state.set_state(Admin.kb_content); await m.answer('📄 Endi knowledge matnini yuboring.')
@router.message(Admin.kb_content)
async def kb_content(m:Message,state:FSMContext):
    data=await state.get_data();
    async with SessionLocal() as s: s.add(KnowledgeItem(title=data['title'],content=m.text)); await log(s,m.from_user.id,'ADD_KB','knowledge',data['title']); await s.commit()
    await state.clear(); await m.answer('✅ Knowledge Base ga qo‘shildi.')

@router.callback_query(F.data=='adm:learning')
async def learning(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    await c.message.edit_text('<b>🧠 AI Learning Lab</b>\n\nAdmin uchun prompt, coding, kutubxonalar, AI darslari va kanalga tayyor kontent generatori.',reply_markup=learning_menu(),parse_mode='HTML'); await c.answer()

@router.callback_query(F.data.startswith('learn:'))
async def learn_task(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await deny(c)
    task=c.data.split(':',1)[1]
    labels={'prompt':'Prompt Generator','code':'Coding / Libraries','channel':'Channel Content','lesson':'AI Lesson'}
    await state.update_data(kind=task); await state.set_state(Admin.learning); await c.message.answer(f'🧠 <b>{labels[task]}</b>\n\nNima kerakligini aniq yozing. Masalan: “Python async Telegram bot uchun Redis rate limiter yoz”.',parse_mode='HTML'); await c.answer()

@router.message(Admin.learning)
async def learn_run(m:Message,state:FSMContext):
    data=await state.get_data();
    instruction={'prompt':'Create advanced prompt templates with tags and best practices.', 'code':'Teach coding with complete examples, packages, architecture and debugging tips.', 'channel':'Create engaging, accurate, ready-to-post Telegram channel content about AI and coding. Include title, hook, body and tags.', 'lesson':'Create a practical AI learning lesson for an admin.'}[data['kind']]
    result=await ai_service.learning(instruction+'\nSpecific request: '+m.text,m.from_user.language_code or 'uz')
    async with SessionLocal() as s:
        s.add(LearningItem(kind=data['kind'],title=m.text[:255],prompt=m.text,content=result,tags=[data['kind']]))
        await log(s,m.from_user.id,'AI_LEARNING','learning',None,{'kind':data['kind']}); await s.commit()
    await state.clear(); import html as _html
    await m.answer(f'<b>🧠 Natija</b>\n\n{_html.escape(result)}',parse_mode='HTML')

@router.callback_query(F.data=='adm:broadcast')
async def broadcast(c:CallbackQuery,state:FSMContext):
    if not is_admin(c.from_user.id): return await deny(c)
    await state.set_state(Admin.broadcast); await c.message.edit_text('<b>📢 Broadcast</b>\n\nXabar matnini yuboring. Hozirgi versiya barcha faol userlarga yuboradi.',reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Admin.broadcast)
async def broadcast_send(m:Message,state:FSMContext):
    async with SessionLocal() as s: ids=(await s.scalars(select(User.telegram_id).where(User.is_banned==False))).all(); b=Broadcast(target_type='all',message_text=m.text,status='running'); s.add(b); await s.flush()
    sent=failed=0
    for uid in ids:
        try: await m.bot.send_message(uid,m.text,parse_mode='HTML'); sent+=1
        except Exception: failed+=1
    async with SessionLocal() as s:
        b=await s.get(Broadcast,b.id); b.status='done'; b.sent_count=sent; b.failed_count=failed; await log(s,m.from_user.id,'BROADCAST','broadcast',b.id,{'sent':sent,'failed':failed}); await s.commit()
    await state.clear(); await m.answer(f'✅ Broadcast tugadi. Yuborildi: {sent}, xato: {failed}')

@router.callback_query(F.data=='adm:quality')
async def quality(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    async with SessionLocal() as s:
        avg=await s.scalar(select(func.avg(Rating.score))) or 0; count=await s.scalar(select(func.count()).select_from(Rating)) or 0
    await c.message.edit_text(f'<b>⭐ Support Quality</b>\n\n⭐ Global rating: <b>{float(avg):.1f}</b>\n📝 Ratings: <b>{count}</b>',reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

for simple in ('adm:ai','adm:plans','adm:analytics','adm:promo','adm:security','adm:logs'):
    pass

@router.callback_query(F.data.in_({'adm:ai','adm:plans','adm:analytics','adm:promo','adm:security','adm:logs'}))
async def simple_sections(c:CallbackQuery):
    if not is_admin(c.from_user.id): return await deny(c)
    mapping={'adm:ai':'🤖 AI Management\n\nModel, system prompt, usage va fallback sozlamalari shu bo‘limda boshqariladi.','adm:plans':'⭐ Plans\n\nPlan limitlari env orqali seed qilinadi; user tarifi /setplan orqali o‘zgartiriladi.','adm:analytics':'📈 Analytics\n\nDashboard va usage_daily jadvalidagi eventlar orqali kengaytiriladi.','adm:promo':'🎟 Promo / Campaigns\n\nCampaign modelini keyingi migrationda kengaytirish mumkin.','adm:security':'🛡 Security\n\nBan, rate limit, RBAC va audit loglar faol.','adm:logs':'📋 Audit Logs\n\nAdmin amallari audit_logs jadvaliga yoziladi.'}
    await c.message.edit_text('<b>'+mapping[c.data].replace('\n\n','</b>\n\n',1),reply_markup=admin_back(),parse_mode='HTML'); await c.answer()

@router.message(Command('reply'))
async def operator_reply(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split(maxsplit=2)
    if len(p)<3:return await m.answer('Format: /reply TICKET_ID message')
    async with SessionLocal() as s:
        t=await s.scalar(select(Ticket).where(Ticket.public_id==p[1].upper()))
        if not t:return await m.answer('Ticket topilmadi.')
        u=await s.get(User,t.user_id); t.status='processing'; s.add(__import__('app.db.models',fromlist=['TicketMessage']).TicketMessage(ticket_id=t.id,sender_type='operator',sender_telegram_id=m.from_user.id,content=p[2])); await log(s,m.from_user.id,'TICKET_REPLY','ticket',t.public_id); await s.commit()
    await m.bot.send_message(u.telegram_id,f'👨‍💻 <b>Support javobi</b>\n\n{p[2]}\n\n🎫 #{t.public_id}',parse_mode='HTML'); await m.answer('✅ Javob yuborildi.')

@router.message(Command('close'))
async def operator_close(m:Message):
    if not is_admin(m.from_user.id): return
    p=m.text.split();
    if len(p)!=2:return await m.answer('Format: /close TICKET_ID')
    async with SessionLocal() as s:
        t=await s.scalar(select(Ticket).where(Ticket.public_id==p[1].upper()))
        if not t:return await m.answer('Ticket topilmadi.')
        u=await s.get(User,t.user_id); t.status='closed'; await log(s,m.from_user.id,'CLOSE_TICKET','ticket',t.public_id); await s.commit()
    await m.bot.send_message(u.telegram_id,f'✅ <b>Ticket #{t.public_id} yopildi.</b>\nXizmatni baholashingiz mumkin: /start',parse_mode='HTML'); await m.answer('✅ Ticket yopildi.')
