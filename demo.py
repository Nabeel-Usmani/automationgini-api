import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from db import run_query

router = APIRouter(prefix="/demo", tags=["demo"])

AI_DEMO_WEBHOOK_URL = os.environ.get("AI_DEMO_WEBHOOK_URL", "")
CHATBOT_DEMO_WEBHOOK_URL = os.environ.get("CHATBOT_DEMO_WEBHOOK_URL", "")
WEBSITE_PREVIEW_WEBHOOK_URL = os.environ.get("PREVIEW_WEBHOOK_URL", "")


def _scope_clause(user: dict, alias: str) -> tuple[str, list]:
    if user["role"] == "agent":
        return f"{alias}.tenant_id = %s AND {alias}.agent_id = %s", [user["tenant_id"], user["id"]]
    return f"{alias}.tenant_id = %s", [user["tenant_id"]]


def _own_lead_or_403(lead_id: int, user: dict):
    scope_sql, params = _scope_clause(user, "l")
    rows = run_query(f"SELECT id FROM gmaps_leads l WHERE l.id = %s AND {scope_sql};", tuple([lead_id] + params))
    if not rows:
        raise HTTPException(status_code=403, detail="This lead doesn't belong to you.")


class VoiceDemoRequest(BaseModel):
    lead_id: int
    demo_type: str = "bilingual"


@router.post("/voice")
def run_voice_demo(body: VoiceDemoRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not AI_DEMO_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Voice demo service not configured.")
    resp = requests.post(
        AI_DEMO_WEBHOOK_URL,
        json={"lead_id": body.lead_id, "demo_type": body.demo_type, "agent_id": user["id"]},
        timeout=15,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return {"success": True}


@router.get("/voice/created")
def voice_demos_created(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "u")
    return run_query(
        f"SELECT DISTINCT ON (l.id) l.id AS lead_id, l.business_name, l.niche, l.city, l.phone_number, "
        f"u.created_at AS last_demo_at FROM usage_log u JOIN gmaps_leads l ON l.id = u.lead_id "
        f"WHERE u.event_type = 'vapi_call' AND {scope_sql} ORDER BY l.id, u.created_at DESC;",
        tuple(params),
    )


class ChatbotDemoRequest(BaseModel):
    lead_id: int


@router.post("/chatbot")
def run_chatbot_demo(body: ChatbotDemoRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not CHATBOT_DEMO_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Chatbot demo service not configured.")
    resp = requests.post(
        CHATBOT_DEMO_WEBHOOK_URL,
        json={"lead_id": body.lead_id, "tenant_id": user["tenant_id"], "agent_id": user["id"]},
        timeout=45,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.get("/chatbot/created")
def chatbot_demos_created(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "c")
    return run_query(
        f"SELECT id, lead_id, business_name, chatbot_token, created_at, demo_expires_at "
        f"FROM chatbot_configs c WHERE is_demo = true AND {scope_sql} ORDER BY created_at DESC;",
        tuple(params),
    )


class WebsitePreviewRequest(BaseModel):
    lead_id: int
    product_type: str = "website_html"


@router.post("/website")
def build_website_preview(body: WebsitePreviewRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not WEBSITE_PREVIEW_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Website preview service not configured.")
    resp = requests.post(
        WEBSITE_PREVIEW_WEBHOOK_URL,
        json={"lead_id": body.lead_id, "agent_id": user["id"], "tenant_id": user["tenant_id"], "product_type": body.product_type},
        timeout=240,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.get("/website/created")
def website_previews_created(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "p")
    return run_query(
        f"SELECT p.id, p.lead_id, l.business_name, l.niche, l.city, p.preview_token, p.preview_expires_at, "
        f"p.payment_status, p.created_at FROM purchases p JOIN gmaps_leads l ON l.id = p.lead_id "
        f"WHERE p.product_type IN ('website_html','website_react') AND {scope_sql} ORDER BY p.created_at DESC;",
        tuple(params),
    )
