import os
import json
import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from auth import get_current_user
from db import run_query, run_command
from billing import PLAN_DEFINITIONS

router = APIRouter(prefix="/search", tags=["search"])

SEARCH_WEBHOOK_URL = os.environ.get(
    "SEARCH_WEBHOOK_URL", "https://app.automationgini.com/webhook/run-search"
)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

_COUNTRIES_PATH = os.path.join(os.path.dirname(__file__), "countries.json")
with open(_COUNTRIES_PATH) as f:
    _COUNTRIES = json.load(f)


@router.get("/countries")
def list_countries(user: dict = Depends(get_current_user)):
    return _COUNTRIES


@router.get("/cities-autocomplete")
def cities_autocomplete(country: str, query: str, user: dict = Depends(get_current_user)):
    if not query or len(query) < 2:
        return []
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="City search not configured.")
    resp = requests.post(
        "https://places.googleapis.com/v1/places:autocomplete",
        json={
            "input": query,
            "includedRegionCodes": [country],
            "includedPrimaryTypes": ["(cities)"],
        },
        headers={
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            "X-Goog-FieldMask": "suggestions.placePrediction.text,suggestions.placePrediction.structuredFormat",
        },
        timeout=10,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    data = resp.json()
    suggestions = data.get("suggestions", [])
    results = []
    for s in suggestions:
        pred = s.get("placePrediction", {})
        structured = pred.get("structuredFormat", {})
        main_text = structured.get("mainText", {}).get("text")
        full_text = pred.get("text", {}).get("text")
        results.append({"city": main_text or full_text, "full_text": full_text})
    return results


class SearchRequest(BaseModel):
    niche: str
    country: str
    cities: List[str]
    max_leads: int = 20
    search_mode: str = "google_maps"  # "google_maps" | "other_platforms"
    # Google Maps mode filters
    min_reviews: int = 1
    max_reviews: int = 15
    max_rating: float = 4.0
    # Other Platforms mode filters (Perplexity-driven)
    platforms: List[str] = []
    business_type: str = "both"  # "b2b" | "b2c" | "both"
    presence_gap: str = "no_website"  # "no_website" | "weak_presence" | "no_social" | "any"
    business_size: str = "any"  # "solo" | "small_team" | "any"
    min_contactability: bool = True
    reputation_signal: bool = False
    geo_scope: str = "city"  # "city" | "metro"


@router.post("/run")
def run_search(body: SearchRequest, user: dict = Depends(get_current_user)):
    if not body.cities:
        raise HTTPException(status_code=400, detail="Select at least one city.")
    if body.search_mode not in ("google_maps", "other_platforms"):
        raise HTTPException(status_code=400, detail="Invalid search_mode.")

    # Real cap enforcement - this was previously missing entirely, meaning
    # searches ran with no limit regardless of plan (confirmed: a Free-plan
    # account had scraped 110 leads despite a 100/month cap).
    plan = PLAN_DEFINITIONS.get(user["plan_name"], PLAN_DEFINITIONS["Free"])
    lead_cap = plan.get("leads")
    if lead_cap is not None:
        used_rows = run_query(
            "SELECT COUNT(*) AS n FROM gmaps_leads WHERE tenant_id = %s "
            "AND scraped_at >= date_trunc('month', NOW());",
            (user["tenant_id"],),
        )
        used = used_rows[0]["n"]
        if used >= lead_cap:
            raise HTTPException(
                status_code=403,
                detail=f"You've reached your plan's {lead_cap}-lead monthly limit ({used} used). Upgrade your plan to continue searching.",
            )

    started = []
    errors = []
    jobs = []
    for city in body.cities:
        search_id = str(uuid.uuid4())
        run_command(
            "INSERT INTO gmaps_search_jobs (id, tenant_id, agent_id, niche, city, target_leads, search_channel) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s);",
            (search_id, user["tenant_id"], user["id"], body.niche, city, body.max_leads, body.search_mode),
        )
        try:
            resp = requests.post(
                SEARCH_WEBHOOK_URL,
                json={
                    "niche": body.niche,
                    "city": city,
                    "country": body.country,
                    "agent_id": user["id"],
                    "max_leads": body.max_leads,
                    "search_mode": body.search_mode,
                    "min_reviews": body.min_reviews,
                    "max_reviews": body.max_reviews,
                    "max_rating": body.max_rating,
                    "platforms": body.platforms,
                    "business_type": body.business_type,
                    "presence_gap": body.presence_gap,
                    "business_size": body.business_size,
                    "min_contactability": body.min_contactability,
                    "reputation_signal": body.reputation_signal,
                    "geo_scope": body.geo_scope,
                    "search_id": search_id,
                },
                timeout=20,
            )
            if resp.status_code >= 400:
                errors.append(city)
                run_command("UPDATE gmaps_search_jobs SET status = 'failed', finished_at = NOW() WHERE id = %s;", (search_id,))
            else:
                started.append(city)
                jobs.append({"city": city, "search_id": search_id})
        except Exception:
            errors.append(city)
            run_command("UPDATE gmaps_search_jobs SET status = 'failed', finished_at = NOW() WHERE id = %s;", (search_id,))

    return {
        "success": len(started) > 0,
        "message": f"Search started for {', '.join(started)}." + (f" Failed to start: {', '.join(errors)}." if errors else ""),
        "started": started,
        "failed": errors,
        "jobs": jobs,
    }


@router.get("/status")
def search_status(ids: str, user: dict = Depends(get_current_user)):
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if not id_list:
        return []
    return run_query(
        "SELECT id AS search_id, niche, city, target_leads, leads_found, status, started_at, finished_at, search_channel "
        "FROM gmaps_search_jobs WHERE id = ANY(%s) AND tenant_id = %s;",
        (id_list, user["tenant_id"]),
    )
