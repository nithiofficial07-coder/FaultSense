"""Professional PDF and JSON Diagnostic Report Generator for FaultSense.

Generates comprehensive, multi-page engineering reports adhering to
vertical transportation standards (ASME A17.1 / CSA B44 / EN 81).
Features custom vector branding, numbered page canvases, structured tables,
traceable evidence citations, required equipment, safety advisories, and audit trails.
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.diagnosis.diagnostic_enricher import DiagnosticDossier, DiagnosticEnricher


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' numbering and running headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(
                36, 11 * inch - 26, "FAULTSENSE™ | Autonomous Fault Isolation & Root Cause Analysis Report"
            )
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, 11 * inch - 30, 8.5 * inch - 36, 11 * inch - 30)

        # Running footer (all pages)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 36, 22, footer_text)
        disclaimer = "CONFIDENTIAL & ADVISORY — Qualified Elevator Technician Judgment Required — ASME A17.1 Compliant"
        self.drawString(36, 22, disclaimer)

        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(36, 32, 8.5 * inch - 36, 32)
        self.restoreState()


class DiagnosticReportGenerator:
    """Generates downloadable publication-grade PDF and JSON artifacts from investigation records."""

    # Industrial color tokens
    PRIMARY_NAVY = colors.HexColor("#243247")
    DARK_CARD = colors.HexColor("#1A2638")
    CYAN_ACCENT = colors.HexColor("#4169A8")
    SKY_BLUE = colors.HexColor("#4169A8")
    BORDER_COLOR = colors.HexColor("#E2E8F0")
    LIGHT_BG = colors.HexColor("#F6F8FB")
    ALT_BG = colors.HexColor("#F0F4F9")
    TEXT_MAIN = colors.HexColor("#243247")
    TEXT_MUTED = colors.HexColor("#68778D")
    VERIFIED_GREEN = colors.HexColor("#3F7D62")
    AMBER_WARN = colors.HexColor("#A8752B")
    RED_ALERT = colors.HexColor("#B84C4C")

    @classmethod
    def generate_pdf(
        cls,
        inv_data: Dict[str, Any],
        kb_manager: Optional[Any] = None,
    ) -> bytes:
        """Renders a comprehensive, publication-grade 8-section PDF diagnostic report."""
        dossier = DiagnosticEnricher.enrich_investigation(inv_data, kb_manager=kb_manager)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=38,
            bottomMargin=42,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=cls.PRIMARY_NAVY,
        )

        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=cls.PRIMARY_NAVY,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        )

        h2_style = ParagraphStyle(
            "Heading2_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=cls.SKY_BLUE,
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=True,
        )

        body_style = ParagraphStyle(
            "Body_Custom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=cls.TEXT_MAIN,
        )

        body_bold = ParagraphStyle(
            "Body_Bold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=cls.TEXT_MAIN,
        )

        code_style = ParagraphStyle(
            "CodeCell",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=cls.SKY_BLUE,
        )

        alert_style = ParagraphStyle(
            "AlertCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=cls.RED_ALERT,
        )

        subtle_style = ParagraphStyle(
            "SubtleText",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7,
            leading=9,
            textColor=cls.TEXT_MUTED,
        )

        story: List[Any] = []

        # =========================================================================
        # PAGE 1: COVER AND EXECUTIVE SUMMARY
        # =========================================================================

        # 1.1 Header Banner & Branding
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        banner_content = [
            [
                Paragraph("<b>FAULT<font color='#06B6D4'>SENSE</font>™</b><br/><font size='8' color='#64748B'>ELEVATOR ROOT CAUSE ANALYSIS &amp; TROUBLESHOOTING DOSSIER</font>", title_style),
                Paragraph(
                    f"<b>REPORT ID</b>: <font color='#0284C7'>{dossier.investigation_id}</font><br/>"
                    f"<b>DATE GENERATED</b>: {now_utc} UTC<br/>"
                    f"<b>SPECIFICATION</b>: ASME A17.1-2022 / CSA B44 / EN 81-20<br/>"
                    f"<b>CLASSIFICATION</b>: Non-Control Diagnostic Decision Support",
                    ParagraphStyle("MetaRight", parent=body_style, alignment=2, fontSize=7.5, leading=10),
                )
            ]
        ]
        banner_table = Table(banner_content, colWidths=[3.5 * inch, 4.0 * inch])
        banner_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(banner_table)
        story.append(HRFlowable(width="100%", thickness=2, color=cls.CYAN_ACCENT, spaceBefore=4, spaceAfter=8))

        # 1.2 Target Equipment & Context Card
        eq_box = [
            [
                Paragraph("<b>Elevator Unit Identifier</b>", table_header_style),
                Paragraph("<b>Manufacturer &amp; Model</b>", table_header_style),
                Paragraph("<b>Affected Subsystem</b>", table_header_style),
                Paragraph("<b>DTC Code / Severity</b>", table_header_style),
            ],
            [
                Paragraph(f"<b>{dossier.elevator_id}</b><br/><font color='#64748B'>Site: {dossier.building_id}</font>", table_cell_style),
                Paragraph(f"OEM: <b>{dossier.manufacturer}</b><br/>Model: <b>{dossier.equipment_model}</b>", table_cell_style),
                Paragraph(f"<b>{dossier.subsystem.replace('_', ' ').title()}</b>", table_cell_style),
                Paragraph(f"DTC: <code>{dossier.fault_code or 'None'}</code><br/>Severity: <b>{dossier.severity}</b>", table_cell_style),
            ]
        ]
        eq_table = Table(eq_box, colWidths=[1.8 * inch, 2.1 * inch, 1.8 * inch, 1.8 * inch])
        eq_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(eq_table)
        story.append(Spacer(1, 6))

        # 1.3 Executive Diagnostic Status & Data Sufficiency Card
        status_color = cls.VERIFIED_GREEN if "Verified" in dossier.evidence_based_status else cls.AMBER_WARN
        if "Limited" in dossier.evidence_based_status or "Awaiting" in dossier.evidence_based_status:
            status_color = cls.RED_ALERT

        status_box = [
            [
                Paragraph("<b>EVIDENCE-BASED DIAGNOSTIC STATUS</b>", table_header_style),
                Paragraph("<b>ADVISORY EVIDENCE AFFINITY</b>", table_header_style),
                Paragraph("<b>DATA SUFFICIENCY &amp; QUALITY</b>", table_header_style),
            ],
            [
                Paragraph(f"<b><font color='{status_color.hexval()}'>● {dossier.evidence_based_status.upper()}</font></b><br/><font color='#475569'>{dossier.verification_explanation}</font>", table_cell_style),
                Paragraph(f"<b><font size='13'>{int(dossier.confidence_score * 100)}%</font></b><br/><font color='#64748B'>Evidence Affinity Index<br/>(Empirical Match; Not Physical P(f))</font>", table_cell_style),
                Paragraph(f"Sufficiency: <b>{dossier.input_sufficiency}</b><br/>{dossier.data_quality_assessment}", table_cell_style),
            ]
        ]
        status_table = Table(status_box, colWidths=[3.2 * inch, 2.1 * inch, 2.2 * inch])
        status_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(status_table)
        story.append(Spacer(1, 6))

        # 1.4 Primary Root Cause Hypothesis Card
        rc_box = [
            [
                Paragraph("<b>PRIMARY ROOT CAUSE HYPOTHESIS</b>", table_header_style),
                Paragraph("<b>IMMEDIATE RECOMMENDED ACTION</b>", table_header_style),
            ],
            [
                Paragraph(f"<b>{dossier.primary_root_cause}</b>", ParagraphStyle("RC_P", parent=body_style, fontSize=8.5, leading=11, textColor=cls.PRIMARY_NAVY)),
                Paragraph(f"{dossier.recommended_next_action}", ParagraphStyle("RC_Act", parent=body_style, fontSize=8, leading=10.5, textColor=cls.TEXT_MAIN)),
            ]
        ]
        rc_table = Table(rc_box, colWidths=[3.75 * inch, 3.75 * inch])
        rc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(rc_table)
        story.append(Spacer(1, 6))

        # 1.5 Executive Summary & Urgency Statement
        exec_summary_text = (
            f"<b>EXECUTIVE ADVISORY NOTICE</b>: This dossier details autonomous fault isolation for elevator unit "
            f"<b>{dossier.elevator_id}</b> ({dossier.subsystem.replace('_', ' ').title()}) following reported anomaly: "
            f"<i>\"{dossier.problem_description}\"</i>. Evidence synthesis indicates primary root cause: "
            f"<b>{dossier.primary_root_cause}</b>. Operating severity is evaluated as <b>{dossier.severity}</b>. "
            f"Under ASME A17.1 / EN 81 safety protocols, this report provides decision support and does NOT "
            f"certify the elevator as safe. Certified field technicians must execute the manual inspection checklist "
            f"and physical return-to-service measurements detailed in Sections 5 and 7 prior to passenger release."
        )
        story.append(Paragraph(exec_summary_text, ParagraphStyle("ExecSum", parent=body_style, fontSize=7.5, leading=10, textColor=cls.TEXT_MUTED)))
        story.append(Spacer(1, 8))

        # Distinct Break to start Technical Analysis on Page 2
        story.append(PageBreak())

        # =========================================================================
        # SECTION 4: REPORTED PROBLEM, SYMPTOMS, AND ERROR CODES
        # =========================================================================
        story.append(Paragraph("4. Reported Problem, Observed Symptoms &amp; Error Codes", h1_style))

        # Reported description and symptoms
        sym_text = "<br/>".join([f"• {s}" for s in dossier.symptoms]) or "No discrete symptoms specified."
        prob_box = [
            [
                Paragraph("<b>Technician Problem Description &amp; Operating Conditions</b>", table_header_style),
                Paragraph("<b>Observed Operational Symptoms &amp; Fault Codes</b>", table_header_style),
            ],
            [
                Paragraph(
                    f"<b>Problem Description</b>:<br/>{dossier.problem_description}<br/><br/>"
                    f"<b>Operating Conditions</b>: {dossier.operating_conditions}<br/>"
                    f"<b>Severity Rating</b>: {dossier.severity}",
                    table_cell_style
                ),
                Paragraph(
                    f"<b>OEM Fault Code</b>: <code>{dossier.fault_code or 'None Reported'}</code><br/><br/>"
                    f"<b>Observed Symptoms</b>:<br/>{sym_text}",
                    table_cell_style
                ),
            ]
        ]
        prob_table = Table(prob_box, colWidths=[3.75 * inch, 3.75 * inch])
        prob_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(prob_table)
        story.append(Spacer(1, 6))

        # =========================================================================
        # SECTION 5: TELEMETRY AND DATA-QUALITY ANALYSIS
        # =========================================================================
        story.append(Paragraph("5. Telemetry &amp; Data-Quality Analysis", h1_style))
        telemetry_rows = [
            [
                Paragraph("<b>Sensor Parameter</b>", table_header_style),
                Paragraph("<b>Reading</b>", table_header_style),
                Paragraph("<b>Unit</b>", table_header_style),
                Paragraph("<b>Nominal Range</b>", table_header_style),
                Paragraph("<b>Engineering Evaluation</b>", table_header_style),
            ]
        ]
        if dossier.telemetry_readings:
            for t in dossier.telemetry_readings:
                telemetry_rows.append([
                    Paragraph(f"<b>{t['parameter']}</b>", table_cell_style),
                    Paragraph(f"<code>{t['value']}</code>", code_style),
                    Paragraph(t["unit"], table_cell_style),
                    Paragraph(t["nominal_range"], table_cell_style),
                    Paragraph(t["assessment"], table_cell_style),
                ])
        else:
            telemetry_rows.append([
                Paragraph("<i>No numerical sensor telemetry recorded for this session.</i>", table_cell_style),
                Paragraph("N/A", table_cell_style),
                Paragraph("-", table_cell_style),
                Paragraph("Baseline OEM Threshold", table_cell_style),
                Paragraph("Acoustic &amp; visual symptom matching only; physical wear limits unverified", table_cell_style),
            ])

        tel_table = Table(telemetry_rows, colWidths=[2.0 * inch, 1.0 * inch, 1.1 * inch, 1.6 * inch, 1.8 * inch], repeatRows=1)
        tel_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tel_table)
        story.append(Spacer(1, 6))

        # =========================================================================
        # SECTION 6: SUSPECTED ROOT CAUSE AND ALTERNATIVE HYPOTHESES
        # =========================================================================
        story.append(Paragraph("6. Suspected Root Cause &amp; Alternative Hypotheses", h1_style))
        rc_explanation = (
            f"<b>Primary Hypothesis Causality</b>: The diagnosed root cause (<b>{dossier.primary_root_cause}</b>) "
            f"directly accounts for observed symptoms. In elevator {dossier.subsystem.replace('_', ' ')} dynamics, "
            f"this anomaly triggers safety circuit interruptions or controller cycle timing timeouts without passenger obstruction. "
            f"Available telemetry and DTC ({dossier.fault_code or 'None'}) correlate with verified OEM failure modes."
        )
        story.append(Paragraph(rc_explanation, body_style))
        story.append(Spacer(1, 4))

        if dossier.alternative_causes:
            alt_rows = [
                [
                    Paragraph("<b>Rank</b>", table_header_style),
                    Paragraph("<b>Alternative Root Cause Hypothesis</b>", table_header_style),
                    Paragraph("<b>Likelihood</b>", table_header_style),
                    Paragraph("<b>Engineering Plausibility &amp; Boundary Conditions</b>", table_header_style),
                ]
            ]
            for ac in dossier.alternative_causes:
                alt_rows.append([
                    Paragraph(f"#{ac.get('rank', 2)}", table_cell_style),
                    Paragraph(f"<b>{ac.get('hypothesis_title', 'Alternative Cause')}</b>", table_cell_style),
                    Paragraph(ac.get("probability_band", "possible").upper(), table_cell_style),
                    Paragraph(ac.get("explanation", "Plausible secondary hypothesis under elevated cycle duty or thermal drift."), table_cell_style),
                ])
            alt_table = Table(alt_rows, colWidths=[0.5 * inch, 2.3 * inch, 1.0 * inch, 3.7 * inch], repeatRows=1)
            alt_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
                ("BACKGROUND", (0, 1), (-1, -1), cls.ALT_BG),
                ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(alt_table)
            story.append(Spacer(1, 8))

        # =========================================================================
        # SECTION 7: SUPPORTING EVIDENCE AND HISTORICAL CASE REFERENCES
        # =========================================================================
        story.append(Paragraph("7. Supporting Evidence &amp; Historical Case References", h1_style))

        if dossier.supporting_evidence:
            ev_rows = [
                [
                    Paragraph("<b>Case ID</b>", table_header_style),
                    Paragraph("<b>OEM Reference &amp; Title</b>", table_header_style),
                    Paragraph("<b>Confirmed Historical Cause</b>", table_header_style),
                    Paragraph("<b>Documented Corrective Action</b>", table_header_style),
                    Paragraph("<b>Provenance</b>", table_header_style),
                ]
            ]
            for ev in dossier.supporting_evidence:
                prov = "Verified Field" if not ev.get("is_synthetic") else "Synthetic Benchmark"
                ev_rows.append([
                    Paragraph(f"<code>{ev['case_id']}</code>", code_style),
                    Paragraph(f"<b>{ev.get('source_title', 'OEM Bulletin')}</b><br/><font color='#64748B'>{ev.get('source_reference', '')}</font>", table_cell_style),
                    Paragraph(ev.get("confirmed_root_cause", ""), table_cell_style),
                    Paragraph(ev.get("corrective_action", ""), table_cell_style),
                    Paragraph(prov, table_cell_style),
                ])
            ev_table = Table(ev_rows, colWidths=[1.2 * inch, 1.8 * inch, 1.9 * inch, 1.7 * inch, 0.9 * inch], repeatRows=1)
            ev_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
                ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(ev_table)
            story.append(Spacer(1, 6))

        # Evidence Gaps Callout
        gaps_text = "<br/>".join([f"<b>EVIDENCE GAP</b>: {g}" for g in dossier.evidence_gaps]) or "No critical evidence gaps detected."
        gaps_box = Table([
            [Paragraph("<b>Identified Evidence Gaps, Contradictions &amp; Missing Information</b>", table_header_style)],
            [Paragraph(gaps_text, ParagraphStyle("GapsP", parent=body_style, textColor=cls.AMBER_WARN, leading=10.5))]
        ], colWidths=[7.5 * inch])
        gaps_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(gaps_box)
        story.append(Spacer(1, 8))

        # =========================================================================
        # SECTION 8: REQUIRED TOOLS, INSTRUMENTS, AND PPE
        # =========================================================================
        story.append(Paragraph("8. Required Diagnostic Tools, Instruments &amp; PPE", h1_style))
        story.append(Paragraph(
            "The following instruments and personal protective equipment are mandatory for diagnosing and isolating this fault. "
            "Never perform physical troubleshooting without calibrated instruments and appropriate PPE.",
            subtle_style
        ))
        story.append(Spacer(1, 4))

        tool_rows = [
            [
                Paragraph("<b>Required Instrument / Tool</b>", table_header_style),
                Paragraph("<b>Purpose &amp; Application</b>", table_header_style),
                Paragraph("<b>Why Needed for this Investigation</b>", table_header_style),
                Paragraph("<b>Diagnostic Step</b>", table_header_style),
                Paragraph("<b>Safety &amp; PPE Measures</b>", table_header_style),
            ]
        ]
        for t in dossier.required_tools:
            tool_rows.append([
                Paragraph(f"<b>{t.name}</b>", table_cell_style),
                Paragraph(t.purpose, table_cell_style),
                Paragraph(t.why_needed, table_cell_style),
                Paragraph(f"<code>{t.inspection_step[:35]}</code>", code_style),
                Paragraph(t.safety_precautions, table_cell_style),
            ])
        tool_table = Table(tool_rows, colWidths=[1.6 * inch, 1.8 * inch, 1.7 * inch, 1.1 * inch, 1.3 * inch], repeatRows=1)
        tool_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tool_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # SECTION 9: DETAILED NUMBERED MANUAL TROUBLESHOOTING PROCEDURE
        # =========================================================================
        story.append(Paragraph("9. Detailed Numbered Manual Troubleshooting Procedure", h1_style))
        story.append(Paragraph(
            "Follow this sequential procedure strictly. Diagnostic inspection steps must be completed before performing corrective action. "
            "<b>DO NOT perform live electrical work without isolation. NEVER place jumpers across safety interlocks.</b>",
            ParagraphStyle("WarnSafetyIntro", parent=body_style, textColor=cls.RED_ALERT, leading=10.5)
        ))
        story.append(Spacer(1, 4))

        for step in dossier.troubleshooting_manual:
            type_color = cls.SKY_BLUE if step.step_type == "Diagnostic Inspection" else cls.CYAN_ACCENT
            step_box = [
                [
                    Paragraph(f"<b>STEP {step.step_number}: {step.title.upper()}</b>", table_header_style),
                    Paragraph(f"<b>CLASSIFICATION: {step.step_type.upper()}</b>", ParagraphStyle("ST_Type", parent=table_header_style, alignment=2)),
                ],
                [
                    Paragraph(
                        f"<b>Purpose</b>: {step.purpose}<br/>"
                        f"<b>Required Tools</b>: <code>{step.required_tools}</code><br/>"
                        f"<b>Inspection / Measurement</b>: {step.inspection_measurement}",
                        table_cell_style
                    ),
                    Paragraph(
                        f"<b>Expected Criterion</b>: <b>{step.expected_criterion}</b><br/>"
                        f"<b>Interpretation</b>: {step.interpretation}<br/>"
                        f"<b>Next Action</b>: {step.next_action}",
                        table_cell_style
                    ),
                ],
                [
                    Paragraph(f"<b>SAFETY WARNING &amp; STOP CONDITION</b>: {step.safety_precautions}", ParagraphStyle("StepWarn", parent=body_style, textColor=cls.RED_ALERT, fontSize=7, leading=9)),
                    Paragraph("<i>Verification: Technician measurement required</i>", subtle_style),
                ]
            ]
            step_table = Table(step_box, colWidths=[3.75 * inch, 3.75 * inch])
            step_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
                ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
                ("BACKGROUND", (0, 2), (-1, 2), cls.ALT_BG),
                ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(KeepTogether([step_table, Spacer(1, 5)]))

        story.append(Spacer(1, 4))

        # =========================================================================
        # SECTION 10: RECOMMENDED CORRECTIVE ACTIONS SUPPORTED BY EVIDENCE
        # =========================================================================
        story.append(Paragraph("10. Recommended Corrective Actions Supported by Evidence", h1_style))

        # Recommended Parts Table
        part_rows = [
            [
                Paragraph("<b>Component / Part Name</b>", table_header_style),
                Paragraph("<b>Classification</b>", table_header_style),
                Paragraph("<b>Engineering Justification</b>", table_header_style),
                Paragraph("<b>Evidence Basis</b>", table_header_style),
            ]
        ]
        if dossier.recommended_parts:
            for p in dossier.recommended_parts:
                part_rows.append([
                    Paragraph(f"<b>{p.part_name}</b>", table_cell_style),
                    Paragraph(p.part_type, table_cell_style),
                    Paragraph(p.justification, table_cell_style),
                    Paragraph(p.evidence_basis, table_cell_style),
                ])
        else:
            part_rows.append([
                Paragraph("<i>No immediate component replacement recommended.</i>", table_cell_style),
                Paragraph("N/A", table_cell_style),
                Paragraph("Existing evidence indicates mechanical cleaning, realignment, and terminal calibration will resolve fault without part replacement.", table_cell_style),
                Paragraph("Physical verification pending", table_cell_style),
            ])

        part_table = Table(part_rows, colWidths=[2.2 * inch, 1.3 * inch, 2.5 * inch, 1.5 * inch], repeatRows=1)
        part_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(part_table)
        story.append(Spacer(1, 5))

        # =========================================================================
        # SECTION 11: SAFETY INSTRUCTIONS AND STOP CONDITIONS
        # =========================================================================
        story.append(Paragraph("11. Safety Instructions &amp; Critical Stop Conditions", h1_style))
        safety_text = "<br/>".join([f"<b>MANDATORY SAFETY PROTOCOL</b>: {s}" for s in dossier.safety_precautions])
        esc_text = "<br/>".join([f"<b>MANDATORY STOP &amp; ESCALATION CONDITION</b>: {e}" for e in dossier.escalation_requirements])
        safety_box = Table([
            [Paragraph("<b>Jobsite Safety Precautions &amp; Critical Stop Conditions</b>", table_header_style)],
            [Paragraph(f"{safety_text}<br/><br/>{esc_text}", ParagraphStyle("SafeP", parent=body_style, leading=10))]
        ], colWidths=[7.5 * inch])
        safety_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(safety_box)
        story.append(Spacer(1, 6))

        # =========================================================================
        # SECTION 12: VERIFICATION CHECKLIST AND ACCEPTANCE CRITERIA
        # =========================================================================
        story.append(Paragraph("12. Verification Checklist &amp; Documented Acceptance Criteria", h1_style))

        chk_rows = [
            [
                Paragraph("<b>#</b>", table_header_style),
                Paragraph("<b>Acceptance Test Title</b>", table_header_style),
                Paragraph("<b>Required Acceptance Criteria</b>", table_header_style),
                Paragraph("<b>Governing Code</b>", table_header_style),
                Paragraph("<b>Technician Result</b>", table_header_style),
            ]
        ]
        for chk in dossier.return_to_service_checks:
            chk_rows.append([
                Paragraph(str(chk.step_number), table_cell_style),
                Paragraph(f"<b>{chk.title}</b>", table_cell_style),
                Paragraph(chk.acceptance_criterion, table_cell_style),
                Paragraph(chk.applicable_code, table_cell_style),
                Paragraph("[  ] PASS   [  ] FAIL", table_cell_style),
            ])
        chk_table = Table(chk_rows, colWidths=[0.3 * inch, 1.9 * inch, 3.1 * inch, 1.2 * inch, 1.0 * inch], repeatRows=1)
        chk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, -1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(chk_table)
        story.append(Spacer(1, 6))

        # Formal Technician Sign-Off & Closure Table
        tech_rev = inv_data.get("technician_review") or {}
        tech_name_val = tech_rev.get("technician_name") or "<br/><br/>________________________________"
        tech_cert_val = tech_rev.get("certification_number") or "<br/><br/>________________________________"
        tech_date_val = tech_rev.get("reviewed_at", "")[:19].replace("T", " ") if tech_rev.get("reviewed_at") else "<br/><br/>____ / ____ / 202__   __:__"
        tech_outcome_val = tech_rev.get("verification_outcome") or "<br/><br/>________________________________"

        sign_box = [
            [
                Paragraph("<b>Lead Certified Technician Name (Print)</b>", table_header_style),
                Paragraph("<b>License / Certification Number</b>", table_header_style),
                Paragraph("<b>Date &amp; Time (Local)</b>", table_header_style),
                Paragraph("<b>Physical Verification Outcome / Signature</b>", table_header_style),
            ],
            [
                Paragraph(f"<b>{tech_name_val}</b>", table_cell_style),
                Paragraph(f"<b>{tech_cert_val}</b>", table_cell_style),
                Paragraph(f"<b>{tech_date_val}</b>", table_cell_style),
                Paragraph(f"<b>{tech_outcome_val}</b>", table_cell_style),
            ]
        ]
        sign_table = Table(sign_box, colWidths=[2.0 * inch, 1.9 * inch, 1.6 * inch, 2.0 * inch])
        sign_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(sign_table)
        story.append(Spacer(1, 6))

        # =========================================================================
        # SECTION 13: UNRESOLVED ISSUES AND RECOMMENDED NEXT STEPS
        # =========================================================================
        story.append(Paragraph("13. Unresolved Issues, Outstanding Risks &amp; Recommended Next Steps", h1_style))
        de = dossier.downtime_estimate
        unresolved_text = (
            f"<b>Immediate Operational Next Action</b>: {dossier.recommended_next_action}<br/><br/>"
            f"<b>Estimated Service Effort</b>: Total <b>{de.total_hours:.1f} hours</b> "
            f"(Diagnostic Inspection: {de.inspection_hours:.1f} hrs | Corrective Service: {de.service_hours:.1f} hrs).<br/>"
            f"<b>Outstanding Risk Management</b>: Physical elevator safety circuits MUST remain de-energized until "
            f"qualified technicians physically complete the Section 12 verification checklist. If fault symptoms persist "
            f"after completing the Section 9 troubleshooting manual, escalate immediately per Section 11 stop conditions."
        )
        unres_box = Table([
            [Paragraph("<b>Outstanding Risks &amp; Actionable Next Steps</b>", table_header_style)],
            [Paragraph(unresolved_text, ParagraphStyle("UnresP", parent=body_style, leading=10.5))]
        ], colWidths=[7.5 * inch])
        unres_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(unres_box)
        story.append(Spacer(1, 8))

        # =========================================================================
        # SECTION 14: SOURCES, LIMITATIONS, AND SAFETY DISCLAIMER
        # =========================================================================
        disclaimer_block = [
            Paragraph("14. Sources, Traceability, Evidence Limitations &amp; Safety Disclaimer", h1_style),
            Paragraph(
                f"<b>Document References &amp; Case Citations</b>: "
                f"Knowledge Base Cases: {', '.join(inv_data.get('matched_case_ids', [])) or 'None cited'}; "
                f"Governing Standard: ASME A17.1-2022 / CSA B44 / EN 81-20. "
                f"Report Engine Version: FaultSense Core v2.4 (Enterprise RAG &amp; Self-Verification Engine). "
                f"Investigation Record ID: <code>{dossier.investigation_id}</code>.",
                body_style
            ),
            Spacer(1, 4),
            Paragraph(
                "<b>MANDATORY ASME A17.1 / EN 81 REGULATORY DECISION SUPPORT NOTICE</b>:<br/>"
                "FaultSense is an evidence-grounded diagnostic decision-support platform designed strictly for use by licensed, "
                "certified vertical transportation mechanics. FaultSense does NOT directly interface with, energize, override, "
                "or alter elevator safety circuits, operational relays, brake solenoids, or controller software. All safety interlocks "
                "and protective devices must be physically verified, measured, and confirmed compliant by qualified personnel adhering "
                "to ASME A17.1 Lockout/Tagout (LOTO) protocols prior to returning vertical transportation equipment to public passenger "
                "service. This advisory report does NOT certify the elevator as safe for public operation.",
                ParagraphStyle("LegalNotice", parent=body_style, fontSize=7, leading=9, textColor=cls.TEXT_MUTED)
            ),
        ]
        story.append(KeepTogether(disclaimer_block))

        # Build document with dynamic NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return buffer.getvalue()

    @classmethod
    def generate_json(
        cls,
        inv_data: Dict[str, Any],
        kb_manager: Optional[Any] = None,
    ) -> str:
        """Exports the complete structured diagnostic dossier as a formatted JSON string."""
        dossier = DiagnosticEnricher.enrich_investigation(inv_data, kb_manager=kb_manager)
        raw_dict = dossier.to_dict()
        raw_dict["export_timestamp"] = datetime.now(timezone.utc).isoformat()
        raw_dict["export_schema_version"] = "2.0.0"
        return json.dumps(raw_dict, indent=2)


__all__ = ["DiagnosticReportGenerator", "NumberedCanvas"]
