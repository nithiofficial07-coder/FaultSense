"""FaultSense Phase 4 Retrieval & Evidence Packaging Demonstration CLI.

Executes semantic vector retrieval against the indexed elevator fault cases,
computes composite ranking scores, evaluates multi-factor evidence sufficiency,
surfaces candidate cross-subsystem fault propagation, and outputs structured evidence packages.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from src.retrieval.evidence import EvidencePackage
from src.retrieval.ranking import FilterMode, RankingStrategy
from src.retrieval.retrieval_service import FaultRetrievalService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def display_package(pkg: EvidencePackage) -> None:
    print(f"\n[QUERY DETAILS]")
    print(f"  * Subsystem     : {pkg.query.subsystem or 'Any'}")
    print(f"  * Fault Code    : {pkg.query.fault_code or 'None'}")
    print(f"  * Symptoms      : {', '.join(pkg.query.symptoms) if pkg.query.symptoms else 'None'}")
    print(f"  * Telemetry     : {pkg.query.telemetry if pkg.query.telemetry else 'None'}")
    print(f"  * Formulated Str: \"{pkg.query.formulated_text}\"")

    print(f"\n[EVIDENCE SUFFICIENCY EVALUATION]")
    suff = pkg.sufficiency
    print(f"  * Sufficiency Level : {suff.level.upper()} (Is Sufficient: {suff.is_sufficient})")
    print(f"  * Top Cosine Sim    : {suff.top_similarity:.4f}")
    print(f"  * Corroborating N   : {suff.corroborating_case_count} case(s)")
    for r in suff.reasons:
        print(f"    - Rationale: {r}")
    print(f"  * Safety Disclaimer : {suff.disclaimer}")

    if pkg.warnings:
        print(f"\n[WARNINGS & SYSTEM NOTICES]")
        for w in pkg.warnings:
            print(f"  [!] {w}")

    print(f"\n[FILTERING & STRATEGY]")
    print(f"  * Strategy : {pkg.ranking_strategy}")
    print(f"  * Filter   : {pkg.filter_explanation}")

    print(f"\n[RETRIEVED EVIDENCE ITEMS (Top {pkg.returned_count} of {pkg.total_candidates_searched} candidates evaluated)]")
    if not pkg.items:
        print("  (No matching cases found)")
        return

    for it in pkg.items:
        prov = "Synthetic Benchmark" if it.is_synthetic else "Verified Incident"
        print(f"\n  +-- Rank #{it.rank}: Case [{it.case_id}] ({it.subsystem.upper()} | Code: {it.fault_code})")
        print(f"  |   Source: \"{it.source_title}\" [Ref: {it.source_reference}] ({prov})")
        print(f"  |   Cosine Sim: {it.similarity_score:.4f} | Composite Score: {it.composite_score:.4f}")
        print(f"  |   Signal Breakdown: ExactCode={it.match_rationale.exact_fault_code_match}, ExactSub={it.match_rationale.exact_subsystem_match}, TelemOverlap={it.match_rationale.telemetry_feature_overlap}")
        print(f"  |   Confirmed Root Cause: {it.confirmed_root_cause}")
        print(f"  |   Corrective Action   : {it.corrective_action}")
        if it.candidate_propagation:
            prop = it.candidate_propagation
            print(f"  |   -> CANDIDATE PROPAGATION: {prop.source_subsystem} -> {prop.target_subsystem}")
            print(f"  |      Mechanism : {prop.propagation_mechanism}")
            print(f"  |      Field Test: {prop.diagnostic_check}")
            print(f"  |      Disclaimer: {prop.causality_disclaimer}")
        print(f"  +--------------------------------------------------------------------------")


def run_demonstration() -> None:
    service = FaultRetrievalService()

    # Scenario 1: Typical Door Obstruction / Optical Curtain Fault
    print_banner("SCENARIO 1: DOOR OBSTRUCTION & CURTAIN FAILURE (Exact Code + Symptoms)")
    pkg1 = service.retrieve_evidence(
        subsystem="door_system",
        fault_code="E-DR-201",
        symptoms=[
            "Passenger door reopened repeatedly without physical obstruction",
            "Door dwell timer warning sounded twice before closing",
        ],
        telemetry={"curtain_optical_attenuation_db": 6.8, "motor_current_peak_a": 3.8},
        top_k=3,
        filter_mode=FilterMode.SOFT_RERANK,
    )
    display_package(pkg1)

    # Scenario 2: Traction Drive Thermal Overload Fault
    print_banner("SCENARIO 2: TRACTION DRIVE THERMAL TRIP (VVVF Inverter Heat Sink)")
    pkg2 = service.retrieve_evidence(
        subsystem="traction_drive",
        fault_code="E-TR-102",
        symptoms=[
            "Drive inverter shut down on thermal alarm during afternoon peak traffic",
            "Car stalled between floors 14 and 15",
        ],
        telemetry={"heatsink_temperature_c": 87.5, "ambient_machine_room_temp_c": 36.2},
        top_k=3,
        filter_mode=FilterMode.SOFT_RERANK,
    )
    display_package(pkg2)

    # Scenario 3: Cross-Subsystem Cascading Fault (Brake Drag -> Traction Drive Trip)
    print_banner("SCENARIO 3: CROSS-SUBSYSTEM FAULT PROPAGATION (Brake Drag causing Drive Overload)")
    pkg3 = service.retrieve_evidence(
        subsystem="traction_drive",
        fault_code=None,  # No DTC code known by technician initially
        symptoms=[
            "Drive motor humming loudly during launch from landing",
            "Drive inverter trips on instantaneous over-current",
            "Distinct burning friction smell observed near hoist machine brake",
        ],
        telemetry={"motor_current_peak_a": 42.5},
        top_k=3,
        filter_mode=FilterMode.SOFT_RERANK,
    )
    display_package(pkg3)

    # Scenario 4: Out-of-Domain Unrelated Query (Evidence Sufficiency Failure)
    print_banner("SCENARIO 4: UNRELATED QUERY (Out-of-Domain / Low Evidence Demonstration)")
    pkg4 = service.retrieve_evidence(
        subsystem="door_system",
        fault_code=None,
        symptoms=[
            "Espresso coffee machine leaking water on breakroom kitchen table",
            "Filter basket overflowing with wet coffee grounds",
        ],
        top_k=3,
        filter_mode=FilterMode.SOFT_RERANK,
    )
    display_package(pkg4)


def main() -> None:
    parser = argparse.ArgumentParser(description="FaultSense Phase 4 Evidence Retrieval CLI")
    parser.add_argument("--subsystem", type=str, default=None, help="Elevator subsystem (e.g. door_system)")
    parser.add_argument("--fault-code", type=str, default=None, help="OEM Diagnostic Fault Code (e.g. E-DR-201)")
    parser.add_argument("--symptoms", type=str, default=None, help="Observed symptoms description")
    parser.add_argument("--top-k", type=int, default=3, help="Number of cases to retrieve")
    parser.add_argument("--strict", action="store_true", help="Enforce strict subsystem filtering")

    args = parser.parse_args()

    if args.symptoms or args.fault_code:
        service = FaultRetrievalService()
        filter_mode = FilterMode.STRICT if args.strict else FilterMode.SOFT_RERANK
        symptoms = [args.symptoms] if args.symptoms else []
        pkg = service.retrieve_evidence(
            subsystem=args.subsystem,
            fault_code=args.fault_code,
            symptoms=symptoms,
            top_k=args.top_k,
            filter_mode=filter_mode,
        )
        print_banner("CUSTOM TECHNICIAN RETRIEVAL QUERY")
        display_package(pkg)
    else:
        run_demonstration()


if __name__ == "__main__":
    main()
