"""Bind one completed AOSP run to an unchanged exact host/toolchain window."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .aosp_host_evidence import AospHostEvidenceError, load_host_evidence, validate_host_evidence


class AospHostTrustBundleError(ValueError):
    """Raised when one AOSP run cannot be bound to stable host evidence."""


MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospHostTrustBundleError("Host trust JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_run(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute():
        raise AospHostTrustBundleError("AOSP run evidence path must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise AospHostTrustBundleError("AOSP run evidence must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise AospHostTrustBundleError("AOSP run evidence could not be read.") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise AospHostTrustBundleError("AOSP run evidence has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospHostTrustBundleError("AOSP run evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospHostTrustBundleError("AOSP run evidence root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise AospHostTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _validate_run(report: dict[str, object]) -> tuple[str, str, str, str]:
    if report.get("schema_version") != 1 or report.get("source") != "local_aosp_run_evidence_chain":
        raise AospHostTrustBundleError("AOSP run evidence identity is invalid.")
    scope = report.get("scope")
    if scope not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}:
        raise AospHostTrustBundleError("AOSP run evidence scope is invalid.")
    if report.get("build_chain_complete") is not True or report.get("run_evidence_complete") is not True:
        raise AospHostTrustBundleError("AOSP run build chain is incomplete.")
    if scope == "BUILD_AND_RUNTIME" and report.get("runtime_chain_complete") is not True:
        raise AospHostTrustBundleError("Runtime-scoped AOSP run does not contain a complete runtime chain.")
    if scope == "BUILD_ONLY" and report.get("runtime_chain_complete") is not False:
        raise AospHostTrustBundleError("Build-only AOSP run has inconsistent runtime state.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise AospHostTrustBundleError("AOSP run evidence violates the no-write/no-promotion boundary.")
    source_commit = report.get("source_commit")
    if not isinstance(source_commit, str) or _HEX40.fullmatch(source_commit) is None:
        raise AospHostTrustBundleError("AOSP run source commit is invalid.")
    workspace_sha = _hex64(report.get("workspace_sha256"), "workspace_sha256")
    run_sha = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    canonical = {
        key: value for key, value in report.items()
        if key not in {"run_evidence_sha256", "run_evidence_complete"}
    }
    if _canonical_sha(canonical) != run_sha:
        raise AospHostTrustBundleError("AOSP run evidence canonical digest is invalid.")
    return run_sha, workspace_sha, str(scope), source_commit


def create_host_trust_bundle(run_path: Path, pre_path: Path, post_path: Path) -> dict[str, object]:
    run, run_file_sha = _load_run(run_path)
    try:
        pre, pre_file_sha = load_host_evidence(pre_path, expected_phase="PRE_BUILD")
        post, post_file_sha = load_host_evidence(post_path, expected_phase="POST_BUILD")
        pre_identity = validate_host_evidence(pre, expected_phase="PRE_BUILD")
        post_identity = validate_host_evidence(post, expected_phase="POST_BUILD")
    except AospHostEvidenceError as exc:
        raise AospHostTrustBundleError("AOSP host evidence failed strict validation.") from exc

    run_sha, workspace_sha, scope, source_commit = _validate_run(run)
    if pre_identity[1] != workspace_sha or post_identity[1] != workspace_sha:
        raise AospHostTrustBundleError("AOSP host evidence belongs to a different workspace than the completed run.")
    if pre_identity[2] != post_identity[2] or pre_identity[3] != post_identity[3]:
        raise AospHostTrustBundleError("AOSP host or exact required tool identity changed across the build window.")
    if pre.get("host_identity_sha256") != post.get("host_identity_sha256"):
        raise AospHostTrustBundleError("AOSP static host identity changed across the build window.")
    if pre_identity[4] != post_identity[4]:
        raise AospHostTrustBundleError("AOSP KVM availability changed across the build window.")
    if scope == "BUILD_AND_RUNTIME" and pre_identity[4] is not True:
        raise AospHostTrustBundleError("Runtime-scoped AOSP evidence requires KVM availability across the build window.")

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_host_trust_bundle",
        "scope": "BUILD_WITH_EXACT_HOST_TOOLCHAIN_CONTINUITY",
        "aosp_run_scope": scope,
        "source_commit": source_commit,
        "run_evidence_sha256": run_sha,
        "workspace_identity_sha256": workspace_sha,
        "host_identity_sha256": pre.get("host_identity_sha256"),
        "toolchain_sha256": pre_identity[3],
        "environment_identity_sha256": pre_identity[2],
        "prebuild_host_evidence_sha256": pre_identity[0],
        "postbuild_host_evidence_sha256": post_identity[0],
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "host_prebuild_evidence": pre_file_sha,
            "host_postbuild_evidence": post_file_sha,
        },
        "kvm_available_across_build_window": pre_identity[4],
        "workspace_identity_bound": True,
        "toolchain_unchanged_across_build_window": True,
        "host_environment_unchanged_across_build_window": True,
        "host_trust_chain_complete": True,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle binds a completed AOSP run to unchanged exact required host-tool bytes and static host identity.",
            "It does not prove runtime boot unless the bound AOSP run itself has BUILD_AND_RUNTIME scope.",
            "It does not prove physical-device compatibility, install/rollback safety, root support, or beta readiness.",
        ],
    }
    payload["host_trust_bundle_sha256"] = _canonical_sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind one completed AOSP run to exact pre/post-build host evidence")
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--host-pre", required=True, type=Path)
    parser.add_argument("--host-post", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = create_host_trust_bundle(
            args.run_evidence.resolve(),
            args.host_pre.resolve(),
            args.host_post.resolve(),
        )
    except (AospHostTrustBundleError, OSError, ValueError):
        print(
            "AOSP host trust binding failed: use one completed run plus unchanged exact host evidence.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
