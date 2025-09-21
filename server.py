# server.py
import os
import asyncio
from fastapi import FastAPI, Request
from aiogram import Dispatcher
from bot import dp, bot

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # ничего: webhook ты уже ставил руками; для Render достаточно работать по long-poll
    pass

@app.post("/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != os.environ.get("BOT_TOKEN"):
        return {"ok": False}
    update = await request.json()
    await dp.feed_webhook_update(bot, update)
    return {"ok": True}

# локальный запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
