"""FaultSense Retrieval & Vector Indexing Package."""

from src.retrieval.document_builder import DocumentBuilder
from src.retrieval.embeddings import (
    EMBEDDING_DIMENSION,
    BaseEmbeddingGenerator,
    DeterministicEmbeddingGenerator,
    SentenceTransformerEmbeddingGenerator,
    normalize_vectors,
)
from src.retrieval.index_manager import IndexManager
from src.retrieval.retriever import (
    BaseRetriever,
    HybridRetriever,
    KeywordRetriever,
    VectorRetriever,
)
from src.retrieval.evidence import (
    EvidenceItem,
    EvidencePackage,
    EvidenceQuery,
    EvidenceSufficiency,
    EvidenceSufficiencyLevel,
    MatchRationale,
)
from src.retrieval.ranking import (
    FilterMode,
    RankingStrategy,
    RankingWeights,
    explain_filter_mode,
)
from src.retrieval.retrieval_service import FaultRetrievalService, compute_telemetry_overlap
from src.retrieval.topology import CandidatePropagation, ElevatorSubsystemTopology
from src.retrieval.vector_store import FAISSVectorStore, SearchResult, VectorRecord

__all__ = [
    "DocumentBuilder",
    "BaseEmbeddingGenerator",
    "SentenceTransformerEmbeddingGenerator",
    "DeterministicEmbeddingGenerator",
    "normalize_vectors",
    "EMBEDDING_DIMENSION",
    "FAISSVectorStore",
    "VectorRecord",
    "SearchResult",
    "IndexManager",
    "BaseRetriever",
    "KeywordRetriever",
    "VectorRetriever",
    "HybridRetriever",
    "FaultRetrievalService",
    "EvidencePackage",
    "EvidenceItem",
    "EvidenceQuery",
    "EvidenceSufficiency",
    "EvidenceSufficiencyLevel",
    "MatchRationale",
    "FilterMode",
    "RankingStrategy",
    "RankingWeights",
    "explain_filter_mode",
    "CandidatePropagation",
    "ElevatorSubsystemTopology",
    "compute_telemetry_overlap",
]
