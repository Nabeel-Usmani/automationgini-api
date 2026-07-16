from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db import run_query

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_platform_owner(user: dict):
    if not user.get("is_platform_owner"):
        raise HTTPException(status_code=403, detail="Platform owner access only.")


@router.get("/overview")
def platform_overview(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)

    tenants = run_query("SELECT COUNT(*) AS n FROM tenants;")[0]["n"]
    agents = run_query("SELECT COUNT(*) AS n FROM gmaps_users WHERE is_platform_owner = false;")[0]["n"]
    leads = run_query("SELECT COUNT(*) AS n FROM gmaps_leads;")[0]["n"]

    revenue_row = run_query(
        "SELECT COALESCE(SUM(price), 0) AS total FROM purchases WHERE payment_status = 'paid';"
    )[0]
    total_revenue = float(revenue_row["total"])

    plan_breakdown = run_query(
        "SELECT plan_name, COUNT(*) AS n FROM tenants GROUP BY plan_name ORDER BY n DESC;"
    )

    usage_by_type = run_query(
        "SELECT event_type, COUNT(*) AS n, COALESCE(SUM(estimated_cost), 0) AS est_cost "
        "FROM usage_log WHERE created_at >= NOW() - INTERVAL '30 days' "
        "GROUP BY event_type ORDER BY n DESC;"
    )

    leads_last_30d = run_query(
        "SELECT COUNT(*) AS n FROM gmaps_leads WHERE scraped_at >= NOW() - INTERVAL '30 days';"
    )[0]["n"]

    return {
        "total_tenants": tenants,
        "total_agents": agents,
        "total_leads": leads,
        "leads_last_30_days": leads_last_30d,
        "total_revenue": total_revenue,
        "plan_breakdown": plan_breakdown,
        "usage_last_30_days": usage_by_type,
    }


@router.get("/tenants")
def list_tenants(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    rows = run_query(
        "SELECT t.id, t.company_name, t.plan_name, t.subscription_status, t.created_at, "
        "(SELECT COUNT(*) FROM gmaps_users u WHERE u.tenant_id = t.id) AS agent_count, "
        "(SELECT COALESCE(SUM(p.price), 0) FROM purchases p WHERE p.tenant_id = t.id AND p.payment_status = 'paid') AS revenue, "
        "(SELECT COUNT(*) FROM gmaps_leads l WHERE l.tenant_id = t.id) AS lead_count "
        "FROM tenants t ORDER BY t.created_at DESC;"
    )
    return rows


@router.get("/activity")
def recent_activity(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    rows = run_query(
        "SELECT p.id, p.product_type, p.price, p.payment_status, p.created_at, "
        "t.company_name, l.business_name "
        "FROM purchases p "
        "JOIN tenants t ON t.id = p.tenant_id "
        "LEFT JOIN gmaps_leads l ON l.id = p.lead_id "
        "ORDER BY p.created_at DESC LIMIT 30;"
    )
    return rows
