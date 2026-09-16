"""Privacy-checked export for SwirPhoneStudio diagnostic reports."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

ALLOWED_REPORT_KINDS = {"adb", "fastboot", "profiles"}
SENSITIVE_FRAGMENTS = ("serial", "imei", "meid", "unlock_token")


class ReportError(ValueError):
    """Raised when a report is unsafe or invalid for export."""


def _check_tree(value: object, depth: int = 0) -> None:
    if depth > 12:
        raise ReportError("Report nesting is too deep.")
    if isinstance(value, dict):
        if len(value) > 512:
            raise ReportError("Report object is too large.")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ReportError("Report keys must be strings.")
            lowered = key.lower()
            if any(fragment in lowered for fragment in SENSITIVE_FRAGMENTS):
                raise ReportError("Report contains a sensitive identifier field.")
            _check_tree(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 2048:
            raise ReportError("Report list is too large.")
        for item in value:
            _check_tree(item, depth + 1)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise ReportError("Report contains an unsupported value type.")
    elif isinstance(value, str) and len(value) > 8192:
        raise ReportError("Report contains an oversized text value.")


def build_export(kind: str, report: dict[str, object]) -> dict[str, object]:
    if kind not in ALLOWED_REPORT_KINDS:
        raise ReportError("Unknown diagnostic report kind.")
    if not isinstance(report, dict):
        raise ReportError("Diagnostic report must be an object.")
    _check_tree(report)
    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "application": "SwirPhoneStudio",
        "report_kind": kind,
        "privacy": "sanitized_no_intentional_device_serial_or_imei",
        "report": report,
    }


def write_export(path: Path, kind: str, report: dict[str, object]) -> None:
    if path.suffix.lower() != ".json":
        raise ReportError("Diagnostic exports must use a .json extension.")
    payload = build_export(kind, report)
    encoded = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if len(encoded.encode("utf-8")) > 2_000_000:
        raise ReportError("Diagnostic export is too large.")
    path.write_text(encoded, encoding="utf-8")
