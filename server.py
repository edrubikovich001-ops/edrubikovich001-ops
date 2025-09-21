# server.py — FastAPI + aiogram v3 webhook
import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot import dp, BOT_TOKEN  # импортируем уже собранный dp и токен

# Логи по умолчанию
logging.basicConfig(level=logging.INFO)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")  # можно не задавать
APP_URL = os.getenv("APP_URL", "")               # не обязателен для работы на Render
TZ = os.getenv("TZ", "Asia/Almaty")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
app = FastAPI()

# Точку /webhook/{token} используем для безопасности «по токену»
@app.post(f"/webhook/{{token}}")
async def telegram_webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return Response(status_code=403)
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return Response(status_code=200)

# healthcheck
@app.get("/")
async def root():
    return {"status": "ok"}

# запуск dp-startup не нужен — в v3 feed_update достаточен
