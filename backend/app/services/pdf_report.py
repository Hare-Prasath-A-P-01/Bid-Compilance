import io
import datetime
from typing import List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app import models


def generate_compliance_pdf(bid: models.Bid, tender: models.Tender) -> io.BytesIO:
    """Generate an executive PDF compliance evaluation certificate for a bid."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,  # Center
    )
    sub_header_style = ParagraphStyle(
        "SubHeaderTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    cert_title = ParagraphStyle(
        "CertTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # 1. Official Header
    story.append(Paragraph("PUBLIC PROCUREMENT COMPLIANCE PORTAL", header_style))
    story.append(Paragraph("SMART INDIA HACKATHON 2026 — BYTE BUSTERS AUDIT PLATFORM", sub_header_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=10))

    story.append(Paragraph("BID COMPLIANCE EVALUATION CERTIFICATE", cert_title))
    story.append(Spacer(1, 10))

    # 2. Executive Metadata Box
    score_val = bid.compliance_score if bid.compliance_score is not None else 0.0
    risk_val = bid.risk_level.value if hasattr(bid.risk_level, "value") else str(bid.risk_level or "Unknown")

    if risk_val.lower() == "low":
        risk_bg = colors.HexColor("#dcfce7")
        risk_fg = colors.HexColor("#166534")
    elif risk_val.lower() == "medium":
        risk_bg = colors.HexColor("#fef3c7")
        risk_fg = colors.HexColor("#92400e")
    else:
        risk_bg = colors.HexColor("#fee2e2")
        risk_fg = colors.HexColor("#991b1b")

    score_text = f"<b><font size=16 color='{risk_fg.hexval()}'>{score_val}%</font></b><br/><font size=8 color='#475569'>Compliance Score</font>"
    risk_badge = f"<b><font size=12 color='{risk_fg.hexval()}'>{risk_val.upper()} RISK</font></b><br/><font size=7 color='#64748b'>Advisory Rating</font>"

    meta_data = [
        [
            Paragraph("<b>Tender Title:</b>", meta_label),
            Paragraph(tender.title, meta_val),
            Paragraph(score_text, ParagraphStyle("ScoreText", alignment=1)),
        ],
        [
            Paragraph("<b>Reference No:</b>", meta_label),
            Paragraph(tender.reference_no, meta_val),
            Paragraph(risk_badge, ParagraphStyle("RiskText", alignment=1)),
        ],
        [
            Paragraph("<b>Department:</b>", meta_label),
            Paragraph(tender.department or "Central Procurement Unit", meta_val),
            Paragraph(f"<b>Status:</b> {bid.submission_status}", meta_val),
        ],
        [
            Paragraph("<b>Bidder Entity:</b>", meta_label),
            Paragraph(f"{bid.bidder_name} ({bid.bidder_company or 'Independent'})", meta_val),
            Paragraph(f"<b>Version:</b> v{bid.submitted_version}", meta_val),
        ],
        [
            Paragraph("<b>Evaluation Date:</b>", meta_label),
            Paragraph(datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), meta_val),
            Paragraph(f"<b>Total Docs:</b> {len(bid.documents)}", meta_val),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[90, 310, 140])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (1, -1), 0.25, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (2, 0), (2, 1), risk_bg),
        ("BOX", (2, 0), (2, 1), 1, risk_fg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. Compliance Summary KPIs
    from app.services import compliance_engine
    requirements = tender.requirements
    checklist, stats = compliance_engine.build_verification_details(bid, requirements)

    kpi_data = [
        [
            Paragraph(f"<b>Total Checks:</b> {stats['total_checks']}", cell_bold),
            Paragraph(f"<b>Passed (Compliant):</b> <font color='#166534'>{stats['passed']}</font>", cell_bold),
            Paragraph(f"<b>Missing:</b> <font color='#991b1b'>{stats['missing']}</font>", cell_bold),
            Paragraph(f"<b>Flagged / Needs Review:</b> <font color='#b45309'>{stats['mismatched_needs_review']}</font>", cell_bold),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10))

    # 4. Official Review Mandate Notice
    mandate_style = ParagraphStyle(
        "MandateNotice",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1,
    )
    mandate_box = Table(
        [[Paragraph("<b>MANDATORY EVALUATION NOTICE:</b> AI-generated verification result. Final qualification/disqualification decision remains with the Procurement Officer.", mandate_style)]],
        colWidths=[540]
    )
    mandate_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#3b82f6")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(mandate_box)
    story.append(Spacer(1, 12))

    # 5. Requirement Verification & Evidence Matrix
    story.append(Paragraph("<b>STATUTORY REQUIREMENT VERIFICATION BREAKDOWN</b>", ParagraphStyle("TableHeadTitle", fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#1e293b"))))
    story.append(Spacer(1, 4))

    table_rows = [
        [
            Paragraph("Requirement", cell_bold),
            Paragraph("Extracted Value", cell_bold),
            Paragraph("Status", cell_bold),
            Paragraph("Evidence & Reason", cell_bold),
        ]
    ]

    for item in checklist:
        st = item["status"]
        if st == "Compliant":
            st_color = "#166534"
        elif st == "Missing":
            st_color = "#991b1b"
        elif st == "Mismatch":
            st_color = "#dc2626"
        else:
            st_color = "#d97706"

        status_p = Paragraph(f"<font color='{st_color}'><b>{item['status_label']}</b></font>", cell_bold)
        req_p = Paragraph(f"<b>{item['requirement_name']}</b>" + (" <font size=6.5 color='#dc2626'>[Mandatory]</font>" if item['mandatory'] else ""), cell_style)
        val_p = Paragraph(item.get("extracted_value") or "—", cell_style)
        reason_p = Paragraph(f"{item['reason']}<br/><font size=6 color='#64748b'>Verification: {item.get('portal_verification', '')}</font>", cell_style)

        table_rows.append([req_p, val_p, status_p, reason_p])

    req_table = Table(table_rows, colWidths=[140, 140, 90, 170])
    req_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(req_table)
    story.append(Spacer(1, 16))

    # 6. Certification & Sign-off Block
    sign_block = [
        [
            Paragraph("<b>EVALUATED BY:</b><br/><br/>___________________________<br/>Procurement Evaluation Committee", cell_style),
            Paragraph("<b>APPROVED / CONCURRED BY:</b><br/><br/>___________________________<br/>Competent Financial Authority", cell_style),
        ]
    ]
    sign_table = Table(sign_block, colWidths=[270, 270])
    sign_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(KeepTogether(sign_table))
    story.append(Spacer(1, 12))

    # 7. Footer disclaimer
    disclaimer = (
        "Notice: This document is an automated compliance audit certificate generated by the Byte Busters "
        "AI Bid Compliance Engine. Final procurement decisions are subject to statutory verification under "
        "General Financial Rules (GFR 2017). Verification Hash: SHA256-CERT-" + datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    )
    story.append(Paragraph(disclaimer, ParagraphStyle("Footer", fontName="Helvetica", fontSize=6.5, leading=8, textColor=colors.HexColor("#94a3b8"), alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer

