"""Diagnostic Dossier Enricher for vertical transportation systems.

Maps investigated subsystem, symptoms, telemetry, and evidence package into complete,
grounded technician dossiers with required tools, safety precautions, parts,
downtime estimates, and verification acceptance criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolRequirement:
    """A required instrument or tool for diagnosing or verifying elevator faults."""
    name: str
    purpose: str
    why_needed: str
    inspection_step: str
    safety_precautions: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "purpose": self.purpose,
            "why_needed": self.why_needed,
            "inspection_step": self.inspection_step,
            "safety_precautions": self.safety_precautions,
        }


@dataclass
class PartRecommendation:
    """A recommended replacement part supported by telemetry wear thresholds or damage."""
    part_name: str
    part_type: str
    justification: str
    evidence_basis: str
    is_immediate_replacement: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_name": self.part_name,
            "part_type": self.part_type,
            "justification": self.justification,
            "evidence_basis": self.evidence_basis,
            "is_immediate_replacement": self.is_immediate_replacement,
        }


@dataclass
class DowntimeEstimate:
    """Defensible estimate of technician troubleshooting and repair effort."""
    inspection_hours: float
    service_hours: float
    total_hours: float
    defensible_basis: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inspection_hours": self.inspection_hours,
            "service_hours": self.service_hours,
            "total_hours": self.total_hours,
            "defensible_basis": self.defensible_basis,
        }


@dataclass
class VerificationCheck:
    """Specific acceptance criterion a certified technician must verify before release."""
    step_number: int
    title: str
    acceptance_criterion: str
    applicable_code: str
    safety_advisory: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "acceptance_criterion": self.acceptance_criterion,
            "applicable_code": self.applicable_code,
            "safety_advisory": self.safety_advisory,
        }


@dataclass
class TroubleshootingStep:
    """A detailed manual troubleshooting step adhering to ASME A17.1 engineering protocols."""
    step_number: int
    title: str
    step_type: str  # "Diagnostic Inspection" vs "Corrective Action"
    purpose: str
    required_tools: str
    inspection_measurement: str
    expected_criterion: str
    interpretation: str
    next_action: str
    safety_precautions: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "step_type": self.step_type,
            "purpose": self.purpose,
            "required_tools": self.required_tools,
            "inspection_measurement": self.inspection_measurement,
            "expected_criterion": self.expected_criterion,
            "interpretation": self.interpretation,
            "next_action": self.next_action,
            "safety_precautions": self.safety_precautions,
        }


@dataclass
class DiagnosticDossier:
    """Comprehensive 18-point diagnostic dossier fulfilling Phase 4 & Phase 5 requirements."""
    investigation_id: str
    incident_summary: str
    elevator_id: str
    building_id: str
    subsystem: str
    fault_code: Optional[str]
    symptoms: List[str]
    telemetry_readings: List[Dict[str, Any]]
    data_quality_assessment: str
    input_sufficiency: str
    primary_root_cause: str
    ranked_causes: List[Dict[str, Any]]
    supporting_evidence: List[Dict[str, Any]]
    missing_and_conflicting_evidence: List[str]
    uncertainty_notes: List[str]
    inspection_steps: List[str]
    required_tools: List[ToolRequirement]
    recommended_parts: List[PartRecommendation]
    downtime_estimate: DowntimeEstimate
    safety_precautions: List[str]
    escalation_requirements: List[str]
    return_to_service_checks: List[VerificationCheck]
    verification_status: str
    verification_explanation: str
    recommended_next_action: str
    confidence_score: float
    is_verified: bool
    manufacturer: str = "Unspecified / Generic"
    equipment_model: str = "Unspecified"
    problem_description: str = ""
    operating_conditions: str = "Standard Operational Range"
    severity: str = "Medium"
    evidence_based_status: str = "Requires Technician Verification"
    troubleshooting_manual: List[TroubleshootingStep] = field(default_factory=list)
    alternative_causes: List[Dict[str, Any]] = field(default_factory=list)
    evidence_gaps: List[str] = field(default_factory=list)
    recommended_diagnostic_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "incident_summary": self.incident_summary,
            "elevator_id": self.elevator_id,
            "building_id": self.building_id,
            "subsystem": self.subsystem,
            "fault_code": self.fault_code,
            "symptoms": self.symptoms,
            "telemetry_readings": self.telemetry_readings,
            "data_quality_assessment": self.data_quality_assessment,
            "input_sufficiency": self.input_sufficiency,
            "primary_root_cause": self.primary_root_cause,
            "ranked_causes": self.ranked_causes,
            "supporting_evidence": self.supporting_evidence,
            "missing_and_conflicting_evidence": self.missing_and_conflicting_evidence,
            "uncertainty_notes": self.uncertainty_notes,
            "inspection_steps": self.inspection_steps,
            "required_tools": [t.to_dict() for t in self.required_tools],
            "recommended_parts": [p.to_dict() for p in self.recommended_parts],
            "downtime_estimate": self.downtime_estimate.to_dict(),
            "safety_precautions": self.safety_precautions,
            "escalation_requirements": self.escalation_requirements,
            "return_to_service_checks": [c.to_dict() for c in self.return_to_service_checks],
            "verification_status": self.verification_status,
            "verification_explanation": self.verification_explanation,
            "recommended_next_action": self.recommended_next_action,
            "confidence_score": self.confidence_score,
            "is_verified": self.is_verified,
            "manufacturer": self.manufacturer,
            "equipment_model": self.equipment_model,
            "problem_description": self.problem_description,
            "operating_conditions": self.operating_conditions,
            "severity": self.severity,
            "evidence_based_status": self.evidence_based_status,
            "troubleshooting_manual": [t.to_dict() for t in self.troubleshooting_manual],
            "alternative_causes": self.alternative_causes,
            "evidence_gaps": self.evidence_gaps,
            "recommended_diagnostic_checks": self.recommended_diagnostic_checks,
        }


class DiagnosticEnricher:
    """Enriches raw diagnostic reports and database records with domain engineering context."""

    # Subsystem specific tool registries
    _TOOL_REGISTRY: Dict[str, List[ToolRequirement]] = {
        "door_system": [
            ToolRequirement(
                name="Digital Multimeter (CAT III 600V)",
                purpose="Measure DC door operator drive voltages and door interlock contact loop continuity.",
                why_needed="Verifies whether door reopened due to low operator bus voltage or intermittent interlock drop.",
                inspection_step="Step 1: Probe door operator terminal block (pins 3 & 4) during active door open/close cycle.",
                safety_precautions="Verify meter test leads are rated CAT III; perform one-hand measurement rule."
            ),
            ToolRequirement(
                name="Feeler Gauge & Track Alignment Rule",
                purpose="Measure door sill track groove clearance and door hanger roller eccentric gap.",
                why_needed="Detects mechanical binding, debris accumulation, or misaligned sill guides.",
                inspection_step="Step 2: Sweep car and landing door sill grooves along full car travel width.",
                safety_precautions="Mechanically lock doors open; car must remain level at landing."
            ),
            ToolRequirement(
                name="Infrared Optical Lux / Attenuation Tester",
                purpose="Test infrared optical curtain beam array attenuation and transmitter alignment.",
                why_needed="Quantifies optical signal degradation caused by dirt, haze, or physical bracket displacement.",
                inspection_step="Step 3: Measure optical curtain receiver output voltage at 0%, 50%, and 100% door opening span.",
                safety_precautions="Keep hands and clothing clear of door drive belts during cycling."
            ),
            ToolRequirement(
                name="Kinetic Energy Force Gauge",
                purpose="Verify door closing force adheres to ASME A17.1 Rule 2.13.4.2 (< 30 lbf / 133 N).",
                why_needed="Ensures door operator torque limiter is properly calibrated to prevent passenger entrapment or impact.",
                inspection_step="Step 4: Place gauge at 1/3 and 2/3 door travel point during closing stroke.",
                safety_precautions="Stand outside door line of fire; do not use body parts to test closing force."
            ),
        ],
        "traction_drive": [
            ToolRequirement(
                name="True-RMS Clamp Meter & Portable Oscilloscope",
                purpose="Measure 3-phase motor stator current balance and inverter DC bus ripple voltage.",
                why_needed="Isolates regenerative overvoltage spikes, braking chopper failures, or phase unbalance.",
                inspection_step="Step 1: Clamp onto inverter output lines (U, V, W) during rated acceleration and deceleration.",
                safety_precautions="Wear NFPA 70E Category 2 arc flash face shield when opening 480V machine room cabinet."
            ),
            ToolRequirement(
                name="Digital Insulation Resistance Tester (Megohmmeter)",
                purpose="Test traction motor winding insulation resistance at 500V/1000V DC.",
                why_needed="Detects breakdown of motor winding insulation or moisture ingress in brake coil stator.",
                inspection_step="Step 2: Disconnect VFD inverter output terminals before performing 1-minute megger test.",
                safety_precautions="Perform Lockout/Tagout (LOTO) on mainline disconnect; discharge motor windings to ground."
            ),
            ToolRequirement(
                name="Laser Tachometer & Stroboscope",
                purpose="Measure motor encoder shaft RPM versus sheave rotational velocity.",
                why_needed="Detects mechanical coupling slip between motor armature and high-resolution pulse encoder.",
                inspection_step="Step 3: Affix reflective tape to motor shaft and measure RPM during express contract speed run.",
                safety_precautions="Maintain at least 12 inches safe clearance from rotating sheaves and ropes."
            ),
        ],
        "braking_system": [
            ToolRequirement(
                name="Precision Metric Feeler Gauge Set",
                purpose="Measure electromechanical brake shoe air gap (nominal 0.15 mm - 0.25 mm).",
                why_needed="Excess air gap causes delayed brake lift and premature contact wear; tight air gap causes drag.",
                inspection_step="Step 1: Measure clearance around 4 perimeter quadrants of both left and right brake arms.",
                safety_precautions="Confirm car is counterbalanced and empty; never release brake manually while unmonitored."
            ),
            ToolRequirement(
                name="Digital Vernier Caliper & Depth Micrometer",
                purpose="Measure brake lining thickness against OEM minimum allowable wear discard limit.",
                why_needed="Ensures friction material has not worn down to rivet heads, preventing drum scoring.",
                inspection_step="Step 2: Measure lining thickness at 6 distinct points across the shoe arc.",
                safety_precautions="Wear safety glasses and dust mask when inspecting friction material."
            ),
            ToolRequirement(
                name="Four-Wire Precision Micro-ohmmeter",
                purpose="Measure brake solenoid coil winding resistance and detect inter-turn shorts.",
                why_needed="Cold/hot coil resistance discrepancies confirm thermal breakdown or open coil circuits.",
                inspection_step="Step 3: Measure brake coil resistance at ambient machine room temperature (20°C reference).",
                safety_precautions="De-energize brake power supply; verify zero voltage before connecting Kelvin clips."
            ),
        ],
        "hoistway_signaling": [
            ToolRequirement(
                name="Dual-Channel Digital Storage Oscilloscope",
                purpose="Monitor encoder quadrature channels A and B pulse trains and 90° phase shift.",
                why_needed="Verifies pulse dropouts, jitter, or optical disk contamination causing floor leveling error.",
                inspection_step="Step 1: Probe encoder signal harness at controller input card during car leveling approach.",
                safety_precautions="Use 10:1 insulated probe tips to prevent shorting adjacent controller terminal pins."
            ),
            ToolRequirement(
                name="Hoistway Magnetic/Optical Tape Reader Alignment Jig",
                purpose="Verify reader head clearance and axial alignment relative to hoistway perforated tape.",
                why_needed="Vibration during high-speed transit can cause reader head rub or missed position vanes.",
                inspection_step="Step 2: Run car on top-of-car inspection speed and inspect tape reader guide rollers.",
                safety_precautions="Operate strictly from car top inspection station with emergency stop button engaged."
            ),
        ],
        "hydraulic_system": [
            ToolRequirement(
                name="Calibrated Hydraulic Pressure Gauge (0-3000 PSI / 0-200 Bar)",
                purpose="Measure static, running, and bypass relief valve pressure settings.",
                why_needed="Identifies worn pump impellers, relief valve drift, or proportional down-valve contamination.",
                inspection_step="Step 1: Connect gauge to hydraulic power unit test port and cycle car under contract load.",
                safety_precautions="Relieve all reservoir static pressure prior to loosening hydraulic test port plugs."
            ),
            ToolRequirement(
                name="Hydraulic Fluid Viscosity & Particle Patch Test Kit",
                purpose="Check hydraulic oil viscosity, water contamination, and particulate ISO cleanliness code.",
                why_needed="Contaminated oil causes proportional valve seat sticking and irregular car descent speeds.",
                inspection_step="Step 2: Draw 100 mL fluid sample from reservoir return line under warm operating conditions.",
                safety_precautions="Wear nitrile chemical-resistant gloves and splash goggles; hydraulic oil may be hot."
            ),
        ],
        "safety_gear": [
            ToolRequirement(
                name="Mechanical Over-Speed Trip Calibration Kit",
                purpose="Validate centrifugal flyweight governor electrical switch trip and mechanical jaw clamping speeds.",
                why_needed="Ensures governor activates electrical safety circuit before mechanical wedge engagement.",
                inspection_step="Step 1: Drive governor wheel via calibration motor and measure tripping RPM with digital tachometer.",
                safety_precautions="Car must be parked on inspection service with hoistway cleared of all personnel."
            ),
            ToolRequirement(
                name="Guide Rail Caliper & Wedge Penetration Depth Gauge",
                purpose="Measure guide rail blade thickness and safety wedge mark penetration depth.",
                why_needed="Confirms safety gear mechanical jaws bite evenly without gouging or twisting guide rails.",
                inspection_step="Step 2: Inspect guide rail surface at safety application point; measure bite depth.",
                safety_precautions="Ensure car is tethered and suspended safely by hoist ropes prior to wedge release."
            ),
        ],
    }

    _DEFAULT_TOOLS = [
        ToolRequirement(
            name="Digital Multimeter (CAT III 600V)",
            purpose="Measure circuit voltages, control signal levels, and safety circuit continuity.",
            why_needed="Baseline diagnostic verification of electrical subsystems.",
            inspection_step="Step 1: Check power supply rails and safety contact voltage drops.",
            safety_precautions="Follow electrical safety protocols and use calibrated insulated test leads."
        ),
        ToolRequirement(
            name="Mechanical Inspection Kit & Vernier Calipers",
            purpose="Inspect clearances, mechanical linkages, fasteners, and alignment.",
            why_needed="Detects mechanical play, binding, or wear beyond OEM service specifications.",
            inspection_step="Step 2: Inspect subsystem mounting hardware and moving assemblies.",
            safety_precautions="Ensure car is stationary and control switch in STOP position."
        ),
    ]

    @classmethod
    def enrich_investigation(
        cls,
        inv_data: Dict[str, Any],
        kb_manager: Optional[Any] = None,
    ) -> DiagnosticDossier:
        """Constructs an exhaustive DiagnosticDossier from saved investigation record."""
        inv_id = inv_data.get("investigation_id", "INV-UNKNOWN")
        elv_id = inv_data.get("elevator_id", "UNKNOWN")
        building = inv_data.get("building_id") or "Unspecified Job Site"
        subsystem = str(inv_data.get("subsystem", "door_system")).lower().strip()
        fault_code = inv_data.get("fault_code")
        symptoms = inv_data.get("symptoms", [])
        if isinstance(symptoms, str):
            symptoms = [symptoms]
        telemetry = inv_data.get("telemetry", {})
        if not isinstance(telemetry, dict):
            telemetry = {}

        diag_report = inv_data.get("diagnostic_report") or {}
        verif_rec = inv_data.get("verification_record") or {}
        status = inv_data.get("status", "open")
        conf_score = float(inv_data.get("confidence_score", 0.50))
        root_cause = inv_data.get("root_cause_hypothesis") or diag_report.get("summary") or "Under investigation."

        # 1. Telemetry readings with units and interpretation
        telemetry_items: List[Dict[str, Any]] = []
        for k, v in telemetry.items():
            unit, nominal = cls._infer_telemetry_unit(k)
            assessment = cls._assess_telemetry_reading(k, v)
            telemetry_items.append({
                "parameter": k.replace("_", " ").title(),
                "raw_key": k,
                "value": v,
                "unit": unit,
                "nominal_range": nominal,
                "assessment": assessment,
            })

        # 2. Data quality & input sufficiency assessment
        data_quality = cls._assess_data_quality(fault_code, symptoms, telemetry)
        sufficiency_level = diag_report.get("sufficiency_level") or ("high" if (fault_code and telemetry and symptoms) else "moderate")

        # 3. Ranked causes
        ranked_causes: List[Dict[str, Any]] = []
        if diag_report.get("candidate_causes"):
            for c in diag_report["candidate_causes"]:
                ranked_causes.append(c)
        else:
            ranked_causes.append({
                "rank": 1,
                "hypothesis_title": root_cause,
                "subsystem": subsystem,
                "probability_band": "likely" if conf_score >= 0.7 else "possible",
                "explanation": f"Synthesized based on observed symptoms ({', '.join(symptoms[:2])}) and matching OEM advisories.",
                "supporting_case_ids": inv_data.get("matched_case_ids", []),
                "recommended_checks": [f"Inspect {subsystem.replace('_', ' ')} components and wiring."],
                "documented_corrective_actions": [inv_data.get("recommended_actions") or "Clean and calibrate subsystem."],
            })

        # 4. Historical evidence cases
        supporting_evidence: List[Dict[str, Any]] = []
        matched_ids = inv_data.get("matched_case_ids", [])
        if kb_manager and hasattr(kb_manager, "repo"):
            for cid in matched_ids:
                case = kb_manager.repo.get(cid)
                if case:
                    supporting_evidence.append({
                        "case_id": case.case_id,
                        "source_title": case.source_title,
                        "source_reference": case.source_reference,
                        "subsystem": case.subsystem,
                        "fault_code": case.fault_code,
                        "confirmed_root_cause": case.confirmed_root_cause,
                        "corrective_action": case.corrective_action,
                        "is_synthetic": case.is_synthetic,
                        "verification_status": case.verification_status,
                    })

        # 5. Missing / Conflicting Evidence
        missing_evidence: List[str] = list(diag_report.get("uncertainty_and_missing_info", []))
        if not telemetry:
            missing_evidence.append("No controller sensor telemetry supplied; physical operating margins could not be cross-validated.")
        if not fault_code:
            missing_evidence.append("No OEM controller DTC provided; diagnosis relies strictly on acoustic and kinetic symptom matching.")

        uncertainty_notes = [
            f"Advisory Confidence Score is {int(conf_score * 100)}% based on historical evidence affinity. This is not a calibrated failure probability.",
            "Field technician physical verification with ASME A17.1 compliant procedures is mandatory prior to replacing parts.",
        ]

        # 6. Inspection steps
        inspection_steps: List[str] = []
        for rc in ranked_causes:
            for chk in rc.get("recommended_checks", []):
                if chk not in inspection_steps:
                    inspection_steps.append(chk)
        if not inspection_steps:
            inspection_steps = [
                f"Perform physical visual inspection of {subsystem.replace('_', ' ')} mechanical linkages.",
                "Verify electrical terminal torques and safety circuit loop continuity with a digital multimeter.",
                "Execute single-floor trial run under technician inspection control.",
            ]

        # 7. Required tools
        tools = cls._TOOL_REGISTRY.get(subsystem, cls._DEFAULT_TOOLS)

        # 8. Recommended parts (Evidence-grounded only!)
        parts = cls._recommend_parts_grounded(subsystem, root_cause, telemetry)

        # 9. Downtime / Effort estimate
        downtime = cls._estimate_downtime(subsystem, parts, is_verified=(status == "completed"))

        # 10. Safety precautions
        safety = cls._get_safety_precautions(subsystem)

        # 11. Escalation requirements
        escalations = cls._get_escalation_criteria(subsystem, fault_code)

        # 12. Return-to-service verification checks
        return_checks = cls._get_return_to_service_checks(subsystem)

        # 13. Final verification status & explanation
        final_verdict = verif_rec.get("final_verdict", "sufficient" if status == "completed" else "inconclusive")
        is_verified = (final_verdict == "sufficient" or status == "completed")
        verif_status = "VERIFIED GROUNDED" if is_verified else "INCONCLUSIVE ADVISORY"
        verif_exp = (
            f"Verification Loop executed with verdict: {final_verdict.upper()} (Retries: {verif_rec.get('total_retries', 0)}/{verif_rec.get('max_retries', 2)}). "
            f"All hypothesized claims were cross-referenced against historical knowledge base precedents and telemetry constraints."
            if is_verified else
            f"Verification Loop returned verdict: {final_verdict.upper()} after {verif_rec.get('total_retries', 0)} retries. "
            f"Insufficient historical evidence or contradictory physical readings detected. Recommendations are non-verified advisory guidelines only."
        )

        # 14. Recommended next action
        if is_verified:
            next_action = f"Proceed with physical lockout/tagout (LOTO) and execute Step 1: '{inspection_steps[0]}' using the {tools[0].name}."
        else:
            next_action = f"Do NOT replace components yet. Perform physical multimeter voltage drop and mechanical clearance audit across '{subsystem.replace('_', ' ')}'."

        summary = f"Fault isolation analysis for Elevator {elv_id} ({subsystem.replace('_', ' ').title()}). Primary root-cause: {root_cause}."

        # 15. Equipment and intake context
        manufacturer = inv_data.get("manufacturer") or "Unspecified / Generic"
        equipment_model = inv_data.get("equipment_model") or "Unspecified"
        problem_desc = inv_data.get("problem_description") or (symptoms[0] if symptoms else "Reported elevator operational malfunction")
        operating_conditions = inv_data.get("operating_conditions") or "Standard Operational Range"
        severity = inv_data.get("severity") or "Medium"

        # 16. Evidence-based status label
        has_dtc = bool(fault_code and fault_code.strip())
        has_telemetry = bool(telemetry_items)
        has_symp = len(symptoms) >= 1

        if is_verified and sufficiency_level.lower() == "high" and has_dtc:
            evidence_based_status = "Verified Against Documented Criteria"
        elif not has_symp or (not has_dtc and not has_telemetry and len(symptoms) < 2):
            evidence_based_status = "Awaiting Additional Information"
        elif not has_telemetry or not has_dtc:
            evidence_based_status = "Analysis Completed — Evidence Limited"
        elif is_verified:
            evidence_based_status = "Requires Technician Verification"
        else:
            evidence_based_status = "Root-Cause Hypothesis"

        # 17. Alternative causes (Rank 2+)
        alternative_causes = [c for c in ranked_causes if c.get("rank", 1) > 1]
        if not alternative_causes and len(ranked_causes) > 1:
            alternative_causes = ranked_causes[1:]

        # 18. Evidence gaps
        evidence_gaps = list(missing_evidence)
        if not has_dtc:
            evidence_gaps.append("OEM fault code not registered; diagnostic analysis relies strictly on symptom and kinetic signatures.")
        if not has_telemetry:
            evidence_gaps.append("Quantitative controller sensor logs omitted; mechanical/electrical limits cannot be evaluated mathematically.")
        if manufacturer == "Unspecified / Generic":
            evidence_gaps.append("Specific OEM manufacturer unrecorded; exact electrical pinouts and torque values must be referenced on jobsite.")

        # 19. Troubleshooting manual tailored to fault
        troubleshooting_manual = cls._get_troubleshooting_manual(subsystem, root_cause, fault_code, tools)

        return DiagnosticDossier(
            investigation_id=inv_id,
            incident_summary=summary,
            elevator_id=elv_id,
            building_id=building,
            subsystem=subsystem,
            fault_code=fault_code,
            symptoms=symptoms,
            telemetry_readings=telemetry_items,
            data_quality_assessment=data_quality,
            input_sufficiency=sufficiency_level.upper(),
            primary_root_cause=root_cause,
            ranked_causes=ranked_causes,
            supporting_evidence=supporting_evidence,
            missing_and_conflicting_evidence=missing_evidence,
            uncertainty_notes=uncertainty_notes,
            inspection_steps=inspection_steps,
            required_tools=tools,
            recommended_parts=parts,
            downtime_estimate=downtime,
            safety_precautions=safety,
            escalation_requirements=escalations,
            return_to_service_checks=return_checks,
            verification_status=verif_status,
            verification_explanation=verif_exp,
            recommended_next_action=next_action,
            confidence_score=conf_score,
            is_verified=is_verified,
            manufacturer=manufacturer,
            equipment_model=equipment_model,
            problem_description=problem_desc,
            operating_conditions=operating_conditions,
            severity=severity,
            evidence_based_status=evidence_based_status,
            troubleshooting_manual=troubleshooting_manual,
            alternative_causes=alternative_causes,
            evidence_gaps=evidence_gaps,
            recommended_diagnostic_checks=list(inspection_steps),
        )

    @classmethod
    def _infer_telemetry_unit(cls, key: str) -> tuple[str, str]:
        """Infers engineering units and nominal ranges from sensor parameter keys."""
        k = key.lower()
        if "voltage" in k or "_v" in k:
            return "Volts (V)", "Nominal: ±10% rated supply"
        elif "current" in k or "_a" in k:
            return "Amperes (A)", "Peak < 150% rated FLA"
        elif "attenuation" in k or "_db" in k:
            return "Decibels (dB)", "Nominal: < 5.0 dB"
        elif "cycle" in k or "count" in k:
            return "Cycles", "Service threshold: 100,000"
        elif "temp" in k or "_c" in k:
            return "Degrees Celsius (°C)", "Operating: 10°C - 45°C"
        elif "speed" in k or "_mps" in k:
            return "Meters / Second (m/s)", "Rated: ±5% contract speed"
        elif "vibration" in k or "m_s2" in k:
            return "m/s² (ISO 18738)", "Peak < 0.15 m/s²"
        elif "pressure" in k or "psi" in k:
            return "PSI", "Working: 400 - 1800 PSI"
        elif "gap" in k or "mm" in k:
            return "Millimeters (mm)", "Nominal: 0.15 - 0.25 mm"
        elif "resistance" in k or "ohm" in k:
            return "Ohms (Ω)", "OEM rated ±5%"
        return "Units", "As specified by OEM"

    @classmethod
    def _assess_telemetry_reading(cls, key: str, val: Any) -> str:
        """Evaluates whether an individual sensor parameter is in nominal or anomalous state."""
        try:
            num = float(val)
        except (ValueError, TypeError):
            return "Recorded"

        k = key.lower()
        if "attenuation" in k and num > 5.5:
            return "🔴 HIGH ATTENUATION (Optical obstruction/dirt)"
        if "motor_current_peak" in k and num > 3.5:
            return "🟡 ELEVATED PEAK CURRENT (Mechanical drag)"
        if "cycles" in k and num > 100000:
            return "🟡 HIGH CYCLE WEAR (Component fatigue)"
        if "vibration" in k and num > 0.10:
            return "🔴 HIGH VIBRATION (Bearing/rail anomaly)"
        if "bus_voltage" in k and num > 750:
            return "🔴 REGENERATIVE OVERVOLTAGE"
        return "🟢 WITHIN ACCEPTABLE LIMITS"

    @classmethod
    def _assess_data_quality(cls, fault_code: Optional[str], symptoms: List[str], telemetry: Dict[str, Any]) -> str:
        score = 0
        notes = []
        if fault_code and fault_code.strip():
            score += 35
            notes.append("Explicit OEM Fault Code provided")
        else:
            notes.append("Missing OEM fault code")

        if symptoms and len(symptoms) >= 2:
            score += 35
            notes.append(f"{len(symptoms)} discrete operational symptoms reported")
        elif symptoms:
            score += 20
            notes.append("Single symptom reported")

        if telemetry:
            score += 30
            notes.append(f"{len(telemetry)} physical sensor telemetry readings provided")
        else:
            notes.append("No numerical telemetry provided")

        if score >= 80:
            return f"Excellent ({score}/100) — {', '.join(notes)}"
        elif score >= 50:
            return f"Adequate ({score}/100) — {', '.join(notes)}"
        return f"Marginal ({score}/100) — {', '.join(notes)}"

    @classmethod
    def _recommend_parts_grounded(cls, subsystem: str, root_cause: str, telemetry: Dict[str, Any]) -> List[PartRecommendation]:
        """Recommends parts ONLY when supported by evidence or wear limits."""
        parts: List[PartRecommendation] = []
        rc_lower = root_cause.lower()

        # Check optical curtain
        atten = telemetry.get("curtain_optical_attenuation_db") or telemetry.get("optical_attenuation")
        try:
            if atten and float(atten) >= 6.5:
                parts.append(PartRecommendation(
                    part_name="Optical Light Curtain Sensor Bar Set",
                    part_type="Safety Sensor Array",
                    justification=f"Telemetry indicates optical attenuation of {atten} dB exceeding OEM discard threshold (6.0 dB).",
                    evidence_basis="Telemetry reading: curtain_optical_attenuation_db",
                    is_immediate_replacement=False,
                ))
        except (ValueError, TypeError):
            pass

        # Check door sill
        if "sill" in rc_lower or "guide track" in rc_lower:
            parts.append(PartRecommendation(
                part_name="Car Door Bottom Gibs / Guide Shoes",
                part_type="Wear Component",
                justification="Mechanical drag and grit in door sill causes premature gib groove erosion.",
                evidence_basis="Root cause hypothesis documents track grit binding",
                is_immediate_replacement=False,
            ))

        # Check braking system
        if "brake" in subsystem and ("lining" in rc_lower or "shoe" in rc_lower):
            parts.append(PartRecommendation(
                part_name="Electromechanical Brake Shoe Lining Kit",
                part_type="Friction Wear Assembly",
                justification="Excessive air-gap and mechanical drag indicates lining friction wear.",
                evidence_basis="Subsystem braking_system root-cause correlation",
                is_immediate_replacement=False,
            ))

        # Check traction drive
        if "traction" in subsystem and "regenerative" in rc_lower:
            parts.append(PartRecommendation(
                part_name="Dynamic Braking Resistor Bank (DBR)",
                part_type="Power Electronics",
                justification="Regenerative overvoltage occurs when braking resistor or chopper circuit fails to dissipate regenerative energy.",
                evidence_basis="DC bus overvoltage failure pattern",
                is_immediate_replacement=False,
            ))

        return parts

    @classmethod
    def _estimate_downtime(cls, subsystem: str, parts: List[PartRecommendation], is_verified: bool) -> DowntimeEstimate:
        """Calculates defensible effort and downtime estimates."""
        if not is_verified:
            return DowntimeEstimate(
                inspection_hours=1.0,
                service_hours=1.0,
                total_hours=2.0,
                defensible_basis="Standard diagnostic isolation protocol. Scope is unverified pending on-site multimeter measurements."
            )

        if subsystem == "door_system":
            insp = 0.75
            serv = 1.25 if parts else 0.75
            return DowntimeEstimate(
                inspection_hours=insp,
                service_hours=serv,
                total_hours=insp + serv,
                defensible_basis="0.75 hrs for sill cleaning and optical beam alignment; 1.25 hrs if replacing guide gibs."
            )
        elif subsystem == "braking_system":
            insp = 1.0
            serv = 2.0 if parts else 1.0
            return DowntimeEstimate(
                inspection_hours=insp,
                service_hours=serv,
                total_hours=insp + serv,
                defensible_basis="1.0 hrs air-gap feeler gauge audit; 2.0 hrs for spring tension calibration and dynamic stop test."
            )
        elif subsystem == "traction_drive":
            insp = 1.0
            serv = 2.5
            return DowntimeEstimate(
                inspection_hours=insp,
                service_hours=serv,
                total_hours=insp + serv,
                defensible_basis="1.0 hrs oscilloscope & motor insulation megger check; 2.5 hrs for VFD parameter tuning or chopper replacement."
            )
        elif subsystem == "hydraulic_system":
            insp = 1.0
            serv = 2.0
            return DowntimeEstimate(
                inspection_hours=insp,
                service_hours=serv,
                total_hours=insp + serv,
                defensible_basis="1.0 hrs pressure gauge test; 2.0 hrs for proportional valve spool flush and fluid filter replacement."
            )
        else:
            return DowntimeEstimate(
                inspection_hours=1.0,
                service_hours=1.5,
                total_hours=2.5,
                defensible_basis="Standard field inspection, physical isolation, and return-to-service acceptance tests."
            )

    @classmethod
    def _get_safety_precautions(cls, subsystem: str) -> List[str]:
        base_safety = [
            "MANDATORY LOTO: Isolate and apply Lockout/Tagout padlocks to the mainline disconnect before touching controller or motor power circuits.",
            "FALL HAZARD PREVENTION: Wear full-body fall arrest harness and tether to certified hoistway anchorage when performing top-of-car inspections.",
            "NO JUMPERS RULE: Strictly prohibit placing temporary alligator jumper clips across door interlock or safety circuit contacts during live passenger service.",
            "VERIFY ZERO ENERGY: Use a calibrated CAT III/IV digital multimeter to verify zero voltage between all phases and chassis ground before touching terminals.",
        ]
        if subsystem == "door_system":
            base_safety.append("PINCH POINT SAFETY: Mechanically secure door operator drive belt before adjusting pulleys or guide gibs.")
        elif subsystem == "hydraulic_system":
            base_safety.append("HYDRAULIC PRESSURE ISOLATION: Lower car to buffer stands and depressurize cylinder before opening valve blocks.")
        elif subsystem == "braking_system":
            base_safety.append("UNINTENDED CAR MOVEMENT: Ensure car counterweight is properly balanced or car blocked before manual brake release.")
        return base_safety

    @classmethod
    def _get_escalation_criteria(cls, subsystem: str, fault_code: Optional[str]) -> List[str]:
        return [
            "Escalate immediately to Lead Modernization Engineer if motor insulation resistance drops below 5.0 Megohms.",
            "Escalate to OEM Field Engineering if controller fault code persists following two consecutive factory re-initializations.",
            "Report immediately to Jurisdiction AHJ (Authority Having Jurisdiction) if mechanical safety gear or governor activates dynamically under passenger load.",
        ]

    @classmethod
    def _get_return_to_service_checks(cls, subsystem: str) -> List[VerificationCheck]:
        return [
            VerificationCheck(
                step_number=1,
                title="Safety Circuit String Continuity Audit",
                acceptance_criterion="Verify 100% electrical continuity through pit switch, buffer switches, final limits, and car gate switch (0.0 V drop).",
                applicable_code="ASME A17.1 Rule 2.26.2",
                safety_advisory="Test using multimeter in continuity mode with mainline disconnect open."
            ),
            VerificationCheck(
                step_number=2,
                title="Door Interlock Contact Make & Dwell Test",
                acceptance_criterion="Car must NOT initiate transit unless door lock beak contacts make minimum 3/8 inch (9.5 mm) electrical wipe.",
                applicable_code="ASME A17.1 Rule 2.12.2.4",
                safety_advisory="Inspect contact spring tension and silver contact pads for pitting."
            ),
            VerificationCheck(
                step_number=3,
                title="Floor Leveling Accuracy Audit",
                acceptance_criterion="Car sill must level within ±1/4 inch (±6 mm) of landing sill under both empty and rated contract load conditions.",
                applicable_code="ASME A17.1 Rule 2.26.1.6",
                safety_advisory="Check across all terminal and intermediate landings."
            ),
            VerificationCheck(
                step_number=4,
                title="Emergency Unintended Movement & Brake Hold",
                acceptance_criterion="Electromechanical brake must independently hold 125% rated car load without rotational slippage.",
                applicable_code="ASME A17.1 Rule 2.24.8",
                safety_advisory="Execute dynamic brake stop from inspection speed."
            ),
        ]

    @classmethod
    def _get_troubleshooting_manual(
        cls,
        subsystem: str,
        root_cause: str,
        fault_code: Optional[str],
        tools: List[ToolRequirement],
    ) -> List[TroubleshootingStep]:
        """Generates ordered, practical manual troubleshooting procedures tailored to diagnosed fault."""
        mm_tool = next((t.name for t in tools if "Multimeter" in t.name or "meter" in t.name.lower()), "Digital Multimeter (CAT III 600V)")
        mech_tool = next((t.name for t in tools if "Gauge" in t.name or "Caliper" in t.name or "Rule" in t.name), "Precision Feeler Gauge Set")

        if subsystem == "door_system":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Door Sill Track & Mechanical Obstruction Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Identify foreign matter, metal filings, or mechanical deflection in car and landing door sill grooves.",
                    required_tools="Inspection Flashlight & Track Feeler Gauge",
                    inspection_measurement="Visual sweep and feeler gauge measurement along full car door travel width (nominal sill groove clearance 2.0 mm - 3.0 mm).",
                    expected_criterion="Guide track clean and devoid of debris; bottom gibs slide freely without binding or excessive lateral play (< 1.5 mm).",
                    interpretation="Grit or bent sill teeth cause intermittent mechanical drag and premature optical curtain re-open triggers.",
                    next_action="If debris or binding observed, proceed to Step 4 for vacuum cleaning and gib adjustment; otherwise advance to Step 2.",
                    safety_precautions="Mechanically lock doors open; elevator car must be parked level at floor landing with car station in STOP mode."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="Optical Light Curtain Voltage Supply & Receiver Attenuation Test",
                    step_type="Diagnostic Inspection",
                    purpose="Quantify optical curtain array alignment, emitter power, and receiver signal attenuation.",
                    required_tools=f"{mm_tool} & Optical Attenuation Sensor",
                    inspection_measurement="Measure DC supply voltage at curtain transmitter/receiver terminal block (pins 1 & 2), and signal attenuation in closed/open positions.",
                    expected_criterion="Supply voltage 24.0 V DC (±10%); attenuation < 5.0 dB. If manufacturer threshold unavailable, verify clean optic lenses without scratches.",
                    interpretation="Attenuation > 5.5 dB confirms dirty lenses, misaligned transmitter/receiver brackets, or internal photodiode degradation.",
                    next_action="If voltage abnormal, inspect door operator power supply rail. If attenuation elevated, clean optical lenses with isopropyl alcohol wipe.",
                    safety_precautions="Keep hands and clothing clear of door operator belt drive and moving sheaves during open/close cycles."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Door Interlock Contact Make & Safety Circuit Continuity Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Verify mechanical wipe and electrical continuity across car door gate switch and hoistway interlock beaks.",
                    required_tools=f"{mm_tool} (low-resistance ohms mode)",
                    inspection_measurement="Measure contact resistance across closed gate switch contacts and verify physical wipe depth.",
                    expected_criterion="Contact wipe minimum 3/8 inch (9.5 mm) per ASME A17.1 Rule 2.12.2.4; closed contact resistance < 0.5 ohms.",
                    interpretation="Pitted silver contacts or shallow engagement causes vibration-induced micro-interruptions during car movement.",
                    next_action="If contacts exhibit pitting or resistance > 1.0 ohm, dress contacts with burnishing tool or replace contact block.",
                    safety_precautions="Mainline disconnect MUST be locked open (LOTO); verify zero energy with multimeter before probing contacts."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Sill Track Cleaning, Gib Realignment & Lubrication",
                    step_type="Corrective Action",
                    purpose="Remove accumulated debris, calibrate door guide shoes, and align curtain mounting brackets.",
                    required_tools="Industrial HEPA Vacuum, Brass Wire Brush, Guide Alignment Jig",
                    inspection_measurement="Vacuum full length of landing and car sills; re-torque guide gib mounting fasteners to OEM specification.",
                    expected_criterion="Door panel moves smoothly with < 15 N manual force when decoupled from operator belt.",
                    interpretation="Eliminates mechanical drag that triggers door operator current limit overloads.",
                    next_action="Reconnect operator drive belt and verify smooth mechanical cycling under low-speed test mode.",
                    safety_precautions="Wear safety goggles and dust mask; do NOT apply wet oil or grease directly into sill guide grooves (attracts dust)."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Door Kinetic Energy & Closing Force Verification Test",
                    step_type="Corrective Action",
                    purpose="Verify closing force and kinetic energy comply with safety code prior to passenger release.",
                    required_tools="Kinetic Energy Force Gauge & Stopwatch",
                    inspection_measurement="Place force gauge at 1/3 and 2/3 door travel span; measure stall closing force and reversal response time.",
                    expected_criterion="Peak closing force < 30 lbf (133 N) per ASME A17.1 Rule 2.13.4.2; kinetic energy < 10 J (7.37 ft-lbf); reversal < 150 ms upon curtain beam break.",
                    interpretation="Ensures passenger protection while preventing false nuisance reopening during normal passenger transit.",
                    next_action="If force exceeds 30 lbf, reduce operator closing torque potentiometer or VFD parameter. If compliant, proceed to verification sign-off.",
                    safety_precautions="Stand outside car entrance line during closing force measurement; keep hands clear of leading edges."
                ),
            ]
        elif subsystem == "traction_drive":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Machine Room Visual & Ambient Thermal Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Check drive enclosure cooling, braking resistor cage temperature, and motor ventilation ducts.",
                    required_tools="Infrared Non-Contact Thermometer & Inspection Light",
                    inspection_measurement="Measure ambient machine room temperature, VFD heatsink temperature, and dynamic braking resistor (DBR) surface temperature.",
                    expected_criterion="Machine room ambient < 40°C; VFD heatsink < 75°C; braking resistor within manufacturer thermal envelope.",
                    interpretation="Overheated machine room or clogged VFD fan filters trigger regenerative overvoltage and thermal foldback.",
                    next_action="If ambient elevated, check machine room HVAC and clean VFD heatsink filter grilles before electrical tests.",
                    safety_precautions="Observe hot surface warnings; maintain safe clearance from high-voltage DC bus enclosures."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="VFD DC Bus & Dynamic Braking Resistor Resistance Test",
                    step_type="Diagnostic Inspection",
                    purpose="Verify dynamic braking chopper circuit and resistor bank continuity to isolate regenerative overvoltage.",
                    required_tools=f"{mm_tool} & Insulated Probe Leads",
                    inspection_measurement="Measure resistance across DBR terminals (B+ and B-) with drive de-energized, and measure DC bus voltage during deceleration.",
                    expected_criterion="DBR resistance matching cabinet schematic nameplate (±5%); DC bus voltage < 750 V DC during peak deceleration.",
                    interpretation="Open or high-resistance DBR bank prevents energy dissipation during full-load downward express decelerations.",
                    next_action="If DBR open circuit, replace dynamic braking resistor bank. If DBR intact but voltage spikes, test chopper IGBT module.",
                    safety_precautions="LOTO mainline disconnect; WAIT minimum 10 minutes for DC bus discharge capacitors to drain below 50V DC; verify with multimeter."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Motor Insulation Resistance (Megohmmeter) Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Assess stator winding dielectric health and motor feeder cable insulation to earth ground.",
                    required_tools="500V/1000V Digital Insulation Tester (Megohmmeter)",
                    inspection_measurement="Disconnect motor leads from drive output terminals; apply 500V DC test voltage phase-to-phase and phase-to-ground for 60 seconds.",
                    expected_criterion="Insulation resistance > 50 Megohms (absolute minimum acceptable threshold: 5.0 Megohms per IEEE 43).",
                    interpretation="Resistance < 5 Megohms indicates moisture ingress, carbon tracking, or stator insulation breakdown.",
                    next_action="If insulation < 5 Megohms, escalate to Lead Motor Specialist for winding dry-out or rewind; do NOT re-energize drive.",
                    safety_precautions="Ensure all motor terminals isolated from electronic drive boards before applying megohmmeter voltage."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Braking Chopper & Resistor Terminal Torquing",
                    step_type="Corrective Action",
                    purpose="Eliminate high-resistance loose connections on power resistor harness and chopper gate drive.",
                    required_tools="Insulated Calibrated Torque Screwdriver",
                    inspection_measurement="Verify fastener torque on power terminals against manufacturer specification (typically 2.5 - 3.5 N-m).",
                    expected_criterion="All power lug fasteners seated firmly to OEM torque rating without thermal discoloration on copper lugs.",
                    interpretation="Loose connections create thermal hotspots and intermittent overvoltage trip signals.",
                    next_action="Re-torque loose connections; clean oxidized lug terminals with contact cleaner.",
                    safety_precautions="Strict LOTO with lockout padlock applied; confirm zero DC bus voltage."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Full-Speed Empty & Balanced Load Deceleration Trial",
                    step_type="Corrective Action",
                    purpose="Validate DC bus regulation and brake deceleration profile during contract speed run.",
                    required_tools=f"{mm_tool} with Min/Max voltage capture",
                    inspection_measurement="Execute contract speed express runs from top to bottom terminal landings while logging peak DC bus voltage.",
                    expected_criterion="Smooth deceleration without motor hunting or overvoltage fault trips; peak DC bus remains < 720 V DC.",
                    interpretation="Confirms dynamic braking chopper dissipates regenerative energy smoothly under field duty.",
                    next_action="If stable, sign off inspection and restore car to automatic dispatch service.",
                    safety_precautions="Perform test runs under technician inspection supervision before enabling public passenger calls."
                ),
            ]
        elif subsystem == "braking_system":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Brake Shoe Mechanical Air Gap Measurement",
                    step_type="Diagnostic Inspection",
                    purpose="Measure physical air gap between brake friction linings and brake wheel drum across 4 quadrants.",
                    required_tools=f"{mech_tool} (0.05 mm - 1.0 mm blades)",
                    inspection_measurement="Insert feeler gauge at top, bottom, left, and right quadrants of both brake arms while brake energized.",
                    expected_criterion="Air gap uniformly within OEM specification (typically 0.15 mm - 0.25 mm / 0.006 - 0.010 in). Consult OEM manual for exact model limits.",
                    interpretation="Air gap > 0.35 mm causes delayed lifting and loud slamming; air gap < 0.10 mm causes shoe drag and friction lining overheating.",
                    next_action="If air gap out of tolerance, proceed to Step 4 for mechanical shoe stop adjustment; otherwise check coil resistance in Step 2.",
                    safety_precautions="Car must be empty and balanced; do NOT place fingers between brake shoe and rotating drum."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="Brake Solenoid Coil Electrical Resistance & Temperature Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Check solenoid coil winding resistance and measure thermal rise to detect shorted turns.",
                    required_tools=f"{mm_tool} & Surface Thermocouple Probe",
                    inspection_measurement="Measure cold/hot DC coil resistance across coil leads (compare with nameplate value, typically 40 - 120 ohms).",
                    expected_criterion="Coil resistance within ±5% of manufacturer baseline; operating temperature < 85°C after 1 hour continuous cycling.",
                    interpretation="Drop in resistance > 10% indicates inter-turn shorting that reduces electromagnetic lifting force.",
                    next_action="If coil resistance abnormal or coil housing burning hot, replace solenoid coil assembly; do not attempt rewinding in field.",
                    safety_precautions="De-energize brake circuit; observe hot coil housing precautions."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Friction Lining Thickness & Drum Surface Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Inspect brake shoe friction material wear, oil contamination, and drum surface scoring.",
                    required_tools="Digital Vernier Caliper & Inspection Mirror",
                    inspection_measurement="Measure remaining lining thickness above rivet heads or bonding base; inspect drum for glazing or heat cracks.",
                    expected_criterion="Lining thickness > OEM minimum discard threshold (typically > 3.0 mm above rivets); drum surface smooth and dry.",
                    interpretation="Glazed or oil-soaked linings reduce friction coefficient; worn linings risk catastrophic metal-to-metal contact.",
                    next_action="If contaminated with oil or worn below discard limit, replace both brake shoes as a matched set; clean drum with brake degreaser.",
                    safety_precautions="Wear dust particulate respirator when inspecting friction material; do not use compressed air to blow brake dust."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Brake Core Plunger Adjustment & Air Gap Calibration",
                    step_type="Corrective Action",
                    purpose="Adjust core stop screws and spring preload to re-establish nominal air gap and synchronized lifting.",
                    required_tools="Open-End Spanners, Hex Wrenches, Feeler Gauge",
                    inspection_measurement="Adjust core gap adjusting nuts in 1/8-turn increments until feeler gauge reveals uniform 0.20 mm clearance.",
                    expected_criterion="Both brake arms lift simultaneously within 50 ms of run command without cocking or mechanical chatter.",
                    interpretation="Restores balanced mechanical brake application and eliminates shoe drag.",
                    next_action="Tighten locknuts securely; re-verify clearance with feeler gauge after torquing locknuts.",
                    safety_precautions="Lock mainline disconnect open before making mechanical wrench adjustments."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="125% Rated Load Dynamic Brake Hold & Stop Test",
                    step_type="Corrective Action",
                    purpose="Validate compliance with ASME A17.1 Rule 2.24.8.2 dynamic braking and static holding capability.",
                    required_tools="Certified Test Weights / Load Verification Kit & Marking Gauge",
                    inspection_measurement="Park car at lowest landing; simulate emergency stop from inspection speed; verify deceleration without slip.",
                    expected_criterion="Brake independently holds 125% of rated load without rotational slip; car stops smoothly within rated slide distance.",
                    interpretation="Confirms elevator mechanical braking system is fully capable of arresting car under maximum emergency load.",
                    next_action="Record test results in machine room logbook; remove test weights; sign off inspection dossier.",
                    safety_precautions="Strictly prohibit unauthorized personnel inside hoistway or car during heavy-load braking verification."
                ),
            ]
        elif subsystem == "hoistway_signaling":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Encoder Cable Shielding & Ground Continuity Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Check position feedback cable shield termination and ground bond to prevent electrical noise coupling.",
                    required_tools=f"{mm_tool} (low-resistance ohms mode)",
                    inspection_measurement="Measure resistance between encoder cable drain wire and machine room main earth ground busbar.",
                    expected_criterion="Resistance to earth < 0.2 ohms; shield grounded at controller cabinet end ONLY (no ground loops).",
                    interpretation="Ground loop or broken shield introduces spurious high-frequency noise spikes into position count registers.",
                    next_action="If shield ungrounded or grounded at both ends, correct bonding to single-point star ground.",
                    safety_precautions="De-energize controller low-voltage supply before checking internal cabinet shield terminations."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="Dual-Channel Quadrature Pulse (A/B Phase) Waveform Test",
                    step_type="Diagnostic Inspection",
                    purpose="Examine pulse symmetry, signal amplitude, and 90° quadrature phase shift during car transit.",
                    required_tools="Dual-Channel Portable Digital Storage Oscilloscope",
                    inspection_measurement="Probe Channel A and Channel B test points at controller position input card during car leveling transit.",
                    expected_criterion="Clean square wave 0V - 5V (or 24V HTL); 50% duty cycle; exact 90° electrical phase offset without ringing.",
                    interpretation="Missing pulses or phase jitter confirms damaged encoder disc, loose shaft coupling, or optical sensor failure.",
                    next_action="If pulses missing or distorted, check encoder shaft mechanical set-screws; replace encoder if internal disc cracked.",
                    safety_precautions="Use 10:1 insulated oscilloscope probes; avoid shorting adjacent IC pins."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Hoistway Tape Reader / Vane Sensor Alignment Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Inspect physical gap and vertical plumbness of magnetic or optical car-top leveling sensors.",
                    required_tools="Non-Magnetic Feeler Gauge & Brass Alignment Rule",
                    inspection_measurement="Measure air gap between car-top reader heads and hoistway perforated steel tape or door zone vanes.",
                    expected_criterion="Air gap centered within OEM tolerance (typically 6.0 mm ± 1.5 mm); no rub marks on guide shoes.",
                    interpretation="Misaligned tape guide rollers cause intermittent missed floor count triggers during high-speed travel.",
                    next_action="If misaligned, adjust car-top sensor bracket mounting bolts; replace worn guide rollers.",
                    safety_precautions="Operate strictly from car-top inspection station; keep safety harness tethered to certified anchor."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Encoder Shaft Coupling Torquing & Lens Cleaning",
                    step_type="Corrective Action",
                    purpose="Secure flexible mechanical coupling and clean optical reader head lenses.",
                    required_tools="Metric Hex Keys & Isopropyl Alcohol Optical Swabs",
                    inspection_measurement="Verify torque on motor shaft set-screws; clean tape reader optical sensor lenses.",
                    expected_criterion="Zero backlash or rotational slip between motor shaft and encoder spindle; clean optical emitter windows.",
                    interpretation="Eliminates positioning count discrepancies between motor encoder and hoistway tape.",
                    next_action="Cycle elevator on inspection control from bottom to top terminal landing to recalibrate absolute position.",
                    safety_precautions="Keep hands away from moving drive sheaves and governor ropes during car motion."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Floor Leveling Accuracy & Floor Arrival Calibration Audit",
                    step_type="Corrective Action",
                    purpose="Verify car floor stops level with landing sill across all intermediate and terminal landings.",
                    required_tools="Precision Digital Level & Steel Rule",
                    inspection_measurement="Run car to each floor under automatic dispatch; measure vertical step height between car sill and landing sill.",
                    expected_criterion="Car sill levels within ±1/4 inch (±6 mm) of landing sill per ASME A17.1 Rule 2.26.1.6.",
                    interpretation="Confirms hoistway position detection system is fully calibrated and stable.",
                    next_action="If all floors level within tolerance, close investigation and record leveling metrics.",
                    safety_precautions="Ensure hallway landing is barricaded with safety cones during leveling measurements."
                ),
            ]
        elif subsystem == "hydraulic_system":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Hydraulic Fluid Level, Oil Temperature & Viscosity Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Check fluid reservoir volume, oil operating temperature, and contamination index.",
                    required_tools="Fluid Level Dipstick, Infrared Thermometer & Oil Test Kit",
                    inspection_measurement="Measure reservoir level with car on buffer stands; check oil temperature in power unit tank.",
                    expected_criterion="Oil level at FULL mark; operating temperature 35°C - 55°C (never exceed 60°C); clear amber fluid without burnt odor.",
                    interpretation="Low or degraded oil causes pump cavitation, foaming, valve spool binding, and irregular car descent speeds.",
                    next_action="If oil burnt or dark, take 100 mL sample for laboratory patch test; top off or replace hydraulic fluid.",
                    safety_precautions="Wear nitrile chemical-resistant gloves and safety glasses; hydraulic fluid may be hot."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="System Working & Static Pressure Gauge Test",
                    step_type="Diagnostic Inspection",
                    purpose="Measure static holding pressure, running up-pressure, and bypass relief valve tripping pressure.",
                    required_tools="Calibrated Hydraulic Pressure Gauge (0-3000 PSI / 0-200 Bar)",
                    inspection_measurement="Connect gauge to power unit quick-disconnect test port; record static pressure, full-load up-pressure, and bypass pressure.",
                    expected_criterion="Working pressure within machine nameplate range (typically 400 - 1200 PSI); relief valve opens at 125% - 150% working pressure.",
                    interpretation="Pressure drop during static hold confirms internal cylinder packing leak, check valve leakage, or down-valve bypass.",
                    next_action="If static pressure decays > 10 PSI/minute, isolate down-valve spool and inspect cylinder seal gland.",
                    safety_precautions="Relieve all reservoir pressure before connecting/disconnecting gauge fittings; never exceed gauge working pressure."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Proportional Down-Valve Spool & Solenoid Coil Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Inspect valve block electrical solenoids and check for mechanical spool sticking.",
                    required_tools=f"{mm_tool} & Valve Manual Override Tool",
                    inspection_measurement="Measure solenoid coil resistance; depress manual override pin to check smooth spool return spring travel.",
                    expected_criterion="Coil resistance within OEM specification (typically 20 - 50 ohms); spool slides freely without sticking.",
                    interpretation="Debris in proportional valve orifice causes jerky deceleration, leveling creep, or car stall.",
                    next_action="If spool sticky, proceed to Step 4 for valve block flush and filter replacement.",
                    safety_precautions="LOTO mainline disconnect; ensure car is resting securely on mechanical buffer stands."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Valve Block Orifice Cleaning & Fluid Return Filter Replacement",
                    step_type="Corrective Action",
                    purpose="Flush valve manifold contamination, replace return-line filter cartridge, and clean tank strainer.",
                    required_tools="Filter Wrench, Lint-Free Shop Rags, New OEM Filter Cartridge",
                    inspection_measurement="Remove return filter element; inspect pleated paper for metal particulates; install new OEM 10-micron element.",
                    expected_criterion="Filter housing torqued to spec; zero oil weepage around O-ring seal; filter indicator in green zone.",
                    interpretation="Eliminates particulate contamination that jams precision proportional valve spools.",
                    next_action="Purge air from hydraulic cylinder and valve manifold through bleed petcock.",
                    safety_precautions="Catch spilled fluid in approved collection pan; dispose of hazardous waste per local regulations."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Crawl Speed & Top Terminal Anti-Creep Verification Test",
                    step_type="Corrective Action",
                    purpose="Confirm anti-creep leveling system and down-speed control meet ASME A17.1 Rule 2.26.1.6.",
                    required_tools="Stopwatch, Precision Level & Pyrometer",
                    inspection_measurement="Park car at top terminal landing; simulate cooling fluid contraction; observe automatic anti-creep releveling.",
                    expected_criterion="Car automatically re-levels upward if car drops > 1 inch (25 mm) below landing within 15 minutes.",
                    interpretation="Confirms hydraulic safety anti-creep circuit operates reliably to prevent unlevel passenger tripping hazards.",
                    next_action="If compliant, sign off return-to-service checklist and record fluid temperature baseline.",
                    safety_precautions="Verify hoistway pit is cleared of personnel before running down-direction trial."
                ),
            ]
        elif subsystem == "safety_gear":
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Governor Flyweight & Electrical Switch Trip Speed Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Validate electrical overspeed switch trip point before mechanical jaw engagement.",
                    required_tools="Digital Optical Tachometer & Variable Speed Governor Test Motor",
                    inspection_measurement="Drive governor sheave and record RPM at which electrical overspeed contact opens.",
                    expected_criterion="Electrical switch trips at not more than 90% of mechanical tripping speed per ASME A17.1 Rule 2.18.4.",
                    interpretation="Premature or non-tripping electrical switch causes either nuisance trips or failure to de-energize drive prior to safety application.",
                    next_action="If trip speed deviates > 5%, calibrate flyweight spring tension or replace governor switch assembly.",
                    safety_precautions="Car must be parked with hoistway cleared of all personnel; apply inspection STOP switch."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="Safety Plank Linkage & Mechanical Wedge Clearance Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Check safety gear wedges or rollers on bottom car safety plank for equal clearance from guide rails.",
                    required_tools="Precision Feeler Gauge & Calibrated Scale",
                    inspection_measurement="Measure clearance between left and right safety wedges and guide rail blades (nominal 2.5 mm - 4.0 mm).",
                    expected_criterion="Symmetrical clearance on both rail blades; safety pull-rod linkages move freely without rust binding.",
                    interpretation="Unequal clearance or seized linkages cause uneven wedge bite that twists guide rails during safety application.",
                    next_action="If clearances uneven, adjust safety plank connecting rods; lubricate pivot joints with light synthetic machine oil.",
                    safety_precautions="Work strictly from hoistway pit or car-top inspection platform with fall protection harness anchored."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Governor Tension Sheave & Rope Condition Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Inspect governor steel wire rope for broken wires, diameter reduction, and pit tension weight clearance.",
                    required_tools="Wire Rope Diameter Caliper & Inspection Flashlight",
                    inspection_measurement="Measure governor rope diameter along high-wear zones; check pit tension sheave floating clearance above pit floor.",
                    expected_criterion="Rope diameter within discard threshold (< 6% reduction); pit tension weight suspended minimum 2 inches above stops.",
                    interpretation="Rope stretch that allows pit tension weight to bottom out reduces governor rope traction, preventing wedge lift.",
                    next_action="If tension weight grounded, shorten and re-shackle governor rope; replace rope if wire breaks exceed code.",
                    safety_precautions="Lock out elevator mainline disconnect before entering hoistway pit."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Safety Gear Wedge Rail Mark Depth Measurement",
                    step_type="Corrective Action",
                    purpose="Examine rail surfaces following safety activation to verify progressive wedge bite depth.",
                    required_tools="Rail Blade Caliper & Depth Micrometer",
                    inspection_measurement="Measure serrated wedge bite indentations on both left and right guide rail blades.",
                    expected_criterion="Identical bite depth on both rail faces; no rail fracture, gouging, or guide rail alignment deformation.",
                    interpretation="Verifies progressive deceleration without exceeding structural stress limits of elevator guide rails.",
                    next_action="File down high-spot burrs on guide rails using fine mill bastard file; clean and re-lubricate rail surfaces.",
                    safety_precautions="Secure car with hoisting tackle or buffer stands before dressing guide rails."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Slow-Speed Manual Safety Pull-Up Verification Test",
                    step_type="Corrective Action",
                    purpose="Confirm safety gear wedges release cleanly when elevator is hoisted upward.",
                    required_tools="Inspection Control Station & Visual Watch",
                    inspection_measurement="Hoist car upward on inspection control; observe both safety wedges drop freely back into reset position.",
                    expected_criterion="Safety wedges fully retract; safety plank electrical switch automatically resets or latches per code; zero rail drag.",
                    interpretation="Ensures car does not drag released safety gear during subsequent normal passenger runs.",
                    next_action="If compliant, perform full-speed empty trial run and sign return-to-service acceptance log.",
                    safety_precautions="Ensure all tools and personnel are removed from car top and pit before moving car."
                ),
            ]
        else:
            return [
                TroubleshootingStep(
                    step_number=1,
                    title="Initial Lockout/Tagout & Visual Inspection",
                    step_type="Diagnostic Inspection",
                    purpose="Establish safe work boundary and inspect subsystem assembly for visible physical anomalies.",
                    required_tools="Inspection Flashlight & Multimeter",
                    inspection_measurement="Apply LOTO to mainline disconnect; verify zero electrical energy; inspect mechanical linkages.",
                    expected_criterion="Subsystem components securely mounted, free of physical binding, oil contamination, or thermal burning.",
                    interpretation="Identifies blatant physical or mechanical failures before commencing detailed instrumentation testing.",
                    next_action="If mechanical damage visible, document part replacement requirements; otherwise proceed to Step 2.",
                    safety_precautions="Adhere strictly to ASME A17.1 LOTO protocols; verify zero voltage on all incoming phases."
                ),
                TroubleshootingStep(
                    step_number=2,
                    title="Electrical Circuit & Safety Interlock Continuity Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Verify electrical circuit integrity, supply voltages, and safety switch loop continuity.",
                    required_tools=f"{mm_tool} (CAT III 600V)",
                    inspection_measurement="Measure supply bus voltage and point-to-point contact resistance across subsystem safety circuit switches.",
                    expected_criterion="Voltage within ±10% rated supply; closed contact resistance < 0.5 ohms.",
                    interpretation="High resistance or voltage drop indicates oxidized contacts, loose terminal screws, or wiring harness fatigue.",
                    next_action="If wiring loose, re-torque terminal screws; if voltage low, inspect control transformer and fuses.",
                    safety_precautions="Never place temporary bypass jumpers across safety interlock contacts during live troubleshooting."
                ),
                TroubleshootingStep(
                    step_number=3,
                    title="Mechanical Clearances & Dynamic Alignment Audit",
                    step_type="Diagnostic Inspection",
                    purpose="Measure mechanical operating clearances, gaps, and guide alignments against OEM tolerances.",
                    required_tools=f"{mech_tool} & Metric Calipers",
                    inspection_measurement="Measure operating gaps and verify alignment with OEM engineering drawings. If undocumented, do not guess thresholds; consult OEM.",
                    expected_criterion="Clearances comply with equipment technical manual; smooth movement without binding across full travel.",
                    interpretation="Misalignment causes mechanical drag, premature wear, and intermittent fault code registrations.",
                    next_action="If out of tolerance, perform mechanical realignment in Step 4; otherwise test under inspection power.",
                    safety_precautions="Maintain safe clearance from rotating machinery and pinch points."
                ),
                TroubleshootingStep(
                    step_number=4,
                    title="Targeted Cleaning, Calibration & Fastener Torquing",
                    step_type="Corrective Action",
                    purpose="Clean foreign debris, re-torque fasteners to OEM specifications, and calibrate sensor alignment.",
                    required_tools="Torque Wrench & Contact Cleaner",
                    inspection_measurement="Clean contact surfaces and re-torque mounting fasteners to manufacturer specifications.",
                    expected_criterion="Fasteners torqued to spec; contacts clean; sensor alignment marks aligned.",
                    interpretation="Restores optimal mechanical and electrical operating baseline.",
                    next_action="Remove LOTO locks, restore power under technician supervision, and execute single-floor trial run.",
                    safety_precautions="Verify all personnel clear of hoistway and car before restoring mainline electrical power."
                ),
                TroubleshootingStep(
                    step_number=5,
                    title="Return-to-Service Functional Acceptance Run",
                    step_type="Corrective Action",
                    purpose="Validate complete operational restoration through trial runs across all landings.",
                    required_tools="Technician Observation & Controller Event Log Viewer",
                    inspection_measurement="Execute round-trip transit; monitor controller event log for recurrence of diagnostic trouble codes.",
                    expected_criterion="Zero error codes logged; car accelerates, cruises, decelerates, and levels within code tolerances.",
                    interpretation="Confirms suspected fault has been eliminated and elevator is ready for return to public passenger service.",
                    next_action="Sign off Return-to-Service Checklist, record technician certification details, and close investigation.",
                    safety_precautions="Complete technician manual sign-off before unlocking car dispatch for public passengers."
                ),
            ]

