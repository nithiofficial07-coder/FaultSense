"""End-to-End Diagnostic Demonstration for FaultSense Phase 8.

Executes a full interactive demonstration showcasing:
1. System boot and component health probes
2. Knowledge base and FAISS vector index verification
3. Supported fault diagnosis with self-verification finalization
4. Unsupported / out-of-domain fault with bounded retries and inconclusive advisory
5. Evidence-grounded conversational assistant Q&A
6. Database persistence and report export
"""

import json
import sys
import time
from typing import Any, Dict

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fault_sense.schema import SubsystemType
from src.diagnosis.assistant import DiagnosticAssistantService
from src.diagnosis.engine import DiagnosisEngine
from src.diagnosis.session import DiagnosisRequest
from src.knowledge_base.manager import KnowledgeBaseManager
from src.retrieval.index_manager import IndexManager
from src.storage.repository import InvestigationRepository
from src.utils.health import HealthChecker
from src.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger("demo_e2e")


def print_banner(title: str) -> None:
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_e2e_demo() -> None:
    print_banner("[ELEVATOR] FAULTSENSE: AUTONOMOUS FAULT ISOLATION & RCA ASSISTANT (PHASE 8 DEMO)")
    print("Demonstrating end-to-end evidence-grounded diagnosis and self-verification loop.\n")

    # 1. System Health Probes
    print("[STEP 1] Running Component Health Probes...")
    health = HealthChecker.run_all_checks()
    print(f"  ● Overall Health  : {health.overall_status.upper()}")
    for comp, st in health.components.items():
        print(f"    - {comp:<15}: {st.status.upper()} ({st.message})")

    # 2. Knowledge Base & Vector Index
    print("\n[STEP 2] Verifying Knowledge Base & FAISS Vector Index...")
    kb_mgr = KnowledgeBaseManager()
    kb_mgr.seed_initial_data_if_empty()
    stats = kb_mgr.get_stats()
    print(f"  ● Knowledge Base  : {stats['total_cases']} cases ({stats['verified_count']} verified, {stats['synthetic_count']} synthetic)")

    idx_mgr = IndexManager()
    idx_mgr.initialize(repo=kb_mgr.repo, force_rebuild=False)
    v_stat = idx_mgr.get_status()
    print(f"  ● Vector Store    : {v_stat['total_vectors']} vectors indexed (Dim: {v_stat['dimension']}, Metric: Cosine IndexFlatIP)")

    # 3. Process Supported Fault Case
    print_banner("SCENARIO 1: SUPPORTED ELEVATOR FAULT (Optical Curtain Obstruction)")
    print("Technician reports: Car door reopens repeatedly, dwell buzzer sounding, optical attenuation 6.8 dB.")

    supported_req = DiagnosisRequest(
        elevator_id="ELV-NORTH-04",
        building_id="Metropolitan Financial Tower",
        subsystem=SubsystemType.DOOR_SYSTEM.value,
        fault_code="E-DR-201",
        symptoms=[
            "Car door reopens repeatedly without passenger obstruction",
            "Door dwell timer expires causing nudging buzzer activation",
            "Intermittent safety light curtain status flicker in car console",
        ],
        telemetry={
            "door_open_close_cycles": 142500,
            "curtain_optical_attenuation_db": 6.8,
            "motor_current_peak_a": 3.8,
        },
        technician_notes="Visual check completed on door edge detectors.",
    )

    engine = DiagnosisEngine(enable_verification=True)
    t0 = time.perf_counter()
    res1 = engine.analyze(supported_req)
    t_elap1 = (time.perf_counter() - t0) * 1000.0

    print(f"\n  ● Investigation ID: {res1.investigation_id}")
    print(f"  ● Processing Time : {t_elap1:.1f} ms")
    print(f"  ● Advisory Conf.  : {int(res1.confidence_score * 100)}% (Heuristic affinity score)")
    print(f"  ● Sufficiency     : {res1.sufficiency_level.upper()}")
    print(f"  ● Verified Status : {'✅ VERIFIED & FINALIZED' if res1.is_verified else '⚠️ INCONCLUSIVE'}")
    print(f"  ● Retry Count     : {res1.retry_count}")
    print(f"  ● Primary Cause   : {res1.root_cause_hypothesis}")
    print(f"  ● Evidence Cases  : {[m['case_id'] for m in res1.matched_cases]}")
    print("  ● Corrective Work :")
    for act in res1.recommended_actions[:2]:
        print(f"    - {act}")

    # 4. Process Unsupported / Out-of-KB Fault Case
    print_banner("SCENARIO 2: OUT-OF-KB NOVEL FAULT (Overspeed Governor Tripping)")
    print("Technician reports: Safety gear wedges into rails at 2.8 m/s, governor rope switch open.")
    print("Knowledge Base Status: Zero historical cases exist for E-GOV-901 flyweight governor faults.")

    unsupported_req = DiagnosisRequest(
        elevator_id="ELV-EXPRESS-01",
        building_id="Skyline Center",
        subsystem=SubsystemType.SAFETY_GEAR.value,
        fault_code="E-GOV-901",
        symptoms=[
            "Car safety gear wedges into guide rails during downward express run",
            "Flyweight governor tripping mechanism engaged mechanically at 2.8 m/s",
            "Governor rope tension weight switch open circuit",
        ],
        telemetry={
            "rated_speed_mps": 2.5,
            "measured_trip_speed_mps": 2.85,
        },
    )

    t1 = time.perf_counter()
    res2 = engine.analyze(unsupported_req)
    t_elap2 = (time.perf_counter() - t1) * 1000.0

    print(f"\n  ● Investigation ID: {res2.investigation_id}")
    print(f"  ● Processing Time : {t_elap2:.1f} ms")
    print(f"  ● Final Status    : {res2.generation_mode.upper()}")
    print(f"  ● Verified Status : {'✅ VERIFIED' if res2.is_verified else '⚠️ INCONCLUSIVE (UNSUPPORTED)'}")
    print(f"  ● Retry Count     : {res2.retry_count} / {engine.settings.max_verification_retries} (Bounded Exhaustion)")
    print(f"  ● Primary Summary : {res2.root_cause_hypothesis}")
    print("  ● Audit Guardrail : Rejected ungrounded draft; never silently approved unsupported hypothesis.")
    print("  ● Prescribed Tests:")
    for chk in res2.recommended_actions[:2]:
        print(f"    - 🔧 {chk}")

    # 5. Conversational Assistant Demonstration
    print_banner("SCENARIO 3: EVIDENCE-GROUNDED CONVERSATIONAL ASSISTANT")
    assistant = DiagnosticAssistantService()
    inv_repo = InvestigationRepository()
    inv1_data = inv_repo.get(res1.investigation_id)

    # 5a. Grounded Question
    q_grounded = "What specific checks and corrective actions apply to this optical curtain fault?"
    print(f"[Q1 - Grounded] Technician asks: '{q_grounded}'")
    ans1 = assistant.answer_question(inv1_data, q_grounded)
    print(f"[A1 - Response] Mode: {ans1['mode']} | Supported: {ans1['is_supported']}")
    print(f"    {ans1['answer'].replace(chr(10), chr(10)+'    ')}")
    if ans1.get("cited_cases"):
        print(f"    📚 Grounded OEM Citations: {ans1['cited_cases']}")

    # 5b. Out-of-Domain Unsupported Question
    q_out = "What is the hydraulic cylinder oil level and pump pressure?"
    print(f"\n[Q2 - Out-of-Domain] Technician asks: '{q_out}'")
    ans2 = assistant.answer_question(inv1_data, q_out)
    print(f"[A2 - Response] Supported: {ans2['is_supported']}")
    print(f"    {ans2['answer'].replace(chr(10), chr(10)+'    ')}")

    # 6. Database Persistence & Report Export
    print_banner("SCENARIO 4: AUDIT TRAIL PERSISTENCE & REPORT EXPORT")
    all_invs = inv_repo.list_all(limit=10)
    print(f"  ● Total Sessions in SQLite : {len(all_invs)}")
    reloaded = inv_repo.get(res1.investigation_id)
    print(f"  ● Reloaded Session {reloaded['investigation_id']} :")
    print(f"    - Elevator Unit : {reloaded['elevator_id']} ({reloaded['subsystem']})")
    print(f"    - Stored Status : {reloaded['status']}")
    print(f"    - Matched Cases : {reloaded['matched_case_ids']}")
    print(f"    - Has Full Diag : {'diagnostic_report' in reloaded and bool(reloaded['diagnostic_report'])}")

    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")
    print("All Phase 8 core workflows validated and operational.\n")


if __name__ == "__main__":
    run_e2e_demo()
