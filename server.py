# server.py — FastAPI-вебхук для aiogram v3

import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ==== окружение ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
# Render сам прокидывает публичный URL в переменную RENDER_EXTERNAL_URL,
# но на всякий случай оставим твой домен как дефолт.
RENDER_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://saleslosstracker-2-0-bot.onrender.com"
)

# В aiogram v3 parse_mode передаём через DefaultBotProperties:
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

# Путь вебхука: /webhook/<ТОКЕН>
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"


# ===== healthcheck =====
@app.get("/")
async def root():
    return {"status": "running", "webhook_path": WEBHOOK_PATH}


# ===== входящий вебхук от Telegram =====
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)


# ===== события старта/останова =====
@app.on_event("startup")
async def on_startup():
    try:
        # Привяжем вебхук к правильному пути.
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        print("Webhook set to:", WEBHOOK_URL)
    except Exception as e:
        print("Webhook set error:", e)


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook()
    except Exception:
        pass
