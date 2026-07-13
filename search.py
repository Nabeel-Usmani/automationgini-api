import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])

# Confirmed directly against the live workflow's webhookId - this is the real,
# active Google Maps Lead Scraper v2 form endpoint, not a guess.
SEARCH_WEBHOOK_URL = os.environ.get(
    "SEARCH_WEBHOOK_URL", "https://app.automationgini.com/form/89221bd3-0dae-40a7-ae6a-033e24aac9d4"
)


class SearchRequest(BaseModel):
    niche: str
    city: str
    max_leads: int = 100


@router.post("/run")
def run_search(body: SearchRequest, user: dict = Depends(get_current_user)):
    resp = requests.post(
        SEARCH_WEBHOOK_URL,
        data={"Niche": body.niche, "City": body.city, "AgentId": str(user["id"]), "MaxLeads": str(body.max_leads)},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return {"success": True, "message": "Search started - check My Leads shortly."}
