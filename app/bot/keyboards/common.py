from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

LABELS={
'uz':{'ai':'🤖 AI Yordamchi','support':'💬 Support','profile':'👤 Profil','plans':'⭐ Tariflar','settings':'⚙️ Sozlamalar','ref':'🔗 Referral','refresh':'🔄 Yangilash','admin':'🛠 Admin Panel'},
'en':{'ai':'🤖 AI Assistant','support':'💬 Support','profile':'👤 Profile','plans':'⭐ Plans','settings':'⚙️ Settings','ref':'🔗 Referral','refresh':'🔄 Refresh','admin':'🛠 Admin Panel'},
'ru':{'ai':'🤖 AI Помощник','support':'💬 Поддержка','profile':'👤 Профиль','plans':'⭐ Тарифы','settings':'⚙️ Настройки','ref':'🔗 Реферал','refresh':'🔄 Обновить','admin':'🛠 Админ-панель'},
}

def main_reply(is_admin=False,lang='uz'):
    l=LABELS.get(lang,LABELS['uz'])
    rows=[[KeyboardButton(text=l['ai']),KeyboardButton(text=l['support'])],[KeyboardButton(text=l['profile']),KeyboardButton(text=l['plans'])],[KeyboardButton(text=l['settings']),KeyboardButton(text=l['ref'])],[KeyboardButton(text=l['refresh'])]]
    if is_admin: rows.append([KeyboardButton(text=l['admin'])])
    return ReplyKeyboardMarkup(keyboard=rows,resize_keyboard=True,input_field_placeholder='Bo‘limni tanlang…')

def ai_menu(lang='uz'):
    labels={
        'uz':[('💬 Chat','ai:chat'),('🎙 Voice Support','ai:voice'),('📎 Fayl tahlili','ai:file'),('🖼 Rasm yaratish','ai:image'),('📷 Rasmni tahlil qilish','ai:vision'),('🌐 Tarjima','ai:translate'),('📚 Study Mode','ai:study'),('💻 Coding','ai:coding'),('📊 Data Analysis','ai:data'),('📂 Mening murojaatlarim','ticket:list')],
        'en':[('💬 Chat','ai:chat'),('🎙 Voice Support','ai:voice'),('📎 File Analysis','ai:file'),('🖼 Image Generation','ai:image'),('📷 Image Analysis','ai:vision'),('🌐 Translation','ai:translate'),('📚 Study Mode','ai:study'),('💻 Coding','ai:coding'),('📊 Data Analysis','ai:data'),('📂 My Tickets','ticket:list')],
        'ru':[('💬 Чат','ai:chat'),('🎙 Голос','ai:voice'),('📎 Анализ файла','ai:file'),('🖼 Создать изображение','ai:image'),('📷 Анализ изображения','ai:vision'),('🌐 Перевод','ai:translate'),('📚 Учёба','ai:study'),('💻 Кодинг','ai:coding'),('📊 Анализ данных','ai:data'),('📂 Мои тикеты','ticket:list')]
    }[lang]
    b=InlineKeyboardBuilder()
    for t,c in labels: b.button(text=t,callback_data=c)
    b.adjust(2,2,2,2,2); return b.as_markup()

def back_menu(cb='back'): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Orqaga',callback_data=cb)]])

def plan_menu(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⭐ Pro',callback_data='plan:pro'),InlineKeyboardButton(text='💎 Comfort',callback_data='plan:comfort')],[InlineKeyboardButton(text='⬅️ Orqaga',callback_data='back')]])

def ticket_list(items):
    b=InlineKeyboardBuilder()
    for t in items: b.button(text=f'🎫 #{t.public_id} • {t.status}',callback_data=f'ticket:open:{t.public_id}')
    b.button(text='➕ Yangi ticket',callback_data='ticket:new'); b.button(text='⬅️ Orqaga',callback_data='back'); b.adjust(1); return b.as_markup()

def subscription_kb(channels):
    b=InlineKeyboardBuilder()
    for c in channels: b.button(text=f'📢 {c.title}',url=c.invite_url)
    b.button(text='✅ Obunani tekshirish',callback_data='check:sub'); b.adjust(1); return b.as_markup()
