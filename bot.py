# bot.py — инциденты: «закрыть сейчас/позже» и «закрыть» (aiogram v3)
import os
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from db import (
    init_db, get_managers, get_restaurants_by_manager,
    create_incident_open, create_incident_closed,
    list_open_incidents, close_incident
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set")
TZ = timezone(timedelta(hours=6))  # Asia/Almaty

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ---------- UI ----------
BACK = "◀️ Назад"
def kb(rows, one_time=True):
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in rows],
        resize_keyboard=True,
        one_time_keyboard=one_time
    )
def start_menu():
    return kb([["➕ Инцидент", "✳️ Закрыть"], ["📊 Отчёт"]], one_time=False)

REASONS_UI = ["Внешние потери","Внутренние потери","Нехватка персонала","Отсутствие продукта"]
REASON_MAP = {
    "Внешние потери":"external",
    "Внутренние потери":"internal",
    "Нехватка персонала":"staff_lack",
    "Отсутствие продукта":"no_product",
}
AMOUNTS = ["10 000","25 000","50 000","100 000","250 000","500 000","1 000 000","Другая"]
def parse_amount(text:str):
    try: return float(text.replace(" ","").replace(",","."))  # KZT
    except: return None

def day_buttons_for_last_week():
    today = datetime.now(TZ).date()
    labels = [f"Сегодня ({today.isoformat()})", f"Вчера ({(today-timedelta(days=1)).isoformat()})"]
    for i in range(2,8):
        d = today - timedelta(days=i)
        wd = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()]
        labels.append(f"{wd} ({d.isoformat()})")
    rows, row = [], []
    for l in labels:
        row.append(l)
        if len(row)==2: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([BACK])
    return rows

def hours_grid():
    rows, row = [], []
    for h in range(24):
        row.append(f"{h:02d}")
        if len(row)==6: rows.append(row); row=[]
    if row: rows.append(row)
    rows.append([BACK])
    return rows

def minutes_row():
    return [["00","15","30","45"], [BACK]]

def reason_rows():
    return [[r] for r in REASONS_UI] + [[BACK]]

def amounts_rows():
    return [[*AMOUNTS[:4]],[*AMOUNTS[4:7], "Другая"],[BACK]]

# ---------- FSM ----------
class IncidentCreate(StatesGroup):
    manager = State()
    restaurant = State()
    day = State()
    hour_start = State()
    min_start = State()
    end_mode = State()
    hour_end = State()
    min_end = State()
    reason = State()
    comment = State()
    amount = State()

class IncidentClose(StatesGroup):
    pick_open = State()
    day_end = State()
    hour_end = State()
    min_end = State()
    reason = State()
    comment = State()
    amount = State()

# ---------- start ----------
@dp.message(CommandStart())
async def start_cmd(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Главное меню.", reply_markup=start_menu())

# ---------- Инцидент ----------
@dp.message(F.text == "➕ Инцидент")
async def inc_start(m: Message, state: FSMContext):
    mans = await get_managers()
    await state.update_data(_mans=mans)
    await state.set_state(IncidentCreate.manager)
    await m.answer("👤 Выберите управляющего.", reply_markup=kb([[x["name"]] for x in mans] + [[BACK]]))

@dp.message(IncidentCreate.manager)
async def inc_pick_manager(m: Message, state: FSMContext):
    if m.text == BACK: return await start_cmd(m, state)
    data = await state.get_data()
    mans = data["_mans"]
    sel = next((x for x in mans if x["name"] == m.text), None)
    if not sel:
        return await m.answer("Выберите из списка.", reply_markup=kb([[x["name"]] for x in mans] + [[BACK]]))
    await state.update_data(manager_id=sel["id"], manager_name=sel["name"])
    rests = await get_restaurants_by_manager(sel["id"])
    await state.update_data(_rests=rests)
    await state.set_state(IncidentCreate.restaurant)
    await m.answer("🍗 Выберите ресторан.", reply_markup=kb([[x["name"]] for x in rests] + [[BACK]]))

@dp.message(IncidentCreate.restaurant)
async def inc_pick_rest(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_start(m, state)
    data = await state.get_data()
    rests = data["_rests"]
    sel = next((x for x in rests if x["name"] == m.text), None)
    if not sel:
        return await m.answer("Выберите из списка.", reply_markup=kb([[x["name"]] for x in rests] + [[BACK]]))
    await state.update_data(restaurant_id=sel["id"], restaurant_name=sel["name"])
    await state.set_state(IncidentCreate.day)
    await m.answer("📅 День начала.", reply_markup=kb(day_buttons_for_last_week(), one_time=False))

def parse_day(label:str):
    if "(" in label and label.endswith(")"):
        s = label.split("(")[-1][:-1]
        try: return datetime.fromisoformat(s).date()
        except: return None
    return None

@dp.message(IncidentCreate.day)
async def inc_day(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_pick_rest(m, state)
    d = parse_day(m.text)
    if not d:
        return await m.answer("Выберите дату из кнопок.", reply_markup=kb(day_buttons_for_last_week(), one_time=False))
    await state.update_data(day=d.isoformat())
    await state.set_state(IncidentCreate.hour_start)
    await m.answer("⏰ Час начала.", reply_markup=kb(hours_grid(), one_time=False))

@dp.message(IncidentCreate.hour_start)
async def inc_hour_start(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_day(m, state)
    if not m.text.isdigit() or not (0<=int(m.text)<=23):
        return await m.answer("Час 00–23.", reply_markup=kb(hours_grid(), one_time=False))
    await state.update_data(hour_start=int(m.text))
    await state.set_state(IncidentCreate.min_start)
    await m.answer("🕒 Минуты начала.", reply_markup=kb(minutes_row()))

@dp.message(IncidentCreate.min_start)
async def inc_min_start(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_hour_start(m, state)
    if m.text not in {"00","15","30","45"}:
        return await m.answer("Выберите минуты.", reply_markup=kb(minutes_row()))
    await state.update_data(min_start=int(m.text))
    await state.set_state(IncidentCreate.end_mode)
    await m.answer("Закрываем сейчас или позже?",
                   reply_markup=kb([["✅ Закрыть сейчас","⏳ Закрыть позже"],[BACK]], one_time=False))

@dp.message(IncidentCreate.end_mode)
async def inc_end_mode(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_min_start(m, state)
    if m.text == "✅ Закрыть сейчас":
        await state.set_state(IncidentCreate.hour_end)
        return await m.answer("⏰ Час конца.", reply_markup=kb(hours_grid(), one_time=False))
    if m.text == "⏳ Закрыть позже":
        await state.set_state(IncidentCreate.reason)
        return await m.answer("🗂️ Причина.", reply_markup=kb([[r] for r in REASONS_UI]+[[BACK]]))
    await m.answer("Выберите кнопкой.", reply_markup=kb([["✅ Закрыть сейчас","⏳ Закрыть позже"],[BACK]], one_time=False))

@dp.message(IncidentCreate.hour_end)
async def inc_hour_end(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_end_mode(m, state)
    if not m.text.isdigit() or not (0<=int(m.text)<=23):
        return await m.answer("Час 00–23.", reply_markup=kb(hours_grid(), one_time=False))
    await state.update_data(hour_end=int(m.text))
    await state.set_state(IncidentCreate.min_end)
    await m.answer("🕒 Минуты конца.", reply_markup=kb(minutes_row()))

@dp.message(IncidentCreate.min_end)
async def inc_min_end(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_hour_end(m, state)
    if m.text not in {"00","15","30","45"}:
        return await m.answer("Выберите минуты.", reply_markup=kb(minutes_row()))
    await state.update_data(min_end=int(m.text))
    await state.set_state(IncidentCreate.reason)
    await m.answer("🗂️ Причина.", reply_markup=kb([[r] for r in REASONS_UI]+[[BACK]]))

@dp.message(IncidentCreate.reason)
async def inc_reason(m: Message, state: FSMContext):
    if m.text == BACK:
        data = await state.get_data()
        return await (inc_min_end(m, state) if "hour_end" in data else inc_end_mode(m, state))
    if m.text not in REASONS_UI:
        return await m.answer("Выберите причину.", reply_markup=kb([[r] for r in REASONS_UI]+[[BACK]]))
    await state.update_data(reason_ui=m.text, reason=REASON_MAP[m.text])

    d = await state.get_data()
    if "hour_end" not in d:
        day = datetime.fromisoformat(d["day"])
        start_dt = datetime(day.year, day.month, day.day, d["hour_start"], d["min_start"], tzinfo=TZ)
        inc_id = await create_incident_open(
            manager_id=d["manager_id"], restaurant_id=d["restaurant_id"],
            reason=d["reason"], start_time=start_dt, created_by_user=m.from_user.id
        )
        await state.clear()
        return await m.answer(f"Инцидент открыт (id={inc_id}). Закрой через «✳️ Закрыть».", reply_markup=start_menu())

    await state.set_state(IncidentCreate.comment)
    await m.answer("💬 Комментарий (или «—»).", reply_markup=kb([[BACK]], one_time=False))

@dp.message(IncidentCreate.comment)
async def inc_comment(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_reason(m, state)
    await state.update_data(comment=(None if m.text.strip()=="—" else m.text.strip()))
    await state.set_state(IncidentCreate.amount)
    await m.answer("💰 Сумма, KZT.", reply_markup=kb([[*AMOUNTS[:4]],[*AMOUNTS[4:7],"Другая"],[BACK]], one_time=False))

@dp.message(IncidentCreate.amount)
async def inc_amount(m: Message, state: FSMContext):
    if m.text == BACK: return await inc_comment(m, state)
    amt = parse_amount(m.text) if m.text!="Другая" else None
    if m.text=="Другая" or amt is None:
        amt = parse_amount(m.text)
        if amt is None:
            return await m.answer("Введите сумму числом, например 125000.", reply_markup=kb([[BACK]], one_time=False))
    await state.update_data(amount=amt)

    d = await state.get_data()
    day = datetime.fromisoformat(d["day"])
    start_dt = datetime(day.year, day.month, day.day, d["hour_start"], d["min_start"], tzinfo=TZ)
    end_dt   = datetime(day.year, day.month, day.day, d["hour_end"], d["min_end"], tzinfo=TZ)
    if end_dt < start_dt: end_dt += timedelta(days=1)

    inc_id = await create_incident_closed(
        manager_id=d["manager_id"], restaurant_id=d["restaurant_id"],
        reason=d["reason"], start_time=start_dt, end_time=end_dt,
        amount_kzt=d["amount"], comment=d.get("comment"),
        created_by_user=m.from_user.id
    )
    await state.clear()
    await m.answer(f"Инцидент сохранён (id={inc_id}).", reply_markup=start_menu())

# ---------- Закрыть ----------
@dp.message(F.text == "✳️ Закрыть")
async def close_start(m: Message, state: FSMContext):
    opens = await list_open_incidents()
    if not opens:
        return await m.answer("Открытых инцидентов нет.", reply_markup=start_menu())
    await state.update_data(_opens=opens)
    rows=[]
    for r in opens[:10]:
        dt = r["start_time"].astimezone(TZ).strftime("%Y-%m-%d %H:%M")
        reason = r["reason"] or "-"
        amt = f'{int(r["amount_kzt"]):,}'.replace(",", " ") if r["amount_kzt"] else "—"
        rows.append([f'#{r["id"]} | {dt} | {r["restaurant"]} | {reason} | {amt}'])
    await state.set_state(IncidentClose.pick_open)
    await m.answer("Выберите открытый инцидент.", reply_markup=kb(rows+[[BACK]], one_time=False))

def parse_pick(text:str):
    if text.startswith("#"):
        try: return int(text.split()[0][1:])
        except: return None
    return None

@dp.message(IncidentClose.pick_open)
async def close_pick(m: Message, state: FSMContext):
    if m.text == BACK: return await start_cmd(m, state)
    inc_id = parse_pick(m.text)
    if not inc_id: return await close_start(m, state)
    await state.update_data(inc_id=inc_id)
    await state.set_state(IncidentClose.day_end)
    await m.answer("📅 День конца.", reply_markup=kb(day_buttons_for_last_week(), one_time=False))

@dp.message(IncidentClose.day_end)
async def close_day(m: Message, state: FSMContext):
    if m.text == BACK: return await close_start(m, state)
    if "(" not in m.text or not m.text.endswith(")"):
        return await m.answer("Выберите дату.", reply_markup=kb(day_buttons_for_last_week(), one_time=False))
    d = datetime.fromisoformat(m.text.split("(")[-1][:-1]).date()
    await state.update_data(day_end=d.isoformat())
    await state.set_state(IncidentClose.hour_end)
    await m.answer("⏰ Час конца.", reply_markup=kb(hours_grid(), one_time=False))

@dp.message(IncidentClose.hour_end)
async def close_hour(m: Message, state: FSMContext):
    if m.text == BACK: return await close_day(m, state)
    if not m.text.isdigit() or not (0<=int(m.text)<=23):
        return await m.answer("Час 00–23.", reply_markup=kb(hours_grid(), one_time=False))
    await state.update_data(hour_end=int(m.text))
    await state.set_state(IncidentClose.min_end)
    await m.answer("🕒 Минуты конца.", reply_markup=kb(minutes_row()))

@dp.message(IncidentClose.min_end)
async def close_min(m: Message, state: FSMContext):
    if m.text == BACK: return await close_hour(m, state)
    if m.text not in {"00","15","30","45"}:
        return await m.answer("Выберите минуты.", reply_markup=kb(minutes_row()))
    await state.update_data(min_end=int(m.text))
    await state.set_state(IncidentClose.reason)
    await m.answer("🗂️ Причина (можно изменить).", reply_markup=kb([[r] for r in REASONS_UI]+[[BACK]]))

@dp.message(IncidentClose.reason)
async def close_reason(m: Message, state: FSMContext):
    if m.text == BACK: return await close_min(m, state)
    if m.text not in REASONS_UI:
        return await m.answer("Выберите причину.", reply_markup=kb([[r] for r in REASONS_UI]+[[BACK]]))
    await state.update_data(reason=REASON_MAP[m.text], reason_ui=m.text)
    await state.set_state(IncidentClose.comment)
    await m.answer("💬 Комментарий (или «—»).", reply_markup=kb([[BACK]], one_time=False))

@dp.message(IncidentClose.comment)
async def close_comment(m: Message, state: FSMContext):
    if m.text == BACK: return await close_reason(m, state)
    await state.update_data(comment=(None if m.text.strip()=="—" else m.text.strip()))
    await state.set_state(IncidentClose.amount)
    await m.answer("💰 Сумма, KZT.", reply_markup=kb([[*AMOUNTS[:4]],[*AMOUNTS[4:7],"Другая"],[BACK]], one_time=False))

@dp.message(IncidentClose.amount)
async def close_amount(m: Message, state: FSMContext):
    if m.text == BACK: return await close_comment(m, state)
    amt = parse_amount(m.text) if m.text!="Другая" else None
    if m.text=="Другая" or amt is None:
        amt = parse_amount(m.text)
        if amt is None:
            return await m.answer("Введите сумму числом, например 125000.", reply_markup=kb([[BACK]], one_time=False))
    await state.update_data(amount=amt)

    d = await state.get_data()
    day = datetime.fromisoformat(d["day_end"])
    end_dt = datetime(day.year, day.month, day.day, d["hour_end"], d["min_end"], tzinfo=TZ)
    ok = await close_incident(
        d["inc_id"], end_time=end_dt, reason=d["reason"],
        amount_kzt=d["amount"], comment=d.get("comment")
    )
    await state.clear()
    await m.answer("Инцидент закрыт." if ok else "Не удалось закрыть (возможно, уже закрыт).", reply_markup=start_menu())

# ---------- run ----------
async def run_bot():
    await init_db()
    await dp.start_polling(bot)
