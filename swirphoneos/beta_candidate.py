"""Fail-closed cryptographic binding for future SwirPhoneOS beta candidates.

This module verifies that every evidence reference in a fully-filled project ledger
is bound to exact local bytes and that release artifacts are hashed from the same
candidate bundle. It deliberately does NOT decide whether gate evidence is
semantically sufficient. Publication therefore remains blocked until dedicated
gate-specific validators are implemented and reviewed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

REQUIRED_GATES = frozenset({
    "system_build",
    "physical_boot",
    "core_hardware",
    "install_restore",
    "windows_runtime",
    "security_review",
    "artifact_trust",
    "final_ci",
    "release_docs",
})
REQUIRED_RELEASE_KINDS = frozenset({
    "os_image",
    "windows_package",
    "release_manifest",
    "checksums",
})
ALLOWED_RELEASE_KINDS = REQUIRED_RELEASE_KINDS | frozenset({
    "recovery_image",
    "install_bundle",
    "source_manifest",
})
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_BOUND_FILE_SIZE = 32 * 1024 * 1024 * 1024
MANIFEST_KEYS = {
    "schema_version",
    "candidate_commit",
    "version",
    "evidence",
    "release_artifacts",
}
RECORD_KEYS = {"path", "sha256", "size", "kind"}


class BetaCandidateError(ValueError):
    """Raised when a candidate bundle is ambiguous, tampered with, or unsafe to trust."""


@dataclass(frozen=True)
class BoundFile:
    path: str
    sha256: str
    size: int
    kind: str


@dataclass(frozen=True)
class CandidateManifest:
    candidate_commit: str
    version: str
    evidence: tuple[BoundFile, ...]
    release_artifacts: tuple[BoundFile, ...]


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise BetaCandidateError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _text(value: object, field: str, *, limit: int = 256) -> str:
    if not isinstance(value, str):
        raise BetaCandidateError(f"{field} must be a string.")
    value = value.strip()
    if not value or len(value) > limit or not value.isascii():
        raise BetaCandidateError(f"{field} is invalid.")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise BetaCandidateError(f"{field} contains control characters.")
    return value


def _relative_path(value: object) -> str:
    text = _text(value, "candidate path", limit=240)
    if "\\" in text or text.startswith("/"):
        raise BetaCandidateError("Candidate paths must be portable relative POSIX paths.")
    path = PurePosixPath(text)
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BetaCandidateError("Candidate path contains an unsafe component.")
    return path.as_posix()


def _bound_file(value: object, *, evidence: bool) -> BoundFile:
    if not isinstance(value, dict) or set(value) != RECORD_KEYS:
        raise BetaCandidateError("Candidate file records must match schema v1 exactly.")
    path = _relative_path(value["path"])
    digest = _text(value["sha256"], "sha256", limit=64)
    if not SHA256.fullmatch(digest):
        raise BetaCandidateError("sha256 must be lowercase 64-character hex.")
    size = value["size"]
    if type(size) is not int or size <= 0 or size > MAX_BOUND_FILE_SIZE:
        raise BetaCandidateError("Candidate file size must be a positive bounded integer.")
    kind = _text(value["kind"], "kind", limit=64)
    if evidence:
        if kind != "gate_evidence":
            raise BetaCandidateError("Gate evidence records must use kind='gate_evidence'.")
    elif kind not in ALLOWED_RELEASE_KINDS:
        raise BetaCandidateError("Unknown release artifact kind.")
    return BoundFile(path=path, sha256=digest, size=size, kind=kind)


def validate_candidate_manifest(data: object) -> CandidateManifest:
    if not isinstance(data, dict) or set(data) != MANIFEST_KEYS:
        raise BetaCandidateError("Beta candidate manifest must match schema v1 exactly.")
    if data["schema_version"] != 1:
        raise BetaCandidateError("Unsupported beta candidate manifest schema.")
    candidate_commit = _text(data["candidate_commit"], "candidate_commit", limit=40)
    if not COMMIT.fullmatch(candidate_commit):
        raise BetaCandidateError("candidate_commit must be an exact lowercase 40-hex commit.")
    version = _text(data["version"], "version", limit=80)

    evidence_raw = data["evidence"]
    artifact_raw = data["release_artifacts"]
    if not isinstance(evidence_raw, list) or not evidence_raw:
        raise BetaCandidateError("Candidate manifest must contain gate evidence.")
    if not isinstance(artifact_raw, list) or not artifact_raw:
        raise BetaCandidateError("Candidate manifest must contain release artifacts.")
    if len(evidence_raw) > 128 or len(artifact_raw) > 64:
        raise BetaCandidateError("Candidate manifest contains too many file records.")

    evidence = tuple(_bound_file(item, evidence=True) for item in evidence_raw)
    artifacts = tuple(_bound_file(item, evidence=False) for item in artifact_raw)
    all_paths = [item.path for item in (*evidence, *artifacts)]
    if len(all_paths) != len(set(all_paths)):
        raise BetaCandidateError("Candidate file paths must be globally unique.")

    kinds = {item.kind for item in artifacts}
    missing_kinds = sorted(REQUIRED_RELEASE_KINDS - kinds)
    if missing_kinds:
        raise BetaCandidateError(
            "Candidate manifest is missing required release artifact kinds: "
            + ", ".join(missing_kinds)
            + "."
        )
    return CandidateManifest(
        candidate_commit=candidate_commit,
        version=version,
        evidence=evidence,
        release_artifacts=artifacts,
    )


def load_candidate_manifest(path: Path) -> CandidateManifest:
    if not path.is_file() or path.is_symlink():
        raise BetaCandidateError("Candidate manifest must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise BetaCandidateError("Candidate manifest could not be read.") from exc
    if not raw or len(raw) > MAX_MANIFEST_BYTES:
        raise BetaCandidateError("Candidate manifest has an invalid size.")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except BetaCandidateError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BetaCandidateError("Candidate manifest must be strict UTF-8 JSON.") from exc
    return validate_candidate_manifest(data)


def _candidate(root: Path, relative: str) -> Path:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise BetaCandidateError("Candidate path contains a symlink.")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise BetaCandidateError("Candidate file escapes the trusted root or does not exist.") from exc
    if not resolved.is_file():
        raise BetaCandidateError("Candidate record must resolve to a regular file.")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BetaCandidateError("Candidate file could not be read.") from exc
    return digest.hexdigest()


def _verify_bound_file(root: Path, item: BoundFile) -> dict[str, object]:
    path = _candidate(root, item.path)
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BetaCandidateError("Candidate file metadata could not be read.") from exc
    if size != item.size:
        raise BetaCandidateError(f"Candidate file size mismatch for {item.path}.")
    digest = _sha256_file(path)
    if digest != item.sha256:
        raise BetaCandidateError(f"Candidate file SHA-256 mismatch for {item.path}.")
    return {
        "path": item.path,
        "sha256": item.sha256,
        "size": item.size,
        "kind": item.kind,
        "verified": True,
    }


def _ledger_gate_references(ledger: object) -> tuple[str, str, frozenset[str]]:
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1:
        raise BetaCandidateError("Project ledger schema is unsupported.")
    version = _text(ledger.get("version"), "ledger version", limit=80)
    commit = _text(ledger.get("candidate_commit"), "ledger candidate_commit", limit=40)
    if not COMMIT.fullmatch(commit):
        raise BetaCandidateError("Project ledger does not identify an exact candidate commit.")
    gates = ledger.get("beta_gates")
    if not isinstance(gates, list) or len(gates) != len(REQUIRED_GATES):
        raise BetaCandidateError("Project ledger does not contain the exact mandatory beta gate set.")

    seen: set[str] = set()
    references: set[str] = set()
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {"id", "passed", "evidence"}:
            raise BetaCandidateError("Project ledger beta gate entry is malformed.")
        gate_id = _text(gate["id"], "gate id", limit=64)
        if gate_id in seen or gate_id not in REQUIRED_GATES:
            raise BetaCandidateError("Project ledger beta gate set is duplicated or unknown.")
        seen.add(gate_id)
        if gate["passed"] is not True:
            raise BetaCandidateError(f"Beta gate {gate_id} is not passed.")
        evidence = gate["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise BetaCandidateError(f"Beta gate {gate_id} has no evidence references.")
        for value in evidence:
            references.add(_relative_path(value))
    if seen != set(REQUIRED_GATES):
        raise BetaCandidateError("Project ledger is missing mandatory beta gates.")
    return version, commit, frozenset(references)


def verify_candidate_bundle(
    ledger: object,
    manifest: CandidateManifest,
    root: Path,
) -> dict[str, object]:
    """Verify exact file binding without claiming semantic gate sufficiency."""
    root = root.expanduser()
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise BetaCandidateError("Candidate root must be an existing absolute non-symlink directory.")

    version, candidate_commit, gate_references = _ledger_gate_references(ledger)
    if manifest.candidate_commit != candidate_commit:
        raise BetaCandidateError("Candidate manifest commit does not match the project ledger.")
    if manifest.version != version:
        raise BetaCandidateError("Candidate manifest version does not match the project ledger.")

    manifest_evidence = {item.path for item in manifest.evidence}
    if manifest_evidence != set(gate_references):
        missing = sorted(set(gate_references) - manifest_evidence)
        extra = sorted(manifest_evidence - set(gate_references))
        detail = []
        if missing:
            detail.append("missing ledger references: " + ", ".join(missing))
        if extra:
            detail.append("unreferenced evidence: " + ", ".join(extra))
        raise BetaCandidateError("Candidate evidence binding mismatch (" + "; ".join(detail) + ").")

    verified_evidence = [_verify_bound_file(root, item) for item in manifest.evidence]
    verified_artifacts = [_verify_bound_file(root, item) for item in manifest.release_artifacts]
    release_kinds = sorted({item.kind for item in manifest.release_artifacts})
    return {
        "schema_version": 1,
        "candidate_commit": candidate_commit,
        "version": version,
        "beta_gate_count": len(REQUIRED_GATES),
        "gate_reference_count": len(gate_references),
        "verified_gate_evidence_files": len(verified_evidence),
        "verified_release_artifacts": len(verified_artifacts),
        "release_artifact_kinds": release_kinds,
        "candidate_binding_verified": True,
        "semantic_gate_validation_complete": False,
        "beta_release_allowed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "publication_blocker": (
            "Exact candidate files are cryptographically bound, but gate-specific semantic "
            "evidence validators are not yet complete; publication remains fail-closed."
        ),
        "evidence": verified_evidence,
        "release_artifacts": verified_artifacts,
    }


def verify_candidate_bundle_from_files(
    ledger_path: Path,
    manifest_path: Path,
    root: Path,
) -> dict[str, object]:
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise BetaCandidateError("Project ledger must be a regular non-symlink file.")
    try:
        raw = ledger_path.read_bytes()
        if not raw or len(raw) > MAX_MANIFEST_BYTES:
            raise BetaCandidateError("Project ledger has an invalid size.")
        ledger = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except BetaCandidateError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BetaCandidateError("Project ledger must be strict UTF-8 JSON.") from exc
    manifest = load_candidate_manifest(manifest_path)
    return verify_candidate_bundle(ledger, manifest, root)
