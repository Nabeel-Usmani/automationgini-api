"""Credit system: pay-as-you-go on top of each plan's existing monthly
quota (billing.py PLAN_DEFINITIONS), not a replacement for it. New tenants
get 200 credits automatically on signup (DB trigger, migrations/0012).
Each demo - website, app mockup, CRM, or voice call - costs 20 credits
once a tenant's plan quota for that specific type is used up for the
current calendar month.

Checkout/fulfillment mirrors the existing Stripe pattern used for
voice_agent/website/business_crm purchases (create-checkout-session ->
Stripe -> stripe-webhook -> fulfillment), not a separate payment path -
see CREDITS_CHECKOUT_WEBHOOK_URL below and the n8n workflow it points to.
"""
import os
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from billing import PLAN_DEFINITIONS
from db import run_command, run_insert_returning, run_query

router = APIRouter(prefix="/credits", tags=["credits"])

CREDITS_PER_DEMO = 20

# demo usage_log event_type -> the matching PLAN_DEFINITIONS quota key
# (currently 1:1, kept as a separate map since the names could diverge)
QUOTA_KEY = {
    "vapi_call": "vapi_call",
    "mockup": "mockup",
    "app_mockup": "app_mockup",
    "business_crm": "business_crm",
}

CREDITS_CHECKOUT_WEBHOOK_URL = os.environ.get("CREDITS_CHECKOUT_WEBHOOK_URL", "")

# Purchasable packs - not yet wired to real Stripe pricing (see the n8n
# Create Stripe Checkout Session workflow's credits branch), so treat these
# as a starting point, not a locked-in price.
CREDIT_PACKS = {
    "starter": {"credits": 100, "price": 12},
    "growth": {"credits": 300, "price": 30},
    "scale": {"credits": 1000, "price": 90},
}


def _monthly_usage(tenant_id: int, event_type: str) -> int:
    rows = run_query(
        "SELECT COUNT(*) AS n FROM usage_log WHERE tenant_id = %s AND event_type = %s "
        "AND created_at >= date_trunc('month', NOW());",
        (tenant_id, event_type),
    )
    return rows[0]["n"]


def check_and_reserve(tenant_id: int, plan_name: str, event_type: str) -> dict:
    """Call before triggering a demo of the given event_type. Returns
    {"source": "quota"} when it's covered by the plan's monthly included
    amount (no credit charge - usage_log accounting already happens
    downstream in the n8n fulfillment workflow, same as it does today).
    Returns {"source": "credits", "balance_after": int} when it drew from
    credits instead (deducted atomically here). Raises HTTPException(402)
    if neither quota nor credits can cover it - callers should let that
    propagate as-is rather than catch it, so the CRM can show an
    "add credits" prompt."""
    plan = PLAN_DEFINITIONS.get(plan_name, PLAN_DEFINITIONS["Free"])
    cap = plan.get(QUOTA_KEY.get(event_type, event_type))

    if cap is None:
        return {"source": "quota"}  # None = unlimited on this plan (e.g. Agency)
    if _monthly_usage(tenant_id, event_type) < cap:
        return {"source": "quota"}

    row = run_insert_returning(
        "UPDATE tenants SET credit_balance = credit_balance - %s "
        "WHERE id = %s AND credit_balance >= %s RETURNING credit_balance;",
        (CREDITS_PER_DEMO, tenant_id, CREDITS_PER_DEMO),
    )
    if not row:
        raise HTTPException(
            status_code=402,
            detail=(
                f"This month's included {event_type.replace('_', ' ')} demos are used up, "
                f"and there aren't enough credits to cover this one ({CREDITS_PER_DEMO} needed). "
                "Add credits to keep going."
            ),
        )
    run_command(
        "INSERT INTO credit_transactions (tenant_id, delta, reason, balance_after) VALUES (%s, %s, %s, %s);",
        (tenant_id, -CREDITS_PER_DEMO, f"demo_{event_type}", row["credit_balance"]),
    )
    return {"source": "credits", "balance_after": row["credit_balance"]}


@router.get("/balance")
def get_balance(user: dict = Depends(get_current_user)):
    rows = run_query("SELECT credit_balance FROM tenants WHERE id = %s;", (user["tenant_id"],))
    balance = rows[0]["credit_balance"] if rows else 0
    history = run_query(
        "SELECT delta, reason, balance_after, created_at FROM credit_transactions "
        "WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 50;",
        (user["tenant_id"],),
    )
    return {"balance": balance, "credits_per_demo": CREDITS_PER_DEMO, "recent_transactions": history, "packs": CREDIT_PACKS}


class CreditsCheckoutRequest(BaseModel):
    pack: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


@router.post("/checkout")
def credits_checkout(body: CreditsCheckoutRequest, user: dict = Depends(get_current_user)):
    if body.pack not in CREDIT_PACKS:
        raise HTTPException(status_code=400, detail="Unknown credit pack.")
    if not CREDITS_CHECKOUT_WEBHOOK_URL:
        raise HTTPException(status_code=500, detail="Credits checkout isn't configured yet.")
    resp = requests.post(
        CREDITS_CHECKOUT_WEBHOOK_URL,
        json={
            "tenant_id": user["tenant_id"], "agent_id": user["id"],
            "product_type": "credits", "credit_pack": body.pack,
            "success_url": body.success_url, "cancel_url": body.cancel_url,
        },
        timeout=20,
    )
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:300])
    return resp.json()


@router.post("/grant")
def grant_credits(purchase_id: int):
    """Internal - called by the n8n Grant Credits fulfillment workflow after
    a credits Stripe checkout completes. No user auth, matching the other
    fulfillment webhooks (build-website-paid, etc.): the caller is n8n
    itself over the private app.automationgini.com/api network path, not a
    browser. Idempotent - safe if Stripe redelivers the webhook."""
    rows = run_query(
        "SELECT tenant_id, credit_amount, fulfillment_status FROM purchases "
        "WHERE id = %s AND product_type = 'credits';",
        (purchase_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Credits purchase not found.")
    purchase = rows[0]
    if purchase["fulfillment_status"] == "completed":
        return {"success": True, "already_fulfilled": True}

    row = run_insert_returning(
        "UPDATE tenants SET credit_balance = credit_balance + %s WHERE id = %s RETURNING credit_balance;",
        (purchase["credit_amount"], purchase["tenant_id"]),
    )
    run_command(
        "INSERT INTO credit_transactions (tenant_id, delta, reason, reference_id, balance_after) "
        "VALUES (%s, %s, 'purchase', %s, %s);",
        (purchase["tenant_id"], purchase["credit_amount"], purchase_id, row["credit_balance"]),
    )
    run_command(
        "UPDATE purchases SET fulfillment_status = 'completed', fulfilled_at = NOW() WHERE id = %s;",
        (purchase_id,),
    )
    return {"success": True, "balance": row["credit_balance"]}
