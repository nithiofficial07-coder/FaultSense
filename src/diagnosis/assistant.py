"""Conversational diagnostic assistant service for technician follow-up Q&A.

Ensures evidence-grounded responses strictly scoped to the active investigation session,
with explicit rejection of unsupported inquiries.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from config.settings import get_settings
from src.diagnosis.llm import BaseLLMProvider, get_llm_provider
from src.utils.logger import get_logger

logger = get_logger(__name__)


ASSISTANT_SYSTEM_PROMPT = """You are FaultSense Assistant, an industrial diagnostic decision support assistant for certified vertical transportation technicians.
You are assisting a technician currently investigating an elevator fault.

STRICT OPERATIONAL DIRECTIVES:
1. ONLY use the verified facts, symptoms, telemetry readings, diagnostic findings, and retrieved historical cases provided in the INVESTIGATION CONTEXT below.
2. If the technician asks a question that is NOT addressed or supported by the provided investigation evidence, you MUST explicitly state:
   "This question cannot be answered from the evidence retrieved for this investigation."
   Explain what evidence is missing and recommend what physical check or OEM bulletin the technician should consult.
3. NEVER guess, speculate, or fabricate elevator specifications, fault codes, or wiring schematics not present in the context.
4. Always cite specific historical case IDs (e.g. CASE-SYNTH-ELEV-001) when referencing past incidents, confirmed root causes, or corrective actions.
5. NEVER recommend bypassing safety circuits, door locks, governor switches, or hoistway interlocks.
6. Keep answers technical, concise, and focused on technician safety and physical diagnostic steps.
"""


class DiagnosticAssistantService:
    """Provides evidence-grounded conversational assistance scoped to an investigation."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.settings = get_settings()
        self.llm_provider = llm_provider

    def _get_provider(self) -> Optional[BaseLLMProvider]:
        if self.llm_provider is not None:
            return self.llm_provider
        if not self.settings.is_demo_mode:
            try:
                return get_llm_provider()
            except Exception as exc:
                logger.warning("LLM provider unavailable for assistant; using deterministic fallback: %s", exc)
                return None
        return None

    def answer_question(
        self,
        investigation: Dict[str, Any],
        question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Answers a technician's follow-up question scoped strictly to the investigation."""
        q_clean = question.strip()
        if not q_clean:
            return {
                "answer": "Please ask a specific diagnostic question regarding this investigation.",
                "is_supported": True,
                "cited_cases": [],
                "mode": "validation",
            }

        provider = self._get_provider()
        if provider is not None:
            try:
                return self._answer_with_llm(provider, investigation, q_clean, chat_history or [])
            except Exception as exc:
                logger.warning("Assistant LLM inference failed (%s); engaging deterministic fallback.", exc)

        return self._answer_deterministic(investigation, q_clean)

    def _build_context_prompt(self, inv: Dict[str, Any]) -> str:
        """Serializes investigation details into a formatted context block."""
        symptoms = inv.get("symptoms", [])
        if isinstance(symptoms, list):
            symptoms_str = "\n".join(f"- {s}" for s in symptoms)
        else:
            symptoms_str = str(symptoms)

        telemetry = inv.get("telemetry", {})
        diag_report = inv.get("diagnostic_report") or {}
        verif_rec = inv.get("verification_record") or {}

        # Format candidates
        candidates = diag_report.get("candidate_causes", [])
        cand_str = ""
        for c in candidates:
            c_cites = ", ".join(c.get("supporting_case_ids", [])) or "None"
            cand_str += f"\n- [{c.get('rank', 1)}] {c.get('hypothesis_title')} ({c.get('probability_band', 'possible')}): {c.get('explanation')}\n  Supporting Cases: {c_cites}\n"
            if c.get("recommended_checks"):
                cand_str += f"  Checks: {'; '.join(c.get('recommended_checks', []))}\n"
            if c.get("documented_corrective_actions"):
                cand_str += f"  Corrective Actions: {'; '.join(c.get('documented_corrective_actions', []))}\n"

        # Format matched historical cases
        matched_cases = []
        evid_pkg = inv.get("evidence_package") or {}
        if evid_pkg and "evidence_items" in evid_pkg:
            matched_cases = evid_pkg.get("evidence_items", [])
        elif inv.get("matched_case_ids"):
            from src.knowledge_base.manager import KnowledgeBaseManager
            try:
                kb = KnowledgeBaseManager()
                for cid in inv["matched_case_ids"]:
                    c_obj = kb.repo.get(cid)
                    if c_obj:
                        matched_cases.append(c_obj.to_dict())
            except Exception:
                pass

        cases_str = ""
        for mc in matched_cases:
            cid = mc.get("case_id", "N/A")
            sub = mc.get("subsystem", "N/A")
            rc = mc.get("confirmed_root_cause", "N/A")
            ca = mc.get("corrective_action", "N/A")
            cases_str += f"\n[Case {cid} | Subsystem: {sub}]\n- Root Cause: {rc}\n- Corrective Action: {ca}\n"

        context = f"""=== ACTIVE INVESTIGATION CONTEXT ===
Investigation ID: {inv.get('investigation_id', 'UNKNOWN')}
Elevator Unit: {inv.get('elevator_id', 'UNKNOWN')} (Building: {inv.get('building_id') or 'N/A'})
Subsystem: {inv.get('subsystem', 'UNKNOWN')}
Reported Fault Code: {inv.get('fault_code') or 'None'}
Status: {inv.get('status', 'open')} (Confidence Score: {inv.get('confidence_score', 0.0)})

REPORTED SYMPTOMS:
{symptoms_str or 'None reported'}

TELEMETRY / SENSOR READINGS:
{json.dumps(telemetry, indent=2) if telemetry else 'No telemetry recorded'}

SYNTHESIZED ROOT CAUSE:
{inv.get('root_cause_hypothesis', 'None')}

RECOMMENDED ACTIONS:
{inv.get('recommended_actions', 'None')}

RANKED CANDIDATE ROOT CAUSES:
{cand_str or 'None documented'}

VERIFICATION OUTCOME:
Status: {verif_rec.get('final_status', 'N/A')} | Verdict: {verif_rec.get('final_verdict', 'N/A')} | Retries: {inv.get('retry_count', 0)}

RETRIEVED HISTORICAL EVIDENCE CASES:
{cases_str or 'No historical cases attached'}
====================================
"""
        return context

    def _answer_with_llm(
        self,
        provider: BaseLLMProvider,
        inv: Dict[str, Any],
        question: str,
        chat_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Executes LLM inquiry under strict anti-hallucination prompt."""
        context = self._build_context_prompt(inv)

        history_str = ""
        if chat_history:
            history_str = "PREVIOUS CONVERSATION TURNS:\n"
            for turn in chat_history[-6:]:
                role = "Technician" if turn.get("role") == "user" else "Assistant"
                history_str += f"{role}: {turn.get('content')}\n"
            history_str += "\n"

        user_prompt = f"""{context}

{history_str}TECHNICIAN QUESTION:
{question}

Provide your evidence-grounded response. If unsupported by the investigation context, reject it explicitly as instructed."""

        response_text = provider.generate(
            prompt=user_prompt,
            system_instruction=ASSISTANT_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=600,
        )

        is_supported = "This question cannot be answered from the evidence" not in response_text
        cited_cases = [cid for cid in inv.get("matched_case_ids", []) if cid in response_text]

        return {
            "answer": response_text.strip(),
            "is_supported": is_supported,
            "cited_cases": cited_cases,
            "mode": f"llm_{provider.provider_name}",
        }

    def _answer_deterministic(self, inv: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Deterministic offline fallback answering based on grounded investigation fields."""
        q_lower = question.lower()
        inv_id = inv.get("investigation_id", "Current Investigation")
        elv_id = inv.get("elevator_id", "Elevator")
        sub = inv.get("subsystem", "subsystem")
        matched_cases = inv.get("matched_case_ids", [])

        unsupported_keywords = [
            "hydraulic", "piston", "valve", "oil level", "escalator", "moving walk",
            "weather", "forecast", "recipe", "password", "hack", "bypass", "joke",
            "stock", "price", "president", "sports", "football"
        ]
        inv_text = (
            str(inv.get("symptoms", [])) + " " +
            str(inv.get("subsystem", "")) + " " +
            str(inv.get("root_cause_hypothesis", ""))
        ).lower()

        for kw in unsupported_keywords:
            if kw in q_lower and kw not in inv_text:
                return {
                    "answer": (
                        f"**Unsupported Question**: The inquiry regarding '{kw}' cannot be answered from "
                        f"the evidence retrieved for investigation `{inv_id}` ({elv_id}, Subsystem: `{sub}`).\n\n"
                        f"No relevant telemetry or historical maintenance records in this session address '{kw}'. "
                        f"Please consult the OEM technical manual or perform on-site physical diagnostic checks."
                    ),
                    "is_supported": False,
                    "cited_cases": [],
                    "mode": "deterministic_fallback",
                }

        # 1. Telemetry / Sensors
        if any(w in q_lower for w in ["telemetry", "sensor", "reading", "value", "voltage", "current", "cycle"]):
            telemetry = inv.get("telemetry", {})
            if telemetry:
                items = "\n".join(f"- **{k}**: `{v}`" for k, v in telemetry.items())
                ans = f"Recorded telemetry readings for **{elv_id}** ({inv_id}):\n\n{items}"
            else:
                ans = f"No physical telemetry readings were uploaded for investigation `{inv_id}`."
            return {"answer": ans, "is_supported": True, "cited_cases": [], "mode": "deterministic_fallback"}

        # 2. Symptoms
        if any(w in q_lower for w in ["symptom", "observed", "complaint", "reported"]):
            symptoms = inv.get("symptoms", [])
            s_str = "\n".join(f"- {s}" for s in symptoms) if symptoms else "None recorded."
            ans = f"Reported symptoms for **{elv_id}** (Fault Code: `{inv.get('fault_code') or 'None'}`):\n\n{s_str}"
            return {"answer": ans, "is_supported": True, "cited_cases": [], "mode": "deterministic_fallback"}

        # 3. Root Cause / Hypothesis
        if any(w in q_lower for w in ["root cause", "cause", "why", "hypothesis", "reason"]):
            rc = inv.get("root_cause_hypothesis", "No root cause synthesized.")
            diag_rep = inv.get("diagnostic_report") or {}
            cands = diag_rep.get("candidate_causes", [])
            cand_txt = ""
            if cands:
                cand_txt = "\n\n**Candidate Causes**:\n" + "\n".join(
                    f"{c.get('rank', 1)}. **{c.get('hypothesis_title')}** ({c.get('probability_band', 'possible')}): "
                    f"{c.get('explanation')} *(Citations: {', '.join(c.get('supporting_case_ids', [])) or 'None'})*"
                    for c in cands
                )
            ans = f"**Primary Root Cause Hypothesis** for `{inv_id}`:\n\n{rc}{cand_txt}"
            cites = [cid for cid in matched_cases if cid in ans]
            return {"answer": ans, "is_supported": True, "cited_cases": cites, "mode": "deterministic_fallback"}

        # 4. Corrective Actions / Steps
        if any(w in q_lower for w in ["action", "step", "corrective", "fix", "repair", "resolve"]):
            actions = inv.get("recommended_actions", "No corrective actions documented.")
            ans = f"**Documented Corrective Actions** for `{inv_id}`:\n\n{actions}"
            return {"answer": ans, "is_supported": True, "cited_cases": matched_cases, "mode": "deterministic_fallback"}

        # 5. Diagnostic Checks / Testing
        if any(w in q_lower for w in ["check", "meter", "multimeter", "test", "inspect", "probe"]):
            diag_rep = inv.get("diagnostic_report") or {}
            checks: List[str] = []
            for c in diag_rep.get("candidate_causes", []):
                checks.extend(c.get("recommended_checks", []))
            if checks:
                chk_str = "\n".join(f"- {c}" for c in set(checks))
                ans = f"**Recommended Diagnostic Checks** for `{inv_id}`:\n\n{chk_str}"
            else:
                ans = (
                    f"Perform standard LOTO isolation and verify physical connections on elevator `{elv_id}` "
                    f"subsystem `{sub}`."
                )
            return {"answer": ans, "is_supported": True, "cited_cases": [], "mode": "deterministic_fallback"}

        # 6. Safety Advisories
        if any(w in q_lower for w in ["safety", "hazard", "loto", "lockout", "precaution"]):
            diag_rep = inv.get("diagnostic_report") or {}
            safeties = diag_rep.get("safety_advisories", [
                "De-energize main controller breaker and execute Lockout/Tagout (LOTO) prior to servicing.",
                "Ensure elevator is parked and mechanically secured before inspecting hoistway or landing sills.",
            ])
            s_str = "\n".join(f"- {s}" for s in safeties)
            ans = f"**Mandatory Technician Safety Advisories**:\n\n{s_str}"
            return {"answer": ans, "is_supported": True, "cited_cases": [], "mode": "deterministic_fallback"}

        # 7. Historical Cases / Evidence Citations
        if any(w in q_lower for w in ["case", "evidence", "citation", "reference", "history", "oem"]):
            c_str = ", ".join(f"`{cid}`" for cid in matched_cases) if matched_cases else "None"
            ans = (
                f"Investigation `{inv_id}` retrieved **{len(matched_cases)}** historical evidence records: {c_str}.\n\n"
                f"Verification Status: `{inv.get('status')}` (Retry Count: {inv.get('retry_count', 0)})."
            )
            return {"answer": ans, "is_supported": True, "cited_cases": matched_cases, "mode": "deterministic_fallback"}

        # Default contextual synthesis
        ans = (
            f"**Investigation Summary (`{inv_id}`)**:\n"
            f"- **Unit**: `{elv_id}` ({inv.get('subsystem', 'N/A')})\n"
            f"- **Primary Hypothesis**: {inv.get('root_cause_hypothesis', 'N/A')}\n"
            f"- **Recommended Actions**: {inv.get('recommended_actions', 'N/A')}\n"
            f"- **Associated Evidence Cases**: {', '.join(f'`{c}`' for c in matched_cases) or 'None'}\n\n"
            f"_You can ask about specific telemetry readings, root causes, corrective actions, diagnostic checks, or safety advisories._"
        )
        return {"answer": ans, "is_supported": True, "cited_cases": matched_cases, "mode": "deterministic_fallback"}
