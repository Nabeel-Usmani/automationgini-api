import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

_pool = None


def _get_pool():
    """FastAPI runs these sync route functions in a thread pool, so a single
    shared connection (the previous design, mirrored from the Streamlit CRM
    where each session is single-threaded) is unsafe here: two concurrent
    requests can call execute()/commit() on the same libpq connection at once
    and corrupt its protocol state, wedging it for every request afterward.
    A connection pool gives each request its own connection instead."""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(1, 10, os.environ["DATABASE_URL"])
    return _pool


def _run(sql: str, params: tuple, cursor_factory, fetch):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            cur.execute(sql, params)
            result = fetch(cur) if fetch else None
        conn.commit()
        pool.putconn(conn)
        return result
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        pool.putconn(conn, close=True)
        conn = pool.getconn()
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            cur.execute(sql, params)
            result = fetch(cur) if fetch else None
        conn.commit()
        pool.putconn(conn)
        return result
    except Exception:
        try:
            conn.rollback()
        finally:
            pool.putconn(conn)
        raise


def run_query(sql: str, params: tuple = ()):
    """Read-only query, returns a list of dicts."""
    rows = _run(sql, params, psycopg2.extras.RealDictCursor, lambda cur: cur.fetchall())
    return [dict(r) for r in rows]


def run_command(sql: str, params: tuple = ()) -> None:
    """Write query with no return value needed. Commits."""
    _run(sql, params, None, None)


def run_insert_returning(sql: str, params: tuple = ()):
    """INSERT/UPDATE ... RETURNING, commits, returns a single dict or None."""
    row = _run(sql, params, psycopg2.extras.RealDictCursor, lambda cur: cur.fetchone())
    return dict(row) if row else None
