# server.py — HTTP-сервер + запуск бота в фоне (для Render Web Service)

import asyncio
from fastapi import FastAPI
from bot import main as run_bot  # из bot.py

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.on_event("startup")
async def start_bot():
    # запускаем aiogram-поллинг в отдельной задаче
    asyncio.create_task(run_bot())
