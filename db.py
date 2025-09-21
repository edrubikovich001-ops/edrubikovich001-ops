# db.py
import os
import asyncpg

_DB_POOL = None

async def get_pool():
    global _DB_POOL
    if _DB_POOL is None:
        dsn = os.environ["DATABASE_URL"]
        _DB_POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return _DB_POOL

# ---- справочники ----
async def fetch_managers():
    pool = await get_pool()
    rows = await pool.fetch("SELECT id, name FROM managers ORDER BY name")
    return [(r["id"], r["name"]) for r in rows]

async def fetch_restaurants_for_manager(manager_id: int):
    pool = await get_pool()
    sql = """
    SELECT r.id, r.name
    FROM restaurants r
    JOIN manager_restaurants mr ON mr.restaurant_id = r.id
    WHERE mr.manager_id = $1
    ORDER BY r.name
    """
    rows = await pool.fetch(sql, manager_id)
    return [(r["id"], r["name"]) for r in rows]

# ---- инциденты ----
async def insert_incident(
    manager_id: int,
    restaurant_id: int,
    start_ts,  # datetime
    end_ts,    # datetime | None
    reason: str,
    comment: str,
    amount: int
):
    pool = await get_pool()
    sql = """
    INSERT INTO incidents(manager_id, restaurant_id, start_time, end_time,
                          reason, comment, amount, status)
    VALUES ($1,$2,$3,$4,$5,$6,$7,'open')
    RETURNING id
    """
    row = await pool.fetchrow(sql, manager_id, restaurant_id, start_ts, end_ts, reason, comment, amount)
    return row["id"]

async def list_open_incidents(limit: int = 10):
    pool = await get_pool()
    sql = """
    SELECT i.id, i.start_time, i.reason, i.amount, r.name AS restaurant, m.name AS manager
    FROM incidents i
    JOIN restaurants r ON r.id = i.restaurant_id
    JOIN managers m ON m.id = i.manager_id
    WHERE i.status = 'open'
    ORDER BY i.start_time DESC
    LIMIT $1
    """
    rows = await pool.fetch(sql, limit)
    return [dict(r) for r in rows]

async def close_incident(incident_id: int, end_ts):
    pool = await get_pool()
    await pool.execute(
        "UPDATE incidents SET end_time=$1, status='closed' WHERE id=$2",
        end_ts, incident_id
    )
