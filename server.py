# server.py — FastAPI-вебхук для aiogram v3

import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Подключаем роутер с хэндлерами
from bot import router

# ==== окружение ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# Render может прокинуть публичный URL в RENDER_EXTERNAL_URL.
# Если переменной нет — используем твой домен.
RENDER_URL = os.getenv(
    "RENDER_EXTERNAL_URL",
    "https://saleslosstracker-2-0-bot.onrender.com"
)

# В aiogram v3 parse_mode задаётся через DefaultBotProperties
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

app = FastAPI()

# Путь вебхука: /webhook/<ТОКЕН>
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{RENDER_URL}{WEBHOOK_PATH}"


@app.get("/")
async def root():
    # healthcheck
    return {"status": "running", "webhook_path": WEBHOOK_PATH}


@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    # приём апдейтов от Telegram
    data = await request.json()
    update = types.Update(**data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)


@app.on_event("startup")
async def on_startup():
    # устанавливаем вебхук на наш маршрут
    try:
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
