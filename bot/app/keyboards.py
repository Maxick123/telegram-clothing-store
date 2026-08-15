from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👕 Каталог"), KeyboardButton(text="🔥 Новинки")], [KeyboardButton(text="🏷 Скидки"), KeyboardButton(text="❤️ Избранное")], [KeyboardButton(text="🛒 Корзина"), KeyboardButton(text="📦 Мои заказы")], [KeyboardButton(text="💬 Поддержка"), KeyboardButton(text="👤 Профиль")]], resize_keyboard=True)


def payment_keyboard(confirmation_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Перейти к оплате", url=confirmation_url)]])
