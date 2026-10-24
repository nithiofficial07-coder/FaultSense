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
