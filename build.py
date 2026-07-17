import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/build", tags=["build"])

CHECKOUT_WEBHOOK_URL = os.environ.get("CHECKOUT_WEBHOOK_URL", "")
REVISION_WEBHOOK_URL = os.environ.get("REVISION_WEBHOOK_URL", "https://app.automationgini.com/webhook/request-website-revision")
CHATBOT_SUBSCRIPTION_WEBHOOK_URL = os.environ.get("CHATBOT_SUBSCRIPTION_WEBHOOK_URL", "")
EDIT_AGENT_WEBHOOK_URL = os.environ.get("EDIT_AGENT_WEBHOOK_URL", "")


def _scope_clause(user: dict, alias: str) -> tuple[str, list]:
    if user["role"] == "agent":
        return f"{alias}.tenant_id = %s AND {alias}.agent_id = %s", [user["tenant_id"], user["id"]]
    return f"{alias}.tenant_id = %s", [user["tenant_id"]]


def _own_lead_or_403(lead_id: int, user: dict):
    scope_sql, params = _scope_clause(user, "l")
    rows = run_query(f"SELECT id FROM gmaps_leads l WHERE l.id = %s AND {scope_sql};", tuple([lead_id] + params))
    if not rows:
        raise HTTPException(status_code=403, detail="This lead doesn't belong to you.")


class VoiceAgentBuildRequest(BaseModel):
    lead_id: int
    byok_key: str
    custom_instructions: Optional[str] = None
    language_code: Optional[str] = None


@router.post("/voice-agent/checkout")
def build_voice_agent(body: VoiceAgentBuildRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not CHECKOUT_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Checkout service not configured.")
    resp = requests.post(
        CHECKOUT_WEBHOOK_URL,
        json={
            "product_type": "voice_agent", "lead_id": body.lead_id, "agent_id": user["id"],
            "tenant_id": user["tenant_id"], "byok_key": body.byok_key,
            "custom_instructions": body.custom_instructions, "language_code": body.language_code,
        },
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.get("/voice-agent/created")
def voice_agents_created(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "p")
    return run_query(
        f"SELECT p.id, p.lead_id, l.business_name, l.niche, l.city, p.fulfillment_detail, p.fulfillment_status, "
        f"p.created_at FROM purchases p JOIN gmaps_leads l ON l.id = p.lead_id "
        f"WHERE p.product_type = 'voice_agent' AND p.fulfillment_status = 'completed' AND {scope_sql} "
        f"ORDER BY p.created_at DESC;",
        tuple(params),
    )


class PageConfig(BaseModel):
    page_key: str
    page_title: str
    use_default_content: bool = True
    custom_content: Optional[str] = None


class WebsiteCheckoutRequest(BaseModel):
    lead_id: int
    product_type: str  # 'website_html' | 'website_react' | 'website_react_video'
    purchase_id: Optional[int] = None
    logo_data_uri: Optional[str] = None
    pages: Optional[list[PageConfig]] = None
    template_id: Optional[str] = None


@router.post("/website/checkout")
def website_checkout(body: WebsiteCheckoutRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not CHECKOUT_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Checkout service not configured.")

    design_brief = None
    if body.template_id:
        from templates_data import NORMAL_TEMPLATES, MODERN_TEMPLATES
        for t in NORMAL_TEMPLATES + MODERN_TEMPLATES:
            if t["id"] == body.template_id:
                design_brief = t["design_brief"]
                break

    build_config = {
        "logo_data_uri": body.logo_data_uri,
        "pages": [p.dict() for p in body.pages] if body.pages else None,
        "template_id": body.template_id,
        "design_brief": design_brief,
    }

    resp = requests.post(
        CHECKOUT_WEBHOOK_URL,
        json={
            "product_type": body.product_type, "lead_id": body.lead_id, "agent_id": user["id"],
            "tenant_id": user["tenant_id"], "purchase_id": body.purchase_id,
            "build_config": build_config,
        },
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


class ChatbotCheckoutRequest(BaseModel):
    lead_id: int
    system_prompt: Optional[str] = None


@router.post("/chatbot/checkout")
def chatbot_checkout(body: ChatbotCheckoutRequest, user: dict = Depends(get_current_user)):
    _own_lead_or_403(body.lead_id, user)
    if not CHATBOT_SUBSCRIPTION_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Chatbot subscription service not configured.")
    resp = requests.post(
        CHATBOT_SUBSCRIPTION_WEBHOOK_URL,
        json={"lead_id": body.lead_id, "tenant_id": user["tenant_id"], "agent_id": user["id"], "system_prompt": body.system_prompt},
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.get("/chatbot/created")
def chatbots_created(user: dict = Depends(get_current_user)):
    scope_sql, params = _scope_clause(user, "c")
    return run_query(
        f"SELECT id, lead_id, business_name, chatbot_token, status, current_period_end, created_at "
        f"FROM chatbot_configs c WHERE status = 'active' AND {scope_sql} ORDER BY created_at DESC;",
        tuple(params),
    )


class EditInstructionsRequest(BaseModel):
    config_id: int
    agent_type: str  # 'voice_agent' | 'chatbot'
    new_instruction: str


@router.post("/edit-instructions")
def edit_instructions(body: EditInstructionsRequest, user: dict = Depends(get_current_user)):
    if not EDIT_AGENT_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Edit instructions service not configured.")
    resp = requests.post(
        EDIT_AGENT_WEBHOOK_URL,
        json={"config_id": body.config_id, "type": body.agent_type, "new_instruction": body.new_instruction},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


def _own_purchase_or_403(purchase_id: int, user: dict):
    rows = run_query("SELECT tenant_id FROM purchases WHERE id = %s;", (purchase_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Site not found.")
    if rows[0]["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not your site.")


class RequestRevisionRequest(BaseModel):
    page_key: str
    request_text: str


@router.post("/website/{purchase_id}/request-change")
def request_website_change(purchase_id: int, body: RequestRevisionRequest, user: dict = Depends(get_current_user)):
    _own_purchase_or_403(purchase_id, user)
    if not body.request_text.strip():
        raise HTTPException(status_code=400, detail="Describe the change you want.")

    revision_id = run_insert_returning(
        "INSERT INTO website_revisions (purchase_id, page_key, request_text, requested_by) "
        "VALUES (%s, %s, %s, %s) RETURNING id;",
        (purchase_id, body.page_key, body.request_text.strip(), user["id"]),
    )["id"]

    try:
        requests.post(REVISION_WEBHOOK_URL, json={"revision_id": revision_id}, timeout=15)
    except Exception:
        pass  # Fire-and-forget - the agent polls status instead

    return {"success": True, "revision_id": revision_id}


@router.get("/website/{purchase_id}/revisions")
def list_website_revisions(purchase_id: int, user: dict = Depends(get_current_user)):
    _own_purchase_or_403(purchase_id, user)
    rows = run_query(
        "SELECT id, page_key, request_text, status, created_at, resolved_at, "
        "revised_html IS NOT NULL AS has_preview "
        "FROM website_revisions WHERE purchase_id = %s ORDER BY created_at DESC;",
        (purchase_id,),
    )
    return rows


@router.post("/website/revisions/{revision_id}/approve")
def approve_website_revision(revision_id: int, user: dict = Depends(get_current_user)):
    rows = run_query(
        "SELECT r.id, r.purchase_id, r.page_key, r.revised_html, r.status, p.tenant_id "
        "FROM website_revisions r JOIN purchases p ON p.id = r.purchase_id WHERE r.id = %s;",
        (revision_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Revision not found.")
    row = rows[0]
    if row["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not your site.")
    if not row["revised_html"]:
        raise HTTPException(status_code=400, detail="Revision isn't ready yet.")
    if row["status"] == "applied":
        raise HTTPException(status_code=400, detail="Already applied.")

    run_command(
        "UPDATE purchases SET fulfillment_detail = jsonb_set("
        "COALESCE(fulfillment_detail, '{\"pages\":{}}'::jsonb), ARRAY['pages', %s], to_jsonb(%s::text)) "
        "WHERE id = %s;",
        (row["page_key"], row["revised_html"], row["purchase_id"]),
    )
    run_command(
        "UPDATE website_revisions SET status = 'applied', resolved_at = NOW() WHERE id = %s;",
        (revision_id,),
    )
    return {"success": True}


@router.post("/website/revisions/{revision_id}/reject")
def reject_website_revision(revision_id: int, user: dict = Depends(get_current_user)):
    rows = run_query(
        "SELECT r.id, p.tenant_id FROM website_revisions r JOIN purchases p ON p.id = r.purchase_id WHERE r.id = %s;",
        (revision_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Revision not found.")
    if rows[0]["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not your site.")
    run_command(
        "UPDATE website_revisions SET status = 'rejected', resolved_at = NOW() WHERE id = %s;",
        (revision_id,),
    )
    return {"success": True}
