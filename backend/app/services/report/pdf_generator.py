"""
PDF Report Generator
====================
Produces a professional engineering report using ReportLab.

Sections:
  Cover         — scores, project meta
  Exec Summary  — key findings table
  Repo Overview — architecture, strengths
  Bugs          — per-issue cards
  Security      — per-vuln cards, OWASP mapping
  Docs          — grade, quick wins
  Action Items  — prioritised table
"""

import os
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor("#0f1117")
C_SURF    = colors.HexColor("#1a1d2e")
C_BRAND   = colors.HexColor("#4f6ef7")
C_TEXT    = colors.HexColor("#e2e8f0")
C_MUTED   = colors.HexColor("#64748b")
C_GREEN   = colors.HexColor("#22c55e")
C_YELLOW  = colors.HexColor("#eab308")
C_ORANGE  = colors.HexColor("#f97316")
C_RED     = colors.HexColor("#ef4444")
C_BORDER  = colors.HexColor("#2d3148")
C_WHITE   = colors.white

SEV_COLORS = {
    "critical": C_RED,
    "high":     C_ORANGE,
    "medium":   C_YELLOW,
    "low":      C_BRAND,
    "info":     C_MUTED,
}

W, H = A4


# ── Style factory ─────────────────────────────────────────────────────────────
def _S() -> dict:
    return {
        "cover_title": ParagraphStyle("cover_title",
            fontName="Helvetica-Bold", fontSize=26,
            textColor=C_WHITE, alignment=TA_CENTER, spaceAfter=8),
        "cover_sub": ParagraphStyle("cover_sub",
            fontName="Helvetica", fontSize=12,
            textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=4),
        "h1": ParagraphStyle("h1",
            fontName="Helvetica-Bold", fontSize=15,
            textColor=C_WHITE, spaceBefore=12, spaceAfter=6),
        "h2": ParagraphStyle("h2",
            fontName="Helvetica-Bold", fontSize=11,
            textColor=C_BRAND, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9,
            textColor=C_TEXT, leading=14, spaceAfter=4),
        "muted": ParagraphStyle("muted",
            fontName="Helvetica", fontSize=8,
            textColor=C_MUTED, leading=12),
        "code": ParagraphStyle("code",
            fontName="Courier", fontSize=8,
            textColor=C_GREEN, leading=11,
            backColor=C_SURF, leftIndent=6, rightIndent=6),
        "right": ParagraphStyle("right",
            fontName="Helvetica", fontSize=8,
            textColor=C_MUTED, alignment=TA_RIGHT),
        "center": ParagraphStyle("center",
            fontName="Helvetica-Bold", fontSize=9,
            textColor=C_TEXT, alignment=TA_CENTER),
    }


def _sev_color(sev: str) -> colors.Color:
    return SEV_COLORS.get(sev.lower(), C_MUTED)


def _sp(story, h=6):
    story.append(Spacer(1, h))


def _hr(story, color=C_BORDER):
    story.append(HRFlowable(width="100%", thickness=0.5, color=color, spaceAfter=8))


# ── Page callbacks ────────────────────────────────────────────────────────────
def _on_body_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(C_SURF)
    canvas.rect(0, H - 18*mm, W, 18*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(C_BRAND)
    canvas.drawString(15*mm, H - 11*mm, "AI Code Review Platform")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawRightString(W - 15*mm, H - 11*mm, f"Page {doc.page}  |  Confidential")
    # Footer bar
    canvas.setFillColor(C_SURF)
    canvas.rect(0, 0, W, 11*mm, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_MUTED)
    canvas.drawString(15*mm, 3.5*mm,
        "AI Code Review Platform  ·  Groq + LangGraph + ChromaDB")
    canvas.drawRightString(W - 15*mm, 3.5*mm,
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    canvas.restoreState()


def _on_cover_page(canvas, doc):
    canvas.saveState()
    # Full dark background
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Brand accent strip at top
    canvas.setFillColor(C_BRAND)
    canvas.rect(0, H - 8*mm, W, 8*mm, fill=1, stroke=0)
    canvas.restoreState()


# ── Score card ────────────────────────────────────────────────────────────────
def _score_card(sev: int, conf: int, health: int) -> Table:
    sev_color = C_RED if sev > 70 else C_YELLOW if sev > 40 else C_GREEN

    def block(label, val, col):
        return [
            Paragraph(f'<font size="30"><b>{val}</b></font>',
                ParagraphStyle("sv", fontName="Helvetica-Bold", fontSize=30,
                               textColor=col, alignment=TA_CENTER)),
            Paragraph(label,
                ParagraphStyle("sl", fontName="Helvetica", fontSize=8,
                               textColor=C_MUTED, alignment=TA_CENTER)),
        ]

    t = Table(
        [[block("SEVERITY", sev, sev_color),
          block("CONFIDENCE", conf, C_BRAND),
          block("HEALTH", health, C_GREEN)]],
        colWidths=[W * 0.25, W * 0.25, W * 0.25],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_SURF),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
    ]))
    return t


# ── Issue card ────────────────────────────────────────────────────────────────
def _issue_card(title, file_, sev, desc, fix, snippet,
                tag_label, tag_value, S) -> Table:
    col = _sev_color(sev)
    rows = []

    # Title row
    rows.append([
        Paragraph(f"<b>{title[:90]}</b>", S["body"]),
        Paragraph(f'<font color="#{col.hexval()[2:]}"><b>{sev.upper()}</b></font>',
                  S["right"]),
    ])
    # File
    rows.append([Paragraph(f"📄 {file_}", S["muted"]), Paragraph("")])
    # Tag
    if tag_label and tag_value:
        rows.append([
            Paragraph(f'<font color="#4f6ef7">{tag_label}: {tag_value}</font>',
                      S["muted"]),
            Paragraph(""),
        ])
    # Description
    rows.append([Paragraph(desc[:350], S["body"]), Paragraph("")])
    # Code snippet
    if snippet and snippet.strip():
        safe = snippet[:250].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        rows.append([Paragraph(safe, S["code"]), Paragraph("")])
    # Fix
    rows.append([Paragraph(f"💡 <b>Fix:</b> {fix[:250]}", S["body"]), Paragraph("")])

    t = Table(rows, colWidths=[W*0.70, W*0.14])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_SURF),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("LINEBELOW",     (0,-1),(-1,-1), 0.4, C_BORDER),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    return t


# ── Main entry ────────────────────────────────────────────────────────────────
def generate_pdf(report_data: dict[str, Any], output_path: str) -> str:
    """
    Generate a styled PDF report from agent output data.

    Args:
        report_data: Serialised Report dict from PostgreSQL
        output_path: Absolute path to write the PDF

    Returns:
        output_path
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    S = _S()

    # ── Unpack ────────────────────────────────────────────────────────────────
    repo    = report_data.get("repo_summary") or {}
    bugs    = report_data.get("bugs") or {}
    sec     = report_data.get("security_issues") or {}
    docs    = report_data.get("docs_suggestions") or {}
    final   = report_data.get("final_review") or {}
    sev_s   = report_data.get("severity_score", 0) or 0
    conf_s  = report_data.get("confidence_score", 0) or 0
    health  = (final.get("metrics_summary") or {}).get("overall_health_score", 0) or 0
    risk    = final.get("risk_assessment") or {}
    metrics = final.get("metrics_summary") or {}

    bug_issues = bugs.get("issues") or []
    vulns      = (sec.get("vulnerabilities") or [])
    actions    = (final.get("action_items") or [])

    # ── Doc setup ─────────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        output_path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=22*mm, bottomMargin=16*mm,
        title=f"Code Review — {repo.get('project_name','Report')}",
        author="AI Code Review Platform",
    )

    cover_frame = Frame(0, 0, W, H,
        leftPadding=25*mm, rightPadding=25*mm,
        topPadding=35*mm, bottomPadding=20*mm, id="cover")
    body_frame  = Frame(15*mm, 16*mm, W-30*mm, H-38*mm, id="body")

    doc.addPageTemplates([
        PageTemplate(id="Cover", frames=[cover_frame], onPage=_on_cover_page),
        PageTemplate(id="Body",  frames=[body_frame],  onPage=_on_body_page),
    ])

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("AI Code Review Platform", S["cover_sub"]))
    _sp(story, 16)
    story.append(Paragraph(repo.get("project_name","Code Review Report"), S["cover_title"]))
    _sp(story, 6)
    story.append(Paragraph(repo.get("purpose","Automated multi-agent analysis")[:120],
                           S["cover_sub"]))
    _sp(story, 28)
    story.append(_score_card(sev_s, conf_s, health))
    _sp(story, 20)

    # Meta grid
    meta = [
        ["Language",    repo.get("primary_language","—"),
         "Architecture", repo.get("architecture_style","—")],
        ["Complexity",  repo.get("complexity_assessment","—"),
         "Sec Posture",  sec.get("overall_security_posture","—")],
        ["Bugs Found",  str(len(bug_issues)),
         "Vulns Found",  str(len(vulns))],
        ["Doc Grade",   docs.get("overall_documentation_grade","—"),
         "Prod Ready",   risk.get("production_readiness","—")],
    ]
    mt = Table(meta, colWidths=[W*0.20, W*0.22, W*0.20, W*0.22])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_SURF),
        ("TEXTCOLOR",     (0,0),(0,-1),  C_MUTED),
        ("TEXTCOLOR",     (2,0),(2,-1),  C_MUTED),
        ("TEXTCOLOR",     (1,0),(1,-1),  C_TEXT),
        ("TEXTCOLOR",     (3,0),(3,-1),  C_TEXT),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica"),
        ("FONTNAME",      (1,0),(1,-1),  "Helvetica-Bold"),
        ("FONTNAME",      (3,0),(3,-1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
    ]))
    story.append(mt)
    _sp(story, 24)
    story.append(Paragraph(
        datetime.now(timezone.utc).strftime("Generated %B %d, %Y  at  %H:%M UTC"),
        S["muted"]))
    story.append(Paragraph(
        "Powered by Groq Llama 3.3  ·  LangGraph  ·  ChromaDB RAG",
        S["muted"]))

    # Switch to body template
    story.append(NextPageTemplate("Body"))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Executive Summary", S["h1"]))
    _hr(story)
    story.append(Paragraph(
        final.get("executive_summary","No summary available."), S["body"]))
    _sp(story, 8)

    # Key findings table
    kf = final.get("key_findings") or []
    if kf:
        story.append(Paragraph("Key Findings", S["h2"]))
        rows = [["Severity","Category","Finding"]]
        for f in kf[:10]:
            c = _sev_color(f.get("severity","info"))
            rows.append([
                Paragraph(f'<font color="#{c.hexval()[2:]}"><b>'
                          f'{f.get("severity","").upper()}</b></font>', S["muted"]),
                Paragraph(f.get("category",""), S["muted"]),
                Paragraph(f.get("finding","")[:120], S["body"]),
            ])
        kft = Table(rows, colWidths=[W*0.13, W*0.16, W*0.55])
        kft.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), C_BRAND),
            ("TEXTCOLOR",     (0,0),(-1,0), C_WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, C_SURF]),
            ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        story.append(kft)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # REPOSITORY OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Repository Overview", S["h1"]))
    _hr(story)

    ov = [
        ["Project",      repo.get("project_name","—")],
        ["Purpose",      (repo.get("purpose","—") or "")[:200]],
        ["Architecture", repo.get("architecture_style","—")],
        ["Languages",    ", ".join(repo.get("languages") or [])],
        ["Frameworks",   ", ".join(repo.get("frameworks") or [])],
        ["Complexity",   repo.get("complexity_assessment","—")],
        ["Entry Points", ", ".join(repo.get("entry_points") or [])[:120]],
        ["Notes",        (repo.get("architecture_notes","—") or "")[:200]],
    ]
    ovt = Table(ov, colWidths=[W*0.22, W*0.62])
    ovt.setStyle(TableStyle([
        ("TEXTCOLOR",     (0,0),(0,-1), C_MUTED),
        ("TEXTCOLOR",     (1,0),(1,-1), C_TEXT),
        ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0),(1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [C_BG, C_SURF]),
        ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    story.append(ovt)

    strengths = final.get("strengths") or []
    if strengths:
        _sp(story, 10)
        story.append(Paragraph("Codebase Strengths", S["h2"]))
        for s in strengths[:6]:
            story.append(Paragraph(f"✓  {s}", S["body"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # BUG DETECTION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph(f"Bug Detection — {len(bug_issues)} Issue(s)", S["h1"]))
    _hr(story)

    if bug_issues:
        story.append(Paragraph(
            f"Code Quality: <b>{bugs.get('overall_code_quality','—')}</b>  ·  "
            f"Testing Gaps: {(bugs.get('testing_gaps','—') or '')[:80]}",
            S["muted"]))
        _sp(story, 8)
        for bug in bug_issues[:15]:
            story.append(_issue_card(
                title=bug.get("title","Unknown Bug"),
                file_=bug.get("file","—"),
                sev=bug.get("severity","low"),
                desc=bug.get("description",""),
                fix=bug.get("suggested_fix",""),
                snippet=bug.get("code_snippet"),
                tag_label="Category",
                tag_value=bug.get("category",""),
                S=S,
            ))
            _sp(story, 4)
    else:
        story.append(Paragraph("✓ No bugs detected.", S["body"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECURITY REVIEW
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph(f"Security Review — {len(vulns)} Vulnerability/Vulnerabilities", S["h1"]))
    _hr(story)

    # Severity counts bar
    sc_data = [
        ["Critical","High","Medium","Low"],
        [str(sec.get("critical_count",0)), str(sec.get("high_count",0)),
         str(sec.get("medium_count",0)),   str(sec.get("low_count",0))],
    ]
    sct = Table(sc_data, colWidths=[W*0.18]*4)
    sct.setStyle(TableStyle([
        ("TEXTCOLOR",     (0,0),(0,0), C_RED),
        ("TEXTCOLOR",     (1,0),(1,0), C_ORANGE),
        ("TEXTCOLOR",     (2,0),(2,0), C_YELLOW),
        ("TEXTCOLOR",     (3,0),(3,0), C_BRAND),
        ("TEXTCOLOR",     (0,1),(-1,1), C_WHITE),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 9),
        ("FONTSIZE",      (0,1),(-1,1), 18),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("BACKGROUND",    (0,0),(-1,-1), C_SURF),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
    ]))
    story.append(sct)
    _sp(story, 10)

    if vulns:
        for v in vulns[:15]:
            story.append(_issue_card(
                title=v.get("title","Unknown Vulnerability"),
                file_=v.get("file","—"),
                sev=v.get("severity","low"),
                desc=v.get("description",""),
                fix=v.get("remediation",""),
                snippet=v.get("code_snippet"),
                tag_label=v.get("owasp_category",""),
                tag_value=v.get("owasp_name",""),
                S=S,
            ))
            _sp(story, 4)
    else:
        story.append(Paragraph("✓ No vulnerabilities detected.", S["body"]))

    secrets = sec.get("secrets_exposed") or []
    if secrets:
        _sp(story, 8)
        story.append(Paragraph("⚠️  Exposed Secrets / Credentials", S["h2"]))
        for s in secrets:
            story.append(Paragraph(f"• {s}", S["body"]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # DOCUMENTATION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Documentation Review", S["h1"]))
    _hr(story)

    dr = [
        ["Overall Grade",       docs.get("overall_documentation_grade","—")],
        ["README Score",        f"{docs.get('readme_score',0)}/100"],
        ["Docstring Coverage",  docs.get("docstring_coverage_estimate","—")],
    ]
    dt = Table(dr, colWidths=[W*0.28, W*0.56])
    dt.setStyle(TableStyle([
        ("TEXTCOLOR",     (0,0),(0,-1), C_MUTED),
        ("TEXTCOLOR",     (1,0),(1,-1), C_TEXT),
        ("FONTNAME",      (0,0),(0,-1), "Helvetica"),
        ("FONTNAME",      (1,0),(1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("BACKGROUND",    (0,0),(-1,-1), C_SURF),
        ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
    ]))
    story.append(dt)
    _sp(story, 10)

    qw = docs.get("quick_wins") or []
    if qw:
        story.append(Paragraph("Quick Wins", S["h2"]))
        for w in qw[:8]:
            story.append(Paragraph(f"⚡  {w}", S["body"]))

    improv = docs.get("readme_improvements") or []
    if improv:
        _sp(story, 8)
        story.append(Paragraph("README Improvements", S["h2"]))
        ir = [["Priority","Section","Suggestion"]]
        for i in improv[:10]:
            c = _sev_color(i.get("priority","low"))
            ir.append([
                Paragraph(f'<font color="#{c.hexval()[2:]}"><b>'
                          f'{i.get("priority","").upper()}</b></font>', S["muted"]),
                Paragraph(i.get("section",""), S["muted"]),
                Paragraph(i.get("suggestion","")[:120], S["body"]),
            ])
        irt = Table(ir, colWidths=[W*0.12, W*0.18, W*0.54])
        irt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), C_BRAND),
            ("TEXTCOLOR",     (0,0),(-1,0), C_WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, C_SURF]),
            ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        story.append(irt)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # ACTION ITEMS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Prioritised Action Items", S["h1"]))
    _hr(story)

    if actions:
        ar = [["#","Category","Effort","Impact","Action"]]
        for item in sorted(actions, key=lambda x: x.get("priority",99))[:20]:
            ar.append([
                str(item.get("priority","—")),
                item.get("category","—"),
                item.get("effort","—"),
                item.get("impact","—"),
                Paragraph(item.get("action","")[:160], S["body"]),
            ])
        at = Table(ar, colWidths=[W*0.05, W*0.14, W*0.09, W*0.09, W*0.47])
        at.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), C_BRAND),
            ("TEXTCOLOR",     (0,0),(-1,0), C_WHITE),
            ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),(-1,-1), 8),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, C_SURF]),
            ("GRID",          (0,0),(-1,-1), 0.3, C_BORDER),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("ALIGN",         (0,0),(3,-1), "CENTER"),
        ]))
        story.append(at)

    nxt = final.get("recommended_next_steps") or []
    if nxt:
        _sp(story, 14)
        story.append(Paragraph("Recommended Next Steps", S["h2"]))
        for i, step in enumerate(nxt[:7], 1):
            story.append(Paragraph(f"{i}.  {step}", S["body"]))

    _sp(story, 16)
    _hr(story, C_BRAND)
    story.append(Paragraph(
        "This report was generated automatically by the AI Code Review Platform "
        "using Groq Llama 3.3, LangGraph multi-agent orchestration, and ChromaDB RAG "
        "retrieval. All findings should be reviewed by a qualified engineer before remediation.",
        S["muted"]))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story)
    logger.info("PDF generated", path=output_path)
    return output_path