import requests
from fastapi import APIRouter, Depends, Query
from typing import Optional

from auth import get_current_user
from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _scope_clause(user: dict, alias: str = "l") -> tuple[str, list]:
    """Agents see only their own data. Individual owners (non-Agency admins) see
    their whole tenant, which in practice is just themselves since they have no team."""
    if user["role"] == "agent":
        return f"{alias}.tenant_id = %s AND {alias}.agent_id = %s", [user["tenant_id"], user["id"]]
    return f"{alias}.tenant_id = %s", [user["tenant_id"]]


@router.get("/summary")
def dashboard_summary(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    scope_sql, scope_params = _scope_clause(user, "l")

    extra_sql = ""
    extra_params = []
    if date_from:
        extra_sql += " AND l.scraped_at >= %s"
        extra_params.append(date_from)
    if date_to:
        extra_sql += " AND l.scraped_at <= %s"
        extra_params.append(date_to)
    if niche:
        extra_sql += " AND l.niche = %s"
        extra_params.append(niche)
    if country:
        extra_sql += " AND l.country = %s"
        extra_params.append(country)
    if city:
        extra_sql += " AND l.city = %s"
        extra_params.append(city)

    leads_extracted = run_query(
        f"SELECT COUNT(*) AS n FROM gmaps_leads l WHERE {scope_sql}{extra_sql};",
        tuple(scope_params + extra_params),
    )[0]["n"]

    # Demos created: combined across voice/website/chatbot, scoped the same way via usage_log
    usage_scope_sql, usage_scope_params = _scope_clause(user, "u")
    demos_created = run_query(
        f"SELECT COUNT(*) AS n FROM usage_log u WHERE {usage_scope_sql} "
        f"AND event_type IN ('vapi_call','chatbot_demo','mockup');",
        tuple(usage_scope_params),
    )[0]["n"]

    calls_made = run_query(
        f"SELECT COUNT(*) AS n FROM usage_log u WHERE {usage_scope_sql} AND event_type = 'zoom_call';",
        tuple(usage_scope_params),
    )[0]["n"]

    leads_by_city = run_query(
        f"SELECT l.city, l.country, l.country_code, COUNT(*) AS n "
        f"FROM gmaps_leads l WHERE {scope_sql}{extra_sql} "
        f"GROUP BY l.city, l.country, l.country_code ORDER BY n DESC LIMIT 25;",
        tuple(scope_params + extra_params),
    )

    return {
        "leads_extracted": leads_extracted,
        "demos_created": demos_created,
        "calls_made": calls_made,
        "leads_by_city": leads_by_city,
    }


@router.get("/filter-options")
def filter_options(user: dict = Depends(get_current_user)):
    scope_sql, scope_params = _scope_clause(user, "l")
    niches = run_query(f"SELECT DISTINCT niche FROM gmaps_leads l WHERE {scope_sql} ORDER BY niche;", tuple(scope_params))
    countries = run_query(
        f"SELECT DISTINCT country, country_code FROM gmaps_leads l WHERE {scope_sql} ORDER BY country;", tuple(scope_params)
    )
    cities = run_query(f"SELECT DISTINCT city, country FROM gmaps_leads l WHERE {scope_sql} ORDER BY city;", tuple(scope_params))
    return {"niches": [r["niche"] for r in niches], "countries": countries, "cities": cities}


@router.post("/log-call")
def log_call(lead_id: int, user: dict = Depends(get_current_user)):
    """Called when an agent clicks 'Call via Zoom' on a lead - real click tracking,
    not a fabricated number."""
    run_command(
        "INSERT INTO usage_log (event_type, lead_id, agent_id, estimated_cost, detail, tenant_id) "
        "VALUES ('zoom_call', %s, %s, 0, 'Called via Zoom', %s);",
        (lead_id, user["id"], user["tenant_id"]),
    )
    return {"success": True}


def _geocode_city(city: str, country: str):
    """Nominatim (OpenStreetMap) free geocoding - no API key required. Results are
    cached in city_coordinates so this only ever runs once per city."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": city, "country": country, "format": "json", "limit": 1},
            headers={"User-Agent": "AutomationGini/1.0"},
            timeout=8,
        )
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None, None


@router.get("/city-coordinates")
def city_coordinates(user: dict = Depends(get_current_user)):
    """Returns lat/lng for every city this tenant/agent has leads in, geocoding
    and caching any city not already known."""
    scope_sql, scope_params = _scope_clause(user, "l")
    cities = run_query(
        f"SELECT DISTINCT l.city, l.country FROM gmaps_leads l WHERE {scope_sql};", tuple(scope_params)
    )

    results = []
    for row in cities:
        city, country = row["city"], row["country"]
        cached = run_query(
            "SELECT lat, lng FROM city_coordinates WHERE city = %s AND country = %s;", (city, country)
        )
        if cached:
            lat, lng = cached[0]["lat"], cached[0]["lng"]
        else:
            lat, lng = _geocode_city(city, country)
            if lat is not None:
                run_command(
                    "INSERT INTO city_coordinates (city, country, lat, lng) VALUES (%s,%s,%s,%s) "
                    "ON CONFLICT (city, country) DO NOTHING;",
                    (city, country, lat, lng),
                )
        if lat is not None:
            results.append({"city": city, "country": country, "lat": lat, "lng": lng})

    return results
