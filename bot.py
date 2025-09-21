# bot.py — SalesLossTracker 2.0
import os
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Tuple, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)

import asyncpg

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")  # например: postgresql://user:pass@host/db?sslmode=require

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sales_loss_bot")

# ---------- DB helpers ----------
async def get_pool() -> asyncpg.Pool:
    # создаём пул один раз на процесс
    if not hasattr(get_pool, "_pool"):
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        get_pool._pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return get_pool._pool  # type: ignore[attr-defined]


async def fetch_managers() -> List[asyncpg.Record]:
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch("SELECT id, name FROM managers ORDER BY name")
        return rows


async def fetch_manager_restaurants(manager_id: int) -> List[asyncpg.Record]:
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch(
            """
            SELECT r.id, r.name
            FROM restaurants r
            JOIN manager_restaurants mr ON mr.restaurant_id = r.id
            WHERE mr.manager_id = $1
            ORDER BY r.name
            """,
            manager_id,
        )
        return rows


# ---------- FSM ----------
class IncidentForm(StatesGroup):
    manager = State()
    restaurant = State()
    day = State()
    hour_start = State()
    minute_start = State()
    close_choice = State()
    hour_end = State()
    minute_end = State()
    reason = State()
    comment = State()
    amount = State()
    confirm = State()


# ---------- Keyboards ----------
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🆕 Инцидент"),
                KeyboardButton(text="✅ Закрыть"),
            ],
            [
                KeyboardButton(text="📊 Отчёт"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


def list_to_inline_buttons(items: List[Tuple[str, str]], row_width: int = 2) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(items), row_width):
        row = [InlineKeyboardButton(text=txt, callback_data=cb) for txt, cb in items[i:i+row_width]]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def days_kb() -> InlineKeyboardMarkup:
    today = date.today()
    items: List[Tuple[str, str]] = []
    # Сегодня/вчера первыми
    items.append((f"📅 Сегодня ({today:%d.%m})", f"day:{today.isoformat()}"))
    y = today - timedelta(days=1)
    items.append((f"📅 Вчера ({y:%d.%m})", f"day:{y.isoformat()}"))
    # Ещё до 7 дней назад
    for d in range(2, 8):
        dd = today - timedelta(days=d)
        # показываем день недели + дату
        items.append((f"📅 {dd:%a} ({dd:%d.%m})", f"day:{dd.isoformat()}"))
    return list_to_inline_buttons(items, row_width=2)


def hours_kb(prefix: str) -> InlineKeyboardMarkup:
    items = [(f"🕰 {h:02d}", f"{prefix}:{h}") for h in range(0, 24)]
    return list_to_inline_buttons(items, row_width=6)


def minutes_kb(prefix: str) -> InlineKeyboardMarkup:
    for_vals = [0, 15, 30, 45]
    items = [(f"🕒 {m:02d}", f"{prefix}:{m}") for m in for_vals]
    return list_to_inline_buttons(items, row_width=4)


def close_choice_kb() -> InlineKeyboardMarkup:
    items = [
        ("🔒 Закрыть сейчас", "close:now"),
        ("⏳ Закрыть позже", "close:later"),
    ]
    return list_to_inline_buttons(items, row_width=2)


def reasons_kb() -> InlineKeyboardMarkup:
    items = [
        ("🌧 Внешние потери", "reason:external"),
        ("🏭 Внутренние потери", "reason:internal"),
        ("👥 Нехватка персонала", "reason:staff_shortage"),
        ("🍔 Отсутствие продукта", "reason:no_product"),
    ]
    return list_to_inline_buttons(items, row_width=2)


def amounts_kb() -> InlineKeyboardMarkup:
    preset = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]
    items = [(f"🪙 {v:,}".replace(",", " "), f"amount:{v}") for v in preset]
    items.append(("✍️ Другая сумма", "amount:other"))
    return list_to_inline_buttons(items, row_width=3)


def back_only_kb(cbdata: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=cbdata)]]
    )


# ---------- Bot & handlers ----------
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_menu_kb(),
    )


@dp.message(F.text == "🆕 Инцидент")
async def incident_start(m: Message, state: FSMContext):
    # показываем список управляющих
    rows = await fetch_managers()
    if not rows:
        await m.answer("Список управляющих пуст.")
        return

    items = [(f"👤 {r['name']}", f"mgr:{r['id']}") for r in rows]
    kb = list_to_inline_buttons(items, row_width=2)
    await state.set_state(IncidentForm.manager)
    await m.answer("Выберите ТУ (управляющего):", reply_markup=kb)


@dp.callback_query(IncidentForm.manager, F.data.startswith("mgr:"))
async def pick_manager(c: CallbackQuery, state: FSMContext):
    manager_id = int(c.data.split(":", 1)[1])
    await state.update_data(manager_id=manager_id)

    # подгружаем рестораны
    rows = await fetch_manager_restaurants(manager_id)
    if not rows:
        await c.message.edit_text("У выбранного ТУ нет ресторанов.")
        await c.answer()
        return

    items = [(f"🍗 {r['name']}", f"rest:{r['id']}") for r in rows]
    await state.set_state(IncidentForm.restaurant)
    await c.message.edit_text("Выберите ресторан:", reply_markup=list_to_inline_buttons(items, row_width=2))
    await c.answer()


@dp.callback_query(IncidentForm.restaurant, F.data.startswith("rest:"))
async def pick_restaurant(c: CallbackQuery, state: FSMContext):
    rest_id = int(c.data.split(":", 1)[1])
    await state.update_data(restaurant_id=rest_id)

    # день
    await state.set_state(IncidentForm.day)
    await c.message.edit_text("Выберите день инцидента:", reply_markup=days_kb())
    await c.answer()


@dp.callback_query(IncidentForm.day, F.data.startswith("day:"))
async def pick_day(c: CallbackQuery, state: FSMContext):
    day_iso = c.data.split(":", 1)[1]
    await state.update_data(day=day_iso)

    # время начала — часы
    await state.set_state(IncidentForm.hour_start)
    await c.message.edit_text("⏰ Выберите час начала (0–23):", reply_markup=hours_kb("hstart"))
    await c.answer()


@dp.callback_query(IncidentForm.hour_start, F.data.startswith("hstart:"))
async def pick_hour_start(c: CallbackQuery, state: FSMContext):
    hour = int(c.data.split(":", 1)[1])
    await state.update_data(hour_start=hour)

    # минуты начала
    await state.set_state(IncidentForm.minute_start)
    await c.message.edit_text("🕒 Выберите минуты начала:", reply_markup=minutes_kb("mstart"))
    await c.answer()


@dp.callback_query(IncidentForm.minute_start, F.data.startswith("mstart:"))
async def pick_minute_start(c: CallbackQuery, state: FSMContext):
    minute = int(c.data.split(":", 1)[1])
    await state.update_data(minute_start=minute)

    # выбор закрыть сейчас/позже
    await state.set_state(IncidentForm.close_choice)
    await c.message.edit_text("Как поступим с завершением инцидента?", reply_markup=close_choice_kb())
    await c.answer()


@dp.callback_query(IncidentForm.close_choice, F.data == "close:now")
async def choose_close_now(c: CallbackQuery, state: FSMContext):
    # если «закрыть сейчас» — спрашиваем время окончания
    await state.set_state(IncidentForm.hour_end)
    await c.message.edit_text("⏰ Час конца (0–23):", reply_markup=hours_kb("hend"))
    await c.answer()


@dp.callback_query(IncidentForm.close_choice, F.data == "close:later")
async def choose_close_later(c: CallbackQuery, state: FSMContext):
    # отметим, что конец позже
    await state.update_data(close_later=True)
    # дальше — причина
    await state.set_state(IncidentForm.reason)
    await c.message.edit_text("🗂️ Причина:", reply_markup=reasons_kb())
    await c.answer()


@dp.callback_query(IncidentForm.hour_end, F.data.startswith("hend:"))
async def pick_hour_end(c: CallbackQuery, state: FSMContext):
    hour = int(c.data.split(":", 1)[1])
    await state.update_data(hour_end=hour)

    await state.set_state(IncidentForm.minute_end)
    await c.message.edit_text("🕒 Минуты конца:", reply_markup=minutes_kb("mend"))
    await c.answer()


@dp.callback_query(IncidentForm.minute_end, F.data.startswith("mend:"))
async def pick_minute_end(c: CallbackQuery, state: FSMContext):
    minute = int(c.data.split(":", 1)[1])
    await state.update_data(minute_end=minute, close_later=False)

    await state.set_state(IncidentForm.reason)
    await c.message.edit_text("🗂️ Причина:", reply_markup=reasons_kb())
    await c.answer()


@dp.callback_query(IncidentForm.reason, F.data.startswith("reason:"))
async def pick_reason(c: CallbackQuery, state: FSMContext):
    reason = c.data.split(":", 1)[1]
    await state.update_data(reason=reason)

    await state.set_state(IncidentForm.comment)
    await c.message.edit_text("💬 Комментарий (введите текст; можно «—»):")
    await c.answer()


@dp.message(IncidentForm.comment)
async def get_comment(m: Message, state: FSMContext):
    text = (m.text or "").strip()
    if not text:
        await m.answer("Введите комментарий (или «—»).")
        return
    await state.update_data(comment=text)

    await state.set_state(IncidentForm.amount)
    await m.answer("💰 Сумма потерь (тенге):", reply_markup=amounts_kb())


@dp.callback_query(IncidentForm.amount, F.data.startswith("amount:"))
async def pick_amount(c: CallbackQuery, state: FSMContext):
    kind = c.data.split(":", 1)[1]
    if kind == "other":
        await c.message.edit_text("Введите сумму числом (тенге):", reply_markup=None)
        await c.answer()
        return

    amount = int(kind)
    await state.update_data(amount=amount)
    await show_confirm(c.message, state)
    await state.set_state(IncidentForm.confirm)
    await c.answer()


@dp.message(IncidentForm.amount)
async def type_amount(m: Message, state: FSMContext):
    raw = (m.text or "").replace(" ", "")
    if not raw.isdigit():
        await m.answer("Нужно число в тенге. Попробуйте снова:")
        return
    amount = int(raw)
    await state.update_data(amount=amount)
    await show_confirm(m, state)
    await state.set_state(IncidentForm.confirm)


async def show_confirm(target_message: Message, state: FSMContext):
    data = await state.get_data()
    # читаемые поля
    day = date.fromisoformat(data["day"])
    h1 = data["hour_start"]
    m1 = data["minute_start"]
    close_later = data.get("close_later", None)

    if close_later is False:
        h2 = data.get("hour_end")
        m2 = data.get("minute_end")
        end_str = f"{h2:02d}:{m2:02d}"
        # длительность
        start_dt = datetime.combine(day, datetime.min.time()).replace(hour=h1, minute=m1)
        end_dt = datetime.combine(day, datetime.min.time()).replace(hour=h2, minute=m2)
        delta = end_dt - start_dt
        dur_min = int(delta.total_seconds() // 60)
        dur_str = f"{dur_min} мин"
    else:
        end_str = "—"
        dur_str = "—"

    reasons_map = {
        "external": "Внешние потери",
        "internal": "Внутренние потери",
        "staff_shortage": "Нехватка персонала",
        "no_product": "Отсутствие продукта",
    }

    text = (
        "Подтверждение:\n"
        f"• ТУ: выбран (ID {data['manager_id']})\n"
        f"• Ресторан: выбран (ID {data['restaurant_id']})\n"
        f"• Время начала: {day:%d.%m.%Y} {h1:02d}:{m1:02d}\n"
        f"• Время конца: {end_str}\n"
        f"• Длительность: {dur_str}\n"
        f"• Причина: {reasons_map.get(data['reason'], data['reason'])}\n"
        f"• Комментарий: {data['comment']}\n"
        f"• Сумма: 🪙 {data['amount']:,} KZT".replace(",", " ")
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Да, сохранить", callback_data="confirm:save")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="confirm:cancel")],
        ]
    )
    await target_message.answer(text, reply_markup=kb)


@dp.callback_query(IncidentForm.confirm, F.data == "confirm:cancel")
async def confirm_cancel(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("Отменено. Возврат в меню.", reply_markup=None)
    await c.message.answer("Что дальше?", reply_markup=main_menu_kb())
    await c.answer()


@dp.callback_query(IncidentForm.confirm, F.data == "confirm:save")
async def confirm_save(c: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pool = await get_pool()

    # составляем timestamps
    start_dt = datetime.combine(date.fromisoformat(data["day"]), datetime.min.time()).replace(
        hour=data["hour_start"], minute=data["minute_start"]
    )
    end_dt: Optional[datetime] = None
    if data.get("close_later") is False:
        end_dt = datetime.combine(date.fromisoformat(data["day"]), datetime.min.time()).replace(
            hour=data["hour_end"], minute=data["minute_end"]
        )

    async with pool.acquire() as con:
        await con.execute(
            """
            INSERT INTO incidents
                (manager_id, restaurant_id, start_time, end_time, reason, comment, amount_kzt, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7,
                    CASE WHEN $4 IS NULL THEN 'open' ELSE 'closed' END)
            """,
            data["manager_id"],
            data["restaurant_id"],
            start_dt,
            end_dt,
            data["reason"],
            data["comment"],
            int(data["amount"]),
        )

    await state.clear()
    await c.message.edit_text("✅ Инцидент сохранён.", reply_markup=None)
    await c.message.answer("Готово. Что дальше?", reply_markup=main_menu_kb())
    await c.answer()


# ------- Заглушки для двух кнопок меню, чтобы не молчали -------
@dp.message(F.text == "✅ Закрыть")
async def close_placeholder(m: Message):
    await m.answer("Список открытых инцидентов и закрытие — скоро подключим. Пока доступна регистрация «Инцидент».",
                   reply_markup=main_menu_kb())


@dp.message(F.text == "📊 Отчёт")
async def report_placeholder(m: Message):
    await m.answer("Отчёты PDF/Excel добавим после завершения мастера инцидентов.",
                   reply_markup=main_menu_kb())


# ---------- runner ----------
async def run_bot():
    # прогреем пул
    if DATABASE_URL:
        await get_pool()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
