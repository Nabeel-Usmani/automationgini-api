import os
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel

from db import run_query, run_command, run_insert_returning

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def create_access_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "tenant_id": user["tenant_id"],
        "role": user["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session.")


def get_current_user(authorization: str = Header(None)) -> dict:
    """FastAPI dependency - use as `user = Depends(get_current_user)` on any
    protected route. Expects 'Authorization: Bearer <token>'."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)

    rows = run_query(
        "SELECT u.id, u.username, u.full_name, u.role, u.is_active, u.tenant_id, "
        "u.is_platform_owner, t.company_name, t.plan_name, t.subscription_status "
        "FROM gmaps_users u JOIN tenants t ON t.id = u.tenant_id WHERE u.id = %s;",
        (payload["sub"],),
    )
    if not rows or not rows[0]["is_active"]:
        raise HTTPException(status_code=401, detail="Account not found or deactivated.")
    row = rows[0]
    if row["subscription_status"] not in ("active", "trialing"):
        raise HTTPException(status_code=403, detail="Subscription is not active.")

    # Lightweight heartbeat for "active now" tracking - only writes if the
    # last heartbeat was more than 60s ago, to avoid a write on every request.
    try:
        run_command(
            "UPDATE gmaps_users SET last_active_at = NOW() WHERE id = %s "
            "AND (last_active_at IS NULL OR last_active_at < NOW() - INTERVAL '60 seconds');",
            (row["id"],),
        )
    except Exception:
        pass

    return row


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    company_name: str
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str
    account_type: str = "individual"  # 'individual' | 'agency_owner' | 'agent'


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/signup")
def signup(body: SignupRequest):
    email = body.email.strip().lower()
    existing = run_query("SELECT id FROM gmaps_users WHERE username = %s;", (email,))
    if existing:
        raise HTTPException(status_code=400, detail="That email is already registered.")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password needs to be at least 8 characters.")

    tenant = run_insert_returning(
        "INSERT INTO tenants (company_name, plan_name, subscription_status) VALUES (%s, 'Free', 'active') RETURNING id;",
        (body.company_name.strip(),),
    )
    tenant_id = tenant["id"]

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    full_name = f"{body.first_name.strip()} {body.last_name.strip()}".strip()
    user = run_insert_returning(
        "INSERT INTO gmaps_users (username, password_hash, full_name, role, tenant_id) "
        "VALUES (%s,%s,%s,'admin',%s) RETURNING id, username, full_name, role, tenant_id;",
        (email, pw_hash, full_name, tenant_id),
    )

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "full_name": full_name}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def _capture_login_location(user_id: int, request: Request):
    """Best-effort IP geolocation on login - never blocks or breaks login if it fails."""
    try:
        ip = _client_ip(request)
        if not ip or ip.startswith("127.") or ip.startswith("192.168.") or ip == "localhost":
            return
        resp = requests.get(f"https://free.freeipapi.com/api/json/{ip}", timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            country_code = data.get("countryCode")
            country_name = data.get("countryName")
            if country_code:
                run_command(
                    "UPDATE gmaps_users SET country_code = %s, country_name = %s WHERE id = %s;",
                    (country_code, country_name, user_id),
                )
    except Exception:
        pass


@router.post("/login")
def login(body: LoginRequest, request: Request):
    email = body.email.strip().lower()
    rows = run_query(
        "SELECT u.id, u.username, u.password_hash, u.full_name, u.role, u.is_active, u.tenant_id, "
        "t.subscription_status FROM gmaps_users u JOIN tenants t ON t.id = u.tenant_id WHERE u.username = %s;",
        (email,),
    )
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    row = rows[0]
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")
    if row["subscription_status"] not in ("active", "trialing"):
        raise HTTPException(status_code=403, detail="Your subscription is not active.")
    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    _capture_login_location(row["id"], request)

    token = create_access_token(row)
    return {"access_token": token, "token_type": "bearer", "full_name": row["full_name"]}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "company_name": user["company_name"],
        "plan_name": user["plan_name"],
        "is_platform_owner": bool(user["is_platform_owner"]),
    }


class UpdateProfileRequest(BaseModel):
    full_name: str


@router.patch("/profile")
def update_profile(body: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    if not body.full_name.strip():
        raise HTTPException(status_code=400, detail="Name can't be empty.")
    run_command("UPDATE gmaps_users SET full_name = %s WHERE id = %s;", (body.full_name.strip(), user["id"]))
    return {"success": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    rows = run_query("SELECT password_hash FROM gmaps_users WHERE id = %s;", (user["id"],))
    if not rows or not bcrypt.checkpw(body.current_password.encode(), rows[0]["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password needs to be at least 8 characters.")
    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    run_command("UPDATE gmaps_users SET password_hash = %s WHERE id = %s;", (new_hash, user["id"]))
    return {"success": True}


@router.post("/google")
def google_auth(body: GoogleAuthRequest):
    # Verify the token server-side against Google directly - never trust the
    # client-side token claims alone. Same approach already proven in n8n.
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": body.credential},
        timeout=10,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified.")
    info = resp.json()
    if info.get("aud") != GOOGLE_CLIENT_ID or info.get("email_verified") != "true":
        raise HTTPException(status_code=401, detail="Google sign-in could not be verified.")

    email = info["email"].strip().lower()
    full_name = info.get("name", email.split("@")[0])

    existing = run_query(
        "SELECT u.id, u.username, u.full_name, u.role, u.is_active, u.tenant_id, "
        "u.is_platform_owner, t.company_name, t.plan_name, t.subscription_status "
        "FROM gmaps_users u JOIN tenants t ON t.id = u.tenant_id WHERE u.username = %s;",
        (email,),
    )

    if existing:
        row = existing[0]
        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="This account has been deactivated.")
        if row["subscription_status"] not in ("active", "trialing"):
            raise HTTPException(status_code=403, detail="Your subscription is not active.")
        token = create_access_token(row)
        return {"access_token": token, "token_type": "bearer", "full_name": row["full_name"]}

    # No existing account - only Individual mode may self-create a new tenant.
    if body.account_type in ("agent", "agency_owner"):
        raise HTTPException(
            status_code=404,
            detail="No account found with this email. If you were given credentials by "
                   "AutomationGini or your agency admin, make sure you're using the right email.",
        )

    tenant = run_insert_returning(
        "INSERT INTO tenants (company_name, plan_name, subscription_status) VALUES (%s, 'Free', 'active') RETURNING id;",
        (f"{full_name}'s Team",),
    )
    user = run_insert_returning(
        "INSERT INTO gmaps_users (username, password_hash, full_name, role, tenant_id) "
        "VALUES (%s,%s,%s,'admin',%s) RETURNING id, username, full_name, role, tenant_id;",
        (email, bcrypt.hashpw(secrets.token_hex(16).encode(), bcrypt.gensalt()).decode(), full_name, tenant["id"]),
    )
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "full_name": full_name}
