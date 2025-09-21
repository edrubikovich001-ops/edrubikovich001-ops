# db.py — простая обёртка над asyncpg
import os
import asyncpg

_DB_URL = os.getenv("DATABASE_URL")
_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not _DB_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = await asyncpg.create_pool(dsn=_DB_URL, min_size=1, max_size=5)
    return _pool

# ---- Список управляющих (ТУ) ----
async def list_managers() -> list[asyncpg.Record]:
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch("""SELECT id, name FROM managers ORDER BY name""")
    return rows

# ---- Рестораны ТУ ----
async def list_restaurants_by_manager(manager_id: int) -> list[asyncpg.Record]:
    pool = await get_pool()
    q = """
    SELECT r.id, r.name
    FROM manager_restaurants mr
    JOIN restaurants r ON r.id = mr.restaurant_id
    WHERE mr.manager_id = $1
    ORDER BY r.name
    """
    async with pool.acquire() as con:
        rows = await con.fetch(q, manager_id)
    return rows

# ---- Вставка инцидента ----
async def insert_incident(
    manager_id: int,
    restaurant_id: int,
    start_ts,                   # datetime
    end_ts,                     # datetime | None
    reason: str,                # enum текст: 'external'/'internal'/'staff_shortage'/'no_product'
    comment: str | None,
    amount_kzt: int,
    status: str                 # 'open' или 'closed'
) -> int:
    pool = await get_pool()
    q = """
    INSERT INTO incidents
        (manager_id, restaurant_id, start_time, end_time, reason, comment, amount_kzt, status)
    VALUES
        ($1, $2, $3, $4, $5::loss_reason, $6, $7, $8::incident_status)
    RETURNING id
    """
    async with pool.acquire() as con:
        new_id = await con.fetchval(q, manager_id, restaurant_id, start_ts, end_ts, reason, comment, amount_kzt, status)
    return int(new_id)
