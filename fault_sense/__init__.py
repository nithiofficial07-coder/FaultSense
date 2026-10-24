"""FaultSense: Elevator Fault Case Ingestion & Knowledge Base.

High-reliability ingestion, validation, and structured knowledge repository
for vertical transportation diagnostics and predictive maintenance.
"""

from fault_sense.indexing_interface import EmbeddingDocument, FaultCaseIndexingAdapter
from fault_sense.ingestion import (
    FaultCaseIngestionPipeline,
    ImportSummary,
    IngestionConfig,
)
from fault_sense.preprocessor import (
    clean_text,
    compute_sensor_statistics,
    dataframe_to_fault_cases,
    normalize_symptoms,
    normalize_telemetry,
    preprocess_fault_dataframe,
    zscore_normalize,
)
from fault_sense.repository import DuplicateCaseError, FaultCaseRepository
from fault_sense.schema import (
    FaultCase,
    FaultCaseValidationError,
    SourceType,
    SubsystemType,
    VerificationStatus,
)

__version__ = "0.2.0"

__all__ = [
    # Schema
    "FaultCase",
    "SubsystemType",
    "SourceType",
    "VerificationStatus",
    "FaultCaseValidationError",
    # Ingestion
    "FaultCaseIngestionPipeline",
    "ImportSummary",
    "IngestionConfig",
    # Repository
    "FaultCaseRepository",
    "DuplicateCaseError",
    # Indexing Interface
    "FaultCaseIndexingAdapter",
    "EmbeddingDocument",
    # Preprocessor
    "clean_text",
    "normalize_symptoms",
    "normalize_telemetry",
    "compute_sensor_statistics",
    "zscore_normalize",
    "preprocess_fault_dataframe",
    "dataframe_to_fault_cases",
]
