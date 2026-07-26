"""Shared helpers for the business-CRM feature (portal_auth, portal,
public_booking) - kept separate from build.py's helpers since this is a
distinct product surface with its own tenancy (client-business workspaces,
not AutomationGini agency tenants)."""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

UTC = ZoneInfo("UTC")


def local_to_utc(naive_iso: str, tz_name: str) -> datetime:
    """Interprets naive_iso (e.g. '2026-08-01T14:00:00', no offset) as a
    wall-clock time in the workspace's own timezone and converts it to UTC.
    Storing everything as UTC and doing this conversion in Python (rather
    than relying on `::timestamptz` casts) avoids any dependence on the
    database session's timezone setting."""
    try:
        naive = datetime.fromisoformat(naive_iso)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format.")
    if naive.tzinfo is not None:
        raise HTTPException(status_code=400, detail="starts_at must be a local wall-clock time with no timezone offset.")
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        raise HTTPException(status_code=400, detail="Invalid workspace timezone.")
    return naive.replace(tzinfo=tz).astimezone(UTC)


def utc_to_local_naive(dt: datetime, tz_name: str) -> datetime:
    """Inverse of local_to_utc, for comparing DB-stored UTC timestamps
    against wall-clock availability windows."""
    return dt.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
