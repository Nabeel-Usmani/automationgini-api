from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from db import run_query, run_command

router = APIRouter(prefix="/survey", tags=["survey"])


@router.get("/check")
def check_survey_needed(trigger: str, user: dict = Depends(get_current_user)):
    """
    Determines whether the mandatory survey should show for this login/logout event.
    Rule: never on the user's first-ever login; from their second login onward,
    show on every login and every logout.
    """
    if trigger not in ("login", "logout"):
        raise HTTPException(status_code=400, detail="trigger must be 'login' or 'logout'.")

    rows = run_query("SELECT login_count FROM gmaps_users WHERE id = %s;", (user["id"],))
    login_count = rows[0]["login_count"] if rows else 0

    should_show = login_count >= 2
    return {"should_show": should_show, "session_number": login_count}


class SurveyResponse(BaseModel):
    trigger_type: str
    rating: int
    likely_to_reuse: int
    willingness_to_pay: Optional[float] = None


@router.post("/submit")
def submit_survey(body: SurveyResponse, user: dict = Depends(get_current_user)):
    if body.trigger_type not in ("login", "logout"):
        raise HTTPException(status_code=400, detail="trigger_type must be 'login' or 'logout'.")
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=400, detail="rating must be between 1 and 5.")
    if not (1 <= body.likely_to_reuse <= 5):
        raise HTTPException(status_code=400, detail="likely_to_reuse must be between 1 and 5.")

    rows = run_query("SELECT login_count FROM gmaps_users WHERE id = %s;", (user["id"],))
    session_number = rows[0]["login_count"] if rows else None

    run_command(
        "INSERT INTO user_surveys (user_id, trigger_type, session_number, rating, likely_to_reuse, willingness_to_pay) "
        "VALUES (%s, %s, %s, %s, %s, %s);",
        (user["id"], body.trigger_type, session_number, body.rating, body.likely_to_reuse, body.willingness_to_pay),
    )
    return {"success": True}


@router.get("/results")
def survey_results(user: dict = Depends(get_current_user)):
    """Platform-owner-only aggregate view of survey results."""
    if not user.get("is_platform_owner"):
        raise HTTPException(status_code=403, detail="Platform owner access only.")

    summary = run_query(
        "SELECT COUNT(*) AS total_responses, "
        "ROUND(AVG(rating)::numeric, 2) AS avg_rating, "
        "ROUND(AVG(likely_to_reuse)::numeric, 2) AS avg_likely_to_reuse, "
        "ROUND(AVG(willingness_to_pay)::numeric, 2) AS avg_willingness_to_pay "
        "FROM user_surveys;"
    )[0]

    recent = run_query(
        "SELECT s.trigger_type, s.rating, s.likely_to_reuse, s.willingness_to_pay, s.created_at, u.full_name "
        "FROM user_surveys s JOIN gmaps_users u ON u.id = s.user_id "
        "ORDER BY s.created_at DESC LIMIT 50;"
    )

    return {"summary": summary, "recent": recent}
