import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel

from db import run_query, run_command

router = APIRouter(prefix="/portal/auth", tags=["portal-auth"])

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24 * 7
JWT_AUDIENCE = "portal"  # keeps a portal token from being usable against the agency's get_current_user, and vice versa

# Separate cookie from the agency's ag_session - a client business's staff
# are not AutomationGini users, so this is a completely independent login,
# not a role flag on an existing account.
PORTAL_SESSION_COOKIE_NAME = "ag_portal_session"
PORTAL_SESSION_COOKIE_DOMAIN = ".automationgini.com"


def set_portal_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=PORTAL_SESSION_COOKIE_NAME,
        value=token,
        max_age=JWT_EXPIRY_HOURS * 3600,
        httponly=True,
        secure=True,
        samesite="lax",
        domain=PORTAL_SESSION_COOKIE_DOMAIN,
        path="/",
    )


def clear_portal_session_cookie(response: Response):
    response.delete_cookie(key=PORTAL_SESSION_COOKIE_NAME, domain=PORTAL_SESSION_COOKIE_DOMAIN, path="/")


def create_portal_token(staff: dict) -> str:
    payload = {
        "sub": str(staff["id"]),
        "workspace_id": staff["workspace_id"],
        "role": staff["role"],
        "aud": JWT_AUDIENCE,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_portal_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], audience=JWT_AUDIENCE)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired, please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session.")


def get_current_staff(ag_portal_session: str = Cookie(None)) -> dict:
    if not ag_portal_session:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    payload = decode_portal_token(ag_portal_session)

    rows = run_query(
        "SELECT s.id, s.workspace_id, s.email, s.full_name, s.role, s.is_active, "
        "w.business_name, w.slug, w.timezone, w.status AS workspace_status "
        "FROM crm_staff s JOIN crm_workspaces w ON w.id = s.workspace_id WHERE s.id = %s;",
        (payload["sub"],),
    )
    if not rows or not rows[0]["is_active"]:
        raise HTTPException(status_code=401, detail="Account not found or deactivated.")
    row = rows[0]
    if row["workspace_status"] != "active":
        raise HTTPException(status_code=403, detail="This workspace is not active.")
    return row


class SetPasswordRequest(BaseModel):
    invite_token: str
    password: str


@router.post("/set-password")
def set_password(body: SetPasswordRequest, response: Response):
    rows = run_query(
        "SELECT id, workspace_id, role FROM crm_staff "
        "WHERE invite_token = %s AND invite_expires_at > NOW();",
        (body.invite_token,),
    )
    if not rows:
        raise HTTPException(status_code=400, detail="This invite link is invalid or has expired.")
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password needs to be at least 8 characters.")
    row = rows[0]

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    run_command(
        "UPDATE crm_staff SET password_hash = %s, invite_token = NULL, invite_expires_at = NULL WHERE id = %s;",
        (pw_hash, row["id"]),
    )
    token = create_portal_token(row)
    set_portal_session_cookie(response, token)
    return {"success": True}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest, response: Response):
    email = body.email.strip().lower()
    rows = run_query(
        "SELECT id, workspace_id, password_hash, full_name, role, is_active FROM crm_staff WHERE email = %s;",
        (email,),
    )
    if not rows or not rows[0]["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    row = rows[0]
    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")
    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_portal_token(row)
    set_portal_session_cookie(response, token)
    return {"success": True, "full_name": row["full_name"]}


@router.get("/me")
def me(staff: dict = Depends(get_current_staff)):
    return {
        "id": staff["id"],
        "workspace_id": staff["workspace_id"],
        "email": staff["email"],
        "full_name": staff["full_name"],
        "role": staff["role"],
        "business_name": staff["business_name"],
        "slug": staff["slug"],
        "timezone": staff["timezone"],
    }


@router.post("/logout")
def logout(response: Response):
    # HttpOnly, so client JS can't clear it itself - same reasoning as the
    # agency's /auth/logout.
    clear_portal_session_cookie(response)
    return {"success": True}
