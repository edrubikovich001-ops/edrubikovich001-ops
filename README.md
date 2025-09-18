# Telegram Bot (aiogram 3)

## Быстрый старт (локально)
1. Установите Python 3.11+.
2. Скопируйте `.env.example` в `.env` и вставьте ваш `BOT_TOKEN`.
3. Установите зависимости: `pip install -r requirements.txt`
4. Запустите: `python run_local.py`

## Docker
```
docker build -t tg-bot .
docker run --rm -e BOT_TOKEN=xxx tg-bot
```

## Render (деплой без сервера)
- Подключите репозиторий к Render → New → Worker.
- Укажите переменную окружения `BOT_TOKEN`.
- Деплой произойдёт автоматически.
