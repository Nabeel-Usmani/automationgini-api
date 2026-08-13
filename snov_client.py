"""
Snov.io readiness client - not wired into the live owner-email pipeline yet.

The in-house pattern-guess + MX-verification system (see lead_owner_emails /
email_pattern_stats in leads.py) is the primary owner-email path today and
needs no external API. This module exists so that once a Snov.io
subscription is purchased and SNOV_CLIENT_ID / SNOV_CLIENT_SECRET are set as
Render env vars, Snov can be called as a supplementary signal (e.g. to
confirm/backfill emails the pattern system is unsure about) without any
further code changes - just add the two env vars.

The OAuth2 client-credentials exchange below follows Snov's documented,
stable auth flow. The domain-search call follows their documented v2
endpoint shape; verify it against Snov's current API docs once real
credentials are in hand and this gets wired into an actual workflow, since
it hasn't been exercised against a live account yet.
"""
import os
import time

import requests

SNOV_CLIENT_ID = os.environ.get("SNOV_CLIENT_ID", "")
SNOV_CLIENT_SECRET = os.environ.get("SNOV_CLIENT_SECRET", "")

_token_cache = {"access_token": None, "expires_at": 0}


def is_configured() -> bool:
    return bool(SNOV_CLIENT_ID and SNOV_CLIENT_SECRET)


def _get_access_token() -> str | None:
    if not is_configured():
        return None
    if _token_cache["access_token"] and _token_cache["expires_at"] > time.time():
        return _token_cache["access_token"]

    resp = requests.post(
        "https://api.snov.io/v1/oauth/access_token",
        data={
            "grant_type": "client_credentials",
            "client_id": SNOV_CLIENT_ID,
            "client_secret": SNOV_CLIENT_SECRET,
        },
        timeout=15,
    )
    if resp.status_code >= 400:
        return None
    data = resp.json()
    _token_cache["access_token"] = data.get("access_token")
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600)) - 60
    return _token_cache["access_token"]


def find_emails_by_domain(domain: str, limit: int = 10) -> list[dict] | None:
    """Returns Snov's guessed/verified emails for a domain, or None if Snov
    isn't configured or the call fails. Callers should treat this as a
    supplementary signal alongside the in-house pattern-confidence score,
    not a replacement for it."""
    token = _get_access_token()
    if not token:
        return None

    resp = requests.get(
        "https://api.snov.io/v2/domain-search/emails-with-info",
        params={"domain": domain, "limit": limit, "access_token": token},
        timeout=20,
    )
    if resp.status_code >= 400:
        return None
    return resp.json().get("emails", [])
