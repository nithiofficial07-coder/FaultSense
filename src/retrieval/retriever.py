"""Retrieval interfaces and implementations for FaultSense.

Provides KeywordRetriever (SQLite FTS5), VectorRetriever (FAISS-CPU & all-MiniLM-L6-v2),
and HybridRetriever combining lexical and dense semantic signals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.retrieval.index_manager import IndexManager
from src.retrieval.vector_store import SearchResult
from src.storage.repository import FaultCaseRepository
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseRetriever(ABC):
    """Abstract retrieval strategy interface."""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        """Retrieves most relevant fault case records for a given symptom/query description."""


class KeywordRetriever(BaseRetriever):
    """Lexical retrieval using SQLite full-text search and keyword matching."""

    def __init__(self, repository: Optional[FaultCaseRepository] = None):
        self.repo = repository or FaultCaseRepository()

    def retrieve(
        self, query: str, top_k: int = 5, subsystem: Optional[str] = None, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Retrieves cases matching keywords in query or subsystem."""
        if not query.strip() and not subsystem:
            return []

        cases = self.repo.search(query=query, subsystem=subsystem, limit=top_k)
        results = []
        for rank, c in enumerate(cases, start=1):
            score = round(max(0.5, 1.0 - (rank - 1) * 0.08), 2)
            results.append({
                "case_id": c.case_id,
                "score": score,
                "subsystem": c.subsystem,
                "fault_code": c.fault_code,
                "confirmed_root_cause": c.confirmed_root_cause,
                "corrective_action": c.corrective_action,
                "source_title": c.source_title,
                "source_reference": c.source_reference,
                "verification_status": c.verification_status,
                "is_synthetic": c.is_synthetic,
                "symptoms": c.symptoms,
                "retrieval_method": "keyword_fts",
            })
        return results


class VectorRetriever(BaseRetriever):
    """Dense semantic vector retrieval using FAISS-CPU and normalized embeddings."""

    def __init__(self, index_manager: Optional[IndexManager] = None):
        self.index_manager = index_manager or IndexManager()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        subsystem: Optional[str] = None,
        fault_code: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
        score_threshold: Optional[float] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Performs cosine vector similarity search against the indexed fault cases."""
        search_results: List[SearchResult] = self.index_manager.search(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            subsystem=subsystem,
            fault_code=fault_code,
            is_synthetic=is_synthetic,
        )

        output: List[Dict[str, Any]] = []
        for sr in search_results:
            d = sr.to_dict()
            d["retrieval_method"] = "dense_vector_faiss"
            output.append(d)

        return output


class HybridRetriever(BaseRetriever):
    """Combines vector similarity and lexical matching for maximum recall and precision."""

    def __init__(
        self,
        vector_retriever: Optional[VectorRetriever] = None,
        keyword_retriever: Optional[KeywordRetriever] = None,
    ):
        self.vector_retriever = vector_retriever or VectorRetriever()
        self.keyword_retriever = keyword_retriever or KeywordRetriever()

    def retrieve(
        self, query: str, top_k: int = 5, subsystem: Optional[str] = None, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        # 1. Try vector retrieval first
        try:
            vec_results = self.vector_retriever.retrieve(
                query=query, top_k=top_k, subsystem=subsystem, **kwargs
            )
            if vec_results:
                return vec_results
        except Exception as exc:
            logger.warning("Vector retrieval failed (%s); falling back to keyword retrieval.", exc)

        # 2. Fall back to keyword retrieval
        return self.keyword_retriever.retrieve(query=query, top_k=top_k, subsystem=subsystem, **kwargs)
