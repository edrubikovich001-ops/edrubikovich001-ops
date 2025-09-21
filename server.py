# server.py
import os
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update

from bot import bot, dp  # берём уже созданные bot и dp; router здесь не трогаем

APP_URL = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("BASE_URL")
BOT_TOKEN = os.environ["BOT_TOKEN"]

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    # Настраиваем вебхук на наш URL
    if not APP_URL:
        return
    webhook_url = f"{APP_URL}/webhook/{BOT_TOKEN}"
    await bot.delete_webhook(drop_pending_updates=True)
    ok = await bot.set_webhook(webhook_url)
    if not ok:
        raise RuntimeError("Failed to set webhook")

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    # Простейшая проверка токена в пути
    if token != BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
