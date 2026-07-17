from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import bcrypt

from auth import get_current_user
from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_platform_owner(user: dict):
    if not user.get("is_platform_owner"):
        raise HTTPException(status_code=403, detail="Platform owner access only.")


@router.get("/users-overview")
def users_overview(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)

    total_users = run_query(
        "SELECT COUNT(*) AS n FROM gmaps_users WHERE is_platform_owner = false;"
    )[0]["n"]

    active_now = run_query(
        "SELECT COUNT(*) AS n FROM gmaps_users "
        "WHERE is_platform_owner = false AND last_active_at >= NOW() - INTERVAL '5 minutes';"
    )[0]["n"]

    by_country = run_query(
        "SELECT country_code, country_name, COUNT(*) AS n FROM gmaps_users "
        "WHERE is_platform_owner = false AND country_code IS NOT NULL "
        "GROUP BY country_code, country_name ORDER BY n DESC;"
    )

    active_by_country = run_query(
        "SELECT country_code, country_name, COUNT(*) AS n FROM gmaps_users "
        "WHERE is_platform_owner = false AND country_code IS NOT NULL "
        "AND last_active_at >= NOW() - INTERVAL '5 minutes' "
        "GROUP BY country_code, country_name ORDER BY n DESC;"
    )

    return {
        "total_users": total_users,
        "active_now": active_now,
        "users_by_country": by_country,
        "active_users_by_country": active_by_country,
    }


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


# ---------------------------------------------------------------------------
# Agency Owners
# ---------------------------------------------------------------------------

@router.get("/agency-owners")
def list_agency_owners(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    rows = run_query(
        "SELECT u.id, u.username AS email, u.full_name, u.phone_number, u.created_at, "
        "u.country_name, t.company_name, t.plan_name, t.id AS tenant_id, "
        "(SELECT COUNT(*) FROM gmaps_users a WHERE a.tenant_id = u.tenant_id AND a.id != u.id) AS agents_created "
        "FROM gmaps_users u JOIN tenants t ON t.id = u.tenant_id "
        "WHERE u.role = 'admin' AND u.is_platform_owner = false "
        "ORDER BY u.created_at DESC;"
    )
    return rows


@router.get("/agency-owners/{owner_id}/agents")
def agency_owner_agents(owner_id: int, user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    owner_rows = run_query("SELECT tenant_id, full_name FROM gmaps_users WHERE id = %s;", (owner_id,))
    if not owner_rows:
        raise HTTPException(status_code=404, detail="Agency owner not found.")
    tenant_id = owner_rows[0]["tenant_id"]
    agents = run_query(
        "SELECT id, username AS email, full_name, phone_number, role, is_active, created_at "
        "FROM gmaps_users WHERE tenant_id = %s AND id != %s ORDER BY created_at DESC;",
        (tenant_id, owner_id),
    )
    return {"owner_name": owner_rows[0]["full_name"], "agents": agents}


class CreateAgencyOwnerRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: Optional[str] = None
    company_name: str
    plan_name: str = "Free"


@router.post("/agency-owners")
def create_agency_owner(body: CreateAgencyOwnerRequest, user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    email = body.email.strip().lower()

    existing = run_query("SELECT id FROM gmaps_users WHERE username = %s;", (email,))
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    tenant_id = run_insert_returning(
        "INSERT INTO tenants (company_name, plan_name, subscription_status) VALUES (%s, %s, 'active') RETURNING id;",
        (body.company_name, body.plan_name),
    )["id"]

    password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    new_id = run_insert_returning(
        "INSERT INTO gmaps_users (username, password_hash, full_name, role, tenant_id, phone_number) "
        "VALUES (%s, %s, %s, 'admin', %s, %s) RETURNING id;",
        (email, password_hash, body.full_name, tenant_id, body.phone_number),
    )["id"]

    return {"success": True, "id": new_id, "tenant_id": tenant_id}


# ---------------------------------------------------------------------------
# Platform Admins
# ---------------------------------------------------------------------------

@router.get("/platform-admins")
def list_platform_admins(user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    rows = run_query(
        "SELECT id, username AS email, full_name, created_at FROM gmaps_users "
        "WHERE is_platform_owner = true ORDER BY created_at DESC;"
    )
    return rows


class GrantPlatformAdminRequest(BaseModel):
    email: str


@router.post("/platform-admins")
def grant_platform_admin(body: GrantPlatformAdminRequest, user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    email = body.email.strip().lower()
    rows = run_query("SELECT id FROM gmaps_users WHERE username = %s;", (email,))
    if not rows:
        raise HTTPException(status_code=404, detail="No account found with that email. They need to sign up first.")
    run_command("UPDATE gmaps_users SET is_platform_owner = true WHERE id = %s;", (rows[0]["id"],))
    return {"success": True}


@router.delete("/platform-admins/{admin_id}")
def revoke_platform_admin(admin_id: int, user: dict = Depends(get_current_user)):
    _require_platform_owner(user)
    if admin_id == user["id"]:
        raise HTTPException(status_code=400, detail="You can't revoke your own platform admin access.")
    run_command("UPDATE gmaps_users SET is_platform_owner = false WHERE id = %s;", (admin_id,))
    return {"success": True}
