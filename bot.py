import os
import logging
from fastapi import FastAPI, Request, HTTPException
from aiogram.types import Update
from bot import dp, bot  # dp и bot — из bot.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

@app.get("/")
async def root():
    return {"status": "ok"}

# Вебхук ровно по токену
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    logger.info("Update JSON: %s", data)

    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}
