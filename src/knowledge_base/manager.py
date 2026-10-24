"""High-level Knowledge Base Management Service.

Encapsulates CRUD operations, dataset seeding, search filters, and statistics reporting.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import get_settings
from fault_sense.ingestion import FaultCaseIngestionPipeline, ImportSummary
from fault_sense.repository import FaultCaseRepository
from fault_sense.schema import FaultCase
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeBaseManager:
    """Service layer managing the elevator fault knowledge repository."""

    def __init__(self, repository: Optional[FaultCaseRepository] = None):
        settings = get_settings()
        self.repo = repository or FaultCaseRepository(db_path=settings.database_path)
        self.ingestion = FaultCaseIngestionPipeline()

    def get_stats(self) -> Dict[str, Any]:
        """Calculates system-wide distribution metrics."""
        cases = self.repo.search(limit=100000)
        total = len(cases)
        synthetic_count = sum(1 for c in cases if c.is_synthetic)
        verified_count = sum(1 for c in cases if c.verification_status == "verified")
        indexed_count = sum(1 for c in cases if c.is_indexed)

        # Subsystem Breakdown
        subsystem_dist: Dict[str, int] = {}
        for c in cases:
            subsystem_dist[c.subsystem] = subsystem_dist.get(c.subsystem, 0) + 1

        return {
            "total_cases": total,
            "synthetic_count": synthetic_count,
            "verified_count": verified_count,
            "unverified_count": total - verified_count,
            "indexed_count": indexed_count,
            "subsystem_distribution": subsystem_dist,
        }

    def seed_initial_data_if_empty(self) -> int:
        """Loads sample benchmark cases from data/sample_fault_cases.json if database is empty."""
        settings = get_settings()
        existing_count = self.repo.count()
        if existing_count > 0:
            return 0

        seed_file = settings.data_dir / "sample_fault_cases.json"
        if not seed_file.exists():
            logger.warning("Seed data file not found: %s", seed_file)
            return 0

        logger.info("Database empty. Seeding initial benchmark cases from: %s", seed_file)
        cases, summary = self.ingestion.ingest_file(seed_file)
        if cases:
            added = self.repo.add(cases, allow_update=True)
            logger.info("Successfully seeded %d fault cases.", added)
            return added
        return 0

    def import_file(self, file_path: Union[str, Path]) -> ImportSummary:
        """Imports fault cases from a file into the knowledge repository."""
        existing_ids = self.repo.get_all_case_ids()
        cases, summary = self.ingestion.ingest_file(file_path, existing_case_ids=existing_ids)
        if cases:
            self.repo.add(cases, allow_update=False)
            logger.info("Imported %d new fault cases from %s", len(cases), file_path)
        return summary

    def search_cases(
        self,
        query: Optional[str] = None,
        subsystem: Optional[str] = None,
        fault_code: Optional[str] = None,
        verification_status: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[FaultCase]:
        """Searches fault cases with multi-criteria filters."""
        return self.repo.search(
            query=query,
            subsystem=subsystem,
            fault_code=fault_code,
            verification_status=verification_status,
            is_synthetic=is_synthetic,
            limit=limit,
            offset=offset,
        )

    def export_data(
        self, filepath: Union[str, Path], format_type: str = "json"
    ) -> int:
        """Exports all knowledge base records to file."""
        return self.repo.export(filepath=filepath, format_type=format_type)

    def rebuild_vector_index(self, index_manager: Optional[Any] = None) -> int:
        """Triggers complete atomic rebuild of the FAISS vector index."""
        from src.retrieval.index_manager import IndexManager

        im = index_manager or IndexManager()
        return im.rebuild_from_repository(self.repo)

    def sync_vector_index(self, index_manager: Optional[Any] = None) -> int:
        """Synchronizes newly added unindexed cases into the FAISS vector index."""
        from src.retrieval.index_manager import IndexManager

        im = index_manager or IndexManager()
        return im.sync_unindexed_cases(self.repo)

    def get_vector_status(self, index_manager: Optional[Any] = None) -> Dict[str, Any]:
        """Reports the health and vector count of the FAISS vector index."""
        from src.retrieval.index_manager import IndexManager

        im = index_manager or IndexManager()
        return im.get_status()
