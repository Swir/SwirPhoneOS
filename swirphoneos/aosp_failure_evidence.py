"""Bounded, tamper-evident diagnostics for failed dedicated AOSP runs.

This module is intentionally recovery/diagnostics-only. It hashes already-created
local evidence and a bounded diagnostic tail; it never retries a build, changes an
AOSP workspace, starts an emulator, or touches a physical device.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Mapping

from .platform import load_baseline

SHA1 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_EVIDENCE_BYTES = 16 * 1024 * 1024
MAX_DIAGNOSTIC_BYTES = 256 * 1024
ALLOWED_PHASES = (
    "BOOTSTRAP",
    "TOOLCHAIN",
    "PREFLIGHT",
    "SOURCE_SYNC",
    "SOURCE_STAGE",
    "BUILD",
    "POST_BUILD_STAGE",
    "BUILD_EVIDENCE",
    "RUNTIME_LAUNCH",
    "RUNTIME_WAIT",
    "APP_SMOKE",
    "APP_I18N",
    "RUNTIME_REVIEW",
    "RUNTIME_BIND",
    "RUN_BIND",
    "TRUST_BIND",
)
EVIDENCE_IDS = (
    "run_context",
    "builder_preflight",
    "aosp_plan",
    "resolved_manifest",
    "stage_report",
    "post_build_stage",
    "build_evidence",
    "runtime_evidence",
    "app_smoke",
    "runtime_i18n",
    "runtime_review",
    "runtime_bundle",
    "aosp_run_evidence",
    "runtime_trust_bundle",
    "runtime_review_trust_bundle",
)
NEXT_ACTION = {
    "BOOTSTRAP": "Inspect runner availability and checkout diagnostics before retrying.",
    "TOOLCHAIN": "Inspect checkout/Python toolchain setup on the dedicated runner.",
    "PREFLIGHT": "Fix failed host prerequisites; do not start source synchronization until preflight passes.",
    "SOURCE_SYNC": "Inspect Repo synchronization output and exact-tag network/storage failures; keep the pinned revision unchanged.",
    "SOURCE_STAGE": "Fix staged-source contract or copy verification failures without widening the allowlist unnecessarily.",
    "BUILD": "Inspect the bounded Kati/Soong/Ninja diagnostic tail and fix the first reproducible compile failure.",
    "POST_BUILD_STAGE": "Treat staged-source drift as a build-integrity failure and restore exact reviewed bytes.",
    "BUILD_EVIDENCE": "Fix missing/incorrect product artifacts or pinned build identity; do not weaken provenance checks.",
    "RUNTIME_LAUNCH": "Inspect Cuttlefish host prerequisites and launch output for the exact built product.",
    "RUNTIME_WAIT": "Inspect boot failure while preserving exact product/fingerprint/runtime identity checks.",
    "APP_SMOKE": "Fix the first source-ready app that fails package-local launch or resumed-activity confirmation.",
    "APP_I18N": "Fix the first package/locale failure and verify every captured locale override is restored; reset the disposable guest if restoration cannot be proven.",
    "RUNTIME_REVIEW": "Resolve boot/launch/locale/manifest continuity without promoting app status or visual/accessibility claims.",
    "RUNTIME_BIND": "Resolve build/runtime fingerprint continuity failure; never mix evidence from different builds.",
    "RUN_BIND": "Resolve cross-report continuity mismatch before considering any runtime status promotion.",
    "TRUST_BIND": "Resolve exact adb/run/runtime-review continuity; do not weaken tool or localization trust checks.",
}


class AospFailureEvidenceError(ValueError):
    """Raised when failure evidence input is unsafe or internally inconsistent."""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_sha256(data: Mapping[str, object]) -> str:
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return _sha256_bytes(encoded)


def _describe_file(path: Path | None, *, max_bytes: int) -> dict[str, object]:
    if path is None:
        return {"requested": False, "present": False, "file_name": None, "size": None, "sha256": None}
    if path.is_symlink():
        raise AospFailureEvidenceError("Failure evidence inputs must not be symbolic links.")
    if not path.exists():
        return {"requested": True, "present": False, "file_name": path.name, "size": None, "sha256": None}
    if not path.is_file():
        raise AospFailureEvidenceError("Failure evidence inputs must be regular files.")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise AospFailureEvidenceError("Failure evidence input metadata could not be read.") from exc
    if size < 0 or size > max_bytes:
        raise AospFailureEvidenceError("Failure evidence input exceeds the bounded size limit.")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AospFailureEvidenceError("Failure evidence input could not be read.") from exc
    if len(payload) != size:
        raise AospFailureEvidenceError("Failure evidence input changed while it was being read.")
    return {
        "requested": True,
        "present": True,
        "file_name": path.name,
        "size": size,
        "sha256": _sha256_bytes(payload),
    }


def collect_failure_evidence(
    *,
    source_commit: str,
    phase: str,
    baseline_path: Path,
    evidence_paths: Mapping[str, Path | None],
    diagnostic_log: Path | None = None,
) -> dict[str, object]:
    """Create a deterministic read-only report for one failed AOSP workflow run."""
    if not isinstance(source_commit, str) or SHA1.fullmatch(source_commit) is None:
        raise AospFailureEvidenceError("source_commit must be one lowercase 40-character Git SHA-1.")
    if phase not in ALLOWED_PHASES:
        raise AospFailureEvidenceError("Unknown AOSP workflow failure phase.")
    unknown = set(evidence_paths) - set(EVIDENCE_IDS)
    if unknown:
        raise AospFailureEvidenceError("Unknown failure evidence identifiers are not allowed.")

    baseline = load_baseline(baseline_path)
    inventory: list[dict[str, object]] = []
    for evidence_id in EVIDENCE_IDS:
        item = {"id": evidence_id}
        item.update(_describe_file(evidence_paths.get(evidence_id), max_bytes=MAX_EVIDENCE_BYTES))
        inventory.append(item)

    diagnostic = _describe_file(diagnostic_log, max_bytes=MAX_DIAGNOSTIC_BYTES)
    core: dict[str, object] = {
        "schema_version": 1,
        "operation": "READ_ONLY_AOSP_FAILURE_EVIDENCE",
        "state": "FAILED_NOT_READY",
        "source_commit": source_commit,
        "failed_phase": phase,
        "baseline": {
            "status": baseline.status,
            "platform": baseline.platform,
            "api_level": baseline.api_level,
            "release_tag": baseline.candidate_release_tag,
            "build_id": baseline.candidate_build_id,
            "security_patch_level": baseline.security_patch_level,
            "repo_init_revision": baseline.repo_init_revision,
        },
        "evidence_inventory": inventory,
        "diagnostic_tail": diagnostic,
        "next_action": NEXT_ACTION[phase],
        "build_succeeded": False,
        "runtime_succeeded": False,
        "status_promotion_allowed": False,
        "device_write_allowed": False,
        "flash_allowed": False,
        "root_allowed": False,
        "warnings": [
            "This report proves only what diagnostic files existed at failure time; it is not build or runtime evidence.",
            "A missing evidence file is recorded as missing and must never be inferred as a successful earlier phase.",
            "Failure diagnostics never authorize device writes, flashing, root, support status, or beta release.",
        ],
    }
    result = dict(core)
    result["failure_evidence_sha256"] = _canonical_sha256(core)
    return result


def validate_failure_evidence(report: object) -> dict[str, object]:
    """Revalidate a saved schema-v1 report and its canonical integrity digest."""
    required = {
        "schema_version", "operation", "state", "source_commit", "failed_phase", "baseline",
        "evidence_inventory", "diagnostic_tail", "next_action", "build_succeeded", "runtime_succeeded",
        "status_promotion_allowed", "device_write_allowed", "flash_allowed", "root_allowed", "warnings",
        "failure_evidence_sha256",
    }
    if not isinstance(report, dict) or set(report) != required:
        raise AospFailureEvidenceError("Failure evidence must match schema v1 exactly.")
    if report["schema_version"] != 1 or report["operation"] != "READ_ONLY_AOSP_FAILURE_EVIDENCE" or report["state"] != "FAILED_NOT_READY":
        raise AospFailureEvidenceError("Failure evidence identity is invalid.")
    if not isinstance(report["source_commit"], str) or SHA1.fullmatch(report["source_commit"]) is None:
        raise AospFailureEvidenceError("Failure evidence source commit is invalid.")
    if report["failed_phase"] not in ALLOWED_PHASES or report["next_action"] != NEXT_ACTION[report["failed_phase"]]:
        raise AospFailureEvidenceError("Failure phase/action is invalid.")
    for key in ("build_succeeded", "runtime_succeeded", "status_promotion_allowed", "device_write_allowed", "flash_allowed", "root_allowed"):
        if report[key] is not False:
            raise AospFailureEvidenceError("Failure evidence safety flags must remain false.")
    inventory = report["evidence_inventory"]
    if not isinstance(inventory, list) or [item.get("id") for item in inventory if isinstance(item, dict)] != list(EVIDENCE_IDS):
        raise AospFailureEvidenceError("Failure evidence inventory is incomplete or reordered.")
    for item in inventory:
        if set(item) != {"id", "requested", "present", "file_name", "size", "sha256"}:
            raise AospFailureEvidenceError("Failure evidence inventory item is malformed.")
        if not isinstance(item["requested"], bool) or not isinstance(item["present"], bool):
            raise AospFailureEvidenceError("Failure evidence presence flags are invalid.")
        if item["present"]:
            if not item["requested"] or not isinstance(item["file_name"], str) or not item["file_name"]:
                raise AospFailureEvidenceError("Present evidence metadata is invalid.")
            if not isinstance(item["size"], int) or isinstance(item["size"], bool) or not 0 <= item["size"] <= MAX_EVIDENCE_BYTES:
                raise AospFailureEvidenceError("Evidence size is invalid.")
            if not isinstance(item["sha256"], str) or SHA256.fullmatch(item["sha256"]) is None:
                raise AospFailureEvidenceError("Evidence SHA-256 is invalid.")
        elif item["size"] is not None or item["sha256"] is not None:
            raise AospFailureEvidenceError("Missing evidence cannot contain size/hash claims.")
    diagnostic = report["diagnostic_tail"]
    if not isinstance(diagnostic, dict) or set(diagnostic) != {"requested", "present", "file_name", "size", "sha256"}:
        raise AospFailureEvidenceError("Diagnostic tail metadata is malformed.")
    if diagnostic["present"]:
        if not diagnostic["requested"] or not isinstance(diagnostic["size"], int) or isinstance(diagnostic["size"], bool) or not 0 <= diagnostic["size"] <= MAX_DIAGNOSTIC_BYTES:
            raise AospFailureEvidenceError("Diagnostic tail size is invalid.")
        if not isinstance(diagnostic["sha256"], str) or SHA256.fullmatch(diagnostic["sha256"]) is None:
            raise AospFailureEvidenceError("Diagnostic tail SHA-256 is invalid.")
    elif diagnostic["size"] is not None or diagnostic["sha256"] is not None:
        raise AospFailureEvidenceError("Missing diagnostic tail cannot contain size/hash claims.")
    warnings = report["warnings"]
    if not isinstance(warnings, list) or len(warnings) != 3 or not all(isinstance(item, str) and item for item in warnings):
        raise AospFailureEvidenceError("Failure evidence warnings are malformed.")
    baseline = report["baseline"]
    if not isinstance(baseline, dict) or set(baseline) != {"status", "platform", "api_level", "release_tag", "build_id", "security_patch_level", "repo_init_revision"}:
        raise AospFailureEvidenceError("Failure evidence baseline summary is malformed.")
    digest = report["failure_evidence_sha256"]
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        raise AospFailureEvidenceError("Failure evidence digest is malformed.")
    core = dict(report)
    del core["failure_evidence_sha256"]
    if _canonical_sha256(core) != digest:
        raise AospFailureEvidenceError("Failure evidence integrity digest does not match report content.")
    return report
