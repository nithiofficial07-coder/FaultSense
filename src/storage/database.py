"""SQLite database management and schema migration for FaultSense.

Handles connection pooling, WAL mode, schema initialization, and transaction boundaries.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Union

from config.settings import get_settings
from src.utils.exceptions import StorageError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manages SQLite database connections and lifecycle."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        settings = get_settings()
        self.db_path = str(db_path or settings.database_path)
        self._shared_conn: Optional[sqlite3.Connection] = None

        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")

        self.initialize_schema()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a managed transaction connection."""
        if self._shared_conn is not None:
            try:
                yield self._shared_conn
                self._shared_conn.commit()
            except Exception as exc:
                self._shared_conn.rollback()
                raise StorageError(f"Database transaction error: {exc}") from exc
        else:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            try:
                yield conn
                conn.commit()
            except Exception as exc:
                conn.rollback()
                raise StorageError(f"Database transaction error: {exc}") from exc
            finally:
                conn.close()

    def initialize_schema(self) -> None:
        """Executes table and index creations."""
        logger.info("Initializing database schema at: %s", self.db_path)
        with self.get_connection() as conn:
            # 1. Fault Cases Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fault_cases (
                    case_id TEXT PRIMARY KEY,
                    source_title TEXT NOT NULL,
                    source_reference TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    verification_status TEXT NOT NULL,
                    subsystem TEXT NOT NULL,
                    fault_code TEXT NOT NULL,
                    symptoms TEXT NOT NULL,
                    telemetry_summary TEXT NOT NULL,
                    confirmed_root_cause TEXT NOT NULL,
                    corrective_action TEXT NOT NULL,
                    timestamp TEXT,
                    metadata TEXT NOT NULL,
                    is_indexed INTEGER DEFAULT 0,
                    indexed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Indexes for fast lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_subsystem ON fault_cases(subsystem);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_fault_code ON fault_cases(fault_code);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_verification ON fault_cases(verification_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_source_type ON fault_cases(source_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_is_indexed ON fault_cases(is_indexed);")

            # 3. Investigation Sessions Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    elevator_id TEXT NOT NULL,
                    building_id TEXT,
                    subsystem TEXT NOT NULL,
                    fault_code TEXT,
                    symptoms TEXT NOT NULL,
                    telemetry TEXT NOT NULL,
                    root_cause_hypothesis TEXT,
                    recommended_actions TEXT,
                    confidence_score REAL,
                    matched_case_ids TEXT,
                    status TEXT DEFAULT 'open',
                    technician_notes TEXT,
                    verification_record TEXT,
                    retry_count INTEGER DEFAULT 0,
                    diagnostic_report TEXT,
                    evidence_package TEXT,
                    manufacturer TEXT,
                    equipment_model TEXT,
                    severity TEXT,
                    operating_conditions TEXT,
                    problem_description TEXT,
                    technician_review TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Schema migration for existing tables
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN verification_record TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN retry_count INTEGER DEFAULT 0;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN diagnostic_report TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN evidence_package TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN manufacturer TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN equipment_model TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN severity TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN operating_conditions TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN problem_description TEXT;")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE investigations ADD COLUMN technician_review TEXT;")
            except sqlite3.OperationalError:
                pass

            conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_elevator ON investigations(elevator_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_status ON investigations(status);")

            # 4. FTS5 Full-Text Search Table
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS fault_cases_fts USING fts5(
                        case_id UNINDEXED,
                        source_title,
                        subsystem,
                        fault_code,
                        symptoms,
                        confirmed_root_cause,
                        corrective_action,
                        content='fault_cases',
                        content_rowid='rowid'
                    );
                """)
            except sqlite3.OperationalError:
                logger.warning("SQLite FTS5 virtual table not available in current build.")

    def close(self) -> None:
        """Closes shared in-memory connection if active."""
        if self._shared_conn is not None:
            try:
                self._shared_conn.close()
            except Exception:
                pass
            self._shared_conn = None


_DB_MANAGER: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Returns the application DatabaseManager singleton."""
    global _DB_MANAGER
    if _DB_MANAGER is None:
        _DB_MANAGER = DatabaseManager()
    return _DB_MANAGER
