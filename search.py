import os
import json
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from auth import get_current_user

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
    min_reviews: int = 1
    max_reviews: int = 15
    max_rating: float = 4.0


@router.post("/run")
def run_search(body: SearchRequest, user: dict = Depends(get_current_user)):
    if not body.cities:
        raise HTTPException(status_code=400, detail="Select at least one city.")

    started = []
    errors = []
    for city in body.cities:
        try:
            resp = requests.post(
                SEARCH_WEBHOOK_URL,
                json={
                    "niche": body.niche,
                    "city": city,
                    "country": body.country,
                    "agent_id": user["id"],
                    "max_leads": body.max_leads,
                    "min_reviews": body.min_reviews,
                    "max_reviews": body.max_reviews,
                    "max_rating": body.max_rating,
                },
                timeout=20,
            )
            if resp.status_code >= 400:
                errors.append(city)
            else:
                started.append(city)
        except Exception:
            errors.append(city)

    return {
        "success": len(started) > 0,
        "message": f"Search started for {', '.join(started)}." + (f" Failed to start: {', '.join(errors)}." if errors else ""),
        "started": started,
        "failed": errors,
    }
