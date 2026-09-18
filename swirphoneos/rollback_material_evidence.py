"""Exact-byte, read-only revalidation of rollback material for SwirRoot.

A transaction journal proves that artifacts matched a plan when the journal was
created. This module closes the time-of-check/time-of-use gap for later
SwirRoot readiness review by re-reading the exact rollback files and binding
that recheck to the journal digest. It performs no device I/O or mutation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from .journal_evidence import load_journal, validate_journal
from .transaction_evidence import SHA256, TransactionEvidenceError


class RollbackMaterialEvidenceError(ValueError):
    """Raised when rollback material cannot be revalidated fail-closed."""


_REPORT_KEYS = {
    "schema_version",
    "source",
    "transaction_id",
    "profile_id",
    "device_codename",
    "device_model",
    "expected_current_build",
    "target_build",
    "journal_evidence_sha256",
    "rollback_artifacts",
    "all_rollback_artifacts_reverified",
    "rollback_material_verified",
    "device_write_allowed",
    "root_operation_executed",
    "status_promotion_performed",
    "evidence_sha256",
}
_ITEM_KEYS = {"name", "path", "kind", "size", "sha256", "reverified"}
_MAX_REPORT_BYTES = 262_144
_MAX_ARTIFACT_BYTES = 16 * 1024 * 1024 * 1024


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RollbackMaterialEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: object, field: str, *, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise RollbackMaterialEvidenceError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise RollbackMaterialEvidenceError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise RollbackMaterialEvidenceError(f"{field} contains control characters.")
    return value


def _sha256(value: object, field: str) -> str:
    digest = _text(value, field, limit=64)
    if not SHA256.fullmatch(digest):
        raise RollbackMaterialEvidenceError(f"{field} must be a lowercase SHA-256 digest.")
    return digest


def _canonical_sha256(value: dict[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _candidate(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        if part in {"", ".", ".."}:
            raise RollbackMaterialEvidenceError("Rollback artifact path contains an unsafe component.")
        current = current / part
        if current.is_symlink():
            raise RollbackMaterialEvidenceError("Rollback artifact path contains a symlink.")
    try:
        root_resolved = root.resolve(strict=True)
        resolved = current.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise RollbackMaterialEvidenceError("Rollback artifact escapes the trusted root or does not exist.") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise RollbackMaterialEvidenceError("Rollback artifact must be a regular non-symlink file.")
    return resolved


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise RollbackMaterialEvidenceError("Rollback artifact could not be read.") from exc
    return digest.hexdigest()


def collect_rollback_material_evidence(
    journal: dict[str, object], artifact_root: Path
) -> dict[str, object]:
    """Re-hash every journal rollback artifact and bind the result to the journal."""
    try:
        journal = validate_journal(journal)
    except TransactionEvidenceError as exc:
        raise RollbackMaterialEvidenceError("Rollback journal failed validation.") from exc
    if not artifact_root.is_absolute() or not artifact_root.is_dir() or artifact_root.is_symlink():
        raise RollbackMaterialEvidenceError(
            "Artifact root must be an existing absolute non-symlink directory."
        )

    reverified: list[dict[str, object]] = []
    for item in journal["rollback_artifacts"]:
        path = _candidate(artifact_root, str(item["path"]))
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise RollbackMaterialEvidenceError("Rollback artifact metadata could not be read.") from exc
        if size <= 0 or size > _MAX_ARTIFACT_BYTES or size != item["size"]:
            raise RollbackMaterialEvidenceError("Rollback artifact size no longer matches the journal.")
        if _file_sha256(path) != item["sha256"]:
            raise RollbackMaterialEvidenceError("Rollback artifact SHA-256 no longer matches the journal.")
        reverified.append(
            {
                "name": item["name"],
                "path": item["path"],
                "kind": "rollback",
                "size": size,
                "sha256": item["sha256"],
                "reverified": True,
            }
        )

    core: dict[str, object] = {
        "schema_version": 1,
        "source": "swirphoneos_rollback_material_recheck",
        "transaction_id": journal["transaction_id"],
        "profile_id": journal["profile_id"],
        "device_codename": journal["device_codename"],
        "device_model": journal["device_model"],
        "expected_current_build": journal["expected_current_build"],
        "target_build": journal["target_build"],
        "journal_evidence_sha256": journal["evidence_sha256"],
        "rollback_artifacts": reverified,
        "all_rollback_artifacts_reverified": True,
        "rollback_material_verified": True,
        "device_write_allowed": False,
        "root_operation_executed": False,
        "status_promotion_performed": False,
    }
    result = dict(core)
    result["evidence_sha256"] = _canonical_sha256(core)
    validate_rollback_material_evidence(result)
    return result


def validate_rollback_material_evidence(report: object) -> dict[str, object]:
    if not isinstance(report, dict) or set(report) != _REPORT_KEYS:
        raise RollbackMaterialEvidenceError("Rollback material evidence must match schema v1 exactly.")
    if report["schema_version"] != 1 or report["source"] != "swirphoneos_rollback_material_recheck":
        raise RollbackMaterialEvidenceError("Rollback material provenance is invalid.")
    for key in (
        "transaction_id",
        "profile_id",
        "device_codename",
        "device_model",
        "expected_current_build",
        "target_build",
    ):
        _text(report[key], key)
    for key in ("journal_evidence_sha256", "evidence_sha256"):
        _sha256(report[key], key)

    items = report["rollback_artifacts"]
    if not isinstance(items, list) or not items or len(items) > 32:
        raise RollbackMaterialEvidenceError("Rollback material evidence requires a bounded non-empty artifact set.")
    names: set[str] = set()
    paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != _ITEM_KEYS:
            raise RollbackMaterialEvidenceError("Rollback material item is malformed.")
        name = _text(item["name"], "artifact name", limit=128)
        path = _text(item["path"], "artifact path", limit=240)
        if path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
            raise RollbackMaterialEvidenceError("Rollback material item path is unsafe.")
        if item["kind"] != "rollback" or item["reverified"] is not True:
            raise RollbackMaterialEvidenceError("Rollback material item is not positively reverified.")
        if type(item["size"]) is not int or item["size"] <= 0 or item["size"] > _MAX_ARTIFACT_BYTES:
            raise RollbackMaterialEvidenceError("Rollback material item size is invalid.")
        _sha256(item["sha256"], "artifact sha256")
        if name in names or path in paths:
            raise RollbackMaterialEvidenceError("Rollback material evidence contains duplicate items.")
        names.add(name)
        paths.add(path)

    for key in ("all_rollback_artifacts_reverified", "rollback_material_verified"):
        if report[key] is not True:
            raise RollbackMaterialEvidenceError("Rollback material evidence is incomplete.")
    for key in ("device_write_allowed", "root_operation_executed", "status_promotion_performed"):
        if report[key] is not False:
            raise RollbackMaterialEvidenceError("Rollback recheck can never authorize or claim a mutation.")

    digest = _sha256(report["evidence_sha256"], "evidence_sha256")
    core = {key: value for key, value in report.items() if key != "evidence_sha256"}
    if digest != _canonical_sha256(core):
        raise RollbackMaterialEvidenceError("Rollback material evidence integrity hash mismatch.")
    return report


def load_rollback_material_evidence(path: Path) -> dict[str, object]:
    if not path.is_absolute() or path.suffix.lower() != ".json":
        raise RollbackMaterialEvidenceError("Evidence path must be an absolute .json path.")
    if not path.is_file() or path.is_symlink():
        raise RollbackMaterialEvidenceError("Evidence must be an existing regular file, not a symlink.")
    try:
        if path.stat().st_size > _MAX_REPORT_BYTES:
            raise RollbackMaterialEvidenceError("Rollback material evidence is oversized.")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except RollbackMaterialEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RollbackMaterialEvidenceError("Rollback material evidence could not be read as strict UTF-8 JSON.") from exc
    return validate_rollback_material_evidence(data)


def collect_rollback_material_evidence_from_files(
    journal_path: Path, artifact_root: Path
) -> dict[str, object]:
    return collect_rollback_material_evidence(load_journal(journal_path), artifact_root)
