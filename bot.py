# bot.py — Aiogram v3: базовое меню и реакция на кнопки с эмодзи
from __future__ import annotations

import re
import logging
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router(name="main")

# ——— Красивые кнопки (с эмодзи) ———
BTN_INCIDENT_ICON = "🆕"
BTN_CLOSE_ICON    = "✅"
BTN_REPORT_ICON   = "📊"

BTN_INCIDENT = f"{BTN_INCIDENT_ICON} Инцидент"
BTN_CLOSE    = f"{BTN_CLOSE_ICON} Закрыть"
BTN_REPORT   = f"{BTN_REPORT_ICON} Отчёт"

def main_menu() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text=BTN_INCIDENT)],
        [KeyboardButton(text=BTN_CLOSE)],
        [KeyboardButton(text=BTN_REPORT)],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ——— Регулярки: ловим варианты с эмодзи/без и «Отчет/Отчёт» ———
INCIDENT_RX = re.compile(r"Инцидент", re.IGNORECASE)
CLOSE_RX    = re.compile(r"Закрыть", re.IGNORECASE)
REPORT_RX   = re.compile(r"Отч[её]т", re.IGNORECASE)

@router.message(CommandStart())
async def on_start(message: types.Message):
    logging.info("Start from %s (%s)", message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_menu(),
    )

@router.message(F.text.regexp(INCIDENT_RX))
async def on_incident(message: types.Message):
    logging.info("Incident click: %r", message.text)
    # Здесь позже добавим сценарий инцидента; пока заглушка
    await message.answer("Окей, начинаем регистрацию инцидента… (заглушка)")

@router.message(F.text.regexp(CLOSE_RX))
async def on_close(message: types.Message):
    logging.info("Close click: %r", message.text)
    await message.answer("Закрытие инцидента… (заглушка)")

@router.message(F.text.regexp(REPORT_RX))
async def on_report(message: types.Message):
    logging.info("Report click: %r", message.text)
    await message.answer("Формирование отчёта… (заглушка)")

# Фоллбек: любой другой текст — подсказываем про кнопки
@router.message(F.text)
async def fallback(message: types.Message):
    logging.info("Text (no match): %r", message.text)
    await message.answer("Не понял. Нажмите кнопку ниже 👇", reply_markup=main_menu())
