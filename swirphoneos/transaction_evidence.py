"""Local, read-only transaction artifact verification and create-only journaling.

The module validates metadata and local files only. It exposes no external-device,
process-execution, network, installation, or mutation capability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
PROFILE_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._-]{0,63}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_ITEMS = 32
MAX_FILE_SIZE = 16 * 1024 * 1024 * 1024
PLAN_KEYS = {
    "schema_version", "transaction_id", "profile_id", "device_codename", "device_model",
    "expected_current_build", "target_build", "write_enabled", "owner_confirmation_required",
    "rollback_required", "install_artifacts", "rollback_artifacts", "notes",
}
ITEM_KEYS = {"name", "path", "sha256", "size", "kind"}


class TransactionEvidenceError(ValueError):
    """Raised when local transaction evidence is malformed or incomplete."""


@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    path: str
    sha256: str
    size: int
    kind: str


@dataclass(frozen=True)
class TransactionPlan:
    transaction_id: str
    profile_id: str
    device_codename: str
    device_model: str
    expected_current_build: str
    target_build: str
    install_artifacts: tuple[ArtifactSpec, ...]
    rollback_artifacts: tuple[ArtifactSpec, ...]
    notes: str
    canonical_sha256: str

    @property
    def write_allowed(self) -> bool:
        return False


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TransactionEvidenceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path, maximum_bytes: int = 262_144) -> object:
    if not path.is_file() or path.is_symlink():
        raise TransactionEvidenceError("Expected an existing regular JSON file, not a symlink.")
    try:
        if path.stat().st_size > maximum_bytes:
            raise TransactionEvidenceError("JSON input is oversized.")
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except TransactionEvidenceError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionEvidenceError("Input could not be read as strict UTF-8 JSON.") from exc


def _text(value: object, field: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise TransactionEvidenceError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise TransactionEvidenceError(f"{field} has an invalid value.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise TransactionEvidenceError(f"{field} contains control characters.")
    return value


def _relative_path(value: object) -> str:
    text = _text(value, "artifact path", 240)
    if "\\" in text or text.startswith("/"):
        raise TransactionEvidenceError("Artifact path must be a portable relative POSIX path.")
    path = PurePosixPath(text)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise TransactionEvidenceError("Artifact path contains an unsafe component.")
    return path.as_posix()


def _artifact(value: object, kind: str) -> ArtifactSpec:
    if not isinstance(value, dict) or set(value) != ITEM_KEYS:
        raise TransactionEvidenceError("Artifact entries must match schema v1 exactly.")
    name = _text(value["name"], "artifact name", 128)
    if not SAFE_TOKEN.fullmatch(name):
        raise TransactionEvidenceError("Artifact name must be a safe token.")
    path = _relative_path(value["path"])
    digest = _text(value["sha256"], "artifact sha256", 64)
    if not SHA256.fullmatch(digest):
        raise TransactionEvidenceError("Artifact sha256 must be lowercase 64-character hex.")
    size = value["size"]
    if type(size) is not int or size <= 0 or size > MAX_FILE_SIZE:
        raise TransactionEvidenceError("Artifact size must be a positive bounded integer.")
    item_kind = _text(value["kind"], "artifact kind", 16)
    if item_kind != kind:
        raise TransactionEvidenceError(f"Artifact kind must be {kind!r} in this set.")
    return ArtifactSpec(name=name, path=path, sha256=digest, size=size, kind=item_kind)


def _artifact_set(value: object, kind: str) -> tuple[ArtifactSpec, ...]:
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        raise TransactionEvidenceError(f"{kind}_artifacts must contain 1-{MAX_ITEMS} entries.")
    result = tuple(_artifact(item, kind) for item in value)
    names = [item.name for item in result]
    paths = [item.path for item in result]
    if len(set(names)) != len(names) or len(set(paths)) != len(paths):
        raise TransactionEvidenceError("Artifact names and paths must be unique within each set.")
    return result


def validate_plan(data: object) -> TransactionPlan:
    if not isinstance(data, dict) or set(data) != PLAN_KEYS:
        raise TransactionEvidenceError("Transaction plan must match schema v1 exactly.")
    if data["schema_version"] != 1:
        raise TransactionEvidenceError("Unsupported transaction plan schema version.")
    transaction_id = _text(data["transaction_id"], "transaction_id", 128)
    if not SAFE_TOKEN.fullmatch(transaction_id):
        raise TransactionEvidenceError("transaction_id must be a safe token.")
    profile_id = _text(data["profile_id"], "profile_id", 129)
    if not PROFILE_ID.fullmatch(profile_id):
        raise TransactionEvidenceError("profile_id must use vendor/codename safe-token form.")
    codename = _text(data["device_codename"], "device_codename", 128)
    if not SAFE_TOKEN.fullmatch(codename):
        raise TransactionEvidenceError("device_codename must be a safe token.")
    model = _text(data["device_model"], "device_model", 128)
    current_build = _text(data["expected_current_build"], "expected_current_build")
    target_build = _text(data["target_build"], "target_build")
    if data["write_enabled"] is not False:
        raise TransactionEvidenceError("Schema v1 is preparation-only and cannot enable writes.")
    if data["owner_confirmation_required"] is not True:
        raise TransactionEvidenceError("Explicit owner confirmation must remain mandatory.")
    if data["rollback_required"] is not True:
        raise TransactionEvidenceError("Rollback material must remain mandatory.")
    install = _artifact_set(data["install_artifacts"], "install")
    rollback = _artifact_set(data["rollback_artifacts"], "rollback")
    paths = [item.path for item in (*install, *rollback)]
    if len(set(paths)) != len(paths):
        raise TransactionEvidenceError("Artifact paths must be globally unique.")
    notes = _text(data["notes"], "notes", 2048)
    normalized = {
        "schema_version": 1,
        "transaction_id": transaction_id,
        "profile_id": profile_id,
        "device_codename": codename,
        "device_model": model,
        "expected_current_build": current_build,
        "target_build": target_build,
        "write_enabled": False,
        "owner_confirmation_required": True,
        "rollback_required": True,
        "install_artifacts": [item.__dict__ for item in install],
        "rollback_artifacts": [item.__dict__ for item in rollback],
        "notes": notes,
    }
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return TransactionPlan(
        transaction_id, profile_id, codename, model, current_build, target_build,
        install, rollback, notes, hashlib.sha256(canonical).hexdigest(),
    )


def load_plan(path: Path) -> TransactionPlan:
    return validate_plan(_load_json(path))


def _candidate(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise TransactionEvidenceError("Artifact path contains a symlink.")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise TransactionEvidenceError("Artifact escapes the trusted root or does not exist.") from exc
    if not resolved.is_file():
        raise TransactionEvidenceError("Artifact must be a regular file.")
    return resolved


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                digest.update(block)
    except OSError as exc:
        raise TransactionEvidenceError("Artifact could not be read.") from exc
    return digest.hexdigest()


def _verify(root: Path, spec: ArtifactSpec) -> dict[str, object]:
    path = _candidate(root, spec.path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise TransactionEvidenceError("Artifact metadata could not be read.") from exc
    if size != spec.size:
        raise TransactionEvidenceError(f"Artifact size mismatch for {spec.name}.")
    if _file_sha256(path) != spec.sha256:
        raise TransactionEvidenceError(f"Artifact SHA-256 mismatch for {spec.name}.")
    return {"name": spec.name, "path": spec.path, "kind": spec.kind, "size": spec.size, "sha256": spec.sha256, "verified": True}


def verify_artifacts(plan: TransactionPlan, artifact_root: Path) -> dict[str, object]:
    if not artifact_root.is_absolute() or not artifact_root.is_dir() or artifact_root.is_symlink():
        raise TransactionEvidenceError("Artifact root must be an existing absolute non-symlink directory.")
    install = [_verify(artifact_root, item) for item in plan.install_artifacts]
    rollback = [_verify(artifact_root, item) for item in plan.rollback_artifacts]
    return {
        "schema_version": 1,
        "transaction_id": plan.transaction_id,
        "profile_id": plan.profile_id,
        "plan_sha256": plan.canonical_sha256,
        "state": "ARTIFACTS_VERIFIED_READ_ONLY",
        "all_artifacts_verified": True,
        "rollback_ready": bool(rollback),
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "install_artifacts": install,
        "rollback_artifacts": rollback,
    }


def public_plan_summary(plan: TransactionPlan) -> dict[str, object]:
    return {
        "schema_version": 1,
        "transaction_id": plan.transaction_id,
        "profile_id": plan.profile_id,
        "device_codename": plan.device_codename,
        "device_model": plan.device_model,
        "expected_current_build": plan.expected_current_build,
        "target_build": plan.target_build,
        "install_artifact_count": len(plan.install_artifacts),
        "rollback_artifact_count": len(plan.rollback_artifacts),
        "plan_sha256": plan.canonical_sha256,
        "owner_confirmation_required": True,
        "rollback_required": True,
        "write_allowed": False,
        "state": "PLAN_ONLY",
    }


def create_journal(destination: Path, plan: TransactionPlan, evidence: dict[str, object]) -> dict[str, object]:
    if evidence.get("plan_sha256") != plan.canonical_sha256:
        raise TransactionEvidenceError("Artifact evidence does not belong to this plan.")
    if evidence.get("all_artifacts_verified") is not True or evidence.get("rollback_ready") is not True:
        raise TransactionEvidenceError("Complete verified rollback evidence is required.")
    if evidence.get("write_allowed") is not False:
        raise TransactionEvidenceError("Preparation evidence must never authorize writes.")
    if not destination.is_absolute() or destination.suffix.lower() != ".json":
        raise TransactionEvidenceError("Journal destination must be an absolute .json path.")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise TransactionEvidenceError("Journal parent must be an existing non-symlink directory.")
    core = {
        "schema_version": 1,
        "transaction_id": plan.transaction_id,
        "profile_id": plan.profile_id,
        "device_codename": plan.device_codename,
        "device_model": plan.device_model,
        "expected_current_build": plan.expected_current_build,
        "target_build": plan.target_build,
        "plan_sha256": plan.canonical_sha256,
        "state": "ARTIFACTS_VERIFIED_READ_ONLY",
        "rollback_ready": True,
        "owner_confirmation_recorded": False,
        "write_allowed": False,
        "install_artifacts": evidence["install_artifacts"],
        "rollback_artifacts": evidence["rollback_artifacts"],
    }
    core_bytes = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    payload = dict(core)
    payload["evidence_sha256"] = hashlib.sha256(core_bytes).hexdigest()
    payload["created_utc"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    encoded = (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(destination, flags, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise TransactionEvidenceError("Journal already exists; journals are create-only.") from exc
    except OSError as exc:
        raise TransactionEvidenceError("Journal could not be written safely.") from exc
    return payload
