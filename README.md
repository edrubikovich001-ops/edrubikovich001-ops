# Sales Loss Tracker Bot

Телеграм-бот (aiogram v3) для учёта потерь:
- «Инцидент» → *закрыть сейчас* (ввод конца) или *закрыть позже* (сохраняем open).
- «Закрыть» → список открытых, выбор конца/причины/коммента/суммы.
- Кнопка **◀️ Назад** на каждом шаге. Сумма — 💰.

## Локально
```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                               # заполнить BOT_TOKEN и DATABASE_URL
python run_local.py
