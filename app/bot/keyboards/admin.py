from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu():
    b=InlineKeyboardBuilder()
    items=[('📊 Dashboard','adm:dashboard'),('👥 Users','adm:users'),('🎫 Tickets','adm:tickets'),('👨‍💻 Operators','adm:operators'),('🤖 AI Management','adm:ai'),('📚 Knowledge Base','adm:kb'),('📢 Broadcast','adm:broadcast'),('⭐ Plans','adm:plans'),('📢 Channels','adm:channels'),('⭐ Support Quality','adm:quality'),('📈 Analytics','adm:analytics'),('🧠 AI Learning','adm:learning'),('🎟 Promo / Campaigns','adm:promo'),('🛡 Security','adm:security'),('📋 Audit Logs','adm:logs')]
    for t,c in items: b.button(text=t,callback_data=c)
    b.adjust(2,2,2,2,2,2,2,1); return b.as_markup()

def admin_back(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Admin menu',callback_data='adm:home')]])

def learning_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='💡 Prompt Generator',callback_data='learn:prompt'),InlineKeyboardButton(text='💻 Coding / Libraries',callback_data='learn:code')],[InlineKeyboardButton(text='📢 Channel Content',callback_data='learn:channel'),InlineKeyboardButton(text='📚 AI Lesson',callback_data='learn:lesson')],[InlineKeyboardButton(text='⬅️ Admin',callback_data='adm:home')]])
