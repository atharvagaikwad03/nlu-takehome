import os
import psycopg2
from psycopg2 import pool

# module level pool, initialized once at app startup via initPool
connPool: pool.ThreadedConnectionPool | None = None

#init pool once at app startup
def initPool(app):
    #pulls DATABASE_URL from Flask config
    global connPool
    connPool = pool.ThreadedConnectionPool(
        minconn=1, # keeps one connection warm
        maxconn=10, # caps concurrent DB use
        dsn=app.config["DATABASE_URL"],
    )


def getConn():
    return connPool.getconn()

# always return the connection even if query faces errors
def putConn(conn):
    connPool.putconn(conn)


def query(sql: str, params=None) -> list[dict]:
    conn = getConn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        putConn(conn)

# rool back on error so the connection is,nt left in a bad state
def execute(sql: str, params=None) -> None:
    conn = getConn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        putConn(conn)

# use this for auto-generated id or timestamp back
def executeReturning(sql: str, params=None) -> dict:
    # use this when you need the auto-generated id or timestamp back
    conn = getConn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [desc[0] for desc in cur.description]
            row = cur.fetchone()
        conn.commit()
        return dict(zip(cols, row)) if row else {}
    except Exception:
        conn.rollback()
        raise
    finally:
        putConn(conn)
