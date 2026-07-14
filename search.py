import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user

router = APIRouter(prefix="/search", tags=["search"])

# Confirmed directly against the live workflow - a real, dedicated JSON webhook,
# added specifically because n8n's Form Trigger node doesn't reliably accept
# programmatic (non-browser) submissions.
SEARCH_WEBHOOK_URL = os.environ.get(
    "SEARCH_WEBHOOK_URL", "https://app.automationgini.com/webhook/run-search"
)


class SearchRequest(BaseModel):
    niche: str
    city: str
    max_leads: int = 100


@router.post("/run")
def run_search(body: SearchRequest, user: dict = Depends(get_current_user)):
    resp = requests.post(
        SEARCH_WEBHOOK_URL,
        json={"niche": body.niche, "city": body.city, "agent_id": user["id"], "max_leads": body.max_leads},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return {"success": True, "message": "Search started - check My Leads shortly."}
