import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Update
from aiogram.client.default import DefaultBotProperties

from bot import router
import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)

app = FastAPI(title="SalesLossTracker 2.0 Bot")

@app.on_event("startup")
async def _startup():
    await db.init_pool()
    logger.info("DB pool initialized")

@app.on_event("shutdown")
async def _shutdown():
    await db.close_pool()
    logger.info("DB pool closed")

@app.get("/")
async def root():
    return {"status": "ok", "service": "SalesLossTracker_2.0"}

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
