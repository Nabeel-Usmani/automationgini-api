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
    form_fields = {
        "Niche": body.niche,
        "City": body.city,
        "AgentId": str(user["id"]),
        "MaxLeads": str(body.max_leads),
    }
    # n8n Form Trigger nodes expect a real multipart/form-data submission (what an
    # actual HTML <form> sends), not application/x-www-form-urlencoded. Forcing
    # multipart encoding here even though there's no file involved.
    resp = requests.post(
        SEARCH_WEBHOOK_URL,
        files={k: (None, v) for k, v in form_fields.items()},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return {"success": True, "message": "Search started - check My Leads shortly."}
