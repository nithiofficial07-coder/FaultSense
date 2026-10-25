"""Retrieval Service for FaultSense.

Retrieves relevant historical elevator fault cases using FAISS vector indexing,
applies configurable metadata filtering and composite ranking strategies,
evaluates multi-factor evidence sufficiency, surfaces candidate fault propagation,
and compiles a structured EvidencePackage for technician decision support.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from config.settings import get_settings
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase
from src.retrieval.document_builder import DocumentBuilder
from src.retrieval.evidence import (
    EvidenceItem,
    EvidencePackage,
    EvidenceQuery,
    EvidenceSufficiency,
    EvidenceSufficiencyLevel,
    MatchRationale,
)
from src.retrieval.index_manager import IndexManager
from src.retrieval.ranking import (
    FilterMode,
    RankingStrategy,
    RankingWeights,
    explain_filter_mode,
)
from src.retrieval.topology import CandidatePropagation, ElevatorSubsystemTopology
from src.retrieval.vector_store import SearchResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


def compute_telemetry_overlap(
    query_telem: Dict[str, Any],
    case_telem: Dict[str, Any],
) -> float:
    """Computes sensor telemetry overlap and numerical proximity bounded in [0.0, 1.0]."""
    if not query_telem or not case_telem:
        return 0.0

    q_keys = set(query_telem.keys())
    c_keys = set(case_telem.keys())
    common_keys = q_keys & c_keys
    if not common_keys:
        return 0.0

    key_jaccard = len(common_keys) / len(q_keys | c_keys)

    # Compute numerical proximity on common keys
    proximity_scores = []
    for k in common_keys:
        qv = query_telem[k]
        cv = case_telem[k]
        if isinstance(qv, (int, float)) and isinstance(cv, (int, float)):
            denom = max(abs(qv), abs(cv), 1.0)
            rel_diff = abs(qv - cv) / denom
            proximity_scores.append(max(0.0, 1.0 - rel_diff))
        elif str(qv).strip().lower() == str(cv).strip().lower():
            proximity_scores.append(1.0)
        else:
            proximity_scores.append(0.0)

    val_closeness = sum(proximity_scores) / len(proximity_scores) if proximity_scores else 0.5
    return round(0.4 * key_jaccard + 0.6 * val_closeness, 4)


class FaultRetrievalService:
    """Coordinates semantic vector search, metadata filtering, ranking, and evidence package assembly."""

    def __init__(
        self,
        index_manager: Optional[IndexManager] = None,
        repository: Optional[FaultCaseRepository] = None,
        topology: Optional[ElevatorSubsystemTopology] = None,
        default_ranking_strategy: RankingStrategy = RankingStrategy.HYBRID_BALANCED,
    ):
        settings = get_settings()
        self.repository = repository or FaultCaseRepository(db_path=str(settings.database_path))
        self.index_manager = index_manager or IndexManager()
        self.topology = topology or ElevatorSubsystemTopology()
        self.default_ranking_strategy = default_ranking_strategy

        # Ensure index is initialized
        if self.index_manager.total_vectors == 0:
            self.index_manager.initialize(self.repository)

    def retrieve_evidence(
        self,
        symptoms: Union[str, Sequence[str]],
        fault_code: Optional[str] = None,
        subsystem: Optional[str] = None,
        telemetry: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        filter_mode: FilterMode = FilterMode.SOFT_RERANK,
        ranking_strategy: Optional[RankingStrategy] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        verification_status_filter: Optional[str] = None,
        exclude_synthetic: bool = False,
    ) -> EvidencePackage:
        """Retrieves and packages relevant fault case evidence for diagnostic decision support.

        Args:
            symptoms: Natural-language symptoms as a list of strings or single text block.
            fault_code: Standardized or manufacturer diagnostic trouble code (e.g. 'E-DR-201').
            subsystem: Target elevator subsystem if known (e.g. 'door_system').
            telemetry: Dictionary of normalized sensor readings.
            top_k: Number of ranked cases to return in the evidence package.
            filter_mode: STRICT (hard filter), SOFT_RERANK (cross-subsystem with boost), or NONE.
            ranking_strategy: HYBRID_BALANCED, SEMANTIC_ONLY, CODE_PRIORITIZED, or CUSTOM.
            custom_weights: Optional dict defining custom w_semantic, w_fault_code, etc.
            verification_status_filter: Optional filter ('verified_incident', 'synthetic_benchmark').
            exclude_synthetic: If True, filters out synthetic benchmark cases.

        Returns:
            EvidencePackage containing query data, ranked evidence items, sufficiency evaluation,
            and topology propagation candidate links.
        """
        # 1. Normalize and clean input parameters
        symptoms_list: List[str] = []
        if isinstance(symptoms, str):
            symptoms_list = [s.strip() for s in symptoms.replace(";", "\n").splitlines() if s.strip()]
        elif symptoms:
            symptoms_list = [str(s).strip() for s in symptoms if str(s).strip()]

        clean_fault_code = fault_code.strip() if fault_code and fault_code.strip() else None
        clean_subsystem = (
            subsystem.strip().lower()
            if subsystem and subsystem.strip().lower() not in ("all", "other", "")
            else None
        )
        clean_telemetry = telemetry if isinstance(telemetry, dict) else {}
        clean_top_k = max(1, int(top_k))
        active_strategy = ranking_strategy or self.default_ranking_strategy
        weights = RankingWeights.from_strategy(active_strategy, custom_weights)

        # 2. Formulate canonical query text
        symptoms_text = " | ".join(symptoms_list) if symptoms_list else ""
        telem_text = ""
        if clean_telemetry:
            telem_parts = [f"{k}={v}" for k, v in sorted(clean_telemetry.items())]
            telem_text = f"Telemetry: {', '.join(telem_parts)}"

        combined_symptom_str = f"{symptoms_text} {telem_text}".strip()
        formulated_query = DocumentBuilder.build_query_document(
            query=combined_symptom_str,
            subsystem=clean_subsystem,
            fault_code=clean_fault_code,
        )

        query_record = EvidenceQuery(
            symptoms=symptoms_list,
            fault_code=clean_fault_code,
            subsystem=clean_subsystem,
            telemetry=clean_telemetry,
            formulated_text=formulated_query,
            top_k=clean_top_k,
        )

        # 3. Vector Similarity Search via FAISS
        total_vectors = self.index_manager.total_vectors
        if total_vectors == 0 or (not formulated_query.strip()):
            return self._build_empty_package(
                query=query_record,
                filter_mode=filter_mode,
                strategy_name=active_strategy.value,
                total_candidates=total_vectors,
                reason="Knowledge base vector index is empty or query is blank.",
            )

        # Embed query text
        query_vec = self.index_manager.embedding_generator.encode(formulated_query, normalize=True)

        # Execute vector search based on filter mode
        # In SOFT_RERANK or NONE mode, we retrieve an expanded pool to evaluate cross-subsystem candidates
        subsystem_hard_filter = clean_subsystem if filter_mode == FilterMode.STRICT else None
        is_synth_filter = False if exclude_synthetic else None
        pool_size = clean_top_k if filter_mode == FilterMode.STRICT else max(clean_top_k * 4, 30)

        raw_search_results: List[SearchResult] = self.index_manager.vector_store.search(
            query_vector=query_vec,
            top_k=pool_size,
            subsystem=subsystem_hard_filter,
            is_synthetic=is_synth_filter,
        )

        # 4. Map to Records, Evaluate Metadata Matches, and Score
        scored_items: List[EvidenceItem] = []
        for res in raw_search_results:
            rec = res.record

            # Additional metadata filtering if requested
            if verification_status_filter:
                if rec.verification_status.lower() != verification_status_filter.lower().strip():
                    continue

            # Load full case from repository for deep attributes if present
            full_case = self.repository.get(rec.case_id)
            case_symptoms = full_case.symptoms if full_case else []
            case_telem = full_case.telemetry_summary if full_case else {}

            # Exact match evaluations
            exact_code = bool(
                clean_fault_code
                and rec.fault_code
                and clean_fault_code.upper() == rec.fault_code.strip().upper()
            )
            exact_sub = bool(
                clean_subsystem
                and rec.subsystem
                and clean_subsystem.lower() == rec.subsystem.strip().lower()
            )
            telem_overlap = compute_telemetry_overlap(clean_telemetry, case_telem)

            # Compute composite ranking score
            composite, weights_breakdown = weights.compute_composite_score(
                semantic_sim=res.score,
                exact_code=exact_code,
                exact_subsystem=exact_sub,
                telemetry_overlap=telem_overlap,
            )

            rationale = MatchRationale(
                semantic_similarity=round(res.score, 4),
                exact_fault_code_match=exact_code,
                exact_subsystem_match=exact_sub,
                telemetry_feature_overlap=telem_overlap,
                composite_score=composite,
                weights_applied=weights_breakdown,
            )

            # Check candidate fault propagation if subsystems differ
            candidate_propagation: Optional[CandidatePropagation] = None
            if clean_subsystem and rec.subsystem.lower() != clean_subsystem.lower():
                candidate_propagation = self.topology.get_candidate_propagation(
                    source_subsystem=rec.subsystem,
                    target_subsystem=clean_subsystem,
                )

            item = EvidenceItem(
                case_id=rec.case_id,
                rank=0,  # Will be set after sorting
                similarity_score=round(res.score, 4),
                composite_score=composite,
                subsystem=rec.subsystem,
                fault_code=rec.fault_code,
                symptoms=case_symptoms,
                telemetry_summary=case_telem,
                confirmed_root_cause=rec.confirmed_root_cause,
                corrective_action=rec.corrective_action,
                source_title=rec.source_title,
                source_reference=rec.source_reference,
                source_type=rec.source_type,
                verification_status=rec.verification_status,
                is_synthetic=rec.is_synthetic,
                match_rationale=rationale,
                candidate_propagation=candidate_propagation,
                document_text=rec.document_text,
            )
            scored_items.append(item)

        # 5. Deduplicate and filter out noise floor items
        seen_case_ids: Set[str] = set()
        unique_scored_items: List[EvidenceItem] = []
        for it in scored_items:
            if it.case_id not in seen_case_ids:
                seen_case_ids.add(it.case_id)
                unique_scored_items.append(it)

        # Relevance filtering: Exclude items below noise floor unless corroborated
        retained_items: List[EvidenceItem] = []
        for it in unique_scored_items:
            has_dtc = it.match_rationale.exact_fault_code_match
            has_sub = it.match_rationale.exact_subsystem_match
            has_prop = it.candidate_propagation is not None
            sim = it.similarity_score
            comp = it.composite_score

            if has_dtc:
                retained_items.append(it)
            elif (clean_subsystem is None or has_sub) and (sim >= 0.25 or comp >= 0.28):
                retained_items.append(it)
            elif has_prop and (sim >= 0.30 or comp >= 0.35):
                retained_items.append(it)
            elif sim >= 0.35 or comp >= 0.38:
                retained_items.append(it)

        retained_items.sort(key=lambda it: (it.composite_score, it.similarity_score), reverse=True)
        final_items = retained_items[:clean_top_k]

        # Assign final rank
        for rank, item in enumerate(final_items, start=1):
            item.rank = rank

        # 6. Evaluate Multi-Factor Evidence Sufficiency
        sufficiency, warnings = self._evaluate_evidence_sufficiency(
            items=final_items,
            query=query_record,
            filter_mode=filter_mode,
        )

        filter_expl = explain_filter_mode(filter_mode, clean_subsystem, clean_fault_code)

        return EvidencePackage(
            query=query_record,
            items=final_items,
            total_candidates_searched=len(raw_search_results),
            returned_count=len(final_items),
            sufficiency=sufficiency,
            filter_explanation=filter_expl,
            ranking_strategy=active_strategy.value,
            warnings=warnings,
        )

    def _evaluate_evidence_sufficiency(
        self,
        items: List[EvidenceItem],
        query: EvidenceQuery,
        filter_mode: FilterMode,
    ) -> Tuple[EvidenceSufficiency, List[str]]:
        """Conducts a multi-factor evidence sufficiency evaluation.

        Design Principles:
        1. Avoids universal arbitrary thresholds.
        2. Never equates cosine similarity to a probability of mechanical correctness.
        3. Looks for corroboration, exact code alignment, and semantic margin above noise floor.
        """
        warnings: List[str] = []

        if not items:
            return (
                EvidenceSufficiency(
                    level=EvidenceSufficiencyLevel.INSUFFICIENT.value,
                    is_sufficient=False,
                    top_similarity=0.0,
                    corroborating_case_count=0,
                    reasons=["No historical cases matched query or filter constraints."],
                ),
                ["Zero historical records retrieved. Standard physical inspection required."],
            )

        top_item = items[0]
        top_sim = top_item.similarity_score
        has_exact_code = any(it.match_rationale.exact_fault_code_match for it in items)
        has_exact_sub = any(it.match_rationale.exact_subsystem_match for it in items)

        # Check corroboration across top results: matching root causes or consistent subsystem
        corroboration_count = 1
        top_sub = top_item.subsystem
        for other in items[1:]:
            if other.subsystem == top_sub and other.similarity_score >= 0.40:
                corroboration_count += 1

        reasons: List[str] = []

        # Embedding noise floor check (all-MiniLM-L6-v2 cosine for unrelated elevator texts is ~0.25 - 0.35)
        if top_sim < 0.35 and not has_exact_code:
            level = EvidenceSufficiencyLevel.INSUFFICIENT.value
            is_sufficient = False
            reasons.append(
                f"Top semantic similarity ({top_sim:.4f}) is at or below the domain noise floor (~0.35). "
                "Query symptoms appear unrelated to indexed elevator cases or describe an unindexed failure mode."
            )
            warnings.append(
                "Evidence Insufficient: Low textual alignment. Rely on OEM schematics and multimeter checks."
            )
        elif top_sim < 0.48 and not has_exact_code:
            level = EvidenceSufficiencyLevel.LOW.value
            is_sufficient = False
            reasons.append(
                f"Top semantic similarity ({top_sim:.4f}) is marginal. Symptoms provide weak partial alignment "
                "without an exact fault code anchor."
            )
            warnings.append("Low Evidence: Historical alignment is partial; use as secondary advisory guidance.")
        elif (top_sim >= 0.62 and has_exact_sub) or (has_exact_code and top_sim >= 0.45):
            level = EvidenceSufficiencyLevel.HIGH.value
            is_sufficient = True
            reasons.append(
                f"Strong evidence: High semantic similarity ({top_sim:.4f}) corroborated by "
                f"{'exact fault code match' if has_exact_code else 'exact subsystem alignment'}. "
                f"Corroborated by {corroboration_count} candidate case(s)."
            )
        else:
            level = EvidenceSufficiencyLevel.MODERATE.value
            is_sufficient = True
            reasons.append(
                f"Moderate evidence: Semantic similarity ({top_sim:.4f}) provides meaningful symptom overlap. "
                f"Supported by {corroboration_count} case(s)."
            )

        # Check for cross-subsystem candidates
        cross_sub_items = [it for it in items if it.candidate_propagation is not None]
        if cross_sub_items:
            reasons.append(
                f"{len(cross_sub_items)} retrieved case(s) originate from coupled subsystems with candidate fault propagation paths."
            )
            warnings.append(
                "Cross-subsystem candidates surfaced. Review candidate propagation topology before replacing parts."
            )

        # Check for synthetic-only provenance
        if all(it.is_synthetic for it in items):
            warnings.append(
                "Notice: Top evidence originates solely from synthetic benchmark cases; no verified field incident recorded."
            )

        sufficiency = EvidenceSufficiency(
            level=level,
            is_sufficient=is_sufficient,
            top_similarity=round(top_sim, 4),
            corroborating_case_count=corroboration_count,
            reasons=reasons,
        )

        return sufficiency, warnings

    def _build_empty_package(
        self,
        query: EvidenceQuery,
        filter_mode: FilterMode,
        strategy_name: str,
        total_candidates: int,
        reason: str,
    ) -> EvidencePackage:
        """Constructs an explicit empty evidence package."""
        return EvidencePackage(
            query=query,
            items=[],
            total_candidates_searched=total_candidates,
            returned_count=0,
            sufficiency=EvidenceSufficiency(
                level=EvidenceSufficiencyLevel.INSUFFICIENT.value,
                is_sufficient=False,
                top_similarity=0.0,
                corroborating_case_count=0,
                reasons=[reason],
            ),
            filter_explanation=explain_filter_mode(filter_mode, query.subsystem, query.fault_code),
            ranking_strategy=strategy_name,
            warnings=[reason],
        )
