from datetime import date as date_type, datetime, timedelta

import psycopg2
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from crm_common import UTC, local_to_utc, utc_to_local_naive
from db import run_query, run_insert_returning

router = APIRouter(prefix="/public/crm", tags=["public-booking"])


def _workspace_or_404(slug: str) -> dict:
    rows = run_query(
        "SELECT id, business_name, timezone FROM crm_workspaces WHERE slug = %s AND status = 'active';",
        (slug,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Booking page not found.")
    return rows[0]


def _active_service_or_404(service_id: int, workspace_id: int) -> dict:
    rows = run_query(
        "SELECT id, duration_minutes FROM crm_services WHERE id = %s AND workspace_id = %s AND active = TRUE;",
        (service_id, workspace_id),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Service not found.")
    return rows[0]


@router.get("/{slug}/services")
def public_services(slug: str):
    workspace = _workspace_or_404(slug)
    services = run_query(
        "SELECT id, name, duration_minutes, price_cents FROM crm_services "
        "WHERE workspace_id = %s AND active = TRUE ORDER BY id;",
        (workspace["id"],),
    )
    return {"business_name": workspace["business_name"], "services": services}


@router.get("/{slug}/availability")
def public_availability(slug: str, service_id: int, date: str):
    """Open slots for one calendar day, derived from weekly hours minus
    existing booked appointments and any blackout date."""
    workspace = _workspace_or_404(slug)
    service = _active_service_or_404(service_id, workspace["id"])

    try:
        day = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date - expected YYYY-MM-DD.")

    if run_query("SELECT id FROM crm_blackouts WHERE workspace_id = %s AND date = %s;", (workspace["id"], day)):
        return {"slots": []}

    windows = run_query(
        "SELECT start_time, end_time FROM crm_availability WHERE workspace_id = %s AND day_of_week = %s;",
        (workspace["id"], day.weekday()),
    )
    if not windows:
        return {"slots": []}

    booked = run_query(
        "SELECT starts_at, ends_at FROM crm_appointments WHERE workspace_id = %s AND status = 'booked' "
        "AND (starts_at::date = %s OR ends_at::date = %s);",
        (workspace["id"], day, day),
    )
    booked_local = [
        (utc_to_local_naive(b["starts_at"], workspace["timezone"]), utc_to_local_naive(b["ends_at"], workspace["timezone"]))
        for b in booked
    ]

    duration = timedelta(minutes=service["duration_minutes"])
    now_local = utc_to_local_naive(datetime.now(UTC), workspace["timezone"])

    slots = []
    for w in windows:
        cursor = datetime.combine(day, w["start_time"])
        window_end = datetime.combine(day, w["end_time"])
        while cursor + duration <= window_end:
            slot_end = cursor + duration
            if cursor > now_local and not any(cursor < be and slot_end > bs for bs, be in booked_local):
                slots.append(cursor.strftime("%H:%M"))
            cursor += duration
    return {"slots": slots}


class PublicBookingRequest(BaseModel):
    service_id: int
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    starts_at: str  # local wall-clock time in the workspace's own timezone, e.g. "2026-08-01T14:00:00"


@router.post("/{slug}/book")
def public_book(slug: str, body: PublicBookingRequest):
    workspace = _workspace_or_404(slug)
    if not body.customer_name.strip() or not body.customer_email.strip():
        raise HTTPException(status_code=400, detail="Name and email are required.")
    service = _active_service_or_404(body.service_id, workspace["id"])

    starts_at = local_to_utc(body.starts_at, workspace["timezone"])
    if starts_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="That time is in the past.")
    ends_at = starts_at + timedelta(minutes=service["duration_minutes"])

    try:
        row = run_insert_returning(
            "INSERT INTO crm_appointments "
            "(workspace_id, service_id, customer_name, customer_email, customer_phone, starts_at, ends_at, source) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'public_booking') "
            "RETURNING id, starts_at, ends_at;",
            (workspace["id"], body.service_id, body.customer_name.strip(), body.customer_email.strip(),
             body.customer_phone, starts_at, ends_at),
        )
    except psycopg2.errors.ExclusionViolation:
        raise HTTPException(status_code=409, detail="That time just got booked by someone else - please pick another slot.")
    return {"success": True, "appointment_id": row["id"], "starts_at": row["starts_at"], "ends_at": row["ends_at"]}
