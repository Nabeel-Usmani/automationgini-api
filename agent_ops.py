import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/agent-ops", tags=["agent-ops"])

# Two separate secrets, not one: the dashboard is a static site, so whatever
# secret it uses is visible in its shipped JS bundle to anyone who looks.
# The read secret is safe to expose that way (it only reveals operational
# metadata). The write secret is never given to the dashboard - only the
# autonomous agent session holds it, server-side, so a leaked read secret
# can't be used to forge runs or corrupt the backlog.
AGENT_OPS_READ_SECRET = os.environ.get("AGENT_OPS_READ_SECRET", "")
AGENT_OPS_WRITE_SECRET = os.environ.get("AGENT_OPS_WRITE_SECRET", "")


def require_read_secret(x_agent_ops_secret: str = Header(None)):
    valid = {s for s in (AGENT_OPS_READ_SECRET, AGENT_OPS_WRITE_SECRET) if s}
    if not valid or x_agent_ops_secret not in valid:
        raise HTTPException(status_code=401, detail="Invalid or missing agent-ops secret.")


def require_write_secret(x_agent_ops_secret: str = Header(None)):
    if not AGENT_OPS_WRITE_SECRET or x_agent_ops_secret != AGENT_OPS_WRITE_SECRET:
        raise HTTPException(status_code=401, detail="Invalid or missing agent-ops write secret.")


@router.get("/runs", dependencies=[Depends(require_read_secret)])
def list_runs(limit: int = 50):
    return run_query(
        "SELECT id, category, skill_used, target, task_description, status, summary, "
        "commit_url, error_detail, started_at, finished_at FROM agent_runs "
        "ORDER BY started_at DESC LIMIT %s;",
        (limit,),
    )


@router.get("/stats", dependencies=[Depends(require_read_secret)])
def stats():
    today = run_query(
        "SELECT status, COUNT(*) AS n FROM agent_runs "
        "WHERE started_at >= date_trunc('day', NOW()) GROUP BY status;"
    )
    last_7_days = run_query(
        "SELECT status, COUNT(*) AS n FROM agent_runs "
        "WHERE started_at >= NOW() - INTERVAL '7 days' GROUP BY status;"
    )
    last_run = run_query(
        "SELECT id, task_description, status, started_at, finished_at FROM agent_runs "
        "ORDER BY started_at DESC LIMIT 1;"
    )
    backlog_counts = run_query(
        "SELECT status, COUNT(*) AS n FROM agent_backlog GROUP BY status;"
    )
    return {
        "today_by_status": today,
        "last_7_days_by_status": last_7_days,
        "last_run": last_run[0] if last_run else None,
        "backlog_by_status": backlog_counts,
    }


@router.get("/backlog", dependencies=[Depends(require_read_secret)])
def list_backlog():
    return run_query(
        "SELECT id, title, description, status, priority, blocked_reason, "
        "created_at, updated_at FROM agent_backlog "
        "ORDER BY (status = 'done'), priority ASC, created_at ASC;"
    )


class CreateRunRequest(BaseModel):
    category: str  # 'monitor' | 'build'
    skill_used: Optional[str] = None
    target: Optional[str] = None
    task_description: str
    status: str  # 'success' | 'failed' | 'blocked'
    summary: Optional[str] = None
    commit_url: Optional[str] = None
    error_detail: Optional[str] = None


@router.post("/runs", dependencies=[Depends(require_write_secret)])
def create_run(body: CreateRunRequest):
    row = run_insert_returning(
        "INSERT INTO agent_runs "
        "(category, skill_used, target, task_description, status, summary, commit_url, error_detail, finished_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW()) RETURNING id;",
        (
            body.category,
            body.skill_used,
            body.target,
            body.task_description,
            body.status,
            body.summary,
            body.commit_url,
            body.error_detail,
        ),
    )
    return {"success": True, "id": row["id"]}


class UpdateBacklogRequest(BaseModel):
    status: str  # 'pending' | 'in_progress' | 'done' | 'blocked'
    blocked_reason: Optional[str] = None


@router.patch("/backlog/{backlog_id}", dependencies=[Depends(require_write_secret)])
def update_backlog(backlog_id: int, body: UpdateBacklogRequest):
    run_command(
        "UPDATE agent_backlog SET status = %s, blocked_reason = %s, updated_at = NOW() WHERE id = %s;",
        (body.status, body.blocked_reason, backlog_id),
    )
    return {"success": True}


class CreateBacklogRequest(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 3


@router.post("/backlog", dependencies=[Depends(require_write_secret)])
def create_backlog_item(body: CreateBacklogRequest):
    row = run_insert_returning(
        "INSERT INTO agent_backlog (title, description, priority) VALUES (%s,%s,%s) RETURNING id;",
        (body.title, body.description, body.priority),
    )
    return {"success": True, "id": row["id"]}
