from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from db import run_query

DEMO_BANNER = (
    "<div style='position:fixed;top:0;left:0;right:0;z-index:99999;background:#1e293b;"
    "color:white;text-align:center;padding:8px;font-family:sans-serif;font-size:13px;'>"
    "\U0001F512 FREE PREVIEW from AutomationGini — not a live website yet. "
    "<a href='https://automationgini.com' style='color:#93c5fd;'>automationgini.com</a></div>"
    "<div style='height:36px;'></div>"
)


def _with_banner(html: str) -> str:
    if "<body>" in html:
        return html.replace("<body>", "<body>" + DEMO_BANNER, 1)
    return DEMO_BANNER + html

router = APIRouter(tags=["preview"])


@router.get("/preview-revision", response_class=HTMLResponse)
def preview_revision(id: int = Query(...)):
    rows = run_query("SELECT revised_html, status FROM website_revisions WHERE id = %s;", (id,))
    if not rows:
        return HTMLResponse("<h1>Revision not found.</h1>", status_code=404)
    row = rows[0]
    if not row["revised_html"]:
        return HTMLResponse(
            "<html><head><meta http-equiv='refresh' content='5'></head>"
            "<body style='font-family:sans-serif;text-align:center;padding:80px;'>"
            "<h2>Still generating this change...</h2><p>This refreshes automatically.</p>"
            "</body></html>"
        )
    banner = (
        "<div style='position:fixed;top:0;left:0;right:0;z-index:99999;background:#1e293b;"
        "color:white;text-align:center;padding:8px;font-family:sans-serif;font-size:13px;'>"
        "⚠️ PREVIEW ONLY — this change has not been published yet</div>"
        "<div style='height:36px;'></div>"
    )
    html = row["revised_html"]
    if "<body>" in html:
        html = html.replace("<body>", "<body>" + banner, 1)
    else:
        html = banner + html
    return HTMLResponse(html)


@router.get("/preview", response_class=HTMLResponse)
def serve_preview(preview: str = Query(...), page: str = Query("index")):
    rows = run_query(
        "SELECT fulfillment_detail, fulfillment_status, preview_expires_at "
        "FROM purchases WHERE preview_token = %s;",
        (preview,),
    )
    if not rows:
        return HTMLResponse("<h1>This preview link isn't valid.</h1>", status_code=404)

    row = rows[0]

    expires_at = row["preview_expires_at"]
    if expires_at and datetime.now(timezone.utc) > expires_at:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:80px;'>"
            "<h2>This preview has expired.</h2><p>Ask your agent for a fresh demo.</p>"
            "</body></html>",
            status_code=410,
        )

    pages = (row["fulfillment_detail"] or {}).get("pages", {})
    html = pages.get(page)

    if not html:
        if row["fulfillment_status"] == "building":
            return HTMLResponse(
                "<html><head><meta http-equiv='refresh' content='5'></head>"
                "<body style='font-family:sans-serif;text-align:center;padding:80px;'>"
                "<h2>Still building this page...</h2><p>This refreshes automatically.</p>"
                "</body></html>"
            )
        return HTMLResponse("<h1>This page isn't available yet.</h1>", status_code=404)

    resp = HTMLResponse(_with_banner(html))
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp
