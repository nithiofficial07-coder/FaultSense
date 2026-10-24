"""FAISS Vector Store with explicit metadata mapping and secure persistence.

Implements cosine similarity search with faiss.IndexFlatIP on normalized vectors.
Maintains persistent, non-pickle JSON metadata mappings between vector row positions
and fault case records with atomic, recoverable save/load semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import faiss
import numpy as np

from fault_sense.schema import FaultCase
from src.retrieval.document_builder import DocumentBuilder
from src.retrieval.embeddings import (
    EMBEDDING_DIMENSION,
    BaseEmbeddingGenerator,
    normalize_vectors,
)
from src.utils.exceptions import RetrievalError
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VectorRecord:
    """Explicit mapping entry linking a FAISS row position to case metadata."""
    vector_id: int
    case_id: str
    source_title: str
    source_reference: str
    source_type: str
    verification_status: str
    subsystem: str
    fault_code: str
    confirmed_root_cause: str
    corrective_action: str
    is_synthetic: bool
    document_text: str
    indexed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> VectorRecord:
        """Safely deserializes and validates a metadata record dictionary."""
        required = [
            "vector_id",
            "case_id",
            "source_title",
            "source_reference",
            "source_type",
            "verification_status",
            "subsystem",
            "fault_code",
            "confirmed_root_cause",
            "corrective_action",
            "is_synthetic",
        ]
        for field in required:
            if field not in data:
                raise RetrievalError(f"Corrupt metadata record: missing required field '{field}'.")

        return cls(
            vector_id=int(data["vector_id"]),
            case_id=str(data["case_id"]),
            source_title=str(data["source_title"]),
            source_reference=str(data["source_reference"]),
            source_type=str(data["source_type"]),
            verification_status=str(data["verification_status"]),
            subsystem=str(data["subsystem"]),
            fault_code=str(data["fault_code"]),
            confirmed_root_cause=str(data["confirmed_root_cause"]),
            corrective_action=str(data["corrective_action"]),
            is_synthetic=bool(data["is_synthetic"]),
            document_text=str(data.get("document_text", "")),
            indexed_at=str(data.get("indexed_at", "")),
        )


@dataclass
class SearchResult:
    """Represents a matched fault case from vector similarity retrieval."""
    case_id: str
    score: float  # Cosine similarity in range [-1.0, 1.0]
    vector_id: int
    record: VectorRecord

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "score": round(self.score, 4),
            "vector_id": self.vector_id,
            "subsystem": self.record.subsystem,
            "fault_code": self.record.fault_code,
            "source_title": self.record.source_title,
            "source_reference": self.record.source_reference,
            "verification_status": self.record.verification_status,
            "is_synthetic": self.record.is_synthetic,
            "confirmed_root_cause": self.record.confirmed_root_cause,
            "corrective_action": self.record.corrective_action,
            "document_text": self.record.document_text,
        }


class FAISSVectorStore:
    """Production vector store using FAISS CPU with strict metadata synchronization."""

    def __init__(
        self,
        dimension: int = EMBEDDING_DIMENSION,
        similarity_metric: str = "cosine_similarity",
    ):
        self.dimension = dimension
        self.similarity_metric = similarity_metric
        # IndexFlatIP calculates inner product: <u, v>. On unit L2-normalized vectors, this equals Cosine Similarity.
        self.index: faiss.IndexFlatIP = faiss.IndexFlatIP(self.dimension)
        # Explicit mapping: position index -> VectorRecord
        self._records: List[VectorRecord] = []
        # Reverse mapping: case_id -> position index
        self._case_id_to_pos: Dict[str, int] = {}

    @property
    def total_vectors(self) -> int:
        """Returns the number of vectors indexed in the FAISS structure."""
        return self.index.ntotal

    def clear(self) -> None:
        """Resets the vector index and all associated mappings."""
        self.index.reset()
        self._records.clear()
        self._case_id_to_pos.clear()

    def add_cases(
        self,
        cases: Sequence[FaultCase],
        embedding_generator: BaseEmbeddingGenerator,
        skip_duplicates: bool = True,
    ) -> int:
        """Embeds and indexes a sequence of FaultCase records.

        Duplicate Prevention:
        If a case_id already exists in the vector store and skip_duplicates=True,
        it is skipped to maintain strict 1-to-1 vector position mapping.

        Returns:
            Count of newly added vectors.
        """
        if not cases:
            return 0

        # Validate embedding generator compatibility
        if embedding_generator.dimension != self.dimension:
            raise RetrievalError(
                f"Embedding generator dimension mismatch: generator={embedding_generator.dimension}, index={self.dimension}"
            )

        new_cases: List[FaultCase] = []
        for c in cases:
            if skip_duplicates and c.case_id in self._case_id_to_pos:
                logger.debug("Skipping already indexed duplicate case: %s", c.case_id)
                continue
            new_cases.append(c)

        if not new_cases:
            return 0

        # Build standardized semantic document strings
        docs = [DocumentBuilder.build_document(c) for c in new_cases]

        # Generate normalized vectors
        vectors = embedding_generator.encode(docs, normalize=True)
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        # Append vectors into FAISS index
        self.index.add(vectors)

        # Maintain explicit vector mapping
        now_iso = datetime.now(timezone.utc).isoformat()
        start_pos = len(self._records)

        for i, c in enumerate(new_cases):
            pos = start_pos + i
            rec = VectorRecord(
                vector_id=pos,
                case_id=c.case_id,
                source_title=c.source_title,
                source_reference=c.source_reference,
                source_type=c.source_type,
                verification_status=c.verification_status,
                subsystem=c.subsystem,
                fault_code=c.fault_code,
                confirmed_root_cause=c.confirmed_root_cause,
                corrective_action=c.corrective_action,
                is_synthetic=c.is_synthetic,
                document_text=docs[i],
                indexed_at=now_iso,
            )
            self._records.append(rec)
            self._case_id_to_pos[c.case_id] = pos

        # Verify mapping synchronization
        if self.index.ntotal != len(self._records):
            raise RetrievalError(
                f"Vector store out of sync! FAISS ntotal={self.index.ntotal}, mapped records={len(self._records)}"
            )

        logger.info("Added %d new vectors to FAISS index. Total count: %d", len(new_cases), self.index.ntotal)
        return len(new_cases)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        subsystem: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
    ) -> List[SearchResult]:
        """Performs cosine similarity search against the indexed vector space.

        Args:
            query_vector: 1D or 2D NumPy array representing the embedded query.
            top_k: Maximum number of nearest matches to retrieve.
            score_threshold: Minimum cosine similarity score required (e.g. 0.50).
            subsystem: Optional subsystem filter.
            is_synthetic: Optional provenance filter.

        Returns:
            List of SearchResult objects sorted by descending similarity score.
        """
        if self.total_vectors == 0:
            return []

        # Ensure float32 and shape (1, dimension)
        q = np.asarray(query_vector, dtype=np.float32)
        if q.ndim == 1:
            q = q.reshape(1, -1)

        # Normalize query vector to guarantee cosine similarity
        q = normalize_vectors(q)

        # Request more candidates if filtering is active
        fetch_k = min(self.total_vectors, max(top_k * 3, 20))
        scores, indices = self.index.search(q, fetch_k)

        results: List[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._records):
                continue

            # Check threshold
            if score_threshold is not None and score < score_threshold:
                continue

            rec = self._records[idx]

            # Filter by subsystem
            if subsystem and subsystem.lower() not in ("all", "other", ""):
                if rec.subsystem.lower() != subsystem.lower().strip():
                    continue

            # Filter by provenance
            if is_synthetic is not None:
                if rec.is_synthetic != is_synthetic:
                    continue

            results.append(
                SearchResult(
                    case_id=rec.case_id,
                    score=float(score),
                    vector_id=idx,
                    record=rec,
                )
            )

            if len(results) >= top_k:
                break

        return results

    def save(self, index_dir: Union[str, Path]) -> None:
        """Atomically saves the FAISS index, metadata mapping, and manifest to disk.

        Security & Integrity:
        - NEVER uses pickle. Serializes metadata into strict JSON.
        - Writes to a staging directory first. Only replaces destination upon full validation.
        """
        target_dir = Path(index_dir)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        staging_dir = Path(tempfile.mkdtemp(prefix="faiss_stage_", dir=target_dir.parent))

        try:
            # 1. Write binary FAISS index
            faiss_file = staging_dir / "index.faiss"
            faiss.write_index(self.index, str(faiss_file))

            # 2. Write safe JSON metadata mapping (NO pickle)
            metadata_file = staging_dir / "metadata.json"
            metadata_payload = [r.to_dict() for r in self._records]
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata_payload, f, indent=2, ensure_ascii=False)

            # 3. Compute integrity checksums
            faiss_hash = hashlib.sha256(faiss_file.read_bytes()).hexdigest()
            meta_hash = hashlib.sha256(metadata_file.read_bytes()).hexdigest()

            # 4. Write manifest
            manifest_file = staging_dir / "manifest.json"
            manifest = {
                "format_version": "1.0",
                "dimension": self.dimension,
                "total_vectors": self.total_vectors,
                "similarity_metric": self.similarity_metric,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "faiss_index_sha256": faiss_hash,
                "metadata_sha256": meta_hash,
            }
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            # Atomic swap: remove destination if exists, move staging to target
            if target_dir.exists():
                shutil.rmtree(target_dir)
            shutil.move(str(staging_dir), str(target_dir))
            logger.info("Successfully persisted FAISS index (%d vectors) to: %s", self.total_vectors, target_dir)

        except Exception as exc:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            raise RetrievalError(f"Failed to persist FAISS index: {exc}") from exc

    def load(self, index_dir: Union[str, Path]) -> None:
        """Loads and verifies a persisted FAISS index and JSON metadata mapping.

        Security:
        - Rejects any non-JSON or pickle metadata files.
        - Verifies dimensional and record count consistency.
        """
        target_dir = Path(index_dir)
        if not target_dir.exists() or not target_dir.is_dir():
            raise RetrievalError(f"Vector store directory does not exist: {target_dir}")

        faiss_file = target_dir / "index.faiss"
        metadata_file = target_dir / "metadata.json"
        manifest_file = target_dir / "manifest.json"

        if not faiss_file.exists():
            raise RetrievalError(f"Missing FAISS index file: {faiss_file}")
        if not metadata_file.exists():
            raise RetrievalError(f"Missing metadata mapping file: {metadata_file}")

        # 1. Inspect manifest if present
        if manifest_file.exists():
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    stored_dim = manifest.get("dimension")
                    if stored_dim and stored_dim != self.dimension:
                        raise RetrievalError(
                            f"Index dimension mismatch: manifest specifies {stored_dim}, vector store configured for {self.dimension}"
                        )
            except json.JSONDecodeError as exc:
                raise RetrievalError(f"Corrupt index manifest: {exc}") from exc

        # 2. Load FAISS index
        try:
            loaded_index = faiss.read_index(str(faiss_file))
        except Exception as exc:
            raise RetrievalError(f"Failed to read FAISS index file (corrupted binary): {exc}") from exc

        # Validate loaded index dimension
        if loaded_index.d != self.dimension:
            raise RetrievalError(
                f"FAISS index dimension mismatch: index has {loaded_index.d}, expected {self.dimension}"
            )

        # 3. Securely deserialize JSON metadata (treat as untrusted input)
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                raw_metadata = json.load(f)
                if not isinstance(raw_metadata, list):
                    raise RetrievalError("Root metadata JSON must be an array of vector records.")

                records = [VectorRecord.from_dict(item) for item in raw_metadata]
        except json.JSONDecodeError as exc:
            raise RetrievalError(f"Corrupt metadata JSON: {exc}") from exc
        except Exception as exc:
            raise RetrievalError(f"Failed to parse metadata records: {exc}") from exc

        # 4. Strict synchronization check
        if loaded_index.ntotal != len(records):
            raise RetrievalError(
                f"Index and metadata desynchronization! FAISS vectors: {loaded_index.ntotal}, Metadata rows: {len(records)}"
            )

        # 5. Populate internal structures
        self.index = loaded_index
        self._records = records
        self._case_id_to_pos = {r.case_id: r.vector_id for r in records}

        logger.info("Successfully loaded FAISS vector store (%d vectors) from: %s", self.total_vectors, target_dir)
