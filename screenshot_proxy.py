import os

import requests
from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter(prefix="/screenshots", tags=["screenshots"])

APIFLASH_URL = "https://api.apiflash.com/v1/urltoimage"


@router.get("/proxy")
def screenshot_proxy(url: str = Query(...), w: int = 600, h: int = 450):
    """Server-side screenshot proxy - keeps the ApiFlash access key out of
    outbound emails entirely. An <img> src is fetched by the recipient's
    mail client, so calling ApiFlash directly from an email would leak the
    key to every lead (and any provider that prefetches images). Emails
    embed a link to this endpoint instead; the key never leaves the server."""
    access_key = os.environ.get("APIFLASH_ACCESS_KEY")
    if not access_key:
        raise HTTPException(status_code=500, detail="Screenshot service not configured.")

    resp = requests.get(
        APIFLASH_URL,
        params={
            "access_key": access_key,
            "url": url,
            "width": w,
            "height": h,
            "format": "jpeg",
            "quality": 80,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Screenshot generation failed.")

    return Response(
        content=resp.content,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=604800"},
    )
