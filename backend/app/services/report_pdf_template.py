"""
Module 9 — Academic Evaluation Report PDF Generator
===================================================
Renders structured PublicEvaluationReport data into a professional,
multi-page PDF using ReportLab with clean styling and tables.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict

log = logging.getLogger(__name__)


def generate_report_pdf(project_data: Dict[str, Any], report_data: Dict[str, Any]) -> bytes:
    """
    Generates a PDF binary stream from project and evaluation report dictionaries.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
    except ImportError:
        log.warning("reportlab not installed, generating plain text fallback")
        return _fallback_text_pdf(project_data, report_data)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_navy = colors.HexColor("#0f172a")
    c_teal = colors.HexColor("#0d9488")
    c_slate = colors.HexColor("#475569")
    c_light_slate = colors.HexColor("#f8fafc")
    c_border = colors.HexColor("#e2e8f0")
    c_gold = colors.HexColor("#d97706")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=c_navy,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=c_navy,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=c_slate,
    )
    bold_style = ParagraphStyle(
        "BoldText",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=c_navy,
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("<b>AcadEval+</b> Academic Evaluation Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')}", body_style))
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=c_teal, spaceAfter=14))

    # 2. Project Overview
    title = project_data.get("title", "Capstone Proposal")
    domain = project_data.get("domain", "General CSE")
    submission_type = project_data.get("submissionType", "Document").capitalize()
    overall_score = report_data.get("overallScore", 0.0)
    grade = report_data.get("grade", "N/A")

    info_data = [
        [Paragraph("<b>Project Title:</b>", body_style), Paragraph(title, bold_style)],
        [Paragraph("<b>Domain:</b>", body_style), Paragraph(domain, body_style)],
        [Paragraph("<b>Submission Mode:</b>", body_style), Paragraph(submission_type, body_style)],
        [Paragraph("<b>Overall Score:</b>", body_style), Paragraph(f"<b>{overall_score:.1f} / 100 (Grade {grade})</b>", bold_style)],
        [Paragraph("<b>Novelty Verdict:</b>", body_style), Paragraph(str(report_data.get("noveltyVerdict", "Pending")), body_style)],
        [Paragraph("<b>Feasibility:</b>", body_style), Paragraph(str(report_data.get("feasibilityRating", "Pending")), body_style)],
    ]
    info_table = Table(info_data, colWidths=[120, 410])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), c_light_slate),
        ("BOX", (0, 0), (-1, -1), 1, c_border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # 3. Dimension Scores Breakdown
    dim_scores = report_data.get("dimensionScores", {})
    if isinstance(dim_scores, dict):
        elements.append(Paragraph("Dimension Scores Breakdown", h2_style))
        dim_rows = [
            [Paragraph("<b>Evaluation Dimension</b>", bold_style), Paragraph("<b>Score</b>", bold_style), Paragraph("<b>Status</b>", bold_style)]
        ]
        labels = {
            "novelty": "Novelty & Originality",
            "feasibility": "Technical Feasibility",
            "completeness": "Proposal Completeness",
            "technicalDepth": "Technical Depth",
            "clarity": "Clarity & Readability",
            "similarityRisk": "Similarity Risk (Lower is better)",
            "publicationPotential": "Publication Potential",
        }
        for k, lbl in labels.items():
            val = dim_scores.get(k)
            val_str = f"{val:.1f}" if isinstance(val, (int, float)) else "N/A"
            status = "Strong" if isinstance(val, (int, float)) and val >= 75 else ("Satisfactory" if isinstance(val, (int, float)) and val >= 55 else "Needs Improvement")
            dim_rows.append([Paragraph(lbl, body_style), Paragraph(val_str, bold_style), Paragraph(status, body_style)])

        dim_table = Table(dim_rows, colWidths=[240, 100, 190])
        dim_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_light_slate),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(dim_table)
        elements.append(Spacer(1, 10))

    # 4. Strengths & Weaknesses
    strengths = report_data.get("strengths", [])
    weaknesses = report_data.get("weaknesses", [])
    if strengths or weaknesses:
        elements.append(Paragraph("Key Findings", h2_style))
        findings_data = []
        if strengths:
            findings_data.append([Paragraph("<b>Identified Strengths</b>", bold_style)])
            for s in strengths[:4]:
                findings_data.append([Paragraph(f"• {s}", body_style)])
        if weaknesses:
            findings_data.append([Paragraph("<b>Areas for Improvement</b>", bold_style)])
            for w in weaknesses[:4]:
                findings_data.append([Paragraph(f"• {w}", body_style)])

        if findings_data:
            find_table = Table(findings_data, colWidths=[530])
            find_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), c_light_slate),
                ("BOX", (0, 0), (-1, -1), 1, c_border),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(find_table)
            elements.append(Spacer(1, 10))

    # 5. Improvement Roadmap
    roadmap = report_data.get("improvementRoadmap", [])
    if roadmap:
        elements.append(Paragraph("Evidence-Based Improvement Roadmap", h2_style))
        rm_rows = [
            [Paragraph("<b>Phase / Week</b>", bold_style), Paragraph("<b>Focus Area & Recommended Actions</b>", bold_style)]
        ]
        for item in roadmap[:4]:
            week = item.get("week", 1)
            focus = item.get("focus", "")
            actions = item.get("actions", [])
            act_text = "<br/>".join([f"• {a}" for a in actions[:3]])
            desc = f"<b>{focus}</b><br/>{act_text}"
            rm_rows.append([Paragraph(f"Week {week}", bold_style), Paragraph(desc, body_style)])

        rm_table = Table(rm_rows, colWidths=[80, 450])
        rm_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), c_light_slate),
            ("GRID", (0, 0), (-1, -1), 0.5, c_border),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(rm_table)
        elements.append(Spacer(1, 10))

    # 6. GitHub Repository Analysis (if present)
    gh = report_data.get("githubAnalysis")
    if gh and isinstance(gh, dict) and gh.get("url"):
        elements.append(Paragraph("GitHub Repository Intelligence", h2_style))
        gh_data = [
            [Paragraph("<b>Repository:</b>", body_style), Paragraph(gh.get("url", ""), body_style)],
            [Paragraph("<b>Primary Language:</b>", body_style), Paragraph(str(gh.get("primaryLanguage") or gh.get("primary_language") or "N/A"), body_style)],
            [Paragraph("<b>License:</b>", body_style), Paragraph(str(gh.get("license") or "Not specified"), body_style)],
            [Paragraph("<b>Test Suite:</b>", body_style), Paragraph("Detected" if gh.get("hasTests") or gh.get("has_tests") else "None Detected", body_style)],
            [Paragraph("<b>Detected Stack:</b>", body_style), Paragraph(", ".join(gh.get("detectedStack") or gh.get("detected_stack") or []) or "N/A", body_style)],
        ]
        gh_table = Table(gh_data, colWidths=[120, 410])
        gh_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), c_light_slate),
            ("BOX", (0, 0), (-1, -1), 1, c_border),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(gh_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _fallback_text_pdf(project_data: Dict[str, Any], report_data: Dict[str, Any]) -> bytes:
    """Fallback text representation as bytes when reportlab is not available."""
    text = f"""ACADEVAL+ EVALUATION REPORT
===========================
Project: {project_data.get('title', 'Capstone Proposal')}
Domain: {project_data.get('domain', 'General')}
Overall Score: {report_data.get('overallScore', 0.0)} / 100 (Grade {report_data.get('grade', 'N/A')})
Novelty Verdict: {report_data.get('noveltyVerdict', 'Pending')}
Feasibility: {report_data.get('feasibilityRating', 'Pending')}

Dimension Scores:
{report_data.get('dimensionScores', {})}

Strengths:
{chr(10).join(['- ' + str(s) for s in report_data.get('strengths', [])])}

Weaknesses:
{chr(10).join(['- ' + str(w) for w in report_data.get('weaknesses', [])])}
"""
    return text.encode("utf-8")
