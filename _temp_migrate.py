"""TEMPORARY - one-time endpoint to apply migrations/0001 and 0002 (the
business-CRM schema) from a browser, since no local psql/terminal access is
available. Delete this file and its registration in main.py immediately
after confirming success - this is not something that should stay live."""
import os

from fastapi import APIRouter

from db import get_connection

router = APIRouter()

_DIR = os.path.dirname(__file__)
MIGRATIONS = [
    os.path.join(_DIR, "migrations", "0001_business_crm.sql"),
    os.path.join(_DIR, "migrations", "0002_business_crm_demo.sql"),
]


@router.get("/internal/run-migration-2448d86fff78b16d57a78640")
def run_migrations():
    results = []
    conn = get_connection()
    for path in MIGRATIONS:
        name = os.path.basename(path)
        try:
            with open(path) as f:
                sql = f.read()
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            results.append({"file": name, "status": "ok"})
        except Exception as e:
            conn.rollback()
            results.append({"file": name, "status": "error", "detail": str(e)})
            break  # 0002 depends on 0001, so stop on first failure
    return {"results": results}
