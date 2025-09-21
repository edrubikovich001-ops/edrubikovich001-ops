# server.py
import os
from fastapi import FastAPI, Request, HTTPException
from aiogram import types
from aiogram.types import Update
from bot import dp, bot  # dp и bot берём из bot.py

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

# корень просто для проверки доступности
@app.get("/")
async def root():
    return {"status": "ok"}

# ровно такой путь, как мы поставили в setWebhook (с вашим токеном)
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
