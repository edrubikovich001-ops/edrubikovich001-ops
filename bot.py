# bot.py — aiogram v3.x
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart

# === Безопасность и конфиг ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

router = Router()
dp = Dispatcher()
dp.include_router(router)

# === Тексты кнопок: приём и с эмодзи и без ===
INCIDENT_BTN_TXT = {"Инцидент", "🆕 Инцидент"}
CLOSE_BTN_TXT    = {"Закрыть", "✅ Закрыть"}
REPORT_BTN_TXT   = {"Отчёт", "📊 Отчёт"}

def main_menu_kb() -> ReplyKeyboardMarkup:
    # Показываем красивые подписи (с эмодзи),
    # но хендлеры примут и без эмодзи.
    rows = [
        [KeyboardButton(text="🆕 Инцидент")],
        [KeyboardButton(text="✅ Закрыть")],
        [KeyboardButton(text="📊 Отчёт")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…"
    )

# === Хендлеры ===
@router.message(CommandStart())
async def on_start(message: Message):
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_menu_kb(),
    )

# Инцидент — принимаем варианты текста с/без эмодзи
@router.message(F.text.in_(INCIDENT_BTN_TXT))
async def on_incident(message: Message):
    await message.answer("Окей, начинаем регистрацию инцидента… (заглушка)")

# Закрыть — варианты с/без эмодзи
@router.message(F.text.in_(CLOSE_BTN_TXT))
async def on_close(message: Message):
    await message.answer("Закрытие инцидента… (заглушка)")

# Отчёт — варианты с/без эмодзи
@router.message(F.text.in_(REPORT_BTN_TXT))
async def on_report(message: Message):
    await message.answer("Генерация отчёта… (заглушка)")

# На всякий случай: эхо для отладки остальных сообщений
@router.message(F.text)
async def fallback(message: Message):
    await message.answer(
        f"Я понял: «{message.text}».\nВыберите действие на клавиатуре ниже.",
        reply_markup=main_menu_kb(),
    )
