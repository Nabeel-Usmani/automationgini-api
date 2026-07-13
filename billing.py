from fastapi import APIRouter, Depends

from auth import get_current_user
from db import run_query

router = APIRouter(prefix="/billing", tags=["billing"])

PLAN_DEFINITIONS = {
    "Free": {"price": 0, "leads": 100, "vapi_call": 5, "mockup": 5, "chatbot_demo": 5, "premium_leads": 0, "agents": 1},
    "Starter": {"price": 99, "leads": 1000, "vapi_call": 150, "mockup": 150, "chatbot_demo": 150, "premium_leads": 20, "agents": 1},
    "Professional": {"price": 249, "leads": 3000, "vapi_call": 500, "mockup": 500, "chatbot_demo": 500, "premium_leads": 75, "agents": 1},
    "Agency": {"price": None, "leads": None, "vapi_call": None, "mockup": None, "chatbot_demo": None, "premium_leads": None, "agents": None},
}


@router.get("/summary")
def billing_summary(user: dict = Depends(get_current_user)):
    plan = PLAN_DEFINITIONS.get(user["plan_name"], PLAN_DEFINITIONS["Free"])

    usage = {}
    for event_type in ("vapi_call", "mockup", "chatbot_demo"):
        rows = run_query(
            "SELECT COUNT(*) AS n FROM usage_log WHERE tenant_id = %s AND event_type = %s "
            "AND created_at >= date_trunc('month', NOW());",
            (user["tenant_id"], event_type),
        )
        usage[event_type] = rows[0]["n"]

    leads_rows = run_query(
        "SELECT COUNT(*) AS n FROM gmaps_leads WHERE tenant_id = %s AND scraped_at >= date_trunc('month', NOW());",
        (user["tenant_id"],),
    )
    usage["leads"] = leads_rows[0]["n"]

    return {
        "plan_name": user["plan_name"],
        "company_name": user["company_name"],
        "caps": plan,
        "usage_this_month": usage,
        "all_plans": PLAN_DEFINITIONS,
    }
