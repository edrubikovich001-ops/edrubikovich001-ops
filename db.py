# db.py
import os
import asyncpg
from typing import Optional, List, Tuple, Any
from contextlib import asynccontextmanager

_POOL: Optional[asyncpg.Pool] = None

async def init_pool():
    global _POOL
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    _POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=5)

async def close_pool():
    global _POOL
    if _POOL:
        await _POOL.close()
        _POOL = None

@asynccontextmanager
async def conn():
    if not _POOL:
        raise RuntimeError("DB pool is not initialized")
    async with _POOL.acquire() as c:
        yield c

# ---- helpers ----

async def get_managers() -> List[asyncpg.Record]:
    async with conn() as c:
        rows = await c.fetch("SELECT id, name FROM managers ORDER BY name;")
        return rows

async def get_restaurants_for_manager(manager_id: int) -> List[asyncpg.Record]:
    q = """
    SELECT r.id, r.name
    FROM manager_restaurants mr
    JOIN restaurants r ON r.id = mr.restaurant_id
    WHERE mr.manager_id = $1
    ORDER BY r.name;
    """
    async with conn() as c:
        return await c.fetch(q, manager_id)

async def insert_incident(manager_id: int, restaurant_id: int,
                          start_ts, end_ts, reason: str,
                          comment: str, amount_kzt: int,
                          status: str) -> int:
    q = """
    INSERT INTO incidents (manager_id, restaurant_id, start_time, end_time,
                           reason, comment, amount_kzt, status)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
    RETURNING id;
    """
    async with conn() as c:
        new_id = await c.fetchval(q, manager_id, restaurant_id, start_ts, end_ts,
                                  reason, comment, amount_kzt, status)
        return new_id

async def list_open_incidents() -> List[asyncpg.Record]:
    q = """
    SELECT i.id, i.start_time, i.reason, i.amount_kzt, r.name AS restaurant, m.name AS manager
    FROM incidents i
    JOIN restaurants r ON r.id=i.restaurant_id
    JOIN managers m    ON m.id=i.manager_id
    WHERE i.status='open'
    ORDER BY i.start_time DESC;
    """
    async with conn() as c:
        return await c.fetch(q)

async def close_incident(incident_id: int, end_ts) -> None:
    q = """
    UPDATE incidents
    SET end_time=$2, status='closed'
    WHERE id=$1;
    """
    async with conn() as c:
        await c.execute(q, incident_id, end_ts)
