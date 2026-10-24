"""System health and diagnostic status checks for FaultSense.

Verifies database connectivity, file system permissions, configuration integrity,
and runtime dependencies for startup readiness.
"""

from __future__ import annotations

import platform
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from config.settings import get_settings


@dataclass
class ComponentStatus:
    """Status report for a single system component."""
    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Overall system health and diagnostics report."""
    overall_status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    app_version: str
    environment: str
    components: Dict[str, ComponentStatus]
    notices: List[str]

    @property
    def is_healthy(self) -> bool:
        return self.overall_status in ("healthy", "degraded")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "timestamp": self.timestamp,
            "app_version": self.app_version,
            "environment": self.environment,
            "components": {k: asdict(v) for k, v in self.components.items()},
            "notices": self.notices,
        }


class HealthChecker:
    """Executes automated status probes across all subsystem components."""

    @staticmethod
    def check_database() -> ComponentStatus:
        """Probes SQLite database accessibility and case record counts."""
        settings = get_settings()
        db_path = settings.database_path

        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='fault_cases';"
                )
                has_table = cursor.fetchone() is not None

                count = 0
                if has_table:
                    cursor.execute("SELECT COUNT(*) FROM fault_cases;")
                    count = cursor.fetchone()[0]

                return ComponentStatus(
                    name="database",
                    status="healthy",
                    message="SQLite database is accessible.",
                    details={
                        "path": str(db_path),
                        "has_fault_cases_table": has_table,
                        "case_count": count,
                        "sqlite_version": sqlite3.sqlite_version,
                    },
                )
        except Exception as exc:
            return ComponentStatus(
                name="database",
                status="unhealthy",
                message=f"Database probe failed: {exc}",
                details={"path": str(db_path), "error": str(exc)},
            )

    @staticmethod
    def check_filesystem() -> ComponentStatus:
        """Verifies read and write permissions in data and log directories."""
        settings = get_settings()
        dirs_to_test = [settings.data_dir, settings.upload_dir, settings.log_dir]

        writable = []
        unwritable = []

        for d in dirs_to_test:
            try:
                d.mkdir(parents=True, exist_ok=True)
                test_file = d / ".health_test.tmp"
                test_file.write_text("health_check_ok", encoding="utf-8")
                test_file.unlink()
                writable.append(str(d))
            except Exception as exc:
                unwritable.append(f"{d} ({exc})")

        if unwritable:
            return ComponentStatus(
                name="filesystem",
                status="degraded",
                message="Some directories lack write permissions.",
                details={"writable": writable, "unwritable": unwritable},
            )

        return ComponentStatus(
            name="filesystem",
            status="healthy",
            message="Storage and log directories are writable.",
            details={"directories": writable},
        )

    @staticmethod
    def check_configuration() -> ComponentStatus:
        """Validates configuration parameters and reports runtime mode."""
        settings = get_settings()
        notices = settings.validate()

        status = "degraded" if settings.is_demo_mode else "healthy"
        msg = "Demo Mode active (No external LLM credentials)." if settings.is_demo_mode else "Production configuration active."

        return ComponentStatus(
            name="configuration",
            status=status,
            message=msg,
            details={
                "environment": settings.app_env,
                "debug": settings.debug,
                "demo_mode": settings.is_demo_mode,
                "llm_provider": settings.llm_provider,
                "notices": notices,
            },
        )

    @staticmethod
    def check_runtime() -> ComponentStatus:
        """Reports Python runtime and platform environment metrics."""
        return ComponentStatus(
            name="runtime",
            status="healthy",
            message=f"Python {platform.python_version()} on {platform.system()}",
            details={
                "python_version": sys.version,
                "platform": platform.platform(),
                "machine": platform.machine(),
            },
        )

    @staticmethod
    def check_vector_store() -> ComponentStatus:
        """Probes FAISS vector store files and synchronization state."""
        settings = get_settings()
        idx_dir = settings.faiss_index_dir
        faiss_file = idx_dir / "index.faiss"
        meta_file = idx_dir / "metadata.json"

        if not faiss_file.exists() or not meta_file.exists():
            return ComponentStatus(
                name="vector_store",
                status="degraded",
                message="Vector index not initialized yet. Run indexing to build FAISS store.",
                details={
                    "index_dir": str(idx_dir),
                    "has_index_file": faiss_file.exists(),
                    "has_metadata_file": meta_file.exists(),
                },
            )

        try:
            import json
            meta_count = len(json.loads(meta_file.read_text(encoding="utf-8")))
            return ComponentStatus(
                name="vector_store",
                status="healthy",
                message=f"FAISS vector store active with {meta_count} indexed vectors.",
                details={
                    "index_dir": str(idx_dir),
                    "vector_count": meta_count,
                    "dimension": 384,
                    "metric": "cosine_similarity",
                },
            )
        except Exception as exc:
            return ComponentStatus(
                name="vector_store",
                status="degraded",
                message=f"Error inspecting vector store: {exc}",
                details={"error": str(exc)},
            )

    @classmethod
    def run_all_checks(cls) -> HealthStatus:
        """Executes all component probes and compiles the system status."""
        settings = get_settings()
        components = {
            "database": cls.check_database(),
            "vector_store": cls.check_vector_store(),
            "filesystem": cls.check_filesystem(),
            "configuration": cls.check_configuration(),
            "runtime": cls.check_runtime(),
        }

        # Determine overall status
        statuses = [c.status for c in components.values()]
        if any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        elif any(s == "degraded" for s in statuses):
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthStatus(
            overall_status=overall,
            timestamp=datetime.now(timezone.utc).isoformat(),
            app_version=settings.app_version,
            environment=settings.app_env,
            components=components,
            notices=settings.validate(),
        )
