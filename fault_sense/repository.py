"""SQLite-backed Knowledge Base Repository for Elevator Fault Cases.

Provides persistent storage, retrieval, full-text and parameterized search,
updates, deletion, and export (JSON/CSV) of fault case records.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Sequence, Set, Union

from fault_sense.schema import FaultCase, FaultCaseValidationError, SourceType, VerificationStatus


class DuplicateCaseError(ValueError):
    """Raised when attempting to insert a case_id that already exists."""


class FaultCaseRepository:
    """Manages persistent SQLite storage and querying of elevator fault cases."""

    def __init__(self, db_path: Union[str, Path] = ":memory:", enable_fts: bool = True):
        self.db_path = str(db_path)
        self.enable_fts = enable_fts
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        self._init_database()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Provides a managed SQLite database connection with row factory."""
        if self._shared_conn is not None:
            try:
                yield self._shared_conn
                self._shared_conn.commit()
            except Exception:
                self._shared_conn.rollback()
                raise
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def close(self) -> None:
        """Closes any persistent connection."""
        if self._shared_conn is not None:
            try:
                self._shared_conn.close()
            except Exception:
                pass
            self._shared_conn = None

    def __enter__(self) -> FaultCaseRepository:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _init_database(self) -> None:
        """Initializes tables, indexes, and full-text search structures."""
        with self._get_connection() as conn:
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

            # Indexes for high-frequency queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_subsystem ON fault_cases(subsystem);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_fault_code ON fault_cases(fault_code);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_verification ON fault_cases(verification_status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_source_type ON fault_cases(source_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fc_is_indexed ON fault_cases(is_indexed);")

            # Initialize FTS5 Full-Text Search Table
            if self.enable_fts:
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

                    # Triggers to keep FTS index synchronized
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS fc_ai AFTER INSERT ON fault_cases BEGIN
                            INSERT INTO fault_cases_fts(rowid, case_id, source_title, subsystem, fault_code, symptoms, confirmed_root_cause, corrective_action)
                            VALUES (new.rowid, new.case_id, new.source_title, new.subsystem, new.fault_code, new.symptoms, new.confirmed_root_cause, new.corrective_action);
                        END;
                    """)
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS fc_ad AFTER DELETE ON fault_cases BEGIN
                            INSERT INTO fault_cases_fts(fault_cases_fts, rowid, case_id, source_title, subsystem, fault_code, symptoms, confirmed_root_cause, corrective_action)
                            VALUES ('delete', old.rowid, old.case_id, old.source_title, old.subsystem, old.fault_code, old.symptoms, old.confirmed_root_cause, old.corrective_action);
                        END;
                    """)
                    conn.execute("""
                        CREATE TRIGGER IF NOT EXISTS fc_au AFTER UPDATE ON fault_cases BEGIN
                            INSERT INTO fault_cases_fts(fault_cases_fts, rowid, case_id, source_title, subsystem, fault_code, symptoms, confirmed_root_cause, corrective_action)
                            VALUES ('delete', old.rowid, old.case_id, old.source_title, old.subsystem, old.fault_code, old.symptoms, old.confirmed_root_cause, old.corrective_action);
                            INSERT INTO fault_cases_fts(rowid, case_id, source_title, subsystem, fault_code, symptoms, confirmed_root_cause, corrective_action)
                            VALUES (new.rowid, new.case_id, new.source_title, new.subsystem, new.fault_code, new.symptoms, new.confirmed_root_cause, new.corrective_action);
                        END;
                    """)
                except sqlite3.OperationalError:
                    # In case of environment restriction, fallback without crashing
                    self.enable_fts = False

    def add(self, case: Union[FaultCase, Sequence[FaultCase]], allow_update: bool = False) -> int:
        """Inserts one or more fault cases into the repository.

        Args:
            case: A single FaultCase or a list/tuple of FaultCase instances.
            allow_update: If True, existing cases will be overwritten. If False, raises DuplicateCaseError.

        Returns:
            Number of records successfully inserted/updated.
        """
        cases = [case] if isinstance(case, FaultCase) else list(case)
        if not cases:
            return 0

        inserted_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            for c in cases:
                if not isinstance(c, FaultCase):
                    raise ValueError(f"Expected FaultCase instance, got {type(c).__name__}")

                existing = conn.execute("SELECT case_id FROM fault_cases WHERE case_id = ?", (c.case_id,)).fetchone()

                if existing and not allow_update:
                    raise DuplicateCaseError(
                        f"Cannot add case '{c.case_id}': record already exists. Set allow_update=True to overwrite."
                    )

                if existing and allow_update:
                    conn.execute(
                        """
                        UPDATE fault_cases SET
                            source_title = ?,
                            source_reference = ?,
                            source_type = ?,
                            verification_status = ?,
                            subsystem = ?,
                            fault_code = ?,
                            symptoms = ?,
                            telemetry_summary = ?,
                            confirmed_root_cause = ?,
                            corrective_action = ?,
                            timestamp = ?,
                            metadata = ?,
                            is_indexed = ?,
                            indexed_at = ?,
                            updated_at = ?
                        WHERE case_id = ?;
                        """,
                        (
                            c.source_title,
                            c.source_reference,
                            c.source_type,
                            c.verification_status,
                            c.subsystem,
                            c.fault_code,
                            json.dumps(c.symptoms),
                            json.dumps(c.telemetry_summary),
                            c.confirmed_root_cause,
                            c.corrective_action,
                            c.timestamp,
                            json.dumps(c.metadata),
                            1 if c.is_indexed else 0,
                            c.indexed_at,
                            now_iso,
                            c.case_id,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO fault_cases (
                            case_id, source_title, source_reference, source_type,
                            verification_status, subsystem, fault_code, symptoms,
                            telemetry_summary, confirmed_root_cause, corrective_action,
                            timestamp, metadata, is_indexed, indexed_at, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            c.case_id,
                            c.source_title,
                            c.source_reference,
                            c.source_type,
                            c.verification_status,
                            c.subsystem,
                            c.fault_code,
                            json.dumps(c.symptoms),
                            json.dumps(c.telemetry_summary),
                            c.confirmed_root_cause,
                            c.corrective_action,
                            c.timestamp,
                            json.dumps(c.metadata),
                            1 if c.is_indexed else 0,
                            c.indexed_at,
                            now_iso,
                            now_iso,
                        ),
                    )
                inserted_count += 1

        return inserted_count

    create = add

    def get(self, case_id: str) -> Optional[FaultCase]:
        """Retrieves a single FaultCase by case_id."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM fault_cases WHERE case_id = ?", (case_id.strip(),)).fetchone()
            if not row:
                return None
            return self._row_to_case(row)

    def get_all_case_ids(self) -> Set[str]:
        """Returns a set containing all registered case_ids."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT case_id FROM fault_cases").fetchall()
            return {r["case_id"] for r in rows}

    def search(
        self,
        query: Optional[str] = None,
        subsystem: Optional[str] = None,
        fault_code: Optional[str] = None,
        verification_status: Optional[str] = None,
        source_type: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
        is_indexed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[FaultCase]:
        """Searches fault cases using full-text search and specific attribute filters."""
        params: List[Any] = []
        where_clauses: List[str] = []

        # 1. Attribute filtering
        if subsystem:
            where_clauses.append("subsystem = ?")
            params.append(subsystem.strip().lower().replace(" ", "_").replace("-", "_"))

        if fault_code:
            where_clauses.append("fault_code LIKE ?")
            params.append(f"%{fault_code.strip()}%")

        if verification_status:
            where_clauses.append("verification_status = ?")
            params.append(verification_status.strip().lower())

        if source_type:
            where_clauses.append("source_type = ?")
            params.append(source_type.strip().lower())

        if is_indexed is not None:
            where_clauses.append("is_indexed = ?")
            params.append(1 if is_indexed else 0)

        # 2. Text Query Handling
        if query and query.strip():
            clean_q = query.strip()
            # If FTS is enabled, query via FTS5
            if self.enable_fts:
                # Sanitize query for FTS MATCH
                sanitized_fts = clean_q.replace('"', '""').replace("'", "''")
                fts_expr = f'"{sanitized_fts}"'
                where_clauses.append(
                    """case_id IN (
                        SELECT case_id FROM fault_cases_fts WHERE fault_cases_fts MATCH ?
                    )"""
                )
                params.append(fts_expr)
            else:
                # Fallback to multi-column LIKE matching
                like_term = f"%{clean_q}%"
                where_clauses.append(
                    """(
                        case_id LIKE ? OR
                        source_title LIKE ? OR
                        subsystem LIKE ? OR
                        fault_code LIKE ? OR
                        symptoms LIKE ? OR
                        confirmed_root_cause LIKE ? OR
                        corrective_action LIKE ?
                    )"""
                )
                params.extend([like_term] * 7)

        sql = "SELECT * FROM fault_cases"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        sql += " ORDER BY case_id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            results = [self._row_to_case(r) for r in rows]

        # Post-filter on synthetic status if requested
        if is_synthetic is not None:
            results = [c for c in results if c.is_synthetic == is_synthetic]

        return results

    def update(self, case_id: str, updates: Union[Dict[str, Any], FaultCase]) -> FaultCase:
        """Applies updates to an existing fault case.

        Args:
            case_id: Target case identifier.
            updates: Either a dictionary of attributes to update or a replacement FaultCase.

        Returns:
            The updated and validated FaultCase.
        """
        existing = self.get(case_id)
        if not existing:
            raise KeyError(f"Case '{case_id}' not found in knowledge base.")

        if isinstance(updates, FaultCase):
            updated_dict = updates.to_dict()
            updated_dict["case_id"] = case_id
        elif isinstance(updates, dict):
            updated_dict = existing.to_dict()
            for k, v in updates.items():
                if k != "case_id":
                    updated_dict[k] = v
        else:
            raise ValueError("Updates must be a dictionary or FaultCase instance.")

        # Re-validate
        updated_case = FaultCase.from_dict(updated_dict)
        self.add(updated_case, allow_update=True)
        return updated_case

    def delete(self, case_id: str) -> bool:
        """Deletes a case from the repository. Returns True if deleted, False if not found."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM fault_cases WHERE case_id = ?", (case_id.strip(),))
            return cursor.rowcount > 0

    def count(
        self,
        subsystem: Optional[str] = None,
        verification_status: Optional[str] = None,
        source_type: Optional[str] = None,
        is_synthetic: Optional[bool] = None,
    ) -> int:
        """Returns the total number of fault cases matching optional filters."""
        cases = self.search(
            subsystem=subsystem,
            verification_status=verification_status,
            source_type=source_type,
            is_synthetic=is_synthetic,
            limit=1000000,
        )
        return len(cases)

    def export(
        self,
        filepath: Union[str, Path],
        format_type: str = "json",
        subsystem: Optional[str] = None,
        verification_status: Optional[str] = None,
    ) -> int:
        """Exports stored fault cases to a JSON or CSV file.

        Returns:
            Number of exported records.
        """
        cases = self.search(
            subsystem=subsystem, verification_status=verification_status, limit=1000000
        )
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        fmt = format_type.strip().lower()
        if fmt == "json":
            export_list = [c.to_dict() for c in cases]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_list, f, indent=2, default=str)
        elif fmt == "csv":
            if not cases:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    pass
                return 0
            fieldnames = [
                "case_id",
                "source_title",
                "source_reference",
                "source_type",
                "verification_status",
                "subsystem",
                "fault_code",
                "symptoms",
                "telemetry_summary",
                "confirmed_root_cause",
                "corrective_action",
                "timestamp",
                "metadata",
                "is_indexed",
                "indexed_at",
            ]
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for c in cases:
                    d = c.to_dict()
                    d["symptoms"] = json.dumps(d["symptoms"])
                    d["telemetry_summary"] = json.dumps(d["telemetry_summary"])
                    d["metadata"] = json.dumps(d["metadata"])
                    writer.writerow(d)
        else:
            raise ValueError(f"Unsupported export format '{format_type}'. Use 'json' or 'csv'.")

        return len(cases)

    def get_unindexed(self, limit: int = 100) -> List[FaultCase]:
        """Retrieves cases that have not yet been indexed into vector storage."""
        return self.search(is_indexed=False, limit=limit)

    def mark_as_indexed(self, case_ids: Sequence[str]) -> int:
        """Marks specified case IDs as indexed with current UTC timestamp."""
        if not case_ids:
            return 0
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            placeholders = ",".join("?" for _ in case_ids)
            cursor = conn.execute(
                f"""
                UPDATE fault_cases
                SET is_indexed = 1, indexed_at = ?
                WHERE case_id IN ({placeholders});
                """,
                [now_iso] + list(case_ids),
            )
            return cursor.rowcount

    def _row_to_case(self, row: sqlite3.Row) -> FaultCase:
        """Converts a SQLite Row to a validated FaultCase model."""
        symptoms = json.loads(row["symptoms"]) if row["symptoms"] else []
        telemetry = json.loads(row["telemetry_summary"]) if row["telemetry_summary"] else {}
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        return FaultCase(
            case_id=row["case_id"],
            source_title=row["source_title"],
            source_reference=row["source_reference"],
            source_type=row["source_type"],
            verification_status=row["verification_status"],
            subsystem=row["subsystem"],
            fault_code=row["fault_code"],
            symptoms=symptoms,
            telemetry_summary=telemetry,
            confirmed_root_cause=row["confirmed_root_cause"],
            corrective_action=row["corrective_action"],
            timestamp=row["timestamp"],
            metadata=metadata,
            is_indexed=bool(row["is_indexed"]),
            indexed_at=row["indexed_at"],
        )
