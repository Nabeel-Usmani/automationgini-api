import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from db import run_query, run_command

router = APIRouter(prefix="/leads", tags=["leads"])

CUSTOM_LISTING_WEBHOOK_URL = os.environ.get("CUSTOM_LISTING_WEBHOOK_URL", "")


def _scope_clause(user: dict, alias: str = "l") -> tuple[str, list]:
    if user["role"] == "agent":
        return f"{alias}.tenant_id = %s AND {alias}.agent_id = %s", [user["tenant_id"], user["id"]]
    return f"{alias}.tenant_id = %s", [user["tenant_id"]]


@router.get("")
def list_leads(
    country: Optional[str] = None,
    city: Optional[str] = None,
    niche: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    high_potential_only: bool = False,
    user: dict = Depends(get_current_user),
):
    scope_sql, params = _scope_clause(user, "l")
    extra = ""
    if country:
        extra += " AND l.country = %s"; params.append(country)
    if city:
        extra += " AND l.city = %s"; params.append(city)
    if niche:
        extra += " AND l.niche = %s"; params.append(niche)
    if status:
        extra += " AND l.call_status = %s"; params.append(status)
    if source:
        extra += " AND l.source = %s"; params.append(source)
    if high_potential_only:
        extra += " AND l.review_count BETWEEN 1 AND 15 AND l.total_score < 4"

    rows = run_query(
        f"SELECT l.id, l.business_name, l.niche, l.phone_number, l.email, l.city, l.country, l.country_code, "
        f"l.review_count, l.total_score, l.website, l.website_status, l.call_status, l.source, l.scraped_at, "
        f"(l.review_count BETWEEN 1 AND 15 AND l.total_score < 4) AS is_high_potential "
        f"FROM gmaps_leads l WHERE {scope_sql}{extra} ORDER BY l.scraped_at DESC LIMIT 500;",
        tuple(params),
    )
    return rows


@router.get("/filter-options")
def leads_filter_options(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "l")
    niches = run_query(f"SELECT DISTINCT niche FROM gmaps_leads l WHERE {scope_sql} ORDER BY niche;", tuple(params))
    countries = run_query(f"SELECT DISTINCT country FROM gmaps_leads l WHERE {scope_sql} ORDER BY country;", tuple(params))
    cities = run_query(f"SELECT DISTINCT city FROM gmaps_leads l WHERE {scope_sql} ORDER BY city;", tuple(params))
    statuses = run_query(f"SELECT DISTINCT call_status FROM gmaps_leads l WHERE {scope_sql} ORDER BY call_status;", tuple(params))
    return {
        "niches": [r["niche"] for r in niches],
        "countries": [r["country"] for r in countries],
        "cities": [r["city"] for r in cities],
        "statuses": [r["call_status"] for r in statuses],
    }


class CustomListingRequest(BaseModel):
    url: str
    manual_phone: Optional[str] = None


@router.post("/custom-listing")
def add_custom_listing(body: CustomListingRequest, user: dict = Depends(get_current_user)):
    if not CUSTOM_LISTING_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Custom listing service not configured.")
    resp = requests.post(
        CUSTOM_LISTING_WEBHOOK_URL,
        json={"url": body.url, "tenant_id": user["tenant_id"], "agent_id": user["id"], "manual_phone": body.manual_phone},
        timeout=45,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.post("/{lead_id}/status")
def update_lead_status(lead_id: int, status: str, user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "gmaps_leads")
    run_command(
        f"UPDATE gmaps_leads SET call_status = %s, status_updated_at = NOW() "
        f"WHERE id = %s AND {scope_sql};",
        tuple([status, lead_id] + params),
    )
    return {"success": True}
