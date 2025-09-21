# server.py
import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot import router  # <— импортируем router из bot.py

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

app = FastAPI()
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

@app.get("/")
async def root():
    return {"status": "ok"}

# Вебхук: /webhook/<полный_токен>
@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        # Защита: только наш токен
        return Response(status_code=403)
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)
