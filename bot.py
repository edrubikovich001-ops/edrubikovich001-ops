import os
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
)
from aiogram.filters import Command

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# parse_mode задан через DefaultBotProperties (aiogram v3)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🆕 Инцидент", callback_data="incident:new")],
        [InlineKeyboardButton(text="✅ Закрыть", callback_data="incident:close")],
        [InlineKeyboardButton(text="📊 Отчёт", callback_data="report:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_menu_kb()
    )

# Точные обработчики
@router.callback_query(F.data == "incident:new")
async def incident_new(cb: CallbackQuery):
    log.info("callback_query data=%s", cb.data)
    await cb.answer()  # быстрый ответ во всплывашку
    await cb.message.answer("Окей, начинаем регистрацию инцидента… (заглушка)")

@router.callback_query(F.data == "incident:close")
async def incident_close(cb: CallbackQuery):
    log.info("callback_query data=%s", cb.data)
    await cb.answer()
    await cb.message.answer("Закрытие инцидента… (заглушка)")

@router.callback_query(F.data == "report:menu")
async def report_menu(cb: CallbackQuery):
    log.info("callback_query data=%s", cb.data)
    await cb.answer()
    await cb.message.answer("Меню отчётов… (заглушка)")

# Подстраховка: «ловим всё», чтобы точно видеть реакцию
@router.callback_query()
async def any_callback(cb: CallbackQuery):
    log.info("UNHANDLED callback_query data=%s", cb.data)
    # Ответим, чтобы показать, что клик дошёл
    await cb.answer("Получено: " + (cb.data or "—"))
    await cb.message.answer(f"Колбэк пришёл: <code>{cb.data}</code>")
