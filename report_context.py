#!/usr/bin/env python3
"""
report_context.py - Report context and filtered reports metadata.

Reads from storage (reports.json, factorySettings.json), computes last/next
validation dates, and provides filtered reports list. Used by bridge.py.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


def _parse_date(date_str) -> Optional[datetime]:
    """Parse ISO-like date string. Returns datetime or None."""
    if not date_str:
        return None
    s = str(date_str).replace("Z", "+00:00").split(".")[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except (ValueError, TypeError):
            continue
    return None


def _compute_next_validation_date(last_date_str: str) -> str:
    """Compute next validation date (last + 1 year). Returns DD-MM-YYYY or ''."""
    d = _parse_date(last_date_str)
    if d is None:
        return ""
    d = d.replace(year=d.year + 1)
    return d.strftime("%d-%m-%Y")


def get_report_context(storage_dir: Path) -> dict:
    """
    Read factory settings and reports from storage, compute last/next validation
    dates. Returns dict with companyName, modelNo, serialNo, location,
    instrumentId, lastValidationDate, nextValidationDate.
    """
    storage_dir = Path(storage_dir)
    result = {
        "companyName": "N/A",
        "modelNo": "N/A",
        "serialNo": "N/A",
        "location": "N/A",
        "instrumentId": "N/A",
        "lastValidationDate": "",
        "nextValidationDate": "",
    }

    # Load factory settings
    factory_path = storage_dir / "factorySettings.json"
    if factory_path.exists():
        try:
            with open(factory_path, "r", encoding="utf-8") as f:
                fs = json.load(f)
            result["companyName"] = fs.get("companyName") or "N/A"
            result["modelNo"] = fs.get("modelNo") or "N/A"
            result["serialNo"] = fs.get("serialNo") or "N/A"
            result["location"] = fs.get("companyLocation") or "N/A"
            result["instrumentId"] = fs.get("instrumentId") or "N/A"
        except Exception:
            pass

    # Load reports and compute validation dates
    reports_path = storage_dir / "reports.json"
    if reports_path.exists():
        try:
            with open(reports_path, "r", encoding="utf-8") as f:
                reports = json.load(f)
            if not isinstance(reports, list):
                reports = []
            validation_reports = [
                r for r in reports
                if r.get("type") == "validation"
                and r.get("createdAt")
                and not is_calibration_report(r)
            ]
            if validation_reports:
                validation_reports.sort(
                    key=lambda r: (r.get("createdAt") or ""), reverse=True
                )
                last_validation = validation_reports[0]
                created_at = last_validation.get("createdAt")
                if created_at:
                    d = _parse_date(created_at)
                    if d is not None:
                        result["lastValidationDate"] = d.strftime("%d-%m-%Y")
                        result["nextValidationDate"] = _compute_next_validation_date(
                            created_at
                        )
        except Exception:
            pass

    return result


def is_calibration_report(report: dict) -> bool:
    """Calibration records stay out of the validation list, including older rows saved as validation."""
    if not isinstance(report, dict):
        return False
    rtype = (report.get("type") or "").strip().lower()
    if rtype == "calibration":
        return True
    subtype = (report.get("validationSubtype") or "").strip().lower()
    name = (report.get("name") or "").strip().lower()
    status = (report.get("status") or "").strip().upper()
    return (
        subtype == "calibration"
        or name.startswith("calibration")
        or status.startswith("CALIBRATED")
    )


def get_filtered_reports_meta(storage_dir: Path, filter_type: str = "all") -> list:
    """
    Read reports from storage, filter by type (test|validation|calibration|all),
    sort by createdAt descending (completedAt fallback). Return list unchanged.
    """
    storage_dir = Path(storage_dir)
    reports_path = storage_dir / "reports.json"
    reports = []
    if reports_path.exists():
        try:
            with open(reports_path, "r", encoding="utf-8") as f:
                reports = json.load(f)
            if not isinstance(reports, list):
                reports = []
        except Exception:
            reports = []

    filter_type = (filter_type or "all").strip().lower()
    if filter_type == "calibration":
        reports = [r for r in reports if is_calibration_report(r)]
    elif filter_type == "validation":
        reports = [
            r for r in reports
            if r.get("type") == "validation" and not is_calibration_report(r)
        ]
    elif filter_type == "test":
        reports = [r for r in reports if r.get("type") == "test"]

    def sort_key(r):
        ts = r.get("completedAt") or r.get("createdAt") or ""
        d = _parse_date(ts)
        return d if d is not None else datetime.min

    reports.sort(key=sort_key, reverse=True)
    return reports
