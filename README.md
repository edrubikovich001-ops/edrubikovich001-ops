# SalesLossTracker 2.0 Bot

FastAPI + Aiogram v3 (webhook). Готов к деплою на Render.

## Запуск локально
1. `python -m venv .venv && source .venv/bin/activate` (Windows: `.\.venv\Scripts\activate`)
2. `pip install -r requirements.txt`
3. Экспортируй переменные:
   - `export BOT_TOKEN=...`
   - `export TZ=Asia/Almaty`
4. `python run_local.py` → http://localhost:8000/health

## Вебхук (Render)
После деплоя в Render:
1. Скопируй URL сервиса, например: `https://your-bot.onrender.com`
2. Открой в браузере:
