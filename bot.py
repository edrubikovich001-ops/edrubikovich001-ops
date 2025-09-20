# bot.py — роутеры и простые хэндлеры aiogram v3

from aiogram import Router, F, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)

router = Router()

# Основное меню (как просили — три кнопки)
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Инцидент")],
        [KeyboardButton(text="✅ Закрыть")],
        [KeyboardButton(text="📊 Отчёт")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие…",
)


@router.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\n"
        "Выберите действие из меню ниже.",
        reply_markup=MAIN_KB,
    )


# Заглушки, чтобы видеть, что хэндлеры работают
@router.message(F.text == "🆕 Инцидент")
async def new_incident(message: types.Message):
    await message.answer("Окей, начинаем регистрацию инцидента… (заглушка)")


@router.message(F.text == "✅ Закрыть")
async def close_incident(message: types.Message):
    await message.answer("Выбор открытых инцидентов для закрытия… (заглушка)")


@router.message(F.text == "📊 Отчёт")
async def report_menu(message: types.Message):
    await message.answer("Выбор периода и формата отчёта… (заглушка)")
