import asyncio
import html
import logging
from collections.abc import Awaitable, Callable

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from app.api_client import BackendClient, BackendError
from app.config import Settings, get_settings
from app.keyboards import main_menu, payment_keyboard
from app.support import SupportRelay

LOGGER = logging.getLogger(__name__)
MENU_MESSAGES = {
    "👕 Каталог": "Каталог пока не содержит опубликованных товаров.",
    "🔥 Новинки": "Новинки появятся здесь сразу после публикации коллекции.",
    "🏷 Скидки": "Активных акций сейчас нет. Следите за обновлениями магазина.",
    "❤️ Избранное": "В избранном пока нет товаров. Добавляйте их из карточек каталога.",
    "🛒 Корзина": "Ваша корзина пока пуста.",
    "📦 Мои заказы": "У вас пока нет оформленных заказов.",
}


def money(kopecks: int) -> str:
    return f"{kopecks / 100:,.2f}".replace(",", " ").replace(".", ",") + " ₽"


def customer_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


def message_media(message: Message) -> list[dict[str, str]]:
    """Store Telegram file references without downloading customer media into the bot container."""
    media: list[dict[str, str]] = []
    if message.photo:
        media.append({"type": "photo", "file_id": message.photo[-1].file_id})
    for name, kind in (("video", "video"), ("document", "document"), ("voice", "voice"), ("animation", "animation"), ("sticker", "sticker"), ("video_note", "video_note")):
        attachment = getattr(message, name, None)
        if attachment is not None:
            media.append({"type": kind, "file_id": attachment.file_id})
    return media


async def report_backend_error(answer: Callable[[str], Awaitable[Message]], error: BackendError) -> None:
    messages = {
        "insufficient_stock": "К сожалению, выбранный размер или цвет уже закончился.",
        "variant_not_found": "Эта модификация товара больше недоступна.",
        "product_not_found": "Товар больше недоступен.",
        "already_favorite": "Этот товар уже есть в избранном.",
        "active_cart_not_found": "Корзина не найдена. Добавьте товар в корзину ещё раз.",
        "cart_is_empty": "Корзина пуста.",
        "order_not_found": "Заказ не найден.",
        "order_not_payable": "Этот заказ уже нельзя оплатить.",
        "backend_unavailable": "Магазин временно недоступен. Попробуйте немного позже.",
    }
    await answer(messages.get(error.detail, "Не удалось выполнить действие. Попробуйте ещё раз."))


def build_dispatcher(bot: Bot, backend: BackendClient, settings: Settings) -> Dispatcher:
    dispatcher = Dispatcher()
    relay = SupportRelay()

    @dispatcher.message(CommandStart())
    async def start(message: Message) -> None:
        name = html.escape(message.from_user.first_name) if message.from_user else ""
        greeting = f"Здравствуйте, {name}! " if name else "Здравствуйте! "
        await message.answer(greeting + "Добро пожаловать в магазин одежды. Выберите раздел.", reply_markup=main_menu())

    @dispatcher.message(F.text == "👤 Профиль")
    async def profile(message: Message) -> None:
        name = html.escape(message.from_user.full_name) if message.from_user else "Покупатель"
        await message.answer(
            f"<b>Профиль</b>\n{name}\n\nДанные получателя будут сохранены при первом оформлении заказа.",
            parse_mode="HTML",
        )

    @dispatcher.message(F.text == "💬 Поддержка")
    async def support(message: Message) -> None:
        await message.answer("Напишите вопрос или отправьте медиафайл — оператор ответит вам от имени магазина.")

    @dispatcher.message(F.text.in_(set(MENU_MESSAGES)))
    async def storefront_menu(message: Message) -> None:
        await message.answer(MENU_MESSAGES[message.text])

    @dispatcher.message(Command("add_variant"))
    async def add_variant(message: Message, command: CommandObject) -> None:
        telegram_id = customer_id(message)
        if telegram_id is None or not command.args:
            await message.answer("Откройте товар в каталоге и выберите размер с цветом.")
            return
        variant_id, *quantity_arg = command.args.split()
        try:
            quantity = int(quantity_arg[0]) if quantity_arg else 1
            if not 1 <= quantity <= 20:
                raise ValueError
            result = await backend.add_cart_item(telegram_id, variant_id, quantity=quantity)
        except ValueError:
            await message.answer("Количество должно быть от 1 до 20.")
        except BackendError as error:
            await report_backend_error(message.answer, error)
        else:
            await message.answer(f"Товар добавлен в корзину. Сумма: <b>{money(int(result['subtotal_kopecks']))}</b>", parse_mode="HTML")

    @dispatcher.message(Command("favorite"))
    async def favorite(message: Message, command: CommandObject) -> None:
        telegram_id = customer_id(message)
        if telegram_id is None or not command.args:
            await message.answer("Откройте карточку товара и добавьте его в избранное.")
            return
        try:
            await backend.add_favorite(telegram_id, command.args.strip())
        except BackendError as error:
            await report_backend_error(message.answer, error)
        else:
            await message.answer("Товар добавлен в избранное ❤️")

    @dispatcher.callback_query(F.data.startswith("cart:add:"))
    async def callback_add_cart_item(callback: CallbackQuery) -> None:
        if callback.message is None or callback.from_user is None:
            return
        variant_id = callback.data.removeprefix("cart:add:")
        try:
            result = await backend.add_cart_item(callback.from_user.id, variant_id)
        except BackendError as error:
            await callback.answer("Не удалось добавить товар", show_alert=True)
            await report_backend_error(callback.message.answer, error)
        else:
            await callback.answer("Добавлено в корзину")
            await callback.message.answer(f"Товар добавлен в корзину. Сумма: <b>{money(int(result['subtotal_kopecks']))}</b>", parse_mode="HTML")

    @dispatcher.callback_query(F.data.startswith("favorite:add:"))
    async def callback_add_favorite(callback: CallbackQuery) -> None:
        if callback.message is None or callback.from_user is None:
            return
        product_id = callback.data.removeprefix("favorite:add:")
        try:
            await backend.add_favorite(callback.from_user.id, product_id)
        except BackendError as error:
            await callback.answer("Не удалось добавить товар", show_alert=True)
            await report_backend_error(callback.message.answer, error)
        else:
            await callback.answer("Добавлено в избранное")

    @dispatcher.callback_query(F.data.startswith("payment:"))
    async def pay_order(callback: CallbackQuery) -> None:
        if callback.message is None or callback.from_user is None:
            return
        order_id = callback.data.removeprefix("payment:")
        try:
            payment = await backend.create_yookassa_payment(callback.from_user.id, order_id)
        except BackendError as error:
            await callback.answer("Не удалось создать платёж", show_alert=True)
            await report_backend_error(callback.message.answer, error)
        else:
            await callback.answer()
            await callback.message.answer("Заказ создан. Перейдите к безопасной оплате ЮKassa.", reply_markup=payment_keyboard(str(payment["confirmation_url"])))

    if settings.telegram_admin_group_id is not None:

        @dispatcher.message(F.chat.id == settings.telegram_admin_group_id, F.reply_to_message)
        async def relay_operator_reply(message: Message) -> None:
            reply_to = message.reply_to_message
            if reply_to is None:
                return
            customer_chat_id = relay.customer_for_reply(reply_to.message_id)
            if customer_chat_id is None:
                return
            try:
                await bot.copy_message(chat_id=customer_chat_id, from_chat_id=message.chat.id, message_id=message.message_id)
            except Exception:
                LOGGER.exception("Could not relay an operator reply to customer", extra={"customer_chat_id": customer_chat_id})
                await message.reply("Не удалось доставить ответ клиенту.")

    @dispatcher.message(F.chat.type == "private")
    async def relay_customer_message(message: Message) -> None:
        if settings.telegram_admin_group_id is None:
            await message.answer("Поддержка временно недоступна. Попробуйте позже.")
            return
        if message.from_user is None:
            return
        try:
            saved = await backend.create_customer_message(
                message.from_user.id,
                content=message.text or message.caption,
                media=message_media(message),
                telegram_message_id=message.message_id,
            )
        except BackendError as error:
            await report_backend_error(message.answer, error)
            return
        customer_name = html.escape(message.from_user.full_name)
        username = f"@{html.escape(message.from_user.username)}" if message.from_user.username else "не указан"
        context = await bot.send_message(
            settings.telegram_admin_group_id,
            "<b>Новое обращение</b>\n"
            f"Клиент: {customer_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: <code>{message.from_user.id}</code>\n\n"
            f"Диалог: <code>{html.escape(str(saved['conversation_id']))}</code>\n"
            "Ответьте реплаем на это сообщение или на скопированное сообщение клиента.",
            parse_mode="HTML",
        )
        copied = await bot.copy_message(
            chat_id=settings.telegram_admin_group_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
        relay.remember(context.message_id, message.chat.id)
        relay.remember(copied.message_id, message.chat.id)
        await message.answer("Сообщение передано оператору. Ответ придёт сюда от имени магазина.")

    return dispatcher


async def run() -> None:
    settings = get_settings()
    bot = Bot(token=settings.telegram_bot_token)
    backend = BackendClient(settings.backend_url)
    dispatcher = build_dispatcher(bot, backend, settings)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await backend.close()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
