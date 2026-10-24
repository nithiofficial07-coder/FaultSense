"""Configurable ranking strategies and metadata filtering modes for FaultSense.

Combines dense semantic vector similarity with exact categorical metadata matching
(fault codes, subsystem boundaries, telemetry overlaps) using documented, mathematically
principled weighting schemes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class FilterMode(str, Enum):
    """Controls how metadata constraints are applied during vector candidate retrieval."""
    STRICT = "strict"          # Hard constraint: excludes non-matching records entirely
    SOFT_RERANK = "soft_rerank"# Soft constraint: searches globally, boosts exact matches, surfaces cross-subsystem propagation
    NONE = "none"              # Pure dense vector search without metadata filters


class RankingStrategy(str, Enum):
    """Standardized weighting strategies balancing semantic and exact signals."""
    HYBRID_BALANCED = "hybrid_balanced"  # Default: 70% semantic, 18% fault code, 12% subsystem
    SEMANTIC_ONLY = "semantic_only"      # 100% semantic vector similarity
    CODE_PRIORITIZED = "code_prioritized"# 45% semantic, 40% fault code, 15% subsystem
    CUSTOM = "custom"                    # User-specified weight vector


@dataclass(frozen=True)
class RankingWeights:
    """Documented weights governing multi-signal candidate scoring.

    Rationale:
    - w_semantic (Default 0.70): Dense text embedding captures rich diagnostic descriptions,
      symptom nuances, and physical behavior that categorical codes cannot express.
    - w_fault_code (Default 0.18): Manufacturer DTC codes are highly specific; an exact match
      strongly corroborates diagnostic context.
    - w_subsystem (Default 0.12): Subsystem alignment verifies component boundary consistency
      without completely blinding the system to cross-subsystem cascading faults.
    - w_telemetry (Default 0.00 / dynamic): Measures overlap in sensor parameter regimes.
    """
    w_semantic: float = 0.70
    w_fault_code: float = 0.18
    w_subsystem: float = 0.12
    w_telemetry: float = 0.00

    def __post_init__(self) -> None:
        total = self.w_semantic + self.w_fault_code + self.w_subsystem + self.w_telemetry
        if total <= 0:
            raise ValueError("Total ranking weight sum must be strictly positive.")

    @classmethod
    def from_strategy(
        cls,
        strategy: RankingStrategy,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> RankingWeights:
        """Instantiates ranking weights based on an established strategy or custom dict."""
        if strategy == RankingStrategy.SEMANTIC_ONLY:
            return cls(w_semantic=1.00, w_fault_code=0.00, w_subsystem=0.00, w_telemetry=0.00)
        elif strategy == RankingStrategy.CODE_PRIORITIZED:
            return cls(w_semantic=0.45, w_fault_code=0.40, w_subsystem=0.15, w_telemetry=0.00)
        elif strategy == RankingStrategy.HYBRID_BALANCED:
            return cls(w_semantic=0.70, w_fault_code=0.18, w_subsystem=0.12, w_telemetry=0.00)
        elif strategy == RankingStrategy.CUSTOM:
            if not custom_weights:
                raise ValueError("custom_weights dictionary required for RankingStrategy.CUSTOM")
            return cls(
                w_semantic=float(custom_weights.get("w_semantic", 0.70)),
                w_fault_code=float(custom_weights.get("w_fault_code", 0.18)),
                w_subsystem=float(custom_weights.get("w_subsystem", 0.12)),
                w_telemetry=float(custom_weights.get("w_telemetry", 0.00)),
            )
        return cls()

    def compute_composite_score(
        self,
        semantic_sim: float,
        exact_code: bool,
        exact_subsystem: bool,
        telemetry_overlap: float = 0.0,
    ) -> Tuple[float, Dict[str, float]]:
        """Calculates normalized composite ranking score bounded in [0.0, 1.0]."""
        # Map cosine similarity from [-1.0, 1.0] to [0.0, 1.0] for non-negative weighting
        norm_semantic = max(0.0, min(1.0, (semantic_sim + 1.0) / 2.0))
        code_signal = 1.0 if exact_code else 0.0
        subsystem_signal = 1.0 if exact_subsystem else 0.0
        telem_signal = max(0.0, min(1.0, telemetry_overlap))

        weight_sum = self.w_semantic + self.w_fault_code + self.w_subsystem + self.w_telemetry
        raw_composite = (
            self.w_semantic * norm_semantic
            + self.w_fault_code * code_signal
            + self.w_subsystem * subsystem_signal
            + self.w_telemetry * telem_signal
        )
        composite = raw_composite / weight_sum

        breakdown = {
            "w_semantic": round(self.w_semantic / weight_sum, 4),
            "w_fault_code": round(self.w_fault_code / weight_sum, 4),
            "w_subsystem": round(self.w_subsystem / weight_sum, 4),
            "w_telemetry": round(self.w_telemetry / weight_sum, 4),
        }
        return round(composite, 4), breakdown


def explain_filter_mode(
    mode: FilterMode,
    subsystem: Optional[str] = None,
    fault_code: Optional[str] = None,
) -> str:
    """Provides a clear engineering explanation of metadata filtering implications."""
    sub_label = f"'{subsystem}'" if subsystem else "None"
    code_label = f"'{fault_code}'" if fault_code else "None"

    if mode == FilterMode.STRICT:
        return (
            f"STRICT FILTERING ACTIVE (Subsystem={sub_label}, Code={code_label}): "
            "Only cases matching these exact metadata tags are evaluated. "
            "CAUTION: Elevator faults frequently propagate across boundaries (e.g. guide-rail vibration "
            "causing door interlock contact bounce, or brake drag causing traction drive overload). "
            "Strict filtering eliminates semantically relevant cases originating in connected subsystems."
        )
    elif mode == FilterMode.SOFT_RERANK:
        return (
            f"SOFT RERANK ACTIVE (Target Subsystem={sub_label}, Target Code={code_label}): "
            "Vector similarity search explores the entire knowledge base to preserve cascading fault "
            "candidates across interconnected subsystems. Exact subsystem and fault code matches receive "
            "configured ranking boosts, and cross-subsystem candidates are surfaced with topology "
            "propagation hypotheses."
        )
    else:
        return (
            "NO FILTERING ACTIVE: Pure dense vector search across all indexed elevator cases regardless "
            "of subsystem or fault code category."
        )
