# server.py — HTTP health + запуск бота в фоне
import asyncio
from fastapi import FastAPI
from bot import run_bot

app = FastAPI()

@app.get("/")
def health():
    return {"status": "ok"}

@app.on_event("startup")
async def _startup():
    asyncio.create_task(run_bot())
