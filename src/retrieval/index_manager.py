"""Vector index manager coordinating FAISS storage, embeddings, and repository synchronization.

Handles atomic index rebuilding, unindexed record polling, persistent saving/loading,
and hybrid vector similarity retrieval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import get_settings
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase
from src.retrieval.document_builder import DocumentBuilder
from src.retrieval.embeddings import (
    BaseEmbeddingGenerator,
    SentenceTransformerEmbeddingGenerator,
)
from src.retrieval.vector_store import FAISSVectorStore, SearchResult
from src.utils.exceptions import RetrievalError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IndexManager:
    """Orchestrates embedding generation, vector indexing, and persistent synchronization."""

    def __init__(
        self,
        vector_store: Optional[FAISSVectorStore] = None,
        embedding_generator: Optional[BaseEmbeddingGenerator] = None,
        index_dir: Optional[Union[str, Path]] = None,
    ):
        settings = get_settings()
        self.index_dir = Path(index_dir or settings.faiss_index_dir)
        self.embedding_generator = embedding_generator or SentenceTransformerEmbeddingGenerator()
        self.vector_store = vector_store or FAISSVectorStore(dimension=self.embedding_generator.dimension)

    @property
    def total_vectors(self) -> int:
        return self.vector_store.total_vectors

    def initialize(self, repo: Optional[FaultCaseRepository] = None, force_rebuild: bool = False) -> bool:
        """Initializes the vector index from disk, or builds it from repository if missing."""
        if not force_rebuild and (self.index_dir / "index.faiss").exists():
            try:
                self.vector_store.load(self.index_dir)
                logger.info("Loaded existing vector index with %d vectors.", self.total_vectors)
                return True
            except Exception as exc:
                logger.warning("Could not load existing index (%s). Rebuilding from repository...", exc)

        if repo is not None:
            self.rebuild_from_repository(repo)
            return True

        return False

    def rebuild_from_repository(self, repo: FaultCaseRepository) -> int:
        """Atomically rebuilds the entire vector index from all records in the SQLite repository.

        Ensures:
        1. Clean slate without stale or orphaned vector positions.
        2. Atomic disk persistence to prevent partially updated states.
        3. Updates is_indexed=1 and indexed_at timestamps in SQLite.
        """
        logger.info("Starting complete vector index rebuild from repository...")
        cases = repo.search(limit=100000)

        # Create temporary fresh vector store
        new_store = FAISSVectorStore(dimension=self.embedding_generator.dimension)

        if cases:
            new_store.add_cases(cases, self.embedding_generator, skip_duplicates=True)

        # Atomically save fresh index to disk
        new_store.save(self.index_dir)

        # Swap in-memory store
        self.vector_store = new_store

        # Mark all cases as indexed in the database
        if cases:
            case_ids = [c.case_id for c in cases]
            repo.mark_as_indexed(case_ids)

        logger.info("Vector index rebuild complete. Total indexed cases: %d", self.total_vectors)
        return self.total_vectors

    def sync_unindexed_cases(self, repo: FaultCaseRepository) -> int:
        """Discovers unindexed cases in the repository and appends them to the vector index."""
        unindexed = repo.get_unindexed(limit=500)
        if not unindexed:
            return 0

        logger.info("Found %d unindexed cases to add to vector store.", len(unindexed))
        added_count = self.vector_store.add_cases(
            unindexed, self.embedding_generator, skip_duplicates=True
        )

        if added_count > 0:
            self.vector_store.save(self.index_dir)
            indexed_ids = [c.case_id for c in unindexed]
            repo.mark_as_indexed(indexed_ids)

        return added_count

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        subsystem: Optional[str] = None,
        fault_code: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
    ) -> List[SearchResult]:
        """Embeds query text and performs vector similarity search."""
        if not query.strip() and not fault_code:
            return []

        # Construct asymmetric search query
        query_text = DocumentBuilder.build_query_document(
            query=query, subsystem=subsystem, fault_code=fault_code
        )

        # Generate normalized embedding
        query_vec = self.embedding_generator.encode(query_text, normalize=True)

        # Run vector store search
        return self.vector_store.search(
            query_vector=query_vec,
            top_k=top_k,
            score_threshold=score_threshold,
            subsystem=subsystem,
            is_synthetic=is_synthetic,
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns the status and health of the vector indexing subsystem."""
        index_exists = (self.index_dir / "index.faiss").exists()
        metadata_exists = (self.index_dir / "metadata.json").exists()

        return {
            "status": "ready" if self.total_vectors > 0 else ("empty" if index_exists else "not_initialized"),
            "total_vectors": self.total_vectors,
            "dimension": self.vector_store.dimension,
            "similarity_metric": self.vector_store.similarity_metric,
            "model_name": self.embedding_generator.model_name,
            "index_dir": str(self.index_dir),
            "files_present": {
                "index.faiss": index_exists,
                "metadata.json": metadata_exists,
                "manifest.json": (self.index_dir / "manifest.json").exists(),
            },
        }
