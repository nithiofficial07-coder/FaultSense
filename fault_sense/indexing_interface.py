"""Indexing & Embedding Interface for FaultSense.

Provides a clean, modular adapter connecting the structured Knowledge Base
to future vector indexing and embedding pipelines (e.g., Chroma, FAISS, Qdrant).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase


@dataclass
class EmbeddingDocument:
    """Standardized document payload ready for vector indexing."""
    doc_id: str
    text: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FaultCaseIndexingAdapter:
    """Prepares structured fault case records for semantic embedding and vector indexing."""

    def __init__(self, default_format: str = "rich"):
        self.default_format = default_format

    def case_to_document(self, case: FaultCase, format_style: Optional[str] = None) -> EmbeddingDocument:
        """Transforms a FaultCase entity into a vector database ingestion payload."""
        style = format_style or self.default_format
        text_content = case.to_embedding_text(format_style=style)

        # Standard vector DB payload metadata
        metadata = {
            "case_id": case.case_id,
            "subsystem": case.subsystem,
            "fault_code": case.fault_code,
            "source_type": case.source_type,
            "verification_status": case.verification_status,
            "is_synthetic": case.is_synthetic,
            "source_title": case.source_title,
            "source_reference": case.source_reference,
            "timestamp": case.timestamp or "",
        }

        return EmbeddingDocument(doc_id=case.case_id, text=text_content, metadata=metadata)

    def prepare_batch(
        self, cases: Sequence[FaultCase], format_style: Optional[str] = None
    ) -> List[EmbeddingDocument]:
        """Converts an iterable of FaultCase records into EmbeddingDocuments."""
        return [self.case_to_document(c, format_style=format_style) for c in cases]

    def get_pending_documents(
        self, repo: FaultCaseRepository, limit: int = 100, format_style: Optional[str] = None
    ) -> List[EmbeddingDocument]:
        """Fetches unindexed cases from the repository and formats them as documents."""
        unindexed_cases = repo.get_unindexed(limit=limit)
        return self.prepare_batch(unindexed_cases, format_style=format_style)

    def confirm_indexed(self, repo: FaultCaseRepository, doc_ids: Sequence[str]) -> int:
        """Notifies the repository that the given documents have been embedded and stored."""
        return repo.mark_as_indexed(doc_ids)

    @staticmethod
    def to_chroma_payload(docs: Sequence[EmbeddingDocument]) -> Dict[str, List[Any]]:
        """Formats documents into ChromaDB's native collection.add kwargs structure."""
        return {
            "ids": [d.doc_id for d in docs],
            "documents": [d.text for d in docs],
            "metadatas": [d.metadata for d in docs],
        }

    @staticmethod
    def to_generic_vector_payload(
        docs: Sequence[EmbeddingDocument],
    ) -> List[Dict[str, Any]]:
        """Formats documents for general vector DBs (e.g. Qdrant, Pinecone)."""
        return [{"id": d.doc_id, "text": d.text, "payload": d.metadata} for d in docs]
