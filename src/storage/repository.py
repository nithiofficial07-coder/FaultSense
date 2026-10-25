"""Data access repositories for fault cases and investigation sessions.

Bridges SQLite relational tables with Python domain models.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fault_sense.repository import DuplicateCaseError, FaultCaseRepository
from fault_sense.schema import FaultCase
from src.storage.database import DatabaseManager, get_db_manager
from src.utils.exceptions import StorageError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Canonical alias for fault case repository
CaseRepository = FaultCaseRepository


class InvestigationRepository:
    """Manages persistent technician diagnosis sessions and investigation records."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or get_db_manager()

    def create(self, session_data: Dict[str, Any]) -> str:
        """Stores a new investigation record."""
        now_iso = datetime.now(timezone.utc).isoformat()
        inv_id = str(session_data.get("investigation_id") or f"INV-{int(datetime.now().timestamp())}")

        verif_rec = session_data.get("verification_record")
        if isinstance(verif_rec, (dict, list)):
            verif_rec = json.dumps(verif_rec)

        diag_rep = session_data.get("diagnostic_report")
        if isinstance(diag_rep, (dict, list)):
            diag_rep = json.dumps(diag_rep)

        evid_pkg = session_data.get("evidence_package")
        if isinstance(evid_pkg, (dict, list)):
            evid_pkg = json.dumps(evid_pkg)

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO investigations (
                    investigation_id, elevator_id, building_id, subsystem,
                    fault_code, symptoms, telemetry, root_cause_hypothesis,
                    recommended_actions, confidence_score, matched_case_ids,
                    status, technician_notes, verification_record, retry_count,
                    diagnostic_report, evidence_package,
                    manufacturer, equipment_model, severity, operating_conditions, problem_description,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    inv_id,
                    session_data.get("elevator_id", "UNKNOWN"),
                    session_data.get("building_id", ""),
                    session_data.get("subsystem", "other"),
                    session_data.get("fault_code", ""),
                    json.dumps(session_data.get("symptoms", [])),
                    json.dumps(session_data.get("telemetry", {})),
                    session_data.get("root_cause_hypothesis", ""),
                    session_data.get("recommended_actions", ""),
                    float(session_data.get("confidence_score", 0.0)),
                    json.dumps(session_data.get("matched_case_ids", [])),
                    session_data.get("status", "open"),
                    session_data.get("technician_notes", ""),
                    verif_rec,
                    int(session_data.get("retry_count", 0)),
                    diag_rep,
                    evid_pkg,
                    session_data.get("manufacturer", ""),
                    session_data.get("equipment_model", ""),
                    session_data.get("severity", "Medium"),
                    session_data.get("operating_conditions", ""),
                    session_data.get("problem_description", ""),
                    now_iso,
                    now_iso,
                ),
            )
        logger.info("Recorded investigation session: %s", inv_id)
        return inv_id

    def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves past investigation sessions."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM investigations ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["symptoms"] = json.loads(d["symptoms"]) if d.get("symptoms") else []
                d["telemetry"] = json.loads(d["telemetry"]) if d.get("telemetry") else {}
                d["matched_case_ids"] = (
                    json.loads(d["matched_case_ids"]) if d.get("matched_case_ids") else []
                )
                if d.get("verification_record"):
                    try:
                        d["verification_record"] = json.loads(d["verification_record"])
                    except Exception:
                        pass
                if d.get("diagnostic_report"):
                    try:
                        d["diagnostic_report"] = json.loads(d["diagnostic_report"])
                    except Exception:
                        pass
                if d.get("evidence_package"):
                    try:
                        d["evidence_package"] = json.loads(d["evidence_package"])
                    except Exception:
                        pass
                if d.get("technician_review"):
                    try:
                        d["technician_review"] = json.loads(d["technician_review"])
                    except Exception:
                        pass
                results.append(d)
            return results

    def get(self, investigation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single investigation record by ID."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM investigations WHERE investigation_id = ?",
                (investigation_id.strip(),),
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            d["symptoms"] = json.loads(d["symptoms"]) if d.get("symptoms") else []
            d["telemetry"] = json.loads(d["telemetry"]) if d.get("telemetry") else {}
            d["matched_case_ids"] = (
                json.loads(d["matched_case_ids"]) if d.get("matched_case_ids") else []
            )
            if d.get("verification_record"):
                try:
                    d["verification_record"] = json.loads(d["verification_record"])
                except Exception:
                    pass
            if d.get("diagnostic_report"):
                try:
                    d["diagnostic_report"] = json.loads(d["diagnostic_report"])
                except Exception:
                    pass
            if d.get("evidence_package"):
                try:
                    d["evidence_package"] = json.loads(d["evidence_package"])
                except Exception:
                    pass
            if d.get("technician_review"):
                try:
                    d["technician_review"] = json.loads(d["technician_review"])
                except Exception:
                    pass
            return d

    def update_technician_review(
        self,
        investigation_id: str,
        technician_notes: str,
        review_data: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> bool:
        """Updates technician notes, verification review checklist, and status."""
        now_iso = datetime.now(timezone.utc).isoformat()
        review_json = json.dumps(review_data) if review_data else None
        with self.db.get_connection() as conn:
            if status:
                conn.execute(
                    """
                    UPDATE investigations
                    SET technician_notes = ?, technician_review = ?, status = ?, updated_at = ?
                    WHERE investigation_id = ?
                    """,
                    (technician_notes, review_json, status, now_iso, investigation_id.strip()),
                )
            else:
                conn.execute(
                    """
                    UPDATE investigations
                    SET technician_notes = ?, technician_review = ?, updated_at = ?
                    WHERE investigation_id = ?
                    """,
                    (technician_notes, review_json, now_iso, investigation_id.strip()),
                )
            logger.info("Updated technician review for investigation: %s", investigation_id)
            return True


__all__ = ["FaultCaseRepository", "InvestigationRepository", "DuplicateCaseError"]
