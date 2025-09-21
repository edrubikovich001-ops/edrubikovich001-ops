# bot.py
from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder

router = Router()  # <— ВАЖНО: эта переменная импортируется в server.py

# Кнопки главного меню
def main_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🆕 Инцидент")
    kb.button(text="✅ Закрыть")
    kb.button(text="📊 Отчёт")
    kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "Привет! Я бот учёта потерь продаж.\n"
        "Выберите действие из меню ниже."
    )
    await message.answer(text, reply_markup=main_menu_kb())

# Заглушки на кнопки
@router.message(lambda m: m.text in {"🆕 Инцидент", "Инцидент"})
async def new_incident_stub(message: types.Message):
    await message.answer("Окей, начинаем регистрацию инцидента… (заглушка)")

@router.message(lambda m: m.text in {"✅ Закрыть", "Закрыть"})
async def close_incident_stub(message: types.Message):
    await message.answer("Выбор открытого инцидента для закрытия… (заглушка)")

@router.message(lambda m: m.text in {"📊 Отчёт", "Отчёт"})
async def report_stub(message: types.Message):
    await message.answer("Выбор периода и формата отчёта… (заглушка)")
