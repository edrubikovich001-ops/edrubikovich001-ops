# server.py — HTTP-сервер (FastAPI) + Webhook aiogram v3

import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties

# наши обработчики
from bot import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set (Render → Environment → add BOT_TOKEN)")

# aiogram v3: parse_mode через DefaultBotProperties!
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

app = FastAPI(title="SalesLossTracker 2.0 Bot")

@app.get("/")
async def root():
    return {"status": "ok", "service": "SalesLossTracker_2.0"}

# Вебхук. ВАЖНО: путь содержит токен — именно такой URL ставим в setWebhook
@app.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.exception("bad json")
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("server:Update JSON: %s", str(data)[:800])

    try:
        update = Update.model_validate(data)
    except Exception as e:
        logger.exception("update validate error")
        raise HTTPException(status_code=422, detail=str(e))

    try:
        await dp.feed_update(bot, update)
    except Exception:
        logger.exception("handler failed")

    return JSONResponse({"ok": True})
