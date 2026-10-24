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
                36, 11 * inch - 26, "FAULTSENSE™ | Autonomous Fault Isolation & RCA Diagnostic Report"
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
    """Generates downloadable PDF and JSON artifacts from investigation records."""

    # Industrial color tokens
    PRIMARY_NAVY = colors.HexColor("#0A1120")
    DARK_CARD = colors.HexColor("#131F37")
    CYAN_ACCENT = colors.HexColor("#06B6D4")
    SKY_BLUE = colors.HexColor("#0284C7")
    BORDER_COLOR = colors.HexColor("#CBD5E1")
    LIGHT_BG = colors.HexColor("#F8FAFC")
    ALT_BG = colors.HexColor("#F1F5F9")
    TEXT_MAIN = colors.HexColor("#0F172A")
    TEXT_MUTED = colors.HexColor("#475569")
    VERIFIED_GREEN = colors.HexColor("#047857")
    AMBER_WARN = colors.HexColor("#B45309")
    RED_ALERT = colors.HexColor("#B91C1C")

    @classmethod
    def generate_pdf(
        cls,
        inv_data: Dict[str, Any],
        kb_manager: Optional[Any] = None,
    ) -> bytes:
        """Renders a comprehensive, publication-grade PDF diagnostic report."""
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
            fontSize=18,
            leading=22,
            textColor=cls.PRIMARY_NAVY,
        )

        h1_style = ParagraphStyle(
            "Heading1_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=cls.PRIMARY_NAVY,
            spaceBefore=10,
            spaceAfter=4,
        )

        h2_style = ParagraphStyle(
            "Heading2_Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=cls.SKY_BLUE,
            spaceBefore=6,
            spaceAfter=2,
        )

        body_style = ParagraphStyle(
            "Body_Custom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
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
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        table_cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=cls.TEXT_MAIN,
        )

        code_style = ParagraphStyle(
            "CodeCell",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=9.5,
            textColor=cls.SKY_BLUE,
        )

        alert_style = ParagraphStyle(
            "AlertCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=cls.RED_ALERT,
        )

        story = []

        # =========================================================================
        # 1. Header Banner & Branding
        # =========================================================================
        banner_content = [
            [
                Paragraph("<b>FAULT<font color='#06B6D4'>SENSE</font></b><br/><font size='8' color='#64748B'>ELEVATOR ROOT CAUSE ANALYSIS DOSSIER</font>", title_style),
                Paragraph(
                    f"<b>REPORT ID</b>: <font color='#0284C7'>{dossier.investigation_id}</font><br/>"
                    f"<b>DATE GENERATED</b>: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC<br/>"
                    f"<b>SPECIFICATION</b>: ASME A17.1-2022 / EN 81-20<br/>"
                    f"<b>CLASSIFICATION</b>: Non-Control Diagnostic Advisory",
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

        # =========================================================================
        # 2. Executive Summary & Verification Card
        # =========================================================================
        verif_color = cls.VERIFIED_GREEN if dossier.is_verified else cls.AMBER_WARN
        verif_text = "VERIFIED GROUNDED" if dossier.is_verified else "INCONCLUSIVE ADVISORY"

        summary_box = [
            [
                Paragraph("<b>INVESTIGATION TARGET</b>", table_header_style),
                Paragraph("<b>VERIFICATION STATUS</b>", table_header_style),
                Paragraph("<b>ADVISORY CONFIDENCE</b>", table_header_style),
                Paragraph("<b>DATA SUFFICIENCY</b>", table_header_style),
            ],
            [
                Paragraph(f"Unit: <b>{dossier.elevator_id}</b><br/>Subsystem: <b>{dossier.subsystem.replace('_', ' ').title()}</b><br/>DTC Code: <b>{dossier.fault_code or 'None'}</b><br/>Site: <b>{dossier.building_id}</b>", table_cell_style),
                Paragraph(f"<b><font color='{verif_color.hexval()}'>● {verif_text}</font></b><br/>{dossier.verification_explanation}", table_cell_style),
                Paragraph(f"<b><font size='12'>{int(dossier.confidence_score * 100)}%</font></b><br/>Evidence Affinity Index (Heuristic Match)", table_cell_style),
                Paragraph(f"Level: <b>{dossier.input_sufficiency}</b><br/>{dossier.data_quality_assessment}", table_cell_style),
            ]
        ]
        sum_table = Table(summary_box, colWidths=[2.0 * inch, 2.7 * inch, 1.4 * inch, 1.4 * inch])
        sum_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, 1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(sum_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # 3. Primary Root Cause Hypothesis & Immediate Action
        # =========================================================================
        story.append(Paragraph("1. Primary Root-Cause Synthesis & Next Action", h1_style))
        rc_box = [
            [
                Paragraph("<b>SYNTHESIZED PRIMARY CAUSE</b>", table_header_style),
                Paragraph("<b>RECOMMENDED IMMEDIATE ACTION</b>", table_header_style),
            ],
            [
                Paragraph(f"<b>{dossier.primary_root_cause}</b>", ParagraphStyle("RC_P", parent=body_style, fontSize=9, leading=12, textColor=cls.PRIMARY_NAVY)),
                Paragraph(f"{dossier.recommended_next_action}", ParagraphStyle("RC_Act", parent=body_style, fontSize=8.5, leading=11.5, textColor=cls.TEXT_MAIN)),
            ]
        ]
        rc_table = Table(rc_box, colWidths=[3.75 * inch, 3.75 * inch])
        rc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(rc_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # 4. Technician Reported Symptoms & Recorded Telemetry
        # =========================================================================
        story.append(Paragraph("2. Reported Symptoms & Physical Sensor Telemetry", h1_style))

        sym_text = "<br/>".join([f"• {s}" for s in dossier.symptoms]) or "No distinct symptoms reported."

        telemetry_rows = [
            [
                Paragraph("<b>Sensor Parameter</b>", table_header_style),
                Paragraph("<b>Value</b>", table_header_style),
                Paragraph("<b>Unit</b>", table_header_style),
                Paragraph("<b>Nominal Threshold</b>", table_header_style),
                Paragraph("<b>Telemetry Assessment</b>", table_header_style),
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
                Paragraph("-", table_cell_style),
                Paragraph("-", table_cell_style),
                Paragraph("-", table_cell_style),
                Paragraph("Baseline symptom matching only", table_cell_style),
            ])

        tel_table = Table(telemetry_rows, colWidths=[2.0 * inch, 1.0 * inch, 1.2 * inch, 1.6 * inch, 1.7 * inch])
        tel_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        symptom_table = Table([
            [Paragraph("<b>Reported Symptoms</b>", table_header_style)],
            [Paragraph(sym_text, table_cell_style)]
        ], colWidths=[7.5 * inch])
        symptom_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, 1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(symptom_table)
        story.append(Spacer(1, 4))
        story.append(tel_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # 5. Ranked Hypotheses & Traceable Case Citations
        # =========================================================================
        story.append(Paragraph("3. Ranked Probable Causes & Historical Evidence Precedents", h1_style))

        hypo_rows = [
            [
                Paragraph("<b>Rank</b>", table_header_style),
                Paragraph("<b>Hypothesis Title</b>", table_header_style),
                Paragraph("<b>Band</b>", table_header_style),
                Paragraph("<b>Supporting Citations</b>", table_header_style),
                Paragraph("<b>Detailed Engineering Explanation</b>", table_header_style),
            ]
        ]
        for c in dossier.ranked_causes[:3]:
            cites = ", ".join(c.get("supporting_case_ids", [])) or "None cited"
            band = c.get("probability_band", "possible").upper()
            hypo_rows.append([
                Paragraph(f"<b>#{c.get('rank', 1)}</b>", table_cell_style),
                Paragraph(f"<b>{c.get('hypothesis_title')}</b>", table_cell_style),
                Paragraph(f"<b>{band}</b>", table_cell_style),
                Paragraph(f"<code>{cites}</code>", code_style),
                Paragraph(c.get("explanation", ""), table_cell_style),
            ])

        hypo_table = Table(hypo_rows, colWidths=[0.5 * inch, 1.8 * inch, 0.9 * inch, 1.4 * inch, 2.9 * inch])
        hypo_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(hypo_table)
        story.append(Spacer(1, 8))

        # Historical Case Evidence Records Table
        if dossier.supporting_evidence:
            ev_rows = [
                [
                    Paragraph("<b>Case ID</b>", table_header_style),
                    Paragraph("<b>OEM Document Reference</b>", table_header_style),
                    Paragraph("<b>Confirmed Historical Cause</b>", table_header_style),
                    Paragraph("<b>Documented Corrective Action</b>", table_header_style),
                    Paragraph("<b>Provenance</b>", table_header_style),
                ]
            ]
            for ev in dossier.supporting_evidence:
                prov = "Verified Field" if not ev["is_synthetic"] else "Synthetic Benchmark"
                ev_rows.append([
                    Paragraph(f"<code>{ev['case_id']}</code>", code_style),
                    Paragraph(f"<b>{ev['source_title']}</b><br/><font color='#64748B'>{ev['source_reference']}</font>", table_cell_style),
                    Paragraph(ev["confirmed_root_cause"], table_cell_style),
                    Paragraph(ev["corrective_action"], table_cell_style),
                    Paragraph(prov, table_cell_style),
                ])
            ev_table = Table(ev_rows, colWidths=[1.3 * inch, 1.7 * inch, 2.0 * inch, 1.6 * inch, 0.9 * inch])
            ev_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
                ("BACKGROUND", (0, 1), (-1, -1), cls.ALT_BG),
                ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(ev_table)
            story.append(Spacer(1, 8))

        # =========================================================================
        # 6. Required Tools, Instruments & Equipment
        # =========================================================================
        story.append(Paragraph("4. Required Diagnostic Tools, Equipment & Safety Measures", h1_style))

        tool_rows = [
            [
                Paragraph("<b>Required Instrument / Tool</b>", table_header_style),
                Paragraph("<b>Purpose & Application</b>", table_header_style),
                Paragraph("<b>Why Needed for Suspected Fault</b>", table_header_style),
                Paragraph("<b>Safety Precautions During Use</b>", table_header_style),
            ]
        ]
        for t in dossier.required_tools:
            tool_rows.append([
                Paragraph(f"<b>{t.name}</b>", table_cell_style),
                Paragraph(t.purpose, table_cell_style),
                Paragraph(t.why_needed, table_cell_style),
                Paragraph(t.safety_precautions, table_cell_style),
            ])
        tool_table = Table(tool_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.9 * inch, 1.8 * inch])
        tool_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tool_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # 7. Step-by-Step Inspection Procedure & Recommended Parts
        # =========================================================================
        story.append(Paragraph("5. Step-by-Step Inspection Procedure & Parts Assessment", h1_style))

        insp_content = "<br/>".join([f"<b>Step {idx}</b>: {step}" for idx, step in enumerate(dossier.inspection_steps, 1)])
        story.append(Paragraph(insp_content, body_style))
        story.append(Spacer(1, 6))

        # Parts table
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
                Paragraph("Existing evidence indicates mechanical calibration, cleaning, or circuit continuity testing will resolve fault without part replacement.", table_cell_style),
                Paragraph("Physical verification pending", table_cell_style),
            ])

        part_table = Table(part_rows, colWidths=[2.2 * inch, 1.3 * inch, 2.5 * inch, 1.5 * inch])
        part_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.DARK_CARD),
            ("BACKGROUND", (0, 1), (-1, -1), cls.ALT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(part_table)
        story.append(Spacer(1, 6))

        # Downtime estimate callout
        de = dossier.downtime_estimate
        dt_text = (
            f"<b>Estimated Service Duration</b>: Total <b>{de.total_hours:.1f} hours</b> "
            f"(Diagnostic Inspection: {de.inspection_hours:.1f} hrs | Corrective Service: {de.service_hours:.1f} hrs). "
            f"<i>Basis: {de.defensible_basis}</i>"
        )
        story.append(Paragraph(dt_text, body_style))
        story.append(Spacer(1, 8))

        # =========================================================================
        # 8. Mandatory Safety Precautions & Escalation Criteria
        # =========================================================================
        story.append(Paragraph("6. Mandatory Safety Precautions & Escalation Protocols", h1_style))

        safety_items = "<br/>".join([f"⚠️ <b>SAFETY</b>: {s}" for s in dossier.safety_precautions])
        story.append(Paragraph(safety_items, ParagraphStyle("SafeP", parent=body_style, textColor=cls.RED_ALERT, leading=12)))
        story.append(Spacer(1, 6))

        esc_items = "<br/>".join([f"🚨 <b>ESCALATION</b>: {e}" for e in dossier.escalation_requirements])
        story.append(Paragraph(esc_items, ParagraphStyle("EscP", parent=body_style, textColor=cls.AMBER_WARN, leading=12)))
        story.append(Spacer(1, 8))

        # =========================================================================
        # 9. Return-to-Service Verification Checklist
        # =========================================================================
        story.append(Paragraph("7. Return-to-Service Acceptance Checklist (ASME A17.1)", h1_style))

        chk_rows = [
            [
                Paragraph("<b>#</b>", table_header_style),
                Paragraph("<b>Acceptance Test Title</b>", table_header_style),
                Paragraph("<b>Required Acceptance Criteria</b>", table_header_style),
                Paragraph("<b>Governing Safety Code</b>", table_header_style),
                Paragraph("<b>Technician Sign-Off</b>", table_header_style),
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
        chk_table = Table(chk_rows, colWidths=[0.3 * inch, 1.8 * inch, 3.2 * inch, 1.2 * inch, 1.0 * inch])
        chk_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), cls.PRIMARY_NAVY),
            ("BACKGROUND", (0, 1), (-1, -1), cls.LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 1, cls.BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, cls.BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(chk_table)
        story.append(Spacer(1, 8))

        # =========================================================================
        # 10. Known Limitations, Missing Data & Formal Advisory Disclaimer
        # =========================================================================
        story.append(KeepTogether([
            Paragraph("8. Known Limitations, Uncertainty & Regulatory Advisory Disclaimer", h1_style),
            Paragraph(
                "• <b>Missing Information</b>: " + "; ".join(dossier.missing_and_conflicting_evidence),
                body_style
            ),
            Paragraph(
                "• <b>Uncertainty Assessment</b>: " + "; ".join(dossier.uncertainty_notes),
                body_style
            ),
            Spacer(1, 6),
            Paragraph(
                "<b>REGULATORY DECISION SUPPORT NOTICE (ASME A17.1 / CSA B44 / EN 81)</b>:<br/>"
                "FaultSense is an offline-capable, evidence-grounded diagnostic support assistant designed strictly "
                "for use by licensed, certified elevator service mechanics and modernization engineers. "
                "FaultSense does NOT directly interface with, override, energize, or alter elevator safety circuits, "
                "relays, brake solenoids, or controller software. All safety interlocks and protective devices must be "
                "physically tested, calibrated, and confirmed compliant by qualified personnel adhering to ASME A17.1 "
                "Lockout/Tagout (LOTO) protocols prior to returning vertical transportation equipment to public service.",
                ParagraphStyle("LegalNotice", parent=body_style, fontSize=7, leading=9.5, textColor=cls.TEXT_MUTED)
            ),
        ]))

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
