import os
import re
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup, KeyboardButton,
)

# === Безопасность переменных ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env is not set")

# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# === Клавиатуры ===
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Инцидент")],
        [KeyboardButton(text="✅ Закрыть")],
        [KeyboardButton(text="📊 Отчёт")],
    ],
    resize_keyboard=True,
)

def _norm(text: str) -> str:
    """
    Нормализуем текст: в нижний регистр, удаляем эмодзи/знаки,
    чтобы хэндлеры срабатывали и с эмодзи, и без.
    """
    if not text:
        return ""
    t = text.lower()
    # удалим всё кроме букв/цифр/пробелов (упростим)
    t = re.sub(r"[^\w\sёЁа-яa-z0-9]", "", t, flags=re.IGNORECASE)
    # сводим ё -> е
    t = t.replace("ё", "е")
    return t.strip()

# === Хэндлеры ===

@router.message(CommandStart())
async def start_cmd(msg: Message):
    await msg.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=MAIN_KB
    )

@router.message(F.text)
async def main_menu_handler(msg: Message):
    t = _norm(msg.text)

    # ловим варианты с/без эмодзи, в любом регистре
    if "инцидент" in t:
        await msg.answer("Окей, начинаем регистрацию инцидента… (заглушка)")
        return

    if "закрыть" in t or "закрытие" in t:
        await msg.answer("Открытые инциденты для закрытия… (заглушка)")
        return

    if "отчет" in t or "отчёт" in t:
        await msg.answer("Какой период отчёта выбрать? (заглушка)")
        return

    # Если ничего не подошло — мягкая подсказка
    await msg.answer(
        "Я не понял команду. Нажмите одну из кнопок ниже.",
        reply_markup=MAIN_KB
    )

# === Регистрация роутера ===
dp.include_router(router)

# === Запуск через server.py (uvicorn) ===
# Ничего здесь не запускаем — диспетчер стартует из server.py
