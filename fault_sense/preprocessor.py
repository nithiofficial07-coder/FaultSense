"""Reusable data preprocessing utilities for elevator fault cases.

Utilizes Pandas and NumPy for text normalization, telemetry signal processing,
symptom parsing, missing-value imputation, and DataFrame cleansing.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from fault_sense.schema import FaultCase, FaultCaseValidationError


def clean_text(val: Any) -> str:
    """Normalizes whitespace and removes unprintable control characters from text."""
    if val is None or pd.isna(val):
        return ""
    text = str(val)
    # Remove ASCII control characters except standard whitespace
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Normalize multiple whitespaces and newlines into single spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_symptoms(val: Any) -> List[str]:
    """Parses and normalizes symptom inputs into a clean list of strings.

    Supports:
    - Lists of strings or numbers
    - JSON-encoded arrays: '["door fails to lock", "contact chatter"]'
    - Semicolon or comma-delimited strings: "door open; contact buzz"
    """
    if val is None or pd.isna(val):
        return []

    if isinstance(val, (list, tuple, np.ndarray)):
        raw_items = list(val)
    elif isinstance(val, str):
        trimmed = val.strip()
        if not trimmed:
            return []
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                parsed = json.loads(trimmed)
                raw_items = parsed if isinstance(parsed, list) else [str(parsed)]
            except Exception:
                sep = ";" if ";" in trimmed else ","
                raw_items = trimmed.strip("[]").split(sep)
        else:
            sep = ";" if ";" in trimmed else ","
            raw_items = trimmed.split(sep)
    else:
        raw_items = [str(val)]

    cleaned: List[str] = []
    seen = set()
    for item in raw_items:
        c = clean_text(item)
        if c and c.lower() not in seen:
            seen.add(c.lower())
            cleaned.append(c)

    return cleaned


def normalize_telemetry(val: Any) -> Dict[str, Any]:
    """Parses and casts telemetry inputs to a dictionary with sanitized values.

    Handles dicts, JSON strings, and ensures NaN/Infinity values are handled gracefully.
    """
    if val is None or pd.isna(val):
        return {}

    if isinstance(val, dict):
        raw_dict = dict(val)
    elif isinstance(val, str):
        trimmed = val.strip()
        if not trimmed:
            return {}
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                parsed = json.loads(trimmed)
                raw_dict = parsed if isinstance(parsed, dict) else {}
            except Exception:
                raw_dict = {}
        else:
            # Try key=value or key:value format
            raw_dict = {}
            pairs = re.split(r"[,;]\s*", trimmed)
            for pair in pairs:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    raw_dict[k.strip()] = v.strip()
                elif ":" in pair:
                    k, v = pair.split(":", 1)
                    raw_dict[k.strip()] = v.strip()
    else:
        return {}

    # Sanitize dictionary values
    sanitized: Dict[str, Any] = {}
    for k, v in raw_dict.items():
        k_clean = clean_text(k)
        if not k_clean:
            continue

        if v is None or pd.isna(v):
            sanitized[k_clean] = None
            continue

        # Try numeric cast
        if isinstance(v, (int, float, np.integer, np.floating)):
            if np.isnan(v) or np.isinf(v):
                sanitized[k_clean] = None
            elif isinstance(v, (int, np.integer)):
                sanitized[k_clean] = int(v)
            else:
                sanitized[k_clean] = round(float(v), 4)
        elif isinstance(v, str):
            v_str = v.strip()
            # Attempt to convert to float/int
            try:
                if "." in v_str or "e" in v_str.lower():
                    sanitized[k_clean] = round(float(v_str), 4)
                else:
                    sanitized[k_clean] = int(v_str)
            except ValueError:
                if v_str.lower() in ("true", "yes"):
                    sanitized[k_clean] = True
                elif v_str.lower() in ("false", "no"):
                    sanitized[k_clean] = False
                elif v_str.lower() in ("null", "none", "nan"):
                    sanitized[k_clean] = None
                else:
                    sanitized[k_clean] = clean_text(v_str)
        else:
            sanitized[k_clean] = v

    return sanitized


def compute_sensor_statistics(series: Union[Sequence[float], np.ndarray]) -> Dict[str, float]:
    """Computes descriptive statistical metrics from raw sensor telemetry readings using NumPy.

    Returns:
        dict containing mean, std, min, max, p50 (median), p95, and rms (root mean square).
    """
    arr = np.asarray(series, dtype=np.float64)
    # Remove NaN values
    arr = arr[~np.isnan(arr)]

    if arr.size == 0:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "rms": 0.0,
            "count": 0,
        }

    rms = float(np.sqrt(np.mean(arr**2)))
    return {
        "mean": round(float(np.mean(arr)), 4),
        "std": round(float(np.std(arr)), 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "p50": round(float(np.percentile(arr, 50)), 4),
        "p95": round(float(np.percentile(arr, 95)), 4),
        "rms": round(rms, 4),
        "count": int(arr.size),
    }


def zscore_normalize(
    val: float, baseline_mean: float, baseline_std: float, eps: float = 1e-6
) -> float:
    """Calculates z-score normalization for a telemetry sensor value."""
    std = baseline_std if baseline_std > eps else 1.0
    return round((val - baseline_mean) / std, 4)


def preprocess_fault_dataframe(
    df: pd.DataFrame, fill_defaults: bool = True
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Cleans, normalizes, and validates a Pandas DataFrame of fault cases.

    Performs:
    1. Column name standardization (lowercase, stripped).
    2. Missing value handling.
    3. Type normalization for text, symptoms, and telemetry columns.
    4. Anomaly and missing-field tracking without crashing.

    Returns:
        Tuple of (cleaned_df, issues_list).
    """
    issues: List[Dict[str, Any]] = []

    if df.empty:
        return df.copy(), issues

    # 1. Standardize column names
    clean_df = df.copy()
    clean_df.columns = [str(c).strip().lower().replace(" ", "_") for c in clean_df.columns]

    # Required schema columns
    required_cols = [
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
    ]

    for col in required_cols:
        if col not in clean_df.columns:
            if fill_defaults:
                clean_df[col] = None
                issues.append({
                    "row": None,
                    "field": col,
                    "issue": "missing_column",
                    "message": f"Required column '{col}' was missing and created with null values.",
                })

    # 2. Row-by-row cleaning and type conversions
    text_cols = [
        "case_id",
        "source_title",
        "source_reference",
        "source_type",
        "verification_status",
        "subsystem",
        "fault_code",
        "confirmed_root_cause",
        "corrective_action",
    ]

    for col in text_cols:
        if col in clean_df.columns:
            clean_df[col] = clean_df[col].apply(clean_text)

    # 3. Clean symptoms column
    if "symptoms" in clean_df.columns:
        clean_df["symptoms"] = clean_df["symptoms"].apply(normalize_symptoms)

    # 4. Clean telemetry_summary column
    if "telemetry_summary" in clean_df.columns:
        clean_df["telemetry_summary"] = clean_df["telemetry_summary"].apply(normalize_telemetry)

    # 5. Clean metadata column
    if "metadata" in clean_df.columns:
        clean_df["metadata"] = clean_df["metadata"].apply(
            lambda x: json.loads(x) if isinstance(x, str) and x.strip().startswith("{") else (x if isinstance(x, dict) else {})
        )
    else:
        clean_df["metadata"] = [{} for _ in range(len(clean_df))]

    # 6. Clean timestamp
    if "timestamp" in clean_df.columns:
        clean_df["timestamp"] = clean_df["timestamp"].apply(
            lambda x: clean_text(x) if x is not None and not pd.isna(x) else None
        )
    else:
        clean_df["timestamp"] = None

    return clean_df, issues


def dataframe_to_fault_cases(
    df: pd.DataFrame,
) -> Tuple[List[FaultCase], List[Dict[str, Any]]]:
    """Converts a preprocessed DataFrame into a list of validated FaultCase objects.

    Returns:
        Tuple of (valid_fault_cases, error_reports).
    """
    valid_cases: List[FaultCase] = []
    errors: List[Dict[str, Any]] = []

    clean_df, prep_issues = preprocess_fault_dataframe(df)

    for idx, row in clean_df.iterrows():
        row_dict = row.to_dict()
        case_id = row_dict.get("case_id", f"ROW-{idx}")
        try:
            fc = FaultCase.from_dict(row_dict)
            valid_cases.append(fc)
        except FaultCaseValidationError as exc:
            errors.append({
                "row_index": int(idx),
                "case_id": case_id,
                "field": exc.field_name,
                "error": exc.message,
                "invalid_value": exc.invalid_value,
            })
        except Exception as exc:
            errors.append({
                "row_index": int(idx),
                "case_id": case_id,
                "field": None,
                "error": str(exc),
                "invalid_value": None,
            })

    return valid_cases, errors
