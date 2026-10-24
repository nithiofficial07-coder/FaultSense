"""Custom domain exceptions for FaultSense.

Structured hierarchy providing clear root-cause context across ingestion,
storage, retrieval, and diagnostic processes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class FaultSenseError(Exception):
    """Base exception for all FaultSense application errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(FaultSenseError):
    """Raised when application settings or environment parameters are invalid."""


class IngestionError(FaultSenseError):
    """Raised when data ingestion, format parsing, or schema validation fails."""


class KnowledgeBaseError(FaultSenseError):
    """Raised when knowledge base querying, indexing, or record management fails."""


class StorageError(FaultSenseError):
    """Raised when SQLite database access, schema migration, or persistence operations fail."""


class RetrievalError(FaultSenseError):
    """Raised when vector similarity search or document retrieval fails."""


class DiagnosisError(FaultSenseError):
    """Raised when diagnostic reasoning, symptom analysis, or root cause matching fails."""


class EvaluationError(FaultSenseError):
    """Raised when benchmark evaluation or RAG metrics computation fails."""
