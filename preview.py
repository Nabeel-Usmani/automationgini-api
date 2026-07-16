from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from db import run_query

router = APIRouter(tags=["preview"])


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

    return HTMLResponse(html)
