# bot.py
from __future__ import annotations
import os
import datetime as dt
from typing import Optional

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import pytz

import db

router = Router()

# --- Константы/иконки ---
BTN_INCIDENT = "🆕 Инцидент"
BTN_CLOSE    = "✅ Закрыть"
BTN_REPORT   = "📊 Отчёт"

REASONS = [
    ("🌧 Внешние потери", "external"),
    ("🏠 Внутренние потери", "internal"),
    ("👥 Нехватка персонала", "staff_shortage"),
    ("❌ Отсутствие продукта", "no_product"),
]

AMOUNTS = ["10000", "25000", "50000", "100000", "250000", "500000", "1000000", "Другая"]

TZ = os.getenv("TZ", "Asia/Almaty")
tz = pytz.timezone(TZ)

# --- Главное меню (ReplyKeyboard) ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_INCIDENT)],
        [KeyboardButton(text=BTN_CLOSE)],
        [KeyboardButton(text=BTN_REPORT)],
    ],
    resize_keyboard=True,
)

# --- FSM состояния ---
class IncidentFSM(StatesGroup):
    manager = State()
    restaurant = State()
    day = State()
    start_hour = State()
    start_minute = State()
    end_choice = State()       # сейчас или позже
    end_hour = State()
    end_minute = State()
    reason = State()
    comment = State()
    amount = State()
    confirm = State()

class CloseLaterFSM(StatesGroup):
    pick_incident = State()
    day = State()
    end_hour = State()
    end_minute = State()
    confirm = State()

def kb_back_next(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)]]
    )

# --- Вспомогательные клавиатуры ---
def kb_list(items: list[tuple[str, str]], back: Optional[str]=None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t, callback_data=cb)] for t, cb in items]
    if back:
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_days() -> InlineKeyboardMarkup:
    today = dt.datetime.now(tz).date()
    buttons = []
    buttons.append(("📅 Сегодня", f"day:{today.isoformat()}"))
    buttons.append(("📅 Вчера", f"day:{(today - dt.timedelta(days=1)).isoformat()}"))
    for n in range(2, 8):
        d = today - dt.timedelta(days=n)
        buttons.append((d.strftime("📅 %a %d.%m"), f"day:{d.isoformat()}"))
    return kb_list(buttons, back="back:restaurant")

def kb_hours(next_cb_prefix: str, back: str) -> InlineKeyboardMarkup:
    rows=[]
    for h in range(0,24,6):
        row=[]
        for j in range(h, h+6):
            row.append(InlineKeyboardButton(text=f"{j:02d}", callback_data=f"{next_cb_prefix}:{j:02d}"))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_minutes(next_cb_prefix: str, back: str) -> InlineKeyboardMarkup:
    mins = ["00","15","30","45"]
    row = [InlineKeyboardButton(text=m, callback_data=f"{next_cb_prefix}:{m}") for m in mins]
    return InlineKeyboardMarkup(inline_keyboard=[row, [InlineKeyboardButton(text="⬅️ Назад", callback_data=back)]])

def kb_end_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Закрыть сейчас", callback_data="end:now")],
            [InlineKeyboardButton(text="⏳ Закрыть позже", callback_data="end:later")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:start_minute")],
        ]
    )

def kb_reasons() -> InlineKeyboardMarkup:
    rows=[[InlineKeyboardButton(text=label, callback_data=f"reason:{val}")] for label,val in REASONS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:end_choice")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_amounts() -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(text=a, callback_data=f"amount:{a}") for a in AMOUNTS[:4]]
    row2 = [InlineKeyboardButton(text=a, callback_data=f"amount:{a}") for a in AMOUNTS[4:8]]
    return InlineKeyboardMarkup(inline_keyboard=[row1,row2,[InlineKeyboardButton(text="⬅️ Назад", callback_data="back:reason")]])

def kb_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, сохранить", callback_data="confirm:yes")],
        [InlineKeyboardButton(text="❌ Отменить",    callback_data="confirm:no")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back:amount")],
    ])

def kb_open_incidents(open_list) -> InlineKeyboardMarkup:
    rows=[]
    for rec in open_list:
        title = f"#{rec['id']} • {rec['restaurant']} • {rec['reason']} • {rec['amount_kzt']}₸"
        rows.append([InlineKeyboardButton(text=title, callback_data=f"pick:{rec['id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_confirm_close(incident_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, закрыть", callback_data=f"close_yes:{incident_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="back:main")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back:close_time:{incident_id}")],
    ])

# ====== /start ======
@router.message(F.text == "/start")
async def on_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_kb,
    )

# ====== Инцидент: шаги ======
@router.message(F.text == BTN_INCIDENT)
async def inc_start(message: Message, state: FSMContext):
    # шаг 1: выбрать управляющего
    managers = await db.get_managers()
    if not managers:
        await message.answer("В БД нет управляющих.")
        return
    items = [(f"👤 {m['name']}", f"mgr:{m['id']}") for m in managers]
    await state.set_state(IncidentFSM.manager)
    await message.answer("Выберите управляющего:", reply_markup=kb_list(items, back="back:main"))

@router.callback_query(IncidentFSM.manager, F.data.startswith("mgr:"))
async def inc_pick_manager(cb: CallbackQuery, state: FSMContext):
    mgr_id = int(cb.data.split(":")[1])
    await state.update_data(manager_id=mgr_id)

    # шаг 2: ресторан
    rests = await db.get_restaurants_for_manager(mgr_id)
    if not rests:
        await cb.message.edit_text("У этого управляющего нет привязанных ресторанов.", reply_markup=kb_back_next("back:main"))
        await cb.answer()
        return
    items = [(f"🍗 {r['name']}", f"rest:{r['id']}") for r in rests]
    await state.set_state(IncidentFSM.restaurant)
    await cb.message.edit_text("Выберите ресторан:", reply_markup=kb_list(items, back="back:manager"))
    await cb.answer()

@router.callback_query(F.data=="back:manager")
async def back_to_manager(cb: CallbackQuery, state:FSMContext):
    managers = await db.get_managers()
    items = [(f"👤 {m['name']}", f"mgr:{m['id']}") for m in managers]
    await state.set_state(IncidentFSM.manager)
    await cb.message.edit_text("Выберите управляющего:", reply_markup=kb_list(items, back="back:main"))
    await cb.answer()

@router.callback_query(IncidentFSM.restaurant, F.data.startswith("rest:"))
async def inc_pick_rest(cb: CallbackQuery, state:FSMContext):
    r_id = int(cb.data.split(":")[1])
    await state.update_data(restaurant_id=r_id)
    await state.set_state(IncidentFSM.day)
    await cb.message.edit_text("День инцидента:", reply_markup=kb_days())
    await cb.answer()

@router.callback_query(F.data=="back:restaurant")
async def back_to_rest(cb:CallbackQuery, state:FSMContext):
    data = await state.get_data()
    mgr_id = data.get("manager_id")
    rests = await db.get_restaurants_for_manager(mgr_id)
    items = [(f"🍗 {r['name']}", f"rest:{r['id']}") for r in rests]
    await state.set_state(IncidentFSM.restaurant)
    await cb.message.edit_text("Выберите ресторан:", reply_markup=kb_list(items, back="back:manager"))
    await cb.answer()

@router.callback_query(IncidentFSM.day, F.data.startswith("day:"))
async def inc_pick_day(cb:CallbackQuery, state:FSMContext):
    day_iso = cb.data.split(":",1)[1]
    await state.update_data(day=day_iso)
    await state.set_state(IncidentFSM.start_hour)
    await cb.message.edit_text("Час начала (0–23):", reply_markup=kb_hours("sh", "back:restaurant"))
    await cb.answer()

@router.callback_query(F.data=="back:start_hour")
async def back_to_start_hour(cb:CallbackQuery, state:FSMContext):
    await state.set_state(IncidentFSM.start_hour)
    await cb.message.edit_text("Час начала (0–23):", reply_markup=kb_hours("sh", "back:restaurant"))
    await cb.answer()

@router.callback_query(IncidentFSM.start_hour, F.data.startswith("sh:"))
async def inc_pick_start_hour(cb:CallbackQuery, state:FSMContext):
    h = cb.data.split(":")[1]
    await state.update_data(start_hour=h)
    await state.set_state(IncidentFSM.start_minute)
    await cb.message.edit_text("Минуты начала:", reply_markup=kb_minutes("sm", "back:start_hour"))
    await cb.answer()

@router.callback_query(IncidentFSM.start_minute, F.data.startswith("sm:"))
async def inc_pick_start_minute(cb:CallbackQuery, state:FSMContext):
    m = cb.data.split(":")[1]
    await state.update_data(start_minute=m)
    await state.set_state(IncidentFSM.end_choice)
    await cb.message.edit_text("Завершение:", reply_markup=kb_end_choice())
    await cb.answer()

@router.callback_query(F.data=="back:start_minute")
async def back_to_start_minute(cb:CallbackQuery, state:FSMContext):
    await state.set_state(IncidentFSM.start_minute)
    await cb.message.edit_text("Минуты начала:", reply_markup=kb_minutes("sm", "back:start_hour"))
    await cb.answer()

@router.callback_query(IncidentFSM.end_choice, F.data=="end:now")
async def end_now(cb:CallbackQuery, state:FSMContext):
    await state.update_data(end_now=True)
    await state.set_state(IncidentFSM.reason)
    await cb.message.edit_text("Причина потерь:", reply_markup=kb_reasons())
    await cb.answer()

@router.callback_query(IncidentFSM.end_choice, F.data=="end:later")
async def end_later(cb:CallbackQuery, state:FSMContext):
    await state.update_data(end_now=False)
    await state.set_state(IncidentFSM.reason)
    await cb.message.edit_text("Причина потерь:", reply_markup=kb_reasons())
    await cb.answer()

@router.callback_query(F.data=="back:end_choice")
async def back_to_end_choice(cb:CallbackQuery, state:FSMContext):
    await state.set_state(IncidentFSM.end_choice)
    await cb.message.edit_text("Завершение:", reply_markup=kb_end_choice())
    await cb.answer()

@router.callback_query(IncidentFSM.reason, F.data.startswith("reason:"))
async def pick_reason(cb:CallbackQuery, state:FSMContext):
    val = cb.data.split(":")[1]
    await state.update_data(reason=val)
    await state.set_state(IncidentFSM.comment)
    await cb.message.edit_text("💬 Комментарий (введите текст) или «—».", reply_markup=kb_back_next("back:reason"))
    await cb.answer()

@router.message(IncidentFSM.comment, F.text)
async def comment_entered(msg:Message, state:FSMContext):
    text = msg.text.strip()
    if not text:
        text = "—"
    await state.update_data(comment=text)
    await state.set_state(IncidentFSM.amount)
    await msg.answer("💸 Сумма, KZT:", reply_markup=kb_amounts())

@router.callback_query(IncidentFSM.amount, F.data.startswith("amount:"))
async def pick_amount(cb:CallbackQuery, state:FSMContext):
    raw = cb.data.split(":")[1]
    if raw == "Другая":
        await cb.message.edit_text("Введите сумму числом (тенге):", reply_markup=kb_back_next("back:reason"))
        await state.set_state(IncidentFSM.amount)  # остаёмся в этом стейте, ждём сообщение
        await cb.answer()
        return
    await state.update_data(amount=int(raw))
    await show_confirm(cb.message, state)
    await state.set_state(IncidentFSM.confirm)
    await cb.answer()

@router.message(IncidentFSM.amount, F.text.regexp(r"^\d+$"))
async def amount_other(msg:Message, state:FSMContext):
    await state.update_data(amount=int(msg.text))
    await show_confirm(msg, state)
    await state.set_state(IncidentFSM.confirm)

async def show_confirm(target, state:FSMContext):
    data = await state.get_data()
    day = dt.date.fromisoformat(data["day"])
    start = tz.localize(dt.datetime.combine(day, dt.time(int(data["start_hour"]), int(data["start_minute"]))))
    end_now = data.get("end_now", False)

    end_str = "—"
    dur_str = "—"
    if end_now:
        end_ts = dt.datetime.now(tz)
        end_str = end_ts.strftime("%d.%m %H:%M")
        minutes = int((end_ts - start).total_seconds() // 60)
        dur_str = f"{minutes} мин"

    # читаемые названия
    reason_label = next((lbl for lbl,val in REASONS if val==data["reason"]), data["reason"])

    text = (
        "<b>Подтверждение</b>\n"
        f"ТУ: выбрано ID {data['manager_id']}\n"
        f"Ресторан: ID {data['restaurant_id']}\n"
        f"Время начала: {start.strftime('%d.%m %H:%M')}\n"
        f"Время конца: {end_str}\n"
        f"Длительность: {dur_str}\n"
        f"Причина: {reason_label}\n"
        f"Комментарий: {data['comment']}\n"
        f"Сумма: {data['amount']:,} ₸".replace(",", " ")
    )
    await target.answer(text, reply_markup=kb_confirm())

@router.callback_query(IncidentFSM.confirm, F.data.startswith("confirm:"))
async def confirm_create(cb:CallbackQuery, state:FSMContext):
    if cb.data == "confirm:no":
        await state.clear()
        await cb.message.edit_text("Отменено.", reply_markup=None)
        await cb.answer()
        return

    # собираем и пишем в БД
    data = await state.get_data()
    day = dt.date.fromisoformat(data["day"])
    start_ts = tz.localize(dt.datetime.combine(day, dt.time(int(data["start_hour"]), int(data["start_minute"]))))

    end_ts = None
    status = "open"
    if data.get("end_now"):
        end_ts = dt.datetime.now(tz)
        status = "closed"

    incident_id = await db.insert_incident(
        manager_id=int(data["manager_id"]),
        restaurant_id=int(data["restaurant_id"]),
        start_ts=start_ts,
        end_ts=end_ts,
        reason=data["reason"],
        comment=data["comment"],
        amount_kzt=int(data["amount"]),
        status=status,
    )
    await state.clear()
    if status == "open":
        await cb.message.edit_text(f"Инцидент #{incident_id} сохранён как ОТКРЫТЫЙ.", reply_markup=None)
    else:
        await cb.message.edit_text(f"Инцидент #{incident_id} сохранён и ЗАКРЫТ.", reply_markup=None)
    await cb.answer()

# ====== Закрыть позже ======
@router.message(F.text == BTN_CLOSE)
async def on_close_entry(msg:Message, state:FSMContext):
    opens = await db.list_open_incidents()
    if not opens:
        await msg.answer("Открытых инцидентов нет.", reply_markup=main_kb)
        return
    await state.set_state(CloseLaterFSM.pick_incident)
    await msg.answer("Выберите открытый инцидент:", reply_markup=kb_open_incidents(opens))

@router.callback_query(CloseLaterFSM.pick_incident, F.data.startswith("pick:"))
async def pick_open(cb:CallbackQuery, state:FSMContext):
    inc_id = int(cb.data.split(":")[1])
    await state.update_data(incident_id=inc_id)
    await state.set_state(CloseLaterFSM.day)
    await cb.message.edit_text("День окончания:", reply_markup=kb_days())
    await cb.answer()

@router.callback_query(CloseLaterFSM.day, F.data.startswith("day:"))
async def close_pick_day(cb:CallbackQuery, state:FSMContext):
    day_iso = cb.data.split(":",1)[1]
    await state.update_data(day=day_iso)
    await state.set_state(CloseLaterFSM.end_hour)
    await cb.message.edit_text("Час конца:", reply_markup=kb_hours("eh", "back:main"))
    await cb.answer()

@router.callback_query(CloseLaterFSM.end_hour, F.data.startswith("eh:"))
async def close_pick_hour(cb:CallbackQuery, state:FSMContext):
    h = cb.data.split(":")[1]
    await state.update_data(end_hour=h)
    await state.set_state(CloseLaterFSM.end_minute)
    await cb.message.edit_text("Минуты конца:", reply_markup=kb_minutes("em", "back:main"))
    await cb.answer()

@router.callback_query(CloseLaterFSM.end_minute, F.data.startswith("em:"))
async def close_pick_min(cb:CallbackQuery, state:FSMContext):
    m = cb.data.split(":")[1]
    await state.update_data(end_minute=m)
    data = await state.get_data()
    day = dt.date.fromisoformat(data["day"])
    end_ts = tz.localize(dt.datetime.combine(day, dt.time(int(data["end_hour"]), int(m))))
    await state.set_state(CloseLaterFSM.confirm)
    text = f"Подтвердить закрытие инцидента #{data['incident_id']} временем {end_ts.strftime('%d.%m %H:%M')}?"
    await cb.message.edit_text(text, reply_markup=kb_confirm_close(data['incident_id']))
    await cb.answer()

@router.callback_query(CloseLaterFSM.confirm, F.data.startswith("close_yes:"))
async def do_close(cb:CallbackQuery, state:FSMContext):
    inc_id = int(cb.data.split(":")[1])
    data = await state.get_data()
    day = dt.date.fromisoformat(data["day"])
    end_ts = tz.localize(dt.datetime.combine(day, dt.time(int(data["end_hour"]), int(data["end_minute"]))))
    await db.close_incident(inc_id, end_ts)
    await state.clear()
    await cb.message.edit_text(f"Инцидент #{inc_id} закрыт.", reply_markup=None)
    await cb.answer()

# ====== Отчёт (заглушка-меню) ======
@router.message(F.text == BTN_REPORT)
async def on_report(msg:Message, state:FSMContext):
    await state.clear()
    await msg.answer("Выбор периода отчёта появится в следующем шаге (PDF/Excel).", reply_markup=main_kb)

# ====== fallback ======
@router.message()
async def fallback(message: Message):
    await message.answer("Нажмите кнопку внизу: «Инцидент», «Закрыть» или «Отчёт».", reply_markup=main_kb)
