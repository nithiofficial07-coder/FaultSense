"""Elevator subsystem dependency and topology model for fault propagation analysis.

Represents physical, electrical, and control couplings between elevator subsystems.
Identifies candidate fault propagation relationships supported by engineering domain
knowledge without claiming proven causality from semantic similarity alone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class CandidatePropagation:
    """Represents a hypothesized physical or electrical coupling between subsystems."""
    source_subsystem: str
    target_subsystem: str
    coupling_type: str  # e.g. "series_electrical", "mechanical_drag", "sensor_feedback"
    propagation_mechanism: str
    diagnostic_check: str
    causality_disclaimer: str = (
        "Candidate propagation is a domain hypothesis based on elevator subsystem topology. "
        "Physical causality must be verified through on-site electrical isolation and "
        "mechanical inspection, and cannot be proven by vector similarity alone."
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ElevatorSubsystemTopology:
    """Domain model of elevator subsystem interconnections and failure propagation paths."""

    # Directed candidate propagation graph: (source, target) -> Propagation Details
    _COUPLINGS: Dict[Tuple[str, str], Dict[str, str]] = {
        ("door_system", "safety_circuit"): {
            "coupling_type": "series_electrical",
            "propagation_mechanism": (
                "Car gate switch and landing door interlock contacts are wired in series "
                "with the safety string. Mechanical door bounce, sill obstruction, or contact "
                "wear breaks the safety circuit, halting car dispatch."
            ),
            "diagnostic_check": "Inspect door interlock contact gap, sill debris, and safety relay PUD input.",
        },
        ("safety_circuit", "door_system"): {
            "coupling_type": "supervisory_control",
            "propagation_mechanism": (
                "Safety circuit trip commands immediate door motor inhibit or emergency "
                "door reopen sequence depending on passenger safety zoning."
            ),
            "diagnostic_check": "Verify safety circuit relay terminal voltage before door controller power-up.",
        },
        ("brake_system", "traction_drive"): {
            "coupling_type": "mechanical_drag",
            "propagation_mechanism": (
                "Brake shoe dragging or incomplete plunger lift imposes high mechanical friction "
                "on the drive sheave, leading to inverter over-current trips (OC), motor overheating, "
                "or leveling jerk."
            ),
            "diagnostic_check": "Measure brake coil pickup voltage, shoe air gap, and motor no-load current.",
        },
        ("traction_drive", "brake_system"): {
            "coupling_type": "handover_timing",
            "propagation_mechanism": (
                "Delayed drive torque prove-out or premature brake lift command during launch "
                "causes traction rollback and brake pad glazing."
            ),
            "diagnostic_check": "Check VVVF drive torque prove parameter and brake control contactor delay.",
        },
        ("traction_drive", "controller_electronics"): {
            "coupling_type": "sensor_feedback",
            "propagation_mechanism": (
                "Encoder pulse slip, tachometer jitter, or inverter DC-bus fluctuation feeds "
                "fault signals to the supervisory motion controller, triggering dispatch halts."
            ),
            "diagnostic_check": "Verify encoder shield grounding, cable routing, and drive bus ripple voltage.",
        },
        ("hoistway_structural", "door_system"): {
            "coupling_type": "mechanical_alignment",
            "propagation_mechanism": (
                "Guide rail misalignment or counterweight shoe play induces car canting during flight, "
                "skewing door clutch engagement with landing door interlock rollers."
            ),
            "diagnostic_check": "Check car sill to landing sill running clearance (standard 25-32 mm).",
        },
        ("hoistway_structural", "car_chassis_cab"): {
            "coupling_type": "mechanical_vibration",
            "propagation_mechanism": (
                "Rail joint offsets or worn roller guides transfer lateral acceleration and vibration "
                "into the cab frame, causing false slack-cable or load-weighing alarms."
            ),
            "diagnostic_check": "Measure guide rail plumbness, fishplate torque, and roller tire wear.",
        },
        ("controller_electronics", "safety_circuit"): {
            "coupling_type": "software_supervisory",
            "propagation_mechanism": (
                "Microprocessor watchdog timeout, emergency stop command, or phase failure board "
                "triggers the safety line drop relay, opening the safety string."
            ),
            "diagnostic_check": "Inspect controller fault log, 24VDC safety supply rail, and phase sequence.",
        },
        ("car_chassis_cab", "safety_circuit"): {
            "coupling_type": "series_electrical",
            "propagation_mechanism": (
                "Car emergency exit switch, inspection station stop switch, or safety gear plank "
                "switch opens the car top branch of the safety circuit."
            ),
            "diagnostic_check": "Check cab roof inspection box stop button and safety plank microswitch.",
        },
    }

    @classmethod
    def _normalize_sub(cls, val: str) -> str:
        s = val.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "brake_system": "braking_system",
            "brakes": "braking_system",
            "brake": "braking_system",
            "safety_circuit": "safety_gear",
            "safety_string": "safety_gear",
            "safety": "safety_gear",
            "hoistway": "hoistway_signaling",
            "hoistway_structural": "hoistway_signaling",
            "doors": "door_system",
            "doors_system": "door_system",
            "traction": "traction_drive",
            "vfd": "traction_drive",
            "drive": "traction_drive",
        }
        return aliases.get(s, s)

    @classmethod
    def get_candidate_propagation(
        cls,
        source_subsystem: Optional[str],
        target_subsystem: Optional[str],
    ) -> Optional[CandidatePropagation]:
        """Returns candidate propagation details between two subsystems if a known topology link exists."""
        if not source_subsystem or not target_subsystem:
            return None

        src = cls._normalize_sub(source_subsystem)
        tgt = cls._normalize_sub(target_subsystem)

        if src == tgt:
            return None

        # Check direct or alias match in couplings table
        for (k_src, k_tgt), coupling in cls._COUPLINGS.items():
            norm_k_src = cls._normalize_sub(k_src)
            norm_k_tgt = cls._normalize_sub(k_tgt)
            if src == norm_k_src and tgt == norm_k_tgt:
                return CandidatePropagation(
                    source_subsystem=source_subsystem.strip().lower(),
                    target_subsystem=target_subsystem.strip().lower(),
                    coupling_type=coupling["coupling_type"],
                    propagation_mechanism=coupling["propagation_mechanism"],
                    diagnostic_check=coupling["diagnostic_check"],
                )

        # Check reverse coupling
        for (k_src, k_tgt), coupling in cls._COUPLINGS.items():
            norm_k_src = cls._normalize_sub(k_src)
            norm_k_tgt = cls._normalize_sub(k_tgt)
            if src == norm_k_tgt and tgt == norm_k_src:
                return CandidatePropagation(
                    source_subsystem=source_subsystem.strip().lower(),
                    target_subsystem=target_subsystem.strip().lower(),
                    coupling_type=f"bi-directional ({coupling['coupling_type']})",
                    propagation_mechanism=(
                        f"Coupling documented in reverse direction ({k_src} -> {k_tgt}): "
                        f"{coupling['propagation_mechanism']}"
                    ),
                    diagnostic_check=coupling["diagnostic_check"],
                )

        return None

    @classmethod
    def get_connected_subsystems(cls, subsystem: str) -> List[str]:
        """Returns a list of subsystems with documented mechanical or electrical couplings."""
        sub = subsystem.lower().strip()
        connected = set()
        for (src, tgt) in cls._COUPLINGS.keys():
            if src == sub:
                connected.add(tgt)
            elif tgt == sub:
                connected.add(src)
        return sorted(list(connected))
