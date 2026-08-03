from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db import run_query

router = APIRouter(prefix="/email-automation", tags=["email-automation"])


def _scope_clause(user: dict, alias: str) -> tuple[str, list]:
    if user["role"] == "agent":
        return f"{alias}.tenant_id = %s AND {alias}.agent_id = %s", [user["tenant_id"], user["id"]]
    return f"{alias}.tenant_id = %s", [user["tenant_id"]]


def _require_enabled(user: dict):
    # Beta feature - only tenants with email_automation_enabled have it wired
    # up while the outreach mailbox and ESP get set up. Everyone else keeps
    # seeing "Coming Soon" in the sidebar.
    if not user.get("email_automation_enabled"):
        raise HTTPException(status_code=403, detail="Email automation isn't available on your account yet.")


@router.get("/stats")
def stats(user: dict = Depends(get_current_user)):
    _require_enabled(user)
    scope_sql, params = _scope_clause(user, "s")
    row = run_query(
        f"SELECT "
        f"COUNT(*) FILTER (WHERE s.step >= 1) AS initial_sent, "
        f"COALESCE(SUM(GREATEST(s.step - 1, 0)), 0) AS followups_sent, "
        f"COUNT(*) FILTER (WHERE s.status = 'replied') AS replied, "
        f"COUNT(*) FILTER (WHERE s.status = 'active') AS active, "
        f"COUNT(*) FILTER (WHERE s.status = 'completed_no_reply') AS completed_no_reply, "
        f"COUNT(*) FILTER (WHERE s.status = 'failed') AS failed, "
        f"COUNT(*) AS total_enrolled "
        f"FROM lead_email_sequences s WHERE {scope_sql};",
        tuple(params),
    )[0]
    initial = row["initial_sent"] or 0
    row["reply_rate"] = round((row["replied"] / initial) * 100, 1) if initial else 0.0
    return row


@router.get("/sequences")
def sequences(user: dict = Depends(get_current_user)):
    _require_enabled(user)
    scope_sql, params = _scope_clause(user, "s")
    return run_query(
        f"SELECT s.id, s.lead_id, l.business_name, l.niche, l.city, l.country, l.email, "
        f"s.sequence_type, s.demo_url, s.step, s.status, s.last_sent_at, s.replied_at, s.created_at "
        f"FROM lead_email_sequences s JOIN gmaps_leads l ON l.id = s.lead_id "
        f"WHERE {scope_sql} ORDER BY s.created_at DESC LIMIT 500;",
        tuple(params),
    )


@router.get("/sends")
def sends(email_type: str = "all", user: dict = Depends(get_current_user)):
    """Individual emails actually sent, for the drill-down when an agent
    clicks a metric card (e.g. Initial Sent, Follow-ups Sent). Excludes the
    html body to keep the list light - fetch /sends/{id} for that."""
    _require_enabled(user)
    scope_sql, params = _scope_clause(user, "s")
    type_sql = ""
    if email_type == "initial":
        type_sql = " AND e.email_type = 'initial'"
    elif email_type == "followups":
        type_sql = " AND e.email_type LIKE 'followup_%'"
    return run_query(
        f"SELECT e.id, e.sequence_id, e.step, e.email_type, e.sent_at, e.message_id, e.subject, "
        f"l.business_name, l.niche, l.city, l.country, l.email AS to_email, "
        f"s.sequence_type, s.status, s.replied_at "
        f"FROM lead_email_sends e "
        f"JOIN lead_email_sequences s ON s.id = e.sequence_id "
        f"JOIN gmaps_leads l ON l.id = s.lead_id "
        f"WHERE {scope_sql}{type_sql} ORDER BY e.sent_at DESC LIMIT 500;",
        tuple(params),
    )


@router.get("/sends/{send_id}")
def send_detail(send_id: int, user: dict = Depends(get_current_user)):
    """Full content (subject + html) of one sent email, for the preview modal."""
    _require_enabled(user)
    scope_sql, params = _scope_clause(user, "s")
    rows = run_query(
        f"SELECT e.id, e.subject, e.html, e.sent_at, e.message_id, l.business_name, l.email AS to_email "
        f"FROM lead_email_sends e "
        f"JOIN lead_email_sequences s ON s.id = e.sequence_id "
        f"JOIN gmaps_leads l ON l.id = s.lead_id "
        f"WHERE e.id = %s AND {scope_sql};",
        tuple([send_id] + params),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Email not found.")
    return rows[0]


@router.get("/timeseries")
def timeseries(user: dict = Depends(get_current_user)):
    """Daily send counts (initial vs follow-up) for the last 30 days, for the chart."""
    _require_enabled(user)
    scope_sql, params = _scope_clause(user, "s")
    return run_query(
        f"SELECT e.sent_at::date AS day, "
        f"COUNT(*) FILTER (WHERE e.email_type = 'initial') AS initial_sent, "
        f"COUNT(*) FILTER (WHERE e.email_type LIKE 'followup_%') AS followups_sent "
        f"FROM lead_email_sends e "
        f"JOIN lead_email_sequences s ON s.id = e.sequence_id "
        f"WHERE {scope_sql} AND e.sent_at >= NOW() - INTERVAL '30 days' "
        f"GROUP BY e.sent_at::date ORDER BY e.sent_at::date;",
        tuple(params),
    )
