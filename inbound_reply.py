from fastapi import APIRouter, Request

from db import run_insert_returning

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _extract_sender_email(payload: dict) -> str:
    items = payload.get("items") if isinstance(payload.get("items"), list) else [payload]
    first = items[0] if items else {}
    from_field = first.get("From") or first.get("from") or {}
    if isinstance(from_field, str):
        email = from_field
    else:
        email = (
            from_field.get("Address")
            or from_field.get("address")
            or from_field.get("Email")
            or from_field.get("email")
            or ""
        )
    return email.strip().lower()


@router.post("/inbound-reply")
async def inbound_reply(request: Request):
    """Brevo inbound-parse webhook: marks the matching lead's email sequence
    as replied so scheduled follow-ups stop. Always 200s - Brevo has no
    retry logic to benefit from a failure status here."""
    payload = await request.json()
    sender_email = _extract_sender_email(payload)
    if not sender_email:
        return {"success": True, "matched": False}

    row = run_insert_returning(
        "UPDATE lead_email_sequences s SET replied_at = NOW(), status = 'replied' "
        "FROM gmaps_leads l WHERE l.id = s.lead_id AND lower(l.email) = %s "
        "AND s.status = 'active' AND s.replied_at IS NULL "
        "RETURNING s.id, s.lead_id;",
        (sender_email,),
    )
    return {"success": True, "matched": row is not None}
