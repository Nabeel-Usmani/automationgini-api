import io
import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from auth import get_current_user
from db import run_query

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

router = APIRouter(prefix="/leads", tags=["audit"])

AUDIT_WEBHOOK_URL = "https://app.automationgini.com/webhook/generate-audit-report"

NAVY = colors.HexColor("#1e293b")
BLUE = colors.HexColor("#2563eb")
SLATE = colors.HexColor("#64748b")
GREEN = colors.HexColor("#16a34a")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")


def _score_color(score):
    if score is None:
        return SLATE
    if score >= 80:
        return GREEN
    if score >= 50:
        return AMBER
    return RED


def _own_lead_or_403(lead_id: int, user: dict):
    rows = run_query("SELECT tenant_id FROM gmaps_leads WHERE id = %s;", (lead_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Lead not found.")
    if rows[0]["tenant_id"] != user["tenant_id"]:
        raise HTTPException(status_code=403, detail="Not your lead.")


@router.post("/{lead_id}/audit/generate")
def generate_audit(lead_id: int, user: dict = Depends(get_current_user)):
    _own_lead_or_403(lead_id, user)
    try:
        requests.post(AUDIT_WEBHOOK_URL, json={"lead_id": lead_id}, timeout=15)
    except Exception:
        pass
    return {"success": True}


@router.get("/{lead_id}/audit/status")
def audit_status(lead_id: int, user: dict = Depends(get_current_user)):
    _own_lead_or_403(lead_id, user)
    rows = run_query("SELECT generated_at FROM lead_audits WHERE lead_id = %s;", (lead_id,))
    return {"ready": bool(rows)}


def _make_score_chart(scores: dict) -> io.BytesIO:
    labels = list(scores.keys())
    values = [v if v is not None else 0 for v in scores.values()]
    bar_colors = ["#16a34a" if v >= 80 else "#d97706" if v >= 50 else "#dc2626" for v in values]

    fig, ax = plt.subplots(figsize=(6.2, 2.6))
    bars = ax.barh(labels, values, color=bar_colors, height=0.55)
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_xticks([])
    for bar, v in zip(bars, values):
        ax.text(v + 2, bar.get_y() + bar.get_height() / 2, str(v), va="center", fontsize=10, fontweight="bold")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_gauge_chart(score: int, label: str) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(2.6, 2.6), subplot_kw={"aspect": "equal"})
    color = "#16a34a" if score >= 80 else "#d97706" if score >= 50 else "#dc2626"
    ax.pie([score, 100 - score], colors=[color, "#e5e7eb"], startangle=90, counterclock=False,
           wedgeprops={"width": 0.32})
    ax.text(0, 0.08, str(score), ha="center", va="center", fontsize=26, fontweight="bold", color="#1e293b")
    ax.text(0, -0.28, label, ha="center", va="center", fontsize=10, color="#64748b")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf


@router.get("/{lead_id}/audit/download")
def download_audit_pdf(lead_id: int, user: dict = Depends(get_current_user)):
    _own_lead_or_403(lead_id, user)

    lead_rows = run_query("SELECT business_name, niche, city, phone_number FROM gmaps_leads WHERE id = %s;", (lead_id,))
    if not lead_rows:
        raise HTTPException(status_code=404, detail="Lead not found.")
    lead = lead_rows[0]

    audit_rows = run_query(
        "SELECT has_website, performance_score, seo_score, accessibility_score, best_practices_score, "
        "listing_score, listing_score_breakdown, findings, niche_benchmark, action_plan, generated_at "
        "FROM lead_audits WHERE lead_id = %s;",
        (lead_id,),
    )
    if not audit_rows:
        raise HTTPException(status_code=404, detail="Audit not generated yet.")
    audit = audit_rows[0]
    findings_data = audit["findings"] or {}
    benchmark = audit["niche_benchmark"] or {}
    action_plan = audit["action_plan"] or findings_data.get("action_plan") or []

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.55 * inch, bottomMargin=0.65 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle("Brand", parent=styles["Normal"], fontSize=10, textColor=BLUE, fontName="Helvetica-Bold")
    title_style = ParagraphStyle("AuditTitle", parent=styles["Title"], fontSize=22, textColor=NAVY, spaceAfter=2)
    sub_style = ParagraphStyle("AuditSub", parent=styles["Normal"], fontSize=11, textColor=SLATE, spaceAfter=10)
    section_label_style = ParagraphStyle("SectionLabel", parent=styles["Normal"], fontSize=9, textColor=BLUE,
                                          fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=2)
    h2_style = ParagraphStyle("AuditH2", parent=styles["Heading2"], fontSize=15, textColor=NAVY, spaceBefore=2, spaceAfter=8)
    h3_style = ParagraphStyle("AuditH3", parent=styles["Heading3"], fontSize=12, textColor=NAVY, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("AuditBody", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#334155"), leading=15)
    headline_style = ParagraphStyle("Headline", parent=styles["Normal"], fontSize=13, textColor=NAVY, leading=18,
                                     backColor=colors.HexColor("#fef3c7"), borderPadding=12)
    finding_title_style = ParagraphStyle("FindingTitle", parent=styles["Normal"], fontSize=11.5, textColor=NAVY,
                                          fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=2)
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.5, textColor=SLATE, alignment=TA_CENTER)
    action_title_style = ParagraphStyle("ActionTitle", parent=styles["Normal"], fontSize=11, textColor=NAVY, fontName="Helvetica-Bold")
    action_body_style = ParagraphStyle("ActionBody", parent=styles["Normal"], fontSize=9.5, textColor=colors.HexColor("#334155"), leading=13)

    story = []

    # ---------------- PAGE 1: Cover / Overview ----------------
    story.append(Paragraph("AUTOMATIONGINI &middot; ONLINE PRESENCE AUDIT", brand_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(lead["business_name"] or "Business Audit", title_style))
    story.append(Paragraph(f"{lead['niche'] or ''} &middot; {lead['city'] or ''}", sub_style))

    story.append(Paragraph("HEADLINE FINDING", section_label_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(findings_data.get("headline_finding", ""), headline_style))

    story.append(Paragraph("OVERALL ONLINE PRESENCE SCORE", section_label_style))
    gauge_buf = _make_gauge_chart(audit["listing_score"] or 0, "Listing Score")
    story.append(Image(gauge_buf, width=1.9 * inch, height=1.9 * inch))

    breakdown = audit["listing_score_breakdown"] or {}
    bd_rows = [["Factor", "Score"]]
    for key, item in breakdown.items():
        bd_rows.append([item.get("label", key), f"{item.get('points', 0)}/{item.get('max', 25)}"])
    bd_table = Table(bd_rows, colWidths=[3.7 * inch, 1.5 * inch])
    bd_table.setStyle(_table_style())
    story.append(Spacer(1, 8))
    story.append(bd_table)

    story.append(PageBreak())

    # ---------------- PAGE 2: Benchmark comparison ----------------
    story.append(Paragraph("HOW YOU COMPARE", section_label_style))
    story.append(Paragraph(f"Benchmarked Against {benchmark.get('sample_size', 'N/A')} Similar {lead['niche'] or ''} Businesses", h2_style))
    story.append(Paragraph(findings_data.get("benchmark_narrative", ""), body_style))
    story.append(Spacer(1, 12))

    if benchmark.get("avg_rating") is not None:
        rating_chart = _make_comparison_chart(
            "Star Rating", float(benchmark.get("avg_rating") or 0), float(benchmark.get("top_quartile_rating") or 0), 5.0)
        story.append(Image(rating_chart, width=5.6 * inch, height=1.9 * inch))
        story.append(Spacer(1, 6))
    if benchmark.get("avg_reviews") is not None:
        review_max = max(float(benchmark.get("top_quartile_reviews") or 0), 1) * 1.2
        reviews_chart = _make_comparison_chart(
            "Review Count", float(benchmark.get("avg_reviews") or 0), float(benchmark.get("top_quartile_reviews") or 0), review_max)
        story.append(Image(reviews_chart, width=5.6 * inch, height=1.9 * inch))

    if benchmark.get("pct_with_website") is not None:
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"<b>{benchmark.get('pct_with_website')}%</b> of {lead['niche'] or 'similar'} businesses we've analyzed have a live website.",
            body_style))

    story.append(Paragraph("DETAILED FINDINGS", section_label_style))
    story.append(Paragraph("What We Found", h2_style))
    for f in findings_data.get("findings", [])[:3]:
        story.append(Paragraph(f.get("title", ""), finding_title_style))
        story.append(Paragraph(f.get("explanation", ""), body_style))

    story.append(PageBreak())

    # ---------------- PAGE 3: More findings + website technical ----------------
    remaining_findings = findings_data.get("findings", [])[3:]
    if remaining_findings:
        story.append(Paragraph("DETAILED FINDINGS (CONTINUED)", section_label_style))
        for f in remaining_findings:
            story.append(Paragraph(f.get("title", ""), finding_title_style))
            story.append(Paragraph(f.get("explanation", ""), body_style))

    if audit["has_website"]:
        story.append(Paragraph("WEBSITE TECHNICAL AUDIT", section_label_style))
        story.append(Paragraph("Google PageSpeed Insights Scores", h2_style))
        story.append(Paragraph(
            "Independently measured by Google's own PageSpeed Insights tool, the same technology behind Google Search rankings.",
            body_style))
        story.append(Spacer(1, 8))
        scores = {
            "Performance": audit["performance_score"],
            "SEO": audit["seo_score"],
            "Accessibility": audit["accessibility_score"],
            "Best Practices": audit["best_practices_score"],
        }
        chart_buf = _make_score_chart(scores)
        story.append(Image(chart_buf, width=5.6 * inch, height=2.3 * inch))
    else:
        story.append(Paragraph("WEBSITE TECHNICAL AUDIT", section_label_style))
        story.append(Paragraph("No Website Found", h2_style))
        story.append(Paragraph(
            "This business does not currently have a discoverable website, so no technical performance data is available. "
            "This is itself one of the most significant gaps identified in this report.",
            body_style))

    story.append(PageBreak())

    # ---------------- PAGE 4: Action plan ----------------
    story.append(Paragraph("THE PLAN", section_label_style))
    story.append(Paragraph("Prioritized Action Plan", h2_style))
    story.append(Paragraph(
        "Ranked by real impact on this business's specific gaps, starting with the highest-priority fix.",
        body_style))
    story.append(Spacer(1, 10))

    sorted_actions = sorted(action_plan, key=lambda a: a.get("priority", 99)) if action_plan else []
    for a in sorted_actions:
        row_table = Table(
            [[Paragraph(f"#{a.get('priority', '')}", ParagraphStyle("Num", fontSize=16, textColor=BLUE, fontName="Helvetica-Bold")),
              [Paragraph(a.get("action", ""), action_title_style), Paragraph(a.get("impact", ""), action_body_style)]]],
            colWidths=[0.5 * inch, 5.3 * inch],
        )
        row_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(row_table)

    story.append(Spacer(1, 16))
    story.append(Paragraph("THE OPPORTUNITY", section_label_style))
    story.append(Paragraph(findings_data.get("closing_recommendation", ""), body_style))

    story.append(Spacer(1, 24))
    cta_style = ParagraphStyle("CTA", parent=styles["Normal"], fontSize=11, textColor=colors.white,
                                backColor=NAVY, borderPadding=14, alignment=TA_CENTER, leading=15)
    story.append(Paragraph(
        f"Ready to fix these gaps? A specialist can implement this entire plan for {lead['business_name'] or 'this business'}.",
        cta_style))

    story.append(Spacer(1, 20))
    generated_str = audit["generated_at"].strftime("%B %d, %Y") if audit.get("generated_at") else ""
    story.append(Paragraph(
        f"Prepared by AutomationGini on {generated_str} &middot; Listing data via Google Places API &middot; "
        f"Technical scores via Google PageSpeed Insights &middot; Niche benchmarks from AutomationGini's own "
        f"database of verified local business listings.",
        footer_style,
    ))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=audit-{lead_id}.pdf"},
    )


def _table_style():
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])


def _page_footer(canvas_obj, doc_obj):
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(SLATE)
    canvas_obj.drawString(0.7 * inch, 0.4 * inch, "AutomationGini")
    canvas_obj.drawRightString(letter[0] - 0.7 * inch, 0.4 * inch, f"Page {doc_obj.page}")
    canvas_obj.restoreState()


def _make_comparison_chart(label: str, avg_value: float, top_value: float, max_scale: float) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6.2, 1.9))
    categories = ["Niche Average", "Top 25% in Niche"]
    values = [avg_value, top_value]
    bar_colors = ["#94a3b8", "#16a34a"]
    bars = ax.barh(categories, values, color=bar_colors, height=0.5)
    ax.set_xlim(0, max_scale if max_scale > 0 else 1)
    ax.invert_yaxis()
    for spine in ("top", "right", "bottom"):
        ax.spines[spine].set_visible(False)
    ax.set_xticks([])
    ax.set_title(label, fontsize=10, fontweight="bold", color="#1e293b", loc="left")
    for bar, v in zip(bars, values):
        ax.text(v + max_scale * 0.02, bar.get_y() + bar.get_height() / 2, f"{v:g}", va="center", fontsize=9, fontweight="bold")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf
