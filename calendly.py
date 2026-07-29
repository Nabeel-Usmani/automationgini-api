import os
import time
from datetime import datetime, timedelta, timezone

import jwt
import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from auth import JWT_ALGORITHM, JWT_SECRET, get_current_user
from db import run_command, run_query

router = APIRouter(prefix="/calendly", tags=["calendly"])

CALENDLY_CLIENT_ID = os.environ.get("CALENDLY_CLIENT_ID", "")
CALENDLY_CLIENT_SECRET = os.environ.get("CALENDLY_CLIENT_SECRET", "")
CALENDLY_REDIRECT_URI = os.environ.get("CALENDLY_REDIRECT_URI", "https://api.automationgini.com/calendly/callback")
CRM_BUILD_CHATBOT_URL = "https://crm.automationgini.com/build/chatbot"

# Short-lived, signed OAuth state - carries which chatbot this connection is
# for through the Calendly redirect round-trip, without relying on the
# session cookie surviving a cross-site redirect.
STATE_TTL_SECONDS = 600


def _own_chatbot_config_or_403(chatbot_config_id: int, user: dict) -> dict:
    rows = run_query(
        "SELECT id, tenant_id, business_name FROM chatbot_configs WHERE id = %s AND tenant_id = %s;",
        (chatbot_config_id, user["tenant_id"]),
    )
    if not rows:
        raise HTTPException(status_code=403, detail="This chatbot doesn't belong to your account.")
    return rows[0]


@router.get("/connect")
def connect(chatbot_config_id: int, user: dict = Depends(get_current_user)):
    if not CALENDLY_CLIENT_ID or not CALENDLY_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Calendly integration isn't configured yet.")
    _own_chatbot_config_or_403(chatbot_config_id, user)

    state = jwt.encode(
        {
            "chatbot_config_id": chatbot_config_id,
            "tenant_id": user["tenant_id"],
            "exp": int(time.time()) + STATE_TTL_SECONDS,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    authorize_url = (
        "https://auth.calendly.com/oauth/authorize"
        f"?client_id={CALENDLY_CLIENT_ID}&response_type=code"
        f"&redirect_uri={CALENDLY_REDIRECT_URI}&state={state}"
    )
    return {"authorize_url": authorize_url}


@router.get("/callback")
def callback(code: str = None, state: str = None, error: str = None):
    if error or not code or not state:
        return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=error")

    try:
        payload = jwt.decode(state, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=error")

    chatbot_config_id = payload["chatbot_config_id"]
    tenant_id = payload["tenant_id"]

    owns = run_query(
        "SELECT id FROM chatbot_configs WHERE id = %s AND tenant_id = %s;",
        (chatbot_config_id, tenant_id),
    )
    if not owns:
        return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=error")

    token_resp = requests.post(
        "https://auth.calendly.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": CALENDLY_REDIRECT_URI,
            "client_id": CALENDLY_CLIENT_ID,
            "client_secret": CALENDLY_CLIENT_SECRET,
        },
        timeout=15,
    )
    if token_resp.status_code >= 400:
        return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=error")
    tokens = token_resp.json()

    me_resp = requests.get(
        "https://api.calendly.com/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=15,
    )
    if me_resp.status_code >= 400:
        return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=error")
    me = me_resp.json()["resource"]

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens["expires_in"]))
    run_command(
        "INSERT INTO chatbot_calendly_connections "
        "(chatbot_config_id, access_token, refresh_token, token_expires_at, calendly_user_uri, scheduling_url) "
        "VALUES (%s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (chatbot_config_id) DO UPDATE SET "
        "access_token = EXCLUDED.access_token, refresh_token = EXCLUDED.refresh_token, "
        "token_expires_at = EXCLUDED.token_expires_at, calendly_user_uri = EXCLUDED.calendly_user_uri, "
        "scheduling_url = EXCLUDED.scheduling_url, connected_at = NOW();",
        (chatbot_config_id, tokens["access_token"], tokens["refresh_token"], expires_at, me["uri"], me["scheduling_url"]),
    )
    return RedirectResponse(f"{CRM_BUILD_CHATBOT_URL}?calendly=connected")


@router.get("/status")
def status(chatbot_config_id: int, user: dict = Depends(get_current_user)):
    _own_chatbot_config_or_403(chatbot_config_id, user)
    rows = run_query(
        "SELECT scheduling_url, connected_at FROM chatbot_calendly_connections WHERE chatbot_config_id = %s;",
        (chatbot_config_id,),
    )
    if not rows:
        return {"connected": False}
    return {"connected": True, "scheduling_url": rows[0]["scheduling_url"], "connected_at": rows[0]["connected_at"]}


class DisconnectRequest(BaseModel):
    chatbot_config_id: int


@router.post("/disconnect")
def disconnect(body: DisconnectRequest, user: dict = Depends(get_current_user)):
    _own_chatbot_config_or_403(body.chatbot_config_id, user)
    run_command(
        "DELETE FROM chatbot_calendly_connections WHERE chatbot_config_id = %s;",
        (body.chatbot_config_id,),
    )
    return {"success": True}
