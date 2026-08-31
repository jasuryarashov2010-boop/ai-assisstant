from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

LABELS = {
    "uz": {
        "ai": "🤖 AI Yordamchi", "support": "💬 Support", "profile": "👤 Profil",
        "plans": "⭐ Tariflar", "settings": "⚙️ Sozlamalar", "ref": "🔗 Referral",
        "refresh": "🔄 Yangilash", "admin": "🛠 Admin Panel",
    },
    "en": {
        "ai": "🤖 AI Assistant", "support": "💬 Support", "profile": "👤 Profile",
        "plans": "⭐ Plans", "settings": "⚙️ Settings", "ref": "🔗 Referral",
        "refresh": "🔄 Refresh", "admin": "🛠 Admin Panel",
    },
    "ru": {
        "ai": "🤖 AI Помощник", "support": "💬 Поддержка", "profile": "👤 Профиль",
        "plans": "⭐ Тарифы", "settings": "⚙️ Настройки", "ref": "🔗 Реферал",
        "refresh": "🔄 Обновить", "admin": "🛠 Админ-панель",
    },
}

BACK = {"uz": "⬅️ Orqaga", "en": "⬅️ Back", "ru": "⬅️ Назад"}
CANCEL = {"uz": "❌ Bekor qilish", "en": "❌ Cancel", "ru": "❌ Отмена"}


def main_reply(is_admin: bool, lang: str = "uz") -> ReplyKeyboardMarkup:
    l = LABELS.get(lang, LABELS["uz"])
    rows = [
        [KeyboardButton(text=l["ai"]), KeyboardButton(text=l["support"])],
        [KeyboardButton(text=l["profile"]), KeyboardButton(text=l["plans"])],
        [KeyboardButton(text=l["settings"]), KeyboardButton(text=l["ref"])],
        [KeyboardButton(text=l["refresh"])],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=l["admin"])])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder={"uz": "Bo‘limni tanlang…", "en": "Choose a section…", "ru": "Выберите раздел…"}.get(lang),
    )


def ai_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    if lang == "en":
        labels = [
            ("💬 Chat", "ai:chat"), ("📂 My Chats", "ai:history"),
            ("🎙 Voice", "ai:voice"), ("📎 File Analysis", "ai:file"),
            ("🖼 Image Generation", "ai:image"), ("📷 Image Analysis", "ai:vision"),
            ("🌐 Translation", "ai:translate"), ("📚 Study Mode", "ai:study"),
            ("💻 Coding", "ai:coding"), ("📊 Data Analysis", "ai:data"),
            ("🎫 My Tickets", "ticket:list"),
        ]
    elif lang == "ru":
        labels = [
            ("💬 Чат", "ai:chat"), ("📂 Мои чаты", "ai:history"),
            ("🎙 Голос", "ai:voice"), ("📎 Анализ файла", "ai:file"),
            ("🖼 Создать изображение", "ai:image"), ("📷 Анализ изображения", "ai:vision"),
            ("🌐 Перевод", "ai:translate"), ("📚 Учёба", "ai:study"),
            ("💻 Кодинг", "ai:coding"), ("📊 Анализ данных", "ai:data"),
            ("🎫 Мои тикеты", "ticket:list"),
        ]
    else:
        labels = [
            ("💬 Chat", "ai:chat"), ("📂 Chatlarim", "ai:history"),
            ("🎙 Voice Support", "ai:voice"), ("📎 Fayl tahlili", "ai:file"),
            ("🖼 Rasm yaratish", "ai:image"), ("📷 Rasm tahlili", "ai:vision"),
            ("🌐 Tarjima", "ai:translate"), ("📚 Study Mode", "ai:study"),
            ("💻 Coding", "ai:coding"), ("📊 Data Analysis", "ai:data"),
            ("🎫 Mening murojaatlarim", "ticket:list"),
        ]
    b = InlineKeyboardBuilder()
    for text, callback in labels:
        b.button(text=text, callback_data=callback)
    b.button(text=BACK.get(lang, BACK["uz"]), callback_data="nav:main")
    b.adjust(2, 2, 2, 2, 2, 1)
    return b.as_markup()


def ai_chat_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    labels = {
        "uz": [("🆕 Yangi chat", "ai:new"), ("📂 Chatlarim", "ai:history"), ("🤖 AI menyu", "nav:ai")],
        "en": [("🆕 New chat", "ai:new"), ("📂 My chats", "ai:history"), ("🤖 AI menu", "nav:ai")],
        "ru": [("🆕 Новый чат", "ai:new"), ("📂 Мои чаты", "ai:history"), ("🤖 Меню AI", "nav:ai")],
    }[lang]
    for t, c in labels:
        b.button(text=t, callback_data=c)
    b.adjust(2, 1)
    return b.as_markup()


def chat_history(items, lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for item in items:
        title = (item.title or "New chat")[:28]
        b.button(text=f"💬 {title}", callback_data=f"ai:open:{item.id}")
    b.button(text="🆕 Yangi chat" if lang == "uz" else ("🆕 New chat" if lang == "en" else "🆕 Новый чат"), callback_data="ai:new")
    b.button(text=BACK.get(lang, BACK["uz"]), callback_data="nav:ai")
    b.adjust(1)
    return b.as_markup()


def back_menu(callback: str = "nav:main", lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BACK.get(lang, BACK["uz"]), callback_data=callback)]])


def plan_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="⭐ Pro", callback_data="plan:pro")
    b.button(text="💎 Comfort", callback_data="plan:comfort")
    b.button(text=BACK.get(lang, BACK["uz"]), callback_data="nav:main")
    b.adjust(2, 1)
    return b.as_markup()


def support_menu(lang: str = "uz") -> InlineKeyboardMarkup:
    labels = {
        "uz": [("💬 Supportga murojaat", "support:new"), ("📂 Mening ticketlarim", "ticket:list"), ("⭐ Baholash", "support:rate"), ("📝 Feedback", "support:feedback")],
        "en": [("💬 Contact support", "support:new"), ("📂 My tickets", "ticket:list"), ("⭐ Rate", "support:rate"), ("📝 Feedback", "support:feedback")],
        "ru": [("💬 Написать в поддержку", "support:new"), ("📂 Мои тикеты", "ticket:list"), ("⭐ Оценить", "support:rate"), ("📝 Отзыв", "support:feedback")],
    }[lang]
    b = InlineKeyboardBuilder()
    for text, callback in labels:
        b.button(text=text, callback_data=callback)
    b.button(text=BACK.get(lang, BACK["uz"]), callback_data="nav:main")
    b.adjust(1, 1, 2, 1)
    return b.as_markup()


def rating_kb(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{i}⭐", callback_data=f"rate:{ticket_id}:{i}") for i in range(1, 6)]])


def ticket_list(items, lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for ticket in items:
        status = {"pending": "🟡", "processing": "🔵", "closed": "🟢", "escalated": "🔴"}.get(ticket.status, "⚪")
        b.button(text=f"{status} #{ticket.public_id} · {ticket.subject[:18]}", callback_data=f"ticket:open:{ticket.public_id}")
    b.button(text="➕ Yangi ticket", callback_data="ticket:new")
    b.button(text=BACK.get(lang, BACK["uz"]), callback_data="nav:support")
    b.adjust(1)
    return b.as_markup()


def ticket_view(ticket, lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✉️ Davom ettirish" if lang == "uz" else ("✉️ Continue" if lang == "en" else "✉️ Продолжить"), callback_data=f"ticket:continue:{ticket.public_id}")
    if ticket.status != "closed":
        b.button(text="✅ Yopish" if lang == "uz" else ("✅ Close" if lang == "en" else "✅ Закрыть"), callback_data=f"ticket:close:{ticket.public_id}")
    b.button(text="⬅️ Ticketlar" if lang == "uz" else ("⬅️ Tickets" if lang == "en" else "⬅️ Тикеты"), callback_data="ticket:list")
    b.adjust(2, 1)
    return b.as_markup()


def subscription_kb(channels, lang: str = "uz") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for channel in channels:
        b.button(text=f"📢 {channel.title}", url=channel.invite_url)
    b.button(text="✅ Obunani tekshirish" if lang == "uz" else ("✅ Check subscription" if lang == "en" else "✅ Проверить подписку"), callback_data="check:sub")
    b.adjust(1)
    return b.as_markup()
