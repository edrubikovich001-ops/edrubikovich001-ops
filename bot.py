# bot.py
import os
import asyncio
import datetime as dt
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from db import (
    fetch_managers,
    fetch_restaurants_for_manager,
    insert_incident,
    list_open_incidents,
    close_incident,
)

# --- базовые объекты
BOT_TOKEN = os.environ["BOT_TOKEN"]
TZ = ZoneInfo(os.environ.get("TZ", "Asia/Almaty"))

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router(name="main")
dp.include_router(router)

# --- основные кнопки
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🆕 Инцидент")],
        [KeyboardButton(text="✅ Закрыть")],
        [KeyboardButton(text="📊 Отчёт")],
    ],
    resize_keyboard=True,
)

# ====== FSM для создания инцидента ======
class IncidentFSM(StatesGroup):
    manager = State()
    restaurant = State()
    day = State()
    hour = State()
    minute = State()
    reason = State()
    comment = State()
    amount = State()
    confirm = State()

REASONS = [
    ("🌩 Внешние потери", "external"),
    ("🏭 Внутренние потери", "internal"),
    ("👥 Нехватка персонала", "staff_shortage"),
    ("🚫 Отсутствие продукта", "no_product"),
]

AMOUNTS = [10_000, 25_000, 50_000, 100_000, 250_000, 500_000, 1_000_000]

def date_options():
    today = dt.datetime.now(TZ).date()
    days = [today, today - dt.timedelta(days=1)]
    # ещё 6 дат назад, чтобы всего было 8 вариантов (сегодня+вчера+6 дат)
    for i in range(2, 8):
        days.append(today - dt.timedelta(days=i))
    # Покажем кнопками «Сегодня», «Вчера» и конкретные даты
    buttons = [
        [InlineKeyboardButton(text="📆 Сегодня", callback_data=f"day:{today.isoformat()}")],
        [InlineKeyboardButton(text="📆 Вчера", callback_data=f"day:{(today-dt.timedelta(days=1)).isoformat()}")],
    ]
    for d in days[2:]:
        buttons.append([InlineKeyboardButton(text=f"📆 {d.isoformat()}", callback_data=f"day:{d.isoformat()}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def hour_kb():
    rows, row = [], []
    for h in range(24):
        row.append(InlineKeyboardButton(text=f"{h:02d}", callback_data=f"hour:{h}"))
        if len(row) == 6:
            rows.append(row); row = []
    if row: rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def minute_kb():
    options = [0, 15, 30, 45]
    row = [InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min:{m}") for m in options]
    return InlineKeyboardMarkup(inline_keyboard=[row])

def back_cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="nav:cancel"),
    ]])

def reasons_kb():
    rows = [[InlineKeyboardButton(text=title, callback_data=f"reason:{code}") ] for title,code in REASONS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def amounts_kb():
    rows = []
    row=[]
    for a in AMOUNTS:
        row.append(InlineKeyboardButton(text=f"{a:,}".replace(",", " "), callback_data=f"amt:{a}"))
        if len(row)==3:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="🧮 Другая сумма", callback_data="amt:other")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def yes_no_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, сохранить", callback_data="confirm:yes"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="confirm:no"),
    ]])

# --------- старт ----------
@router.message(CommandStart())
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "Привет! Я бот учёта потерь продаж.\nВыберите действие из меню ниже.",
        reply_markup=main_kb,
    )

# ========= Создание инцидента =========
@router.message(F.text == "🆕 Инцидент")
async def start_incident(m: types.Message, state: FSMContext):
    await state.clear()
    managers = await fetch_managers()
    if not managers:
        await m.answer("В базе нет управляющих.")
        return
    # сделаем инлайн-кнопки по 2 в ряд
    rows, row = [], []
    for mid, name in managers:
        row.append(InlineKeyboardButton(text=f"👤 {name}", callback_data=f"mgr:{mid}"))
        if len(row) == 2:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data="nav:cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await m.answer("👤 Выберите управляющего:", reply_markup=kb)
    await state.set_state(IncidentFSM.manager)

@router.callback_query(IncidentFSM.manager, F.data.startswith("mgr:"))
async def choose_manager(c: types.CallbackQuery, state: FSMContext):
    manager_id = int(c.data.split(":")[1])
    await state.update_data(manager_id=manager_id)
    # рестораны
    rest = await fetch_restaurants_for_manager(manager_id)
    if not rest:
        await c.message.edit_text("У выбранного управляющего нет привязанных ресторанов.")
        await c.answer()
        return
    rows, row = [], []
    for rid, name in rest:
        row.append(InlineKeyboardButton(text=f"🍗 {name}", callback_data=f"rst:{rid}"))
        if len(row) == 2:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="nav:back"),
                 InlineKeyboardButton(text="❌ Отменить", callback_data="nav:cancel")])
    await c.message.edit_text("🍗 Выберите ресторан:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await state.set_state(IncidentFSM.restaurant)
    await c.answer()

@router.callback_query(IncidentFSM.restaurant, F.data == "nav:back")
async def back_to_manager(c: types.CallbackQuery, state: FSMContext):
    # вернёмся к списку управляющих
    managers = await fetch_managers()
    rows, row = [], []
    for mid, name in managers:
        row.append(InlineKeyboardButton(text=f"👤 {name}", callback_data=f"mgr:{mid}"))
        if len(row) == 2:
            rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Отменить", callback_data="nav:cancel")])
    await c.message.edit_text("👤 Выберите управляющего:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await state.set_state(IncidentFSM.manager)
    await c.answer()

@router.callback_query(IncidentFSM.restaurant, F.data.startswith("rst:"))
async def choose_restaurant(c: types.CallbackQuery, state: FSMContext):
    restaurant_id = int(c.data.split(":")[1])
    await state.update_data(restaurant_id=restaurant_id)
    await c.message.edit_text("🗓 Выберите <b>день начала</b>:", reply_markup=date_options())
    await state.set_state(IncidentFSM.day)
    await c.answer()

@router.callback_query(IncidentFSM.day, F.data.startswith("day:"))
async def set_day(c: types.CallbackQuery, state: FSMContext):
    day = dt.date.fromisoformat(c.data.split(":")[1])
    await state.update_data(day=day)
    await c.message.edit_text("⏰ Выберите <b>час начала</b>:", reply_markup=hour_kb())
    await state.set_state(IncidentFSM.hour)
    await c.answer()

@router.callback_query(IncidentFSM.hour, F.data.startswith("hour:"))
async def set_hour(c: types.CallbackQuery, state: FSMContext):
    hour = int(c.data.split(":")[1])
    await state.update_data(hour=hour)
    await c.message.edit_text("🕒 Выберите <b>минуты</b>:", reply_markup=minute_kb())
    await state.set_state(IncidentFSM.minute)
    await c.answer()

@router.callback_query(IncidentFSM.minute, F.data.startswith("min:"))
async def set_minute(c: types.CallbackQuery, state: FSMContext):
    minute = int(c.data.split(":")[1])
    await state.update_data(minute=minute)
    await c.message.edit_text("🗂️ Выберите <b>причину</b>:", reply_markup=reasons_kb())
    await state.set_state(IncidentFSM.reason)
    await c.answer()

@router.callback_query(IncidentFSM.reason, F.data.startswith("reason:"))
async def choose_reason(c: types.CallbackQuery, state: FSMContext):
    reason = c.data.split(":")[1]
    await state.update_data(reason=reason)
    await c.message.edit_text("💬 Введите комментарий или отправьте «—»", reply_markup=None)
    await state.set_state(IncidentFSM.comment)
    await c.answer()

@router.message(IncidentFSM.comment)
async def get_comment(m: types.Message, state: FSMContext):
    comment = m.text.strip()
    await state.update_data(comment=comment)
    await m.answer("💸 Выберите сумму (KZT) или «Другая сумма»:", reply_markup=amounts_kb())

    await state.set_state(IncidentFSM.amount)

@router.callback_query(IncidentFSM.amount, F.data.startswith("amt:"))
async def choose_amount(c: types.CallbackQuery, state: FSMContext):
    _, val = c.data.split(":")
    if val == "other":
        await c.message.edit_text("Введите сумму числом, без разделителей:")
        await c.answer()
        return
    amount = int(val)
    await state.update_data(amount=amount)
    await show_confirm(c.message, state)
    await state.set_state(IncidentFSM.confirm)
    await c.answer()

@router.message(IncidentFSM.amount)
async def other_amount(m: types.Message, state: FSMContext):
    # парсим число
    txt = m.text.replace(" ", "").replace(",", "")
    if not txt.isdigit():
        await m.answer("Нужно число. Попробуйте ещё раз:")
        return
    await state.update_data(amount=int(txt))
    await show_confirm(m, state)
    await state.set_state(IncidentFSM.confirm)

async def show_confirm(target_message: types.Message | types.Message, state: FSMContext):
    data = await state.get_data()
    day: dt.date = data["day"]
    hour: int = data["hour"]
    minute: int = data["minute"]
    start_dt = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)
    reason = data["reason"]
    comment = data["comment"]
    amount = data["amount"]

    # простая карточка
    text = (
        "<b>Подтверждение</b>\n"
        f"ТУ (ID): <code>{data['manager_id']}</code>\n"
        f"Ресторан (ID): <code>{data['restaurant_id']}</code>\n"
        f"Время начала: <code>{start_dt:%Y-%m-%d %H:%M}</code>\n"
        f"Причина: <code>{reason}</code>\n"
        f"Комментарий: {comment}\n"
        f"Сумма: <b>{amount:,}</b> KZT".replace(",", " ")
    )
    await target_message.answer(text, reply_markup=yes_no_kb())

@router.callback_query(IncidentFSM.confirm, F.data == "confirm:yes")
async def do_save(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    day: dt.date = data["day"]
    hour: int = data["hour"]
    minute: int = data["minute"]
    start_dt = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)

    inc_id = await insert_incident(
        manager_id=data["manager_id"],
        restaurant_id=data["restaurant_id"],
        start_ts=start_dt,
        end_ts=None,
        reason=data["reason"],
        comment=data["comment"],
        amount=data["amount"],
    )
    await state.clear()
    await c.message.edit_text(f"✅ Инцидент <b>#{inc_id}</b> сохранён. Статус: <code>open</code>.", reply_markup=None)
    await c.answer()

@router.callback_query(IncidentFSM.confirm, F.data.in_(["confirm:no", "nav:cancel"]))
async def cancel_create(c: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text("Отменено.", reply_markup=None)
    await c.answer()

# ========= Закрытие инцидента =========
@router.message(F.text == "✅ Закрыть")
async def close_menu(m: types.Message, state: FSMContext):
    await state.clear()
    items = await list_open_incidents()
    if not items:
        await m.answer("Открытых инцидентов нет.")
        return
    rows = []
    for it in items:
        caption = f"#{it['id']} • {it['restaurant']} • {it['start_time']:%m-%d %H:%M} • {it['reason']} • {it['amount']}"
        rows.append([InlineKeyboardButton(text=caption, callback_data=f"close:{it['id']}")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await m.answer("Выберите инцидент для закрытия (время конца будет «сейчас»):", reply_markup=kb)

@router.callback_query(F.data.startswith("close:"))
async def do_close_now(c: types.CallbackQuery):
    inc_id = int(c.data.split(":")[1])
    now_ts = dt.datetime.now(TZ)
    await close_incident(inc_id, now_ts)
    await c.message.edit_text(f"✅ Инцидент #{inc_id} закрыт в {now_ts:%Y-%m-%d %H:%M}.")
    await c.answer()

# ========= Отчёт (пока заглушка) =========
@router.message(F.text == "📊 Отчёт")
async def report_stub(m: types.Message):
    await m.answer("Выбор периода и формата отчёта… (позже добавим PDF/Excel).")
