"""Read-only validation of persisted transaction journals.

A validated journal proves only local artifact review. It cannot prove hardware
identity, owner confirmation, update safety, or authorize a device mutation.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from .transaction_evidence import PROFILE_ID, SHA256, TransactionEvidenceError

JOURNAL_KEYS = {
    "schema_version", "transaction_id", "profile_id", "device_codename", "device_model",
    "expected_current_build", "target_build", "plan_sha256", "state", "rollback_ready",
    "owner_confirmation_recorded", "write_allowed", "install_artifacts", "rollback_artifacts",
    "evidence_sha256", "created_utc",
}
VERIFIED_ITEM_KEYS = {"name", "path", "kind", "size", "sha256", "verified"}
SAFE_TEXT = re.compile(r"[\x20-\x7e]{1,512}\Z")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TransactionEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value or len(value) > limit or not SAFE_TEXT.fullmatch(value):
        raise TransactionEvidenceError(f"{field} is invalid.")
    return value


def _verified_items(value: object, expected_kind: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value or len(value) > 32:
        raise TransactionEvidenceError("Journal artifact set is missing or oversized.")
    clean: list[dict[str, object]] = []
    seen_names: set[str] = set()
    seen_paths: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != VERIFIED_ITEM_KEYS:
            raise TransactionEvidenceError("Journal artifact entry does not match schema v1.")
        name = _text(item["name"], "artifact name", 128)
        path = _text(item["path"], "artifact path", 240)
        kind = _text(item["kind"], "artifact kind", 16)
        digest = _text(item["sha256"], "artifact sha256", 64)
        size = item["size"]
        if not SAFE_TOKEN.fullmatch(name) or kind != expected_kind or not SHA256.fullmatch(digest):
            raise TransactionEvidenceError("Journal artifact identity is invalid.")
        if path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")):
            raise TransactionEvidenceError("Journal artifact path is unsafe.")
        if type(size) is not int or size <= 0 or item["verified"] is not True:
            raise TransactionEvidenceError("Journal artifact verification metadata is invalid.")
        if name in seen_names or path in seen_paths:
            raise TransactionEvidenceError("Journal artifact entries contain duplicates.")
        seen_names.add(name)
        seen_paths.add(path)
        clean.append({"name": name, "path": path, "kind": kind, "size": size, "sha256": digest, "verified": True})
    return clean


def validate_journal(data: object) -> dict[str, object]:
    if not isinstance(data, dict) or set(data) != JOURNAL_KEYS:
        raise TransactionEvidenceError("Transaction journal must match schema v1 exactly.")
    if data["schema_version"] != 1 or data["state"] != "ARTIFACTS_VERIFIED_READ_ONLY":
        raise TransactionEvidenceError("Unsupported or unsafe journal state.")
    transaction_id = _text(data["transaction_id"], "transaction_id", 128)
    if not SAFE_TOKEN.fullmatch(transaction_id):
        raise TransactionEvidenceError("Journal transaction id is invalid.")
    profile_id = _text(data["profile_id"], "profile_id", 129)
    if not PROFILE_ID.fullmatch(profile_id):
        raise TransactionEvidenceError("Journal profile id is invalid.")
    codename = _text(data["device_codename"], "device_codename", 128)
    if not SAFE_TOKEN.fullmatch(codename):
        raise TransactionEvidenceError("Journal codename is invalid.")
    model = _text(data["device_model"], "device_model", 128)
    current_build = _text(data["expected_current_build"], "expected_current_build")
    target_build = _text(data["target_build"], "target_build")
    plan_sha = _text(data["plan_sha256"], "plan_sha256", 64)
    evidence_sha = _text(data["evidence_sha256"], "evidence_sha256", 64)
    if not SHA256.fullmatch(plan_sha) or not SHA256.fullmatch(evidence_sha):
        raise TransactionEvidenceError("Journal SHA-256 field is invalid.")
    if data["rollback_ready"] is not True or data["owner_confirmation_recorded"] is not False or data["write_allowed"] is not False:
        raise TransactionEvidenceError("Journal safety booleans were modified.")
    install = _verified_items(data["install_artifacts"], "install")
    rollback = _verified_items(data["rollback_artifacts"], "rollback")
    paths = [item["path"] for item in (*install, *rollback)]
    if len(paths) != len(set(paths)):
        raise TransactionEvidenceError("Journal artifact paths are not globally unique.")
    created = _text(data["created_utc"], "created_utc", 32)
    try:
        parsed = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransactionEvidenceError("Journal timestamp is invalid.") from exc
    if not created.endswith("Z") or parsed.tzinfo is None:
        raise TransactionEvidenceError("Journal timestamp must be UTC Z format.")

    core = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "profile_id": profile_id,
        "device_codename": codename,
        "device_model": model,
        "expected_current_build": current_build,
        "target_build": target_build,
        "plan_sha256": plan_sha,
        "state": "ARTIFACTS_VERIFIED_READ_ONLY",
        "rollback_ready": True,
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "install_artifacts": install,
        "rollback_artifacts": rollback,
    }
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    if hashlib.sha256(encoded).hexdigest() != evidence_sha:
        raise TransactionEvidenceError("Journal evidence SHA-256 does not match its canonical payload.")
    return {**core, "evidence_sha256": evidence_sha, "created_utc": created}


def load_journal(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise TransactionEvidenceError("Expected an existing regular journal JSON file.")
    try:
        if path.stat().st_size > 262_144:
            raise TransactionEvidenceError("Journal is oversized.")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except TransactionEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionEvidenceError("Journal could not be read as strict UTF-8 JSON.") from exc
    return validate_journal(data)


def public_journal_summary(journal: dict[str, object]) -> dict[str, object]:
    journal = validate_journal(journal)
    return {
        "schema_version": 1,
        "transaction_id": journal["transaction_id"],
        "profile_id": journal["profile_id"],
        "expected_current_build": journal["expected_current_build"],
        "target_build": journal["target_build"],
        "state": journal["state"],
        "rollback_ready": True,
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "plan_sha256": journal["plan_sha256"],
        "evidence_sha256": journal["evidence_sha256"],
        "install_artifact_count": len(journal["install_artifacts"]),
        "rollback_artifact_count": len(journal["rollback_artifacts"]),
        "created_utc": journal["created_utc"],
    }


def swirroot_gate_projection(journal: dict[str, object], *, profile_id: str, exact_build: str) -> dict[str, bool]:
    """Project what this local journal can prove to the SwirRoot safety policy.

    Hardware verification, owner confirmation, update safety and expected
    non-root state require independent evidence and therefore remain false.
    """
    journal = validate_journal(journal)
    return {
        "exact_build_match": journal["profile_id"] == profile_id and journal["target_build"] == exact_build,
        "verified_device_profile": False,
        "owner_confirmation": False,
        "rollback_material_verified": True,
        "journal_available": True,
        "update_state_safe": False,
        "expected_nonroot_state_known": False,
        "transition_allowed": False,
    }
