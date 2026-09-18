"""Bind one exact Cuttlefish runtime review to exact adb trust evidence.

This module validates already-produced local JSON evidence only. It never runs adb,
launches Cuttlefish, mutates a phone, promotes application status, or authorizes
physical-device writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .cuttlefish_evidence import EXPECTED_PRODUCT
from .i18n import LOCALES
from .runtime_tool_evidence import MAX_TOOL_BYTES

MAX_REPORT_BYTES = 16 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class RuntimeReviewTrustBundleError(ValueError):
    """Raised when runtime review and exact-adb trust evidence cannot be bound safely."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeReviewTrustBundleError("Runtime review trust JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_report(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute():
        raise RuntimeReviewTrustBundleError("Runtime review trust input path must be absolute.")
    if path.is_symlink() or not path.is_file():
        raise RuntimeReviewTrustBundleError("Runtime review trust input must be a regular non-symlink file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RuntimeReviewTrustBundleError("Runtime review trust input could not be read.") from exc
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise RuntimeReviewTrustBundleError("Runtime review trust input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeReviewTrustBundleError("Runtime review trust input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeReviewTrustBundleError("Runtime review trust input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _hex64(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RuntimeReviewTrustBundleError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _canonical_sha256(report: dict[str, object], excluded: set[str]) -> str:
    canonical = {key: value for key, value in report.items() if key not in excluded}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _unique_strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RuntimeReviewTrustBundleError(f"{field} must be a non-empty list.")
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256 or item in seen:
            raise RuntimeReviewTrustBundleError(f"{field} contains an invalid or duplicate value.")
        output.append(item)
        seen.add(item)
    return output


def _validate_run(report: dict[str, object]) -> tuple[str, str, str, list[str]]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_run_evidence_chain"
        or report.get("scope") != "BUILD_AND_RUNTIME"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("build_chain_complete") is not True
        or report.get("runtime_chain_complete") is not True
        or report.get("run_evidence_complete") is not True
    ):
        raise RuntimeReviewTrustBundleError("AOSP run evidence is not one complete exact SwirPhoneOS runtime run.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise RuntimeReviewTrustBundleError("AOSP run evidence violates the no-write/no-promotion boundary.")

    run_digest = _hex64(report.get("run_evidence_sha256"), "run_evidence_sha256")
    if run_digest != _canonical_sha256(report, {"run_evidence_sha256", "run_evidence_complete"}):
        raise RuntimeReviewTrustBundleError("AOSP run evidence canonical digest is invalid.")
    fingerprint_digest = _hex64(report.get("build_fingerprint_sha256"), "build_fingerprint_sha256")
    manifest_digest = _hex64(report.get("app_manifest_sha256"), "app_manifest_sha256")
    packages = _unique_strings(report.get("source_ready_packages"), "source_ready_packages")
    if packages != sorted(packages):
        raise RuntimeReviewTrustBundleError("AOSP run package set must be sorted deterministically.")
    return run_digest, fingerprint_digest, manifest_digest, packages


def _validate_runtime_trust(
    report: dict[str, object], *, run_digest: str, fingerprint_digest: str
) -> tuple[str, str, str, int]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_runtime_trust_bundle"
        or report.get("scope") != "CUTTLEFISH_BUILD_RUNTIME_AND_EXACT_ADB"
        or report.get("runtime_trust_chain_complete") is not True
        or report.get("runtime_tool_unchanged_across_evidence_window") is not True
        or report.get("tool_capture_executed_adb") is not False
    ):
        raise RuntimeReviewTrustBundleError("Runtime tool trust bundle is invalid or incomplete.")
    if (
        report.get("device_write_allowed") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise RuntimeReviewTrustBundleError("Runtime tool trust bundle violates the no-write/no-promotion boundary.")
    if report.get("run_evidence_sha256") != run_digest or report.get("build_fingerprint_sha256") != fingerprint_digest:
        raise RuntimeReviewTrustBundleError("Runtime tool trust bundle belongs to a different AOSP runtime run.")

    trust_digest = _hex64(report.get("runtime_trust_bundle_sha256"), "runtime_trust_bundle_sha256")
    if trust_digest != _canonical_sha256(report, {"runtime_trust_bundle_sha256"}):
        raise RuntimeReviewTrustBundleError("Runtime tool trust bundle canonical digest is invalid.")
    adb_sha = _hex64(report.get("adb_sha256"), "adb_sha256")
    path_identity = _hex64(report.get("adb_path_identity_sha256"), "adb_path_identity_sha256")
    size = report.get("adb_size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > MAX_TOOL_BYTES:
        raise RuntimeReviewTrustBundleError("Runtime tool trust bundle adb size is invalid.")
    return trust_digest, adb_sha, path_identity, size


def _validate_runtime_review(
    report: dict[str, object], *, fingerprint_digest: str, manifest_digest: str, packages: list[str]
) -> tuple[str, list[str]]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_runtime_review_bundle"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("runtime_review_evidence_complete") is not True
    ):
        raise RuntimeReviewTrustBundleError("Runtime localization review evidence is invalid or incomplete.")
    if (
        report.get("boot_identity_complete") is not True
        or report.get("app_launch_matrix_complete") is not True
        or report.get("locale_matrix_complete") is not True
        or report.get("original_app_locales_restored") is not True
    ):
        raise RuntimeReviewTrustBundleError("Runtime localization review does not prove the complete boot/launch/locale matrix.")
    if (
        report.get("rtl_visual_mirroring_verified") is not False
        or report.get("accessibility_review_complete") is not False
        or report.get("visual_translation_review_complete") is not False
        or report.get("physical_device_support_claimed") is not False
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
    ):
        raise RuntimeReviewTrustBundleError("Runtime localization review overclaims visual/accessibility/support state.")
    if report.get("build_fingerprint_sha256") != fingerprint_digest:
        raise RuntimeReviewTrustBundleError("Runtime localization review belongs to a different build fingerprint.")
    if report.get("app_manifest_sha256") != manifest_digest:
        raise RuntimeReviewTrustBundleError("Runtime localization review belongs to a different system-app manifest.")
    if _unique_strings(report.get("source_ready_packages"), "source_ready_packages") != packages:
        raise RuntimeReviewTrustBundleError("Runtime localization review package set differs from the AOSP run.")

    locales = _unique_strings(report.get("tested_locales"), "tested_locales")
    expected_locales = list(LOCALES)
    if locales != expected_locales:
        raise RuntimeReviewTrustBundleError("Runtime localization review locale set/order differs from the shared catalog.")
    expected_rtl = bool([code for code in expected_locales if LOCALES[code].direction == "rtl"])
    if report.get("rtl_runtime_switch_exercised") is not expected_rtl:
        raise RuntimeReviewTrustBundleError("Runtime localization review RTL-switch flag is inconsistent with the catalog.")

    review_digest = _hex64(report.get("runtime_review_sha256"), "runtime_review_sha256")
    if review_digest != _canonical_sha256(report, {"runtime_review_sha256", "runtime_review_evidence_complete"}):
        raise RuntimeReviewTrustBundleError("Runtime localization review canonical digest is invalid.")
    return review_digest, locales


def create_runtime_review_trust_bundle(
    run_path: Path,
    runtime_trust_path: Path,
    runtime_review_path: Path,
) -> dict[str, object]:
    """Bind one exact build/runtime run, exact adb trust window and locale review."""
    run, run_file_sha = _load_report(run_path)
    runtime_trust, trust_file_sha = _load_report(runtime_trust_path)
    runtime_review, review_file_sha = _load_report(runtime_review_path)

    run_digest, fingerprint_digest, manifest_digest, packages = _validate_run(run)
    trust_digest, adb_sha, adb_path_identity, adb_size = _validate_runtime_trust(
        runtime_trust,
        run_digest=run_digest,
        fingerprint_digest=fingerprint_digest,
    )
    review_digest, locales = _validate_runtime_review(
        runtime_review,
        fingerprint_digest=fingerprint_digest,
        manifest_digest=manifest_digest,
        packages=packages,
    )

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_runtime_review_trust_bundle",
        "scope": "CUTTLEFISH_BUILD_RUNTIME_I18N_AND_EXACT_ADB",
        "expected_product": EXPECTED_PRODUCT,
        "run_evidence_sha256": run_digest,
        "runtime_trust_bundle_sha256": trust_digest,
        "runtime_review_sha256": review_digest,
        "build_fingerprint_sha256": fingerprint_digest,
        "app_manifest_sha256": manifest_digest,
        "source_ready_packages": packages,
        "tested_locales": locales,
        "adb_sha256": adb_sha,
        "adb_path_identity_sha256": adb_path_identity,
        "adb_size": adb_size,
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "runtime_trust_bundle": trust_file_sha,
            "runtime_review_evidence": review_file_sha,
        },
        "build_runtime_chain_complete": True,
        "locale_review_chain_complete": True,
        "runtime_tool_unchanged_across_evidence_window": True,
        "rtl_visual_mirroring_verified": False,
        "accessibility_review_complete": False,
        "visual_translation_review_complete": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle binds one exact SwirPhoneOS Cuttlefish build/runtime run, locale matrix and unchanged local adb tool identity.",
            "It does not prove visual RTL quality, accessibility, translation quality, physical-device support or hardware behavior.",
            "It never authorizes phone writes, flashing, root, application status promotion or beta release.",
        ],
    }
    payload["runtime_review_trust_bundle_sha256"] = _canonical_sha256(payload, set())
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind exact SwirPhoneOS Cuttlefish runtime/i18n review to the unchanged trusted adb evidence window."
    )
    parser.add_argument("--run-evidence", required=True, type=Path)
    parser.add_argument("--runtime-trust", required=True, type=Path)
    parser.add_argument("--runtime-review", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = create_runtime_review_trust_bundle(
            args.run_evidence,
            args.runtime_trust,
            args.runtime_review,
        )
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeReviewTrustBundleError, OSError, ValueError):
        print(
            "Runtime review trust binding failed: use one exact complete AOSP runtime, localization review and unchanged adb trust window.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
