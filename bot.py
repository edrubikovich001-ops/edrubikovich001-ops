# bot.py — кнопки и обработчики (aiogram v3)

from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

BTN_INCIDENT = "🆕 Инцидент"
BTN_CLOSE    = "✅ Закрыть"
BTN_REPORT   = "📊 Отчёт"

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_INCIDENT)],
        [KeyboardButton(text=BTN_CLOSE)],
        [KeyboardButton(text=BTN_REPORT)],
    ],
    resize_keyboard=True,
)

@router.message(F.text == "/start")
async def on_start(message: Message):
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\n"
        "Выберите действие из меню ниже.",
        reply_markup=main_kb,
    )

@router.message(F.text == BTN_INCIDENT)
async def on_incident(message: Message):
    await message.answer("Окей, начинаем регистрацию инцидента…")

@router.message(F.text == BTN_CLOSE)
async def on_close(message: Message):
    await message.answer("Режим закрытия инцидента… (скоро добавим выбор открытых записей)")

@router.message(F.text == BTN_REPORT)
async def on_report(message: Message):
    await message.answer("Режим отчётов… (скоро появится PDF и Excel по периодам)")

@router.message()
async def fallback(message: Message):
    await message.answer(
        "Нажмите кнопку внизу: «Инцидент», «Закрыть» или «Отчёт».",
        reply_markup=main_kb,
    )
