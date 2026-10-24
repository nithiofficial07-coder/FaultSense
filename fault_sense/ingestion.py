"""Data Ingestion Pipeline for Elevator Fault Cases.

Provides CSV and JSON data ingestion with:
- File-type and file-size validation
- Encoding resilience
- Required-column checks
- Missing-value handling
- Type normalization via preprocessor
- Duplicate detection (in-batch and cross-repository)
- Invalid-record tracking and clear import summaries
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

from fault_sense.preprocessor import dataframe_to_fault_cases, preprocess_fault_dataframe
from fault_sense.schema import FaultCase, FaultCaseValidationError, SourceType, VerificationStatus


@dataclass
class IngestionConfig:
    """Configuration options for data ingestion."""
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_extensions: Tuple[str, ...] = (".csv", ".json", ".jsonl")
    strict_provenance: bool = True
    deduplicate_in_batch: bool = True


@dataclass
class ImportSummary:
    """Detailed summary of an ingestion run."""
    source_file: str
    file_type: str
    file_size_bytes: int
    total_records: int = 0
    valid_records: int = 0
    duplicate_records: int = 0
    rejected_records: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        """Returns True if at least one valid record was imported and no fatal file error occurred."""
        return self.valid_records > 0 or (self.total_records == 0 and not self.errors)

    def to_dict(self) -> Dict[str, Any]:
        """Converts summary to dictionary."""
        return {
            "source_file": self.source_file,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "duplicate_records": self.duplicate_records,
            "rejected_records": self.rejected_records,
            "error_count": len(self.errors),
            "errors": self.errors,
            "warnings": self.warnings,
            "duration_seconds": round(self.duration_seconds, 4),
            "success": self.success,
        }

    def formatted_report(self) -> str:
        """Generates a human-readable text report of the ingestion run."""
        lines = [
            "=" * 60,
            "ELEVATOR FAULT CASE INGESTION SUMMARY",
            "=" * 60,
            f"Source File      : {self.source_file}",
            f"File Type        : {self.file_type.upper()}",
            f"File Size        : {self.file_size_bytes:,} bytes",
            f"Processing Time  : {self.duration_seconds:.4f} s",
            f"Total Records    : {self.total_records}",
            f"Valid / Accepted : {self.valid_records}",
            f"Duplicates Found : {self.duplicate_records}",
            f"Rejected Records : {self.rejected_records}",
            "-" * 60,
        ]

        if self.warnings:
            lines.append("Warnings:")
            for w in self.warnings:
                lines.append(f"  [!] {w}")
            lines.append("-" * 60)

        if self.errors:
            lines.append(f"Rejected Record Details ({len(self.errors)} issues):")
            for err in self.errors[:10]:  # Cap display to first 10
                row = err.get("row_index", "N/A")
                cid = err.get("case_id", "Unknown")
                fld = err.get("field") or "general"
                msg = err.get("error") or err.get("message", "Validation error")
                lines.append(f"  - Row {row} (Case ID: {cid}) [{fld}]: {msg}")
            if len(self.errors) > 10:
                lines.append(f"  ... and {len(self.errors) - 10} more errors.")
            lines.append("-" * 60)

        lines.append("=" * 60)
        return "\n".join(lines)


class FaultCaseIngestionPipeline:
    """Robust pipeline for importing, validating, and normalizing fault case datasets."""

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config or IngestionConfig()

    def validate_file(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str], int]:
        """Validates file existence, format extension, and size limits.

        Returns:
            Tuple of (is_valid, error_message, file_size_bytes).
        """
        path = Path(file_path)
        if not path.exists():
            return False, f"File does not exist: {path}", 0

        if not path.is_file():
            return False, f"Specified path is not a file: {path}", 0

        suffix = path.suffix.lower()
        if suffix not in self.config.allowed_extensions:
            return (
                False,
                f"Unsupported file format '{suffix}'. Allowed: {', '.join(self.config.allowed_extensions)}",
                0,
            )

        try:
            size = path.stat().st_size
        except OSError as exc:
            return False, f"Could not inspect file size: {exc}", 0

        if size == 0:
            return False, "File is completely empty (0 bytes).", 0

        if size > self.config.max_file_size_bytes:
            return (
                False,
                f"File size ({size:,} bytes) exceeds maximum permitted limit ({self.config.max_file_size_bytes:,} bytes).",
                size,
            )

        return True, None, size

    def ingest_file(
        self, file_path: Union[str, Path], existing_case_ids: Optional[Set[str]] = None
    ) -> Tuple[List[FaultCase], ImportSummary]:
        """Imports fault cases from either CSV or JSON file format."""
        path = Path(file_path)
        is_valid, err_msg, file_size = self.validate_file(path)
        ext = path.suffix.lower()

        if not is_valid:
            summary = ImportSummary(
                source_file=str(path),
                file_type=ext,
                file_size_bytes=file_size,
                errors=[{"row_index": None, "case_id": None, "field": "file", "error": err_msg}],
            )
            return [], summary

        if ext == ".csv":
            return self.ingest_csv(path, existing_case_ids=existing_case_ids)
        elif ext in (".json", ".jsonl"):
            return self.ingest_json(path, existing_case_ids=existing_case_ids)
        else:
            summary = ImportSummary(
                source_file=str(path),
                file_type=ext,
                file_size_bytes=file_size,
                errors=[{
                    "row_index": None,
                    "case_id": None,
                    "field": "file",
                    "error": f"Unsupported file format '{ext}'. Allowed: {', '.join(self.config.allowed_extensions)}",
                }],
            )
            return [], summary

    def ingest_csv(
        self, file_path: Union[str, Path], existing_case_ids: Optional[Set[str]] = None
    ) -> Tuple[List[FaultCase], ImportSummary]:
        """Imports and validates elevator fault cases from a CSV file."""
        start_time = time.time()
        path = Path(file_path)

        is_valid, err_msg, file_size = self.validate_file(path)
        summary = ImportSummary(source_file=str(path), file_type="csv", file_size_bytes=file_size)

        if not is_valid:
            summary.errors.append({"row_index": None, "case_id": None, "field": "file", "error": err_msg})
            summary.duration_seconds = time.time() - start_time
            return [], summary

        # Read CSV with encoding fallback
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        df: Optional[pd.DataFrame] = None
        read_error = None

        for enc in encodings:
            try:
                df = pd.read_csv(path, encoding=enc)
                break
            except Exception as exc:
                read_error = exc

        if df is None:
            summary.errors.append({
                "row_index": None,
                "case_id": None,
                "field": "file_read",
                "error": f"Failed to parse CSV file: {read_error}",
            })
            summary.duration_seconds = time.time() - start_time
            return [], summary

        if df.empty:
            summary.warnings.append("CSV file contains no data rows.")
            summary.duration_seconds = time.time() - start_time
            return [], summary

        summary.total_records = len(df)
        cases, summary = self._process_records_dataframe(df, summary, existing_case_ids)
        summary.duration_seconds = time.time() - start_time
        return cases, summary

    def ingest_json(
        self, file_path: Union[str, Path], existing_case_ids: Optional[Set[str]] = None
    ) -> Tuple[List[FaultCase], ImportSummary]:
        """Imports and validates elevator fault cases from a JSON or JSONL file."""
        start_time = time.time()
        path = Path(file_path)

        is_valid, err_msg, file_size = self.validate_file(path)
        summary = ImportSummary(source_file=str(path), file_type="json", file_size_bytes=file_size)

        if not is_valid:
            summary.errors.append({"row_index": None, "case_id": None, "field": "file", "error": err_msg})
            summary.duration_seconds = time.time() - start_time
            return [], summary

        records: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    summary.warnings.append("JSON file is empty.")
                    summary.duration_seconds = time.time() - start_time
                    return [], summary

                if content.startswith("["):
                    # JSON array
                    parsed = json.loads(content)
                    if isinstance(parsed, list):
                        records = parsed
                    else:
                        summary.errors.append({
                            "row_index": None,
                            "case_id": None,
                            "field": "json_structure",
                            "error": "Root JSON element must be an array or object list.",
                        })
                        summary.duration_seconds = time.time() - start_time
                        return [], summary
                elif content.startswith("{"):
                    # Either a single object or multi-line JSONL
                    try:
                        single_obj = json.loads(content)
                        records = [single_obj]
                    except json.JSONDecodeError:
                        # Attempt JSONL line-by-line
                        f.seek(0)
                        for line_no, line in enumerate(f, start=1):
                            line_str = line.strip()
                            if line_str:
                                try:
                                    records.append(json.loads(line_str))
                                except json.JSONDecodeError as exc:
                                    summary.errors.append({
                                        "row_index": line_no,
                                        "case_id": None,
                                        "field": "syntax",
                                        "error": f"JSON syntax error on line {line_no}: {exc}",
                                    })
                else:
                    # Try reading JSONL
                    with open(path, "r", encoding="utf-8") as f2:
                        for line_no, line in enumerate(f2, start=1):
                            line_str = line.strip()
                            if line_str:
                                try:
                                    records.append(json.loads(line_str))
                                except json.JSONDecodeError as exc:
                                    summary.errors.append({
                                        "row_index": line_no,
                                        "case_id": None,
                                        "field": "syntax",
                                        "error": f"JSON syntax error on line {line_no}: {exc}",
                                    })
        except json.JSONDecodeError as exc:
            summary.errors.append({
                "row_index": None,
                "case_id": None,
                "field": "json_decode",
                "error": f"Malformed JSON syntax: {exc}",
            })
            summary.duration_seconds = time.time() - start_time
            return [], summary
        except Exception as exc:
            summary.errors.append({
                "row_index": None,
                "case_id": None,
                "field": "file_read",
                "error": f"Unexpected error reading JSON: {exc}",
            })
            summary.duration_seconds = time.time() - start_time
            return [], summary

        summary.total_records = len(records)
        cases, summary = self._process_records_list(records, summary, existing_case_ids)
        summary.duration_seconds = time.time() - start_time
        return cases, summary

    def _process_records_dataframe(
        self, df: pd.DataFrame, summary: ImportSummary, existing_case_ids: Optional[Set[str]]
    ) -> Tuple[List[FaultCase], ImportSummary]:
        """Processes and validates DataFrame rows into FaultCase instances."""
        clean_df, prep_warnings = preprocess_fault_dataframe(df)
        for w in prep_warnings:
            summary.warnings.append(w.get("message", "Preprocessing notice"))

        records = clean_df.to_dict(orient="records")
        return self._process_records_list(records, summary, existing_case_ids)

    def _process_records_list(
        self,
        records: List[Dict[str, Any]],
        summary: ImportSummary,
        existing_case_ids: Optional[Set[str]],
    ) -> Tuple[List[FaultCase], ImportSummary]:
        """Validates records, flags duplicates, and instantiates FaultCase models."""
        seen_case_ids: Set[str] = set()
        external_case_ids = existing_case_ids or set()
        valid_cases: List[FaultCase] = []

        for idx, rec in enumerate(records, start=1):
            if not isinstance(rec, dict):
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": None,
                    "field": "record_type",
                    "error": f"Expected dictionary record, got {type(rec).__name__}",
                })
                continue

            case_id = str(rec.get("case_id", "")).strip()

            # Required case_id check
            if not case_id or case_id.lower() in ("nan", "none", "null"):
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": None,
                    "field": "case_id",
                    "error": "Missing or empty required field 'case_id'.",
                })
                continue

            # Duplicate detection within batch
            if self.config.deduplicate_in_batch and case_id in seen_case_ids:
                summary.duplicate_records += 1
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": case_id,
                    "field": "case_id",
                    "error": f"Duplicate case_id '{case_id}' found within the current batch.",
                })
                continue

            # Duplicate detection against existing repository
            if case_id in external_case_ids:
                summary.duplicate_records += 1
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": case_id,
                    "field": "case_id",
                    "error": f"Duplicate case_id '{case_id}' already exists in knowledge base.",
                })
                continue

            # Validate FaultCase instantiation
            try:
                fc = FaultCase.from_dict(rec)
                seen_case_ids.add(case_id)
                valid_cases.append(fc)
                summary.valid_records += 1
            except FaultCaseValidationError as exc:
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": case_id,
                    "field": exc.field_name,
                    "error": exc.message,
                    "invalid_value": exc.invalid_value,
                })
            except Exception as exc:
                summary.rejected_records += 1
                summary.errors.append({
                    "row_index": idx,
                    "case_id": case_id,
                    "field": "general",
                    "error": str(exc),
                })

        return valid_cases, summary
