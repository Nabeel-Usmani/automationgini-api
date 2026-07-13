import os
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from db import run_query, run_insert_returning

router = APIRouter(prefix="/auth", tags=["auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7  # 7 days


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


@router.post("/login")
def login(body: LoginRequest):
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
