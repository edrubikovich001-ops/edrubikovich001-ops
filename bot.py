# bot.py
import os
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = Bot(BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Подключаем router только здесь (и только один раз)
router = Router(name="main")
dp.include_router(router)

# Клавиатура на главном экране
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Инцидент")],
        [KeyboardButton(text="✅ Закрыть")],
        [KeyboardButton(text="📊 Отчёт")],
    ],
    resize_keyboard=True,
)

@router.message(CommandStart())
async def cmd_start(m: types.Message):
    await m.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_kb,
    )

@router.message(F.text == "🆕 Инцидент")
async def new_incident(m: types.Message):
    await m.answer("Окей, начинаем регистрацию инцидента… (заглушка)")

@router.message(F.text == "✅ Закрыть")
async def close_incident(m: types.Message):
    await m.answer("Выбор инцидента для закрытия… (заглушка)")

@router.message(F.text == "📊 Отчёт")
async def report(m: types.Message):
    await m.answer("Выбор периода и формата отчёта… (заглушка)")
