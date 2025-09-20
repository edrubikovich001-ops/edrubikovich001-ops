# server.py — FastAPI-вебхук для aiogram v3

import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

# === окружение ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "https://saleslosstracker-2-0-bot.onrender.com")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())

app = FastAPI()

# путь вебхука: /webhook/<ТОКЕН>
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"


# ====== healthcheck ======
@app.get("/")
async def root():
    return {"status": "running", "webhook": WEBHOOK_PATH}


# ====== Telegram webhook ======
@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # Telegram шлёт JSON с update
    data = await request.json()
    update = types.Update(**data)
    # передаём апдейт в диспетчер aiogram
    await dp.feed_update(bot, update)
    return Response(status_code=200)


# ====== события старта/останова ======
@app.on_event("startup")
async def on_startup():
    # привяжем вебхук к правильному пути
    try:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    except Exception as e:
        print("Webhook set error:", e)


@app.on_event("shutdown")
async def on_shutdown():
    try:
        await bot.delete_webhook()
    except Exception:
        pass
