# server.py — FastAPI + Aiogram v3 (webhook)
import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from bot import router  # наши хендлеры

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

app = FastAPI(title="SalesLossTracker 2.0 Bot")

# Важно: не передаём parse_mode и прочие снятые параметры (aiogram v3.7+).
bot = Bot(BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)   # подключаем наш роутер ровно один раз

@app.get("/", response_class=PlainTextResponse)
async def root():
    return "OK"

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "healthy"

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    # примитивная защита: только наш токен в пути
    if token != BOT_TOKEN:
        raise HTTPException(status_code=403, detail="forbidden")

    data = await request.json()
    logging.info("server: Update JSON: %s", data)

    try:
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        logging.exception("update handling error: %s", e)
        # отвечаем 200, чтобы Telegram не фладил ретраями
        return JSONResponse({"ok": True})

    return JSONResponse({"ok": True})
