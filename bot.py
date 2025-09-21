# bot.py
import os
import asyncio
from datetime import datetime, timedelta, date, time
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

import asyncpg
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ─────────────────────────────── DB LAYER ─────────────────────────────── #

async def db_pool():
    # создаём singleton-pool на модуле
    if not hasattr(db_pool, "_pool"):
        db_pool._pool = await asyncpg.create_pool(dsn=DATABASE_URL, max_size=5)
    return db_pool._pool  # type: ignore[attr-defined]


async def fetch_managers() -> List[asyncpg.Record]:
    pool = await db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT id, name FROM managers ORDER BY name")


async def fetch_restaurants_by_manager(manager_id: int) -> List[asyncpg.Record]:
    pool = await db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT r.id, r.name
            FROM restaurants r
            JOIN manager_restaurants mr ON mr.restaurant_id = r.id
            WHERE mr.manager_id = $1
            ORDER BY r.name
        """, manager_id)


async def insert_incident(data: dict) -> int:
    pool = await db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO incidents
               (manager_id, restaurant_id, start_time, end_time,
                reason, comment, amount, status)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id
        """,
        data["manager_id"],
        data["restaurant_id"],
        data["start_dt"],
        data.get("end_dt"),
        data["reason"],
        data["comment"],
        data["amount"],
        data["status"])
        return row["id"]


async def fetch_open_incidents() -> List[asyncpg.Record]:
    pool = await db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT i.id, m.name AS manager, r.name AS restaurant,
                   i.start_time, i.amount, i.reason
            FROM incidents i
            JOIN managers m ON m.id = i.manager_id
            JOIN restaurants r ON r.id = i.restaurant_id
            WHERE i.status = 'open'
            ORDER BY i.start_time DESC
        """)


async def close_incident(incident_id: int, end_dt: datetime):
    pool = await db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE incidents
               SET end_time = $2, status = 'closed'
             WHERE id = $1
        """, incident_id, end_dt)

# ─────────────────────────────── FSM & HELPERS ─────────────────────────────── #

LOSS_REASONS = [
    ("Внешние потери", "external"),
    ("Внутренние потери", "internal"),
    ("Нехватка персонала", "staff_shortage"),
    ("Отсутствие продукта", "no_product"),
]

AMOUNTS = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]


@dataclass
class IncidentDraft:
    manager_id: Optional[int] = None
    manager_name: Optional[str] = None
    restaurant_id: Optional[int] = None
    restaurant_name: Optional[str] = None
    start_date: Optional[date] = None
    start_hour: Optional[int] = None
    start_min: Optional[int] = None
    end_hour: Optional[int] = None
    end_min: Optional[int] = None
    close_now: Optional[bool] = None
    reason: Optional[str] = None
    reason_label: Optional[str] = None
    comment: Optional[str] = None
    amount: Optional[int] = None

    @property
    def start_dt(self) -> Optional[datetime]:
        if self.start_date is None or self.start_hour is None or self.start_min is None:
            return None
        return datetime.combine(self.start_date, time(self.start_hour, self.start_min))

    @property
    def end_dt(self) -> Optional[datetime]:
        if self.end_hour is None or self.end_min is None:
            return None
        # если конец в тот же день
        base_date = self.start_date or date.today()
        return datetime.combine(base_date, time(self.end_hour, self.end_min))


class IncidentFSM(StatesGroup):
    choosing_manager = State()
    choosing_restaurant = State()
    choosing_day = State()
    choosing_start_hour = State()
    choosing_start_min = State()
    choose_close_mode = State()
    choosing_end_hour = State()
    choosing_end_min = State()
    choosing_reason = State()
    entering_comment = State()
    choosing_amount = State()
    confirming = State()


class CloseOpenFSM(StatesGroup):
    picking_incident = State()
    picking_end_hour = State()
    picking_end_min = State()
    confirming = State()


def kb_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🆕 Инцидент", callback_data="act_incident")
    kb.button(text="✅ Закрыть", callback_data="act_close")
    kb.button(text="📊 Отчёт", callback_data="act_report")
    kb.adjust(1)
    return kb.as_markup()

def kb_back(text="↩️ Назад", cb="back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=cb)]])

def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✖️ Отменить", callback_data="cancel")]])

def dt_label(d: date) -> str:
    if d == date.today():
        return "Сегодня"
    if d == date.today() - timedelta(days=1):
        return "Вчера"
    return d.strftime("%d.%m (%a)")

# ─────────────────────────────── /start ─────────────────────────────── #

@router.message(CommandStart())
async def on_start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=kb_main_menu()
    )

# ─────────────────────────────── ИНЦИДЕНТ ─────────────────────────────── #

@router.callback_query(F.data == "act_incident")
async def start_incident(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft()
    await state.set_data(asdict(draft))
    # список управляющих
    managers = await fetch_managers()
    if not managers:
        await cb.message.edit_text("В базе пока нет управляющих.", reply_markup=kb_main_menu())
        return
    kb = InlineKeyboardBuilder()
    for row in managers:
        kb.button(text=f"👤 {row['name']}", callback_data=f"mgr:{row['id']}:{row['name']}")
    kb.button(text="↩️ Назад", callback_data="back_main")
    kb.adjust(1)
    await cb.message.edit_text("Выберите управляющего:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_manager)


@router.callback_query(IncidentFSM.choosing_manager, F.data.startswith("mgr:"))
async def pick_manager(cb: CallbackQuery, state: FSMContext):
    _, sid, name = cb.data.split(":", 2)
    draft = IncidentDraft(**await state.get_data())
    draft.manager_id = int(sid)
    draft.manager_name = name
    await state.set_data(asdict(draft))

    # рестораны управляющего
    rests = await fetch_restaurants_by_manager(draft.manager_id)
    if not rests:
        await cb.message.edit_text("У этого управляющего нет ресторанов.", reply_markup=kb_back("⬅️ В меню", "back_main"))
        return

    kb = InlineKeyboardBuilder()
    for r in rests:
        kb.button(text=f"🍗 {r['name']}", callback_data=f"rest:{r['id']}:{r['name']}")
    kb.button(text="↩️ Назад", callback_data="back_manager")
    kb.adjust(1)
    await cb.message.edit_text(f"Управляющий: <b>{draft.manager_name}</b>\nВыберите ресторан:",
                               reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_restaurant)


@router.callback_query(IncidentFSM.choosing_restaurant, F.data == "back_manager")
async def back_to_managers(cb: CallbackQuery, state: FSMContext):
    managers = await fetch_managers()
    kb = InlineKeyboardBuilder()
    for row in managers:
        kb.button(text=f"👤 {row['name']}", callback_data=f"mgr:{row['id']}:{row['name']}")
    kb.button(text="↩️ Назад", callback_data="back_main")
    kb.adjust(1)
    await cb.message.edit_text("Выберите управляющего:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_manager)


@router.callback_query(IncidentFSM.choosing_restaurant, F.data.startswith("rest:"))
async def pick_restaurant(cb: CallbackQuery, state: FSMContext):
    _, sid, name = cb.data.split(":", 2)
    draft = IncidentDraft(**await state.get_data())
    draft.restaurant_id = int(sid)
    draft.restaurant_name = name
    await state.set_data(asdict(draft))

    # даты до 7 дней
    kb = InlineKeyboardBuilder()
    for i in range(0, 8):
        d = date.today() - timedelta(days=i)
        kb.button(text=f"📅 {dt_label(d)}", callback_data=f"d:{d.isoformat()}")
    kb.button(text="↩️ Назад", callback_data="back_rest")
    kb.adjust(2)
    await cb.message.edit_text(
        f"ТУ: <b>{draft.manager_name}</b>\nРесторан: <b>{draft.restaurant_name}</b>\n\nВыберите день начала:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(IncidentFSM.choosing_day)


@router.callback_query(IncidentFSM.choosing_day, F.data == "back_rest")
async def back_to_restaurants(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    rests = await fetch_restaurants_by_manager(draft.manager_id or 0)
    kb = InlineKeyboardBuilder()
    for r in rests:
        kb.button(text=f"🍗 {r['name']}", callback_data=f"rest:{r['id']}:{r['name']}")
    kb.button(text="↩️ Назад", callback_data="back_manager")
    kb.adjust(1)
    await cb.message.edit_text(f"Управляющий: <b>{draft.manager_name}</b>\nВыберите ресторан:",
                               reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_restaurant)


@router.callback_query(IncidentFSM.choosing_day, F.data.startswith("d:"))
async def pick_day(cb: CallbackQuery, state: FSMContext):
    d = date.fromisoformat(cb.data[2:])
    draft = IncidentDraft(**await state.get_data())
    draft.start_date = d
    await state.set_data(asdict(draft))

    # часы
    kb = InlineKeyboardBuilder()
    for h in range(24):
        kb.button(text=f"{h:02d} ⏰", callback_data=f"h:{h}")
    kb.button(text="↩️ Назад", callback_data="back_day")
    kb.adjust(6)
    await cb.message.edit_text(
        f"Дата начала: <b>{dt_label(d)}</b>\n\nВыберите час начала:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(IncidentFSM.choosing_start_hour)


@router.callback_query(IncidentFSM.choosing_start_hour, F.data == "back_day")
async def back_to_day(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for i in range(0, 8):
        d = date.today() - timedelta(days=i)
        kb.button(text=f"📅 {dt_label(d)}", callback_data=f"d:{d.isoformat()}")
    kb.button(text="↩️ Назад", callback_data="back_rest")
    kb.adjust(2)
    await cb.message.edit_text("Выберите день начала:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_day)


@router.callback_query(IncidentFSM.choosing_start_hour, F.data.startswith("h:"))
async def pick_start_hour(cb: CallbackQuery, state: FSMContext):
    h = int(cb.data[2:])
    draft = IncidentDraft(**await state.get_data())
    draft.start_hour = h
    await state.set_data(asdict(draft))

    kb = InlineKeyboardBuilder()
    for m in (0, 15, 30, 45):
        kb.button(text=f"{m:02d} 🕒", callback_data=f"m:{m}")
    kb.button(text="↩️ Назад", callback_data="back_hour")
    kb.adjust(4)
    await cb.message.edit_text(f"Час начала: <b>{h:02d}</b>\nВыберите минуты:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_start_min)


@router.callback_query(IncidentFSM.choosing_start_min, F.data == "back_hour")
async def back_hour(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for h in range(24):
        kb.button(text=f"{h:02d} ⏰", callback_data=f"h:{h}")
    kb.button(text="↩️ Назад", callback_data="back_day")
    kb.adjust(6)
    await cb.message.edit_text("Выберите час начала:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_start_hour)


@router.callback_query(IncidentFSM.choosing_start_min, F.data.startswith("m:"))
async def pick_start_min(cb: CallbackQuery, state: FSMContext):
    mm = int(cb.data[2:])
    draft = IncidentDraft(**await state.get_data())
    draft.start_min = mm
    await state.set_data(asdict(draft))

    kb = InlineKeyboardBuilder()
    kb.button(text="🔒 Закрыть сейчас", callback_data="close_now")
    kb.button(text="⏳ Закрыть позже", callback_data="close_later")
    kb.button(text="↩️ Назад", callback_data="back_min")
    kb.adjust(1)
    await cb.message.edit_text(
        (f"Начало: <b>{draft.start_date.strftime('%d.%m')}</b> "
         f"{draft.start_hour:02d}:{draft.start_min:02d}\n\n"
         "Выберите режим закрытия:"),
        reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choose_close_mode)


@router.callback_query(IncidentFSM.choose_close_mode, F.data == "back_min")
async def back_min(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    h = draft.start_hour or 0
    kb = InlineKeyboardBuilder()
    for m in (0, 15, 30, 45):
        kb.button(text=f"{m:02d} 🕒", callback_data=f"m:{m}")
    kb.button(text="↩️ Назад", callback_data="back_hour")
    kb.adjust(4)
    await cb.message.edit_text(f"Час начала: <b>{h:02d}</b>\nВыберите минуты:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_start_min)


@router.callback_query(IncidentFSM.choose_close_mode, F.data.in_(("close_now", "close_later")))
async def choose_close_mode(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    draft.close_now = cb.data == "close_now"
    await state.set_data(asdict(draft))

    if draft.close_now:
        # сразу спросим время окончания
        kb = InlineKeyboardBuilder()
        for h in range(24):
            kb.button(text=f"{h:02d} ⏰", callback_data=f"eh:{h}")
        kb.button(text="↩️ Назад", callback_data="back_closemode")
        kb.adjust(6)
        await cb.message.edit_text("Выберите час окончания:", reply_markup=kb.as_markup())
        await state.set_state(IncidentFSM.choosing_end_hour)
    else:
        # идём к причинам
        await go_choose_reason(cb, state)


@router.callback_query(IncidentFSM.choosing_end_hour, F.data == "back_closemode")
async def back_closemode(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔒 Закрыть сейчас", callback_data="close_now")
    kb.button(text="⏳ Закрыть позже", callback_data="close_later")
    kb.button(text="↩️ Назад", callback_data="back_min")
    kb.adjust(1)
    await cb.message.edit_text("Выберите режим закрытия:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choose_close_mode)


@router.callback_query(IncidentFSM.choosing_end_hour, F.data.startswith("eh:"))
async def pick_end_hour(cb: CallbackQuery, state: FSMContext):
    h = int(cb.data[3:])
    draft = IncidentDraft(**await state.get_data())
    draft.end_hour = h
    await state.set_data(asdict(draft))

    kb = InlineKeyboardBuilder()
    for m in (0, 15, 30, 45):
        kb.button(text=f"{m:02d} 🕒", callback_data=f"em:{m}")
    kb.button(text="↩️ Назад", callback_data="back_end_hour")
    kb.adjust(4)
    await cb.message.edit_text(f"Час конца: <b>{h:02d}</b>\nВыберите минуты:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_end_min)


@router.callback_query(IncidentFSM.choosing_end_min, F.data == "back_end_hour")
async def back_end_hour(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for h in range(24):
        kb.button(text=f"{h:02d} ⏰", callback_data=f"eh:{h}")
    kb.button(text="↩️ Назад", callback_data="back_closemode")
    kb.adjust(6)
    await cb.message.edit_text("Выберите час окончания:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_end_hour)


@router.callback_query(IncidentFSM.choosing_end_min, F.data.startswith("em:"))
async def pick_end_min(cb: CallbackQuery, state: FSMContext):
    mm = int(cb.data[3:])
    draft = IncidentDraft(**await state.get_data())
    draft.end_min = mm
    await state.set_data(asdict(draft))
    await go_choose_reason(cb, state)


async def go_choose_reason(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for label, code in LOSS_REASONS:
        kb.button(text=label, callback_data=f"reason:{code}:{label}")
    kb.button(text="↩️ Назад", callback_data="back_to_time")
    kb.adjust(1)
    await cb.message.edit_text("🗂️ Причина потерь:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_reason)


@router.callback_query(IncidentFSM.choosing_reason, F.data == "back_to_time")
async def back_to_time(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    # если close_now → мы пришли с end_min, иначе с choose_close_mode
    if draft.close_now:
        kb = InlineKeyboardBuilder()
        for m in (0, 15, 30, 45):
            kb.button(text=f"{m:02d} 🕒", callback_data=f"em:{m}")
        kb.button(text="↩️ Назад", callback_data="back_end_hour")
        kb.adjust(4)
        await cb.message.edit_text("Выберите минуты окончания:", reply_markup=kb.as_markup())
        await state.set_state(IncidentFSM.choosing_end_min)
    else:
        kb = InlineKeyboardBuilder()
        kb.button(text="🔒 Закрыть сейчас", callback_data="close_now")
        kb.button(text="⏳ Закрыть позже", callback_data="close_later")
        kb.button(text="↩️ Назад", callback_data="back_min")
        kb.adjust(1)
        await cb.message.edit_text("Выберите режим закрытия:", reply_markup=kb.as_markup())
        await state.set_state(IncidentFSM.choose_close_mode)


@router.callback_query(IncidentFSM.choosing_reason, F.data.startswith("reason:"))
async def pick_reason(cb: CallbackQuery, state: FSMContext):
    _, code, label = cb.data.split(":", 2)
    draft = IncidentDraft(**await state.get_data())
    draft.reason = code
    draft.reason_label = label
    await state.set_data(asdict(draft))
    await cb.message.edit_text("💬 Введите комментарий (или отправьте дефис «-»):", reply_markup=kb_back())
    await state.set_state(IncidentFSM.entering_comment)


@router.message(IncidentFSM.entering_comment)
async def enter_comment(m: Message, state: FSMContext):
    text = m.text.strip()
    draft = IncidentDraft(**await state.get_data())
    draft.comment = "—" if text in {"-", "—"} else text
    await state.set_data(asdict(draft))

    kb = InlineKeyboardBuilder()
    for val in AMOUNTS:
        kb.button(text=f"{val:,}".replace(",", " "), callback_data=f"amt:{val}")
    kb.button(text="Другая сумма", callback_data="amt:other")
    kb.button(text="↩️ Назад", callback_data="back_comment")
    kb.adjust(3)
    await m.answer("💸 Выберите сумму (KZT) или «Другая сумма»:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_amount)


@router.callback_query(IncidentFSM.choosing_amount, F.data == "back_comment")
async def back_comment(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("💬 Введите комментарий (или отправьте дефис «-»):", reply_markup=kb_back())
    await state.set_state(IncidentFSM.entering_comment)


@router.callback_query(IncidentFSM.choosing_amount, F.data.startswith("amt:"))
async def pick_amount(cb: CallbackQuery, state: FSMContext):
    _, tail = cb.data.split(":", 1)
    draft = IncidentDraft(**await state.get_data())

    if tail == "other":
        await cb.message.edit_text("Введите сумму числом (например, 123456):", reply_markup=kb_back())
        # остаёмся в этом же стейте, но дальше перехватит message-хэндлер
        return
    else:
        draft.amount = int(tail)
        await state.set_data(asdict(draft))
        await show_confirm(cb, state)


@router.message(IncidentFSM.choosing_amount)
async def enter_custom_amount(m: Message, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    try:
        val = int(m.text.replace(" ", ""))
        if val <= 0:
            raise ValueError
    except Exception:
        await m.answer("Введите положительное целое число. Либо нажмите «Назад».", reply_markup=kb_back())
        return
    draft.amount = val
    await state.set_data(asdict(draft))
    await show_confirm(m, state)


async def show_confirm(source: Message | CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())
    start = draft.start_dt.strftime("%d.%m %H:%M") if draft.start_dt else "—"
    end = draft.end_dt.strftime("%d.%m %H:%M") if draft.end_dt else "—"
    dur_text = "—"
    if draft.end_dt and draft.start_dt and draft.end_dt >= draft.start_dt:
        delta = draft.end_dt - draft.start_dt
        minutes = int(delta.total_seconds() // 60)
        if minutes >= 60:
            dur_text = f"{minutes//60} ч {minutes%60} мин"
        else:
            dur_text = f"{minutes} мин"

    text = (
        "<b>Подтверждение</b>\n"
        f"ТУ: <b>{draft.manager_name}</b>\n"
        f"Ресторан: <b>{draft.restaurant_name}</b>\n"
        f"Время начала: <b>{start}</b>\n"
        f"Время конца: <b>{end}</b>\n"
        f"Длительность: <b>{dur_text}</b>\n"
        f"Причина: <b>{draft.reason_label}</b>\n"
        f"Комментарий: <b>{draft.comment}</b>\n"
        f"Сумма: <b>{draft.amount:,} KZT</b>".replace(",", " ")
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, сохранить", callback_data="confirm_save")
    kb.button(text="✖️ Отменить", callback_data="cancel")
    kb.button(text="↩️ Назад", callback_data="back_amount")
    kb.adjust(1)
    if isinstance(source, Message):
        await source.answer(text, reply_markup=kb.as_markup())
    else:
        await source.message.edit_text(text, reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.confirming)


@router.callback_query(IncidentFSM.confirming, F.data == "back_amount")
async def back_amount(cb: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for val in AMOUNTS:
        kb.button(text=f"{val:,}".replace(",", " "), callback_data=f"amt:{val}")
    kb.button(text="Другая сумма", callback_data="amt:other")
    kb.button(text="↩️ Назад", callback_data="back_comment")
    kb.adjust(3)
    await cb.message.edit_text("💸 Выберите сумму (KZT) или «Другая сумма»:", reply_markup=kb.as_markup())
    await state.set_state(IncidentFSM.choosing_amount)


@router.callback_query(IncidentFSM.confirming, F.data == "confirm_save")
async def confirm_save(cb: CallbackQuery, state: FSMContext):
    draft = IncidentDraft(**await state.get_data())

    if not all([draft.manager_id, draft.restaurant_id, draft.start_dt, draft.reason, draft.comment, draft.amount]):
        await cb.message.edit_text("Не хватает данных. Начните заново.", reply_markup=kb_main_menu())
        await state.clear()
        return

    data = {
        "manager_id": draft.manager_id,
        "restaurant_id": draft.restaurant_id,
        "start_dt": draft.start_dt,
        "end_dt": draft.end_dt if draft.close_now else None,
        "reason": draft.reason,
        "comment": draft.comment,
        "amount": draft.amount,
        "status": "closed" if draft.close_now else "open",
    }
    incident_id = await insert_incident(data)
    await cb.message.edit_text(f"✅ Инцидент №{incident_id} сохранён.", reply_markup=kb_main_menu())
    await state.clear()

# ─────────────────────────────── ЗАКРЫТЬ ОТКРЫТЫЕ ─────────────────────────────── #

@router.callback_query(F.data == "act_close")
async def act_close(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    rows = await fetch_open_incidents()
    if not rows:
        await cb.message.edit_text("Открытых инцидентов нет.", reply_markup=kb_main_menu())
        return
    kb = InlineKeyboardBuilder()
    for r in rows:
        started = r["start_time"].strftime("%d.%m %H:%M")
        kb.button(
            text=f"#{r['id']} • {started} • {r['restaurant']} • {r['amount']:,}".replace(",", " "),
            callback_data=f"open:{r['id']}"
        )
    kb.button(text="↩️ Назад", callback_data="back_main")
    kb.adjust(1)
    await cb.message.edit_text("Открытые инциденты:", reply_markup=kb.as_markup())
    await state.set_state(CloseOpenFSM.picking_incident)


@router.callback_query(CloseOpenFSM.picking_incident, F.data.startswith("open:"))
async def close_pick(cb: CallbackQuery, state: FSMContext):
    inc_id = int(cb.data.split(":")[1])
    await state.update_data(incident_id=inc_id)
    kb = InlineKeyboardBuilder()
    for h in range(24):
        kb.button(text=f"{h:02d} ⏰", callback_data=f"ch:{h}")
    kb.button(text="↩️ Назад", callback_data="back_main")
    kb.adjust(6)
    await cb.message.edit_text("Выберите час конца:", reply_markup=kb.as_markup())
    await state.set_state(CloseOpenFSM.picking_end_hour)


@router.callback_query(CloseOpenFSM.picking_end_hour, F.data.startswith("ch:"))
async def close_pick_hour(cb: CallbackQuery, state: FSMContext):
    h = int(cb.data[3:])
    await state.update_data(end_hour=h)
    kb = InlineKeyboardBuilder()
    for m in (0, 15, 30, 45):
        kb.button(text=f"{m:02d} 🕒", callback_data=f"cm:{m}")
    kb.button(text="↩️ Назад", callback_data="back_close_list")
    kb.adjust(4)
    await cb.message.edit_text(f"Час конца: <b>{h:02d}</b>\nВыберите минуты:", reply_markup=kb.as_markup())
    await state.set_state(CloseOpenFSM.picking_end_min)


@router.callback_query(CloseOpenFSM.picking_end_min, F.data == "back_close_list")
async def back_close_list(cb: CallbackQuery, state: FSMContext):
    await act_close(cb, state)


@router.callback_query(CloseOpenFSM.picking_end_min, F.data.startswith("cm:"))
async def close_pick_min(cb: CallbackQuery, state: FSMContext):
    mm = int(cb.data[3:])
    data = await state.get_data()
    inc_id = data["incident_id"]
    h = data["end_hour"]
    # простое правило: дата конца = сегодня (или можно сделать: дата старта инцидента)
    end_dt = datetime.combine(date.today(), time(h, mm))
    await close_incident(inc_id, end_dt)
    await cb.message.edit_text(f"✅ Инцидент №{inc_id} закрыт.", reply_markup=kb_main_menu())
    await state.clear()

# ─────────────────────────────── ПРОЧЕЕ ─────────────────────────────── #

@router.callback_query(F.data == "act_report")
async def act_report(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("📊 Отчёты будут позже. Выберите другое действие.", reply_markup=kb_main_menu())


@router.callback_query(F.data == "back_main")
async def back_main(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Выберите действие:", reply_markup=kb_main_menu())


@router.callback_query(F.data == "cancel")
async def cancel_any(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Действие отменено.", reply_markup=kb_main_menu())


# ─────────────────────────────── ENTRY ─────────────────────────────── #

async def main():
    # прогреем pool
    await db_pool()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
