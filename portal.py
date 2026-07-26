from datetime import timedelta
from typing import Optional

import psycopg2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from portal_auth import get_current_staff
from crm_common import local_to_utc
from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/portal", tags=["portal"])


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

class ServiceRequest(BaseModel):
    name: str
    duration_minutes: int
    price_cents: Optional[int] = None


def _own_service_or_404(service_id: int, staff: dict) -> dict:
    rows = run_query(
        "SELECT id, duration_minutes FROM crm_services WHERE id = %s AND workspace_id = %s;",
        (service_id, staff["workspace_id"]),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Service not found.")
    return rows[0]


@router.get("/services")
def list_services(staff: dict = Depends(get_current_staff)):
    return run_query(
        "SELECT id, name, duration_minutes, price_cents, active FROM crm_services "
        "WHERE workspace_id = %s ORDER BY id;",
        (staff["workspace_id"],),
    )


@router.post("/services")
def create_service(body: ServiceRequest, staff: dict = Depends(get_current_staff)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Service name is required.")
    if body.duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="Duration must be a positive number of minutes.")
    return run_insert_returning(
        "INSERT INTO crm_services (workspace_id, name, duration_minutes, price_cents) "
        "VALUES (%s,%s,%s,%s) RETURNING id, name, duration_minutes, price_cents, active;",
        (staff["workspace_id"], body.name.strip(), body.duration_minutes, body.price_cents),
    )


@router.patch("/services/{service_id}")
def update_service(service_id: int, body: ServiceRequest, staff: dict = Depends(get_current_staff)):
    _own_service_or_404(service_id, staff)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Service name is required.")
    if body.duration_minutes <= 0:
        raise HTTPException(status_code=400, detail="Duration must be a positive number of minutes.")
    run_command(
        "UPDATE crm_services SET name = %s, duration_minutes = %s, price_cents = %s WHERE id = %s;",
        (body.name.strip(), body.duration_minutes, body.price_cents, service_id),
    )
    return {"success": True}


@router.delete("/services/{service_id}")
def deactivate_service(service_id: int, staff: dict = Depends(get_current_staff)):
    _own_service_or_404(service_id, staff)
    # Soft-delete only - past/future appointments still reference this row.
    run_command("UPDATE crm_services SET active = FALSE WHERE id = %s;", (service_id,))
    return {"success": True}


# ---------------------------------------------------------------------------
# Availability (weekly recurring hours - one shared calendar per workspace in v1)
# ---------------------------------------------------------------------------

class AvailabilityWindow(BaseModel):
    day_of_week: int  # 0=Monday .. 6=Sunday
    start_time: str   # "09:00"
    end_time: str     # "17:00"


@router.get("/availability")
def list_availability(staff: dict = Depends(get_current_staff)):
    return run_query(
        "SELECT id, day_of_week, start_time, end_time FROM crm_availability "
        "WHERE workspace_id = %s ORDER BY day_of_week, start_time;",
        (staff["workspace_id"],),
    )


@router.put("/availability")
def replace_availability(windows: list[AvailabilityWindow], staff: dict = Depends(get_current_staff)):
    """Replaces the entire weekly schedule at once - simpler for the staff UI
    (one "Save Hours" action) than per-window CRUD, and there's no
    appointment data on this table to lose."""
    for w in windows:
        if not (0 <= w.day_of_week <= 6):
            raise HTTPException(status_code=400, detail="day_of_week must be between 0 (Monday) and 6 (Sunday).")
        if w.start_time >= w.end_time:
            raise HTTPException(status_code=400, detail="Each window's start_time must be before its end_time.")

    run_command("DELETE FROM crm_availability WHERE workspace_id = %s;", (staff["workspace_id"],))
    for w in windows:
        run_command(
            "INSERT INTO crm_availability (workspace_id, day_of_week, start_time, end_time) VALUES (%s,%s,%s,%s);",
            (staff["workspace_id"], w.day_of_week, w.start_time, w.end_time),
        )
    return {"success": True}


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

class AppointmentRequest(BaseModel):
    service_id: int
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    starts_at: str  # local wall-clock time in the workspace's own timezone, e.g. "2026-08-01T14:00:00"
    notes: Optional[str] = None


@router.get("/appointments")
def list_appointments(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    staff: dict = Depends(get_current_staff),
):
    sql = (
        "SELECT a.id, a.service_id, s.name AS service_name, a.customer_name, a.customer_email, "
        "a.customer_phone, a.starts_at, a.ends_at, a.status, a.source, a.notes "
        "FROM crm_appointments a JOIN crm_services s ON s.id = a.service_id "
        "WHERE a.workspace_id = %s"
    )
    params = [staff["workspace_id"]]
    if from_date:
        sql += " AND a.starts_at >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND a.starts_at < %s"
        params.append(to_date)
    sql += " ORDER BY a.starts_at;"
    return run_query(sql, tuple(params))


@router.post("/appointments")
def create_appointment(body: AppointmentRequest, staff: dict = Depends(get_current_staff)):
    if not body.customer_name.strip():
        raise HTTPException(status_code=400, detail="Customer name is required.")
    service = _own_service_or_404(body.service_id, staff)

    starts_at = local_to_utc(body.starts_at, staff["timezone"])
    ends_at = starts_at + timedelta(minutes=service["duration_minutes"])

    try:
        return run_insert_returning(
            "INSERT INTO crm_appointments "
            "(workspace_id, service_id, customer_name, customer_email, customer_phone, starts_at, ends_at, source, notes) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,'staff_manual',%s) "
            "RETURNING id, starts_at, ends_at, status;",
            (staff["workspace_id"], body.service_id, body.customer_name.strip(), body.customer_email,
             body.customer_phone, starts_at, ends_at, body.notes),
        )
    except psycopg2.errors.ExclusionViolation:
        raise HTTPException(status_code=409, detail="That time slot overlaps an existing appointment.")


@router.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, staff: dict = Depends(get_current_staff)):
    rows = run_query(
        "SELECT id FROM crm_appointments WHERE id = %s AND workspace_id = %s;",
        (appointment_id, staff["workspace_id"]),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    run_command("UPDATE crm_appointments SET status = 'cancelled' WHERE id = %s;", (appointment_id,))
    return {"success": True}
