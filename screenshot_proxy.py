import io
import os

import requests
from fastapi import APIRouter, Query, Response

router = APIRouter(prefix="/screenshots", tags=["screenshots"])

APIFLASH_URL = "https://api.apiflash.com/v1/urltoimage"


def _placeholder_jpeg(w: int, h: int) -> bytes:
    """Branded fallback thumbnail used whenever the real screenshot can't be
    fetched (provider quota exhausted, timeout, misconfiguration, etc). The
    demo link itself still works either way - only the preview image inside
    the email would otherwise render as a broken-image icon, which this
    avoids by always returning a valid 200 image."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor("#111827")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.set_facecolor("#111827")
    ax.text(0.5, 0.56, "AutomationGini", ha="center", va="center", color="#ffffff",
             fontsize=max(12, w / 24), fontweight="bold")
    ax.text(0.5, 0.42, "Click to view live preview", ha="center", va="center", color="#9ca3af",
             fontsize=max(9, w / 45))
    buf = io.BytesIO()
    fig.savefig(buf, format="jpg", facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


@router.get("/proxy")
def screenshot_proxy(url: str = Query(...), w: int = 600, h: int = 450):
    """Server-side screenshot proxy - keeps the ApiFlash access key out of
    outbound emails entirely. An <img> src is fetched by the recipient's
    mail client, so calling ApiFlash directly from an email would leak the
    key to every lead (and any provider that prefetches images). Emails
    embed a link to this endpoint instead; the key never leaves the server."""
    access_key = os.environ.get("APIFLASH_ACCESS_KEY")
    if access_key:
        try:
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
        except requests.RequestException:
            resp = None
        if resp is not None and resp.status_code == 200:
            return Response(
                content=resp.content,
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=604800"},
            )

    # Screenshot unavailable (quota exhausted, provider error, or not
    # configured) - degrade to a branded placeholder instead of a broken
    # <img> icon. Short cache so a real screenshot takes over again on its
    # own once quota resets, with no redeploy needed.
    return Response(
        content=_placeholder_jpeg(w, h),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=300"},
    )
