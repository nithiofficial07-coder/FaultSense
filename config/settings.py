"""Application configuration management for FaultSense.

Loads settings from environment variables and .env file with validation,
safe secret masking, and graceful offline/demo-mode fallbacks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Automatically load environment variables from .env file if present
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)


@dataclass
class Settings:
    """Central application configuration for FaultSense."""

    # Project metadata
    app_name: str = "FaultSense"
    app_tagline: str = "Autonomous Fault Isolation & Root Cause Analysis Assistant"
    app_version: str = "1.0.0"
    app_env: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development").strip().lower()
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").strip().lower() in ("true", "1", "yes")
    )

    # Base Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    )
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "fault_sense.db"))
        )
    )
    upload_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
        )
    )
    export_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("EXPORT_DIR", str(BASE_DIR / "data" / "exports"))
        )
    )
    log_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LOG_DIR", str(BASE_DIR / "logs")))
    )
    log_file: Path = field(
        default_factory=lambda: Path(
            os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "fault_sense.log"))
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").strip().upper()
    )

    # Ingestion Constraints
    max_upload_size_mb: int = field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    )

    # Retrieval & Vector Database Settings
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()
    )
    vector_store_type: str = field(
        default_factory=lambda: os.getenv("VECTOR_STORE_TYPE", "faiss_cpu").strip().lower()
    )
    faiss_index_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("FAISS_INDEX_DIR", str(BASE_DIR / "data" / "vector_store" / "faiss"))
        )
    )
    top_k_retrieval: int = field(
        default_factory=lambda: int(os.getenv("TOP_K_RETRIEVAL", "5"))
    )
    similarity_threshold: float = field(
        default_factory=lambda: float(os.getenv("SIMILARITY_THRESHOLD", "0.60"))
    )

    # LLM & Reasoning Engine Settings
    llm_provider: str = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "mock").strip().lower()
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    )
    llm_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    )
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2"))
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "1500"))
    )

    # Phase 6: Agentic Self-Verification Loop Settings
    verification_enabled: bool = field(
        default_factory=lambda: os.getenv("VERIFICATION_ENABLED", "false").strip().lower() in ("true", "1", "yes")
    )
    max_verification_retries: int = field(
        default_factory=lambda: int(os.getenv("MAX_VERIFICATION_RETRIES", "2"))
    )

    # Demo Mode: automatically enabled if no valid LLM key is configured or explicitly set
    force_demo_mode: bool = field(
        default_factory=lambda: os.getenv("DEMO_MODE", "false").strip().lower() in ("true", "1")
    )

    def __post_init__(self) -> None:
        """Ensure necessary runtime directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_index_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_demo_mode(self) -> bool:
        """Returns True if the application is running in offline demo mode."""
        if self.force_demo_mode:
            return True
        if not self.llm_api_key or self.llm_provider in ("mock", "offline", "none", ""):
            return True
        return False

    def validate(self) -> List[str]:
        """Validates configuration parameters and returns non-fatal notices or warnings."""
        notices: List[str] = []

        if self.is_demo_mode:
            notices.append(
                "Offline Demo Mode active: No external LLM API key detected or provider is set to 'mock'. "
                "Baseline heuristic diagnostics and local knowledge retrieval are enabled."
            )
        else:
            notices.append(f"Configured for external LLM provider: '{self.llm_provider}' ({self.llm_model})")

        if self.top_k_retrieval <= 0 or self.top_k_retrieval > 50:
            notices.append(f"Notice: TOP_K_RETRIEVAL is {self.top_k_retrieval}; default is 5.")

        return notices

    def get_safe_dict(self) -> Dict[str, Any]:
        """Returns dictionary of settings with all API keys and secrets safely masked."""
        masked_key = "(Not Configured - Demo Mode)"
        if self.llm_api_key and len(self.llm_api_key) > 6:
            masked_key = f"{self.llm_api_key[:3]}****{self.llm_api_key[-3:]}"
        elif self.llm_api_key:
            masked_key = "********"

        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "app_env": self.app_env,
            "debug": self.debug,
            "demo_mode": self.is_demo_mode,
            "database_path": str(self.database_path),
            "upload_dir": str(self.upload_dir),
            "export_dir": str(self.export_dir),
            "log_file": str(self.log_file),
            "log_level": self.log_level,
            "vector_store_type": self.vector_store_type,
            "embedding_model": self.embedding_model,
            "top_k_retrieval": self.top_k_retrieval,
            "similarity_threshold": self.similarity_threshold,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_api_key": masked_key,
            "verification_enabled": self.verification_enabled,
            "max_verification_retries": self.max_verification_retries,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns the singleton application Settings instance."""
    return Settings()
