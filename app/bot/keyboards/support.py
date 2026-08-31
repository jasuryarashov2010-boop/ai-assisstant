from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def support_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='💬 Supportga murojaat',callback_data='support:new')],
        [InlineKeyboardButton(text='📂 Mening ticketlarim',callback_data='ticket:list')],
        [InlineKeyboardButton(text='⭐ Baholash',callback_data='support:rate'),InlineKeyboardButton(text='📝 Feedback',callback_data='support:feedback')],
    ])

def rating_kb(ticket_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i)+'⭐',callback_data=f'rate:{ticket_id}:{i}') for i in range(1,6)]])
