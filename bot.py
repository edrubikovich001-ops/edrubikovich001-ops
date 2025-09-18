import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Put it into .env or environment variables.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Привет! Я бот. Готов принять обращение.\n"
        "Напишите вашу проблему одним сообщением или используйте /help."
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start — приветствие.\n"
        "/help — справка.\n"
        "Просто отправьте текст — я зафиксирую обращение."
    )

@dp.message(F.text)
async def collect_complaint(message: Message):
    user = message.from_user
    await message.answer(
        f"Спасибо, {user.full_name or 'гость'}! Ваше сообщение получено:\n\n"
        f"“{message.text}”\n\n"
        "Мы свяжемся с вами при необходимости."
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
