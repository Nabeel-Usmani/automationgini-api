import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import run_query

router = APIRouter(prefix="/demo", tags=["app-mockup"])

APP_MOCKUP_WEBHOOK_URL = os.environ.get(
    "APP_MOCKUP_WEBHOOK_URL", "https://app.automationgini.com/webhook/build-app-mockup"
)


def _own_lead_or_403(lead_id: int, user: dict):
    rows = run_query("SELECT tenant_id FROM gmaps_leads WHERE id = %s;", (lead_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if rows[0]["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not your lead.")


class AppMockupRequest(BaseModel):
    lead_id: int


@router.post("/app-mockup")
def build_app_mockup(body: AppMockupRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    resp = requests.post(
        APP_MOCKUP_WEBHOOK_URL,
        json={"lead_id": body.lead_id, "agent_id": user["id"], "tenant_id": user["tenant_id"]},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.get("/app-mockup/{purchase_id}/status")
def app_mockup_status(purchase_id: int, user: dict = Depends(get_current_user)):
    rows = run_query(
        "SELECT fulfillment_status, tenant_id FROM purchases WHERE id = %s;", (purchase_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Not found.")
    if rows[0]["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not yours.")
    return {"fulfillment_status": rows[0]["fulfillment_status"]}


@router.get("/app-mockup/created")
def app_mockup_created(user: dict = Depends(get_current_user)):
    rows = run_query(
        "SELECT p.id, p.preview_token, p.fulfillment_status, p.created_at, "
        "l.business_name, l.niche, l.city "
        "FROM purchases p JOIN gmaps_leads l ON l.id = p.lead_id "
        "WHERE p.product_type = 'app_mockup' AND p.tenant_id = %s "
        "ORDER BY p.created_at DESC LIMIT 50;",
        (user["tenant_id"],),
    )
    return rows
