# db.py — Postgres (asyncpg) + функции
import os
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")
_pool: asyncpg.Pool | None = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5, command_timeout=60)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as con:
        await con.execute("""
        CREATE TABLE IF NOT EXISTS managers(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT TRUE
        );
        CREATE TABLE IF NOT EXISTS restaurants(
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            manager_id INT REFERENCES managers(id),
            active BOOLEAN NOT NULL DEFAULT TRUE
        );
        DO $$ BEGIN
            CREATE TYPE reason_t AS ENUM ('external','internal','staff_lack','no_product');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        DO $$ BEGIN
            CREATE TYPE status_t AS ENUM ('open','closed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        CREATE TABLE IF NOT EXISTS incidents(
            id BIGSERIAL PRIMARY KEY,
            manager_id INT NOT NULL REFERENCES managers(id),
            restaurant_id INT NOT NULL REFERENCES restaurants(id),
            reason reason_t,
            amount_kzt NUMERIC(14,2),
            comment TEXT,
            start_time TIMESTAMPTZ NOT NULL,
            end_time TIMESTAMPTZ,
            status status_t NOT NULL DEFAULT 'open',
            duration_min INT,
            created_by_user BIGINT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_inc_status ON incidents(status);
        CREATE INDEX IF NOT EXISTS idx_inc_start  ON incidents(start_time);
        CREATE INDEX IF NOT EXISTS idx_inc_rest   ON incidents(restaurant_id);
        CREATE INDEX IF NOT EXISTS idx_inc_reason ON incidents(reason);
        """)
        # демо-данные
        mans = await con.fetchval("SELECT COUNT(*) FROM managers;")
        if mans == 0:
            await con.executemany(
                "INSERT INTO managers(name) VALUES($1) ON CONFLICT DO NOTHING;",
                [("Иванов",), ("Петров",), ("Сидоров",)]
            )
        rests = await con.fetchval("SELECT COUNT(*) FROM restaurants;")
        if rests == 0:
            ids = await con.fetch("SELECT id FROM managers ORDER BY id;")
            demo = [(f"Ресторан-{i+1}", ids[i]["id"]) for i in range(len(ids))]
            await con.executemany(
                "INSERT INTO restaurants(name, manager_id) VALUES($1,$2) ON CONFLICT DO NOTHING;", demo
            )

async def get_managers():
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch("SELECT id,name FROM managers WHERE active ORDER BY name;")
        return [{"id":r["id"],"name":r["name"]} for r in rows]

async def get_restaurants_by_manager(mid: int):
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch(
            "SELECT id,name FROM restaurants WHERE active AND manager_id=$1 ORDER BY name;", mid
        )
        return [{"id":r["id"],"name":r["name"]} for r in rows]

async def create_incident_open(*, manager_id:int, restaurant_id:int, reason:str,
                               start_time, created_by_user:int, comment:str|None=None):
    pool = await get_pool()
    async with pool.acquire() as con:
        rec = await con.fetchrow("""
            INSERT INTO incidents(manager_id,restaurant_id,reason,start_time,status,created_by_user,comment)
            VALUES($1,$2,$3,$4,'open',$5,$6) RETURNING id;
        """, manager_id, restaurant_id, reason, start_time, created_by_user, comment)
        return rec["id"]

async def create_incident_closed(*, manager_id:int, restaurant_id:int, reason:str,
                                 start_time, end_time, amount_kzt:float, comment:str|None,
                                 created_by_user:int):
    pool = await get_pool()
    dur = int((end_time - start_time).total_seconds() // 60)
    async with pool.acquire() as con:
        rec = await con.fetchrow("""
            INSERT INTO incidents(manager_id,restaurant_id,reason,amount_kzt,comment,
                                  start_time,end_time,status,duration_min,created_by_user)
            VALUES($1,$2,$3,$4,$5,$6,$7,'closed',$8,$9)
            RETURNING id;
        """, manager_id, restaurant_id, reason, amount_kzt, comment,
             start_time, end_time, dur, created_by_user)
        return rec["id"]

async def list_open_incidents():
    pool = await get_pool()
    async with pool.acquire() as con:
        rows = await con.fetch("""
            SELECT i.id, i.start_time, i.reason, i.amount_kzt,
                   r.name AS restaurant, m.name AS manager
            FROM incidents i
            JOIN restaurants r ON r.id=i.restaurant_id
            JOIN managers m    ON m.id=i.manager_id
            WHERE i.status='open'
            ORDER BY i.start_time DESC
            LIMIT 50;
        """)
        return [{
            "id": r["id"],
            "start_time": r["start_time"],
            "reason": r["reason"],
            "amount_kzt": float(r["amount_kzt"]) if r["amount_kzt"] is not None else None,
            "restaurant": r["restaurant"],
            "manager": r["manager"],
        } for r in rows]

async def close_incident(inc_id:int, *, end_time, reason:str, amount_kzt:float, comment:str|None):
    pool = await get_pool()
    async with pool.acquire() as con:
        st = await con.fetchval("SELECT start_time FROM incidents WHERE id=$1 AND status='open';", inc_id)
        if not st:
            return False
        dur = int((end_time - st).total_seconds() // 60)
        await con.execute("""
            UPDATE incidents
               SET end_time=$2, reason=$3, amount_kzt=$4, comment=$5,
                   status='closed', duration_min=$6
             WHERE id=$1;
        """, inc_id, end_time, reason, amount_kzt, comment, dur)
        return True
