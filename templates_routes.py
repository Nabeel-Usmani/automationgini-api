from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from auth import get_current_user
from db import run_query
from templates_data import NORMAL_TEMPLATES, MODERN_TEMPLATES

router = APIRouter(prefix="/templates", tags=["templates"])


def _public(t: dict) -> dict:
    return {"id": t["id"], "name": t["name"], "description": t["description"]}


@router.get("")
def list_templates(user: dict = Depends(get_current_user)):
    return {
        "normal": [_public(t) for t in NORMAL_TEMPLATES],
        "modern": [_public(t) for t in MODERN_TEMPLATES],
    }


@router.get("/preview", response_class=HTMLResponse)
def template_preview(id: str = Query(...)):
    rows = run_query("SELECT html FROM template_previews WHERE template_id = %s;", (id,))
    if not rows or not rows[0]["html"]:
        return HTMLResponse("<h1>Preview not available yet.</h1>", status_code=404)
    return HTMLResponse(rows[0]["html"])
