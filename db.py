import os
import psycopg2
import psycopg2.extras

_conn = None


def get_connection():
    """Returns a live connection, reconnecting if the cached one has died.
    Mirrors the exact reconnect pattern already proven in the Streamlit CRM."""
    global _conn
    if _conn is None or _conn.closed:
        _conn = _fresh_connection()
    return _conn


def _fresh_connection():
    global _conn
    database_url = os.environ["DATABASE_URL"]
    _conn = psycopg2.connect(database_url)
    _conn.autocommit = False
    return _conn


def run_query(sql: str, params: tuple = ()):
    """Read-only query, returns a list of dicts. Explicitly ends the transaction
    after reading - leaving it open (the previous behavior) causes connections to
    sit 'idle in transaction' indefinitely, holding locks that can block other
    operations (this was a real, confirmed bug: a stale read left open for 51
    minutes blocked a schema migration)."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.commit()
        return [dict(r) for r in rows]
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        conn = _fresh_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.commit()
        return [dict(r) for r in rows]


def run_command(sql: str, params: tuple = ()) -> None:
    """Write query with no return value needed. Commits."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        conn = _fresh_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def run_insert_returning(sql: str, params: tuple = ()):
    """INSERT/UPDATE ... RETURNING, commits, returns a single dict or None.
    Exact same helper that fixed a real bug in the Streamlit CRM - run_query
    alone never commits, so it's unsafe for writes."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except (psycopg2.InterfaceError, psycopg2.OperationalError):
        conn = _fresh_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        conn.commit()
        return dict(row) if row else None
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
