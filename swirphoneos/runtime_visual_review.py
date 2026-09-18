"""Create and verify human review attestations for exact Cuttlefish visual evidence.

This module never promotes application status, authorizes release artifacts, or
treats screenshot existence as accessibility proof.  It binds a human visual
review to the exact already-trusted package×locale PNG matrix and computes
review results from the attested per-capture checks.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

from .cuttlefish_evidence import EXPECTED_PRODUCT
from .i18n import LOCALES

_MAX_JSON = 16 * 1024 * 1024
_MAX_REVIEWER = 128
_MAX_NOTE = 500
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\Z")
_LOCALE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?\Z")
_REVIEWED_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_CHECKS = ("translation", "text_clipping", "rtl_mirroring")
_FINAL = {"PASS", "FAIL"}
_PENDING = "PENDING"
_NA = "NOT_APPLICABLE"


class RuntimeVisualReviewError(ValueError):
    """Raised when visual-review inputs are unsafe, ambiguous, or inconsistent."""


def _strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeVisualReviewError("duplicate JSON key")
        result[key] = value
    return result


def _load(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RuntimeVisualReviewError("unsafe review evidence input")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_JSON:
        raise RuntimeVisualReviewError("invalid review evidence size")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeVisualReviewError("invalid review evidence JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeVisualReviewError("invalid review evidence root")
    return value, hashlib.sha256(raw).hexdigest()


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _hex(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RuntimeVisualReviewError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RuntimeVisualReviewError(f"{field} must be a non-empty list")
    if any(not isinstance(item, str) or not item or len(item) > 256 for item in value):
        raise RuntimeVisualReviewError(f"{field} contains an invalid value")
    if len(set(value)) != len(value):
        raise RuntimeVisualReviewError(f"{field} contains duplicates")
    return list(value)


def _validate_visual_trust(report: dict[str, object]) -> tuple[str, str, str, list[str], list[str], int]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_visual_trust_bundle"
        or report.get("scope") != "CUTTLEFISH_BUILD_RUNTIME_I18N_VISUAL_CAPTURE_AND_EXACT_ADB"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("visual_capture_matrix_complete") is not True
        or report.get("visual_bytes_reverified") is not True
    ):
        raise RuntimeVisualReviewError("runtime visual trust bundle is invalid or incomplete")
    if any(
        report.get(key) is not False
        for key in (
            "rtl_visual_mirroring_verified",
            "accessibility_review_complete",
            "visual_translation_review_complete",
            "physical_device_support_claimed",
            "device_write_allowed",
            "status_promotion_performed",
            "release_artifact_authorized",
        )
    ):
        raise RuntimeVisualReviewError("runtime visual trust bundle overclaims review or release state")

    digest = _hex(report.get("runtime_visual_trust_bundle_sha256"), "runtime_visual_trust_bundle_sha256")
    if _sha({key: value for key, value in report.items() if key != "runtime_visual_trust_bundle_sha256"}) != digest:
        raise RuntimeVisualReviewError("runtime visual trust bundle digest mismatch")

    visual_digest = _hex(report.get("visual_capture_sha256"), "visual_capture_sha256")
    fingerprint_sha = _hex(report.get("build_fingerprint_sha256"), "build_fingerprint_sha256")
    packages = _string_list(report.get("source_ready_packages"), "source_ready_packages")
    locales = _string_list(report.get("tested_locales"), "tested_locales")
    if packages != sorted(packages) or locales != list(LOCALES):
        raise RuntimeVisualReviewError("runtime visual trust package/locale scope is not canonical")

    count = report.get("capture_count")
    if not isinstance(count, int) or isinstance(count, bool) or count != len(packages) * len(locales):
        raise RuntimeVisualReviewError("runtime visual trust capture count is invalid")
    _hex(report.get("capture_directory_sha256"), "capture_directory_sha256")
    total_bytes = report.get("capture_total_bytes")
    if not isinstance(total_bytes, int) or isinstance(total_bytes, bool) or total_bytes <= 0:
        raise RuntimeVisualReviewError("runtime visual trust byte count is invalid")
    return digest, visual_digest, fingerprint_sha, packages, locales, count


def _validate_visual_report(
    report: dict[str, object],
    *,
    visual_digest: str,
    fingerprint_sha: str,
    packages: list[str],
    locales: list[str],
    count: int,
) -> list[dict[str, object]]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_visual_capture_matrix"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("capture_matrix_complete") is not True
        or report.get("visual_bytes_captured") is not True
        or report.get("original_app_locales_restored") is not True
    ):
        raise RuntimeVisualReviewError("visual capture report is invalid or incomplete")
    if report.get("build_fingerprint_sha256") != fingerprint_sha:
        raise RuntimeVisualReviewError("visual capture belongs to a different build")
    if report.get("tested_packages") != packages or report.get("tested_locales") != locales:
        raise RuntimeVisualReviewError("visual capture package/locale scope mismatch")

    digest = _hex(report.get("visual_capture_sha256"), "visual_capture_sha256")
    if digest != visual_digest:
        raise RuntimeVisualReviewError("visual capture digest differs from trusted bundle")
    if _sha({key: value for key, value in report.items() if key != "visual_capture_sha256"}) != digest:
        raise RuntimeVisualReviewError("visual capture report digest mismatch")

    captures = report.get("captures")
    if not isinstance(captures, list) or len(captures) != count or report.get("capture_count") != count:
        raise RuntimeVisualReviewError("visual capture inventory is incomplete")

    expected_pairs = [(package, locale) for locale in locales for package in packages]
    seen_names: set[str] = set()
    normalized: list[dict[str, object]] = []
    actual_pairs: list[tuple[str, str]] = []
    for item in captures:
        if not isinstance(item, dict):
            raise RuntimeVisualReviewError("visual capture record is malformed")
        package, locale = item.get("package"), item.get("locale")
        if not isinstance(package, str) or _PACKAGE.fullmatch(package) is None or package not in packages:
            raise RuntimeVisualReviewError("visual capture package is invalid")
        if not isinstance(locale, str) or _LOCALE.fullmatch(locale) is None or locale not in locales:
            raise RuntimeVisualReviewError("visual capture locale is invalid")
        direction = item.get("direction")
        if direction != LOCALES[locale].direction:
            raise RuntimeVisualReviewError("visual capture direction is inconsistent")
        name = item.get("relative_path")
        if (
            not isinstance(name, str)
            or PurePosixPath(name).name != name
            or not name.endswith(".png")
            or name in seen_names
        ):
            raise RuntimeVisualReviewError("visual capture filename is invalid or duplicated")
        capture_sha = _hex(item.get("sha256"), "capture sha256")
        size, width, height = item.get("size"), item.get("width"), item.get("height")
        if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in (size, width, height)):
            raise RuntimeVisualReviewError("visual capture size or dimensions are invalid")
        if item.get("foreground_confirmed") is not True:
            raise RuntimeVisualReviewError("visual capture foreground state was not confirmed")
        actual_pairs.append((package, locale))
        seen_names.add(name)
        normalized.append(
            {
                "package": package,
                "locale": locale,
                "direction": direction,
                "relative_path": name,
                "sha256": capture_sha,
            }
        )
    if actual_pairs != expected_pairs:
        raise RuntimeVisualReviewError("visual capture order/scope is not canonical")
    if _sha(captures) != report.get("capture_set_sha256"):
        raise RuntimeVisualReviewError("visual capture-set digest mismatch")
    return normalized


def _load_bound_inputs(
    visual_trust_path: Path, visual_report_path: Path
) -> tuple[dict[str, object], list[dict[str, object]], str, str, int]:
    trust, _ = _load(visual_trust_path)
    visual, _ = _load(visual_report_path)
    trust_digest, visual_digest, fingerprint_sha, packages, locales, count = _validate_visual_trust(trust)
    captures = _validate_visual_report(
        visual,
        visual_digest=visual_digest,
        fingerprint_sha=fingerprint_sha,
        packages=packages,
        locales=locales,
        count=count,
    )
    return trust, captures, trust_digest, visual_digest, count


def create_review_template(visual_trust_path: Path, visual_report_path: Path) -> dict[str, object]:
    """Create a deterministic PENDING human-review input bound to exact PNG evidence."""
    _trust, captures, trust_digest, visual_digest, count = _load_bound_inputs(
        visual_trust_path, visual_report_path
    )
    items: list[dict[str, object]] = []
    for capture in captures:
        rtl = capture["direction"] == "rtl"
        items.append(
            {
                **capture,
                "checks": {
                    "translation": _PENDING,
                    "text_clipping": _PENDING,
                    "rtl_mirroring": _PENDING if rtl else _NA,
                },
                "note": "",
            }
        )
    return {
        "schema_version": 1,
        "source": "local_cuttlefish_visual_human_review_input",
        "scope": "CUTTLEFISH_PACKAGE_LOCALE_VISUAL_REVIEW",
        "runtime_visual_trust_bundle_sha256": trust_digest,
        "visual_capture_sha256": visual_digest,
        "capture_count": count,
        "reviewer": "",
        "reviewed_at_utc": "",
        "items": items,
    }


def _clean_reviewer(value: object) -> str:
    if not isinstance(value, str):
        raise RuntimeVisualReviewError("reviewer must be text")
    clean = value.strip()
    if not clean or len(clean) > _MAX_REVIEWER or any(ord(ch) < 32 for ch in clean):
        raise RuntimeVisualReviewError("reviewer is empty, too long, or contains control characters")
    return clean


def _clean_reviewed_at(value: object) -> str:
    if not isinstance(value, str) or _REVIEWED_AT.fullmatch(value) is None:
        raise RuntimeVisualReviewError("reviewed_at_utc must use YYYY-MM-DDTHH:MM:SSZ")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise RuntimeVisualReviewError("reviewed_at_utc is not a valid UTC timestamp") from exc
    if parsed.year < 2020 or parsed.year > 2200:
        raise RuntimeVisualReviewError("reviewed_at_utc is outside the accepted range")
    return value


def _clean_note(value: object) -> str:
    if not isinstance(value, str) or len(value) > _MAX_NOTE or any(ord(ch) < 9 for ch in value):
        raise RuntimeVisualReviewError("review note is invalid")
    return value


def _validate_completed_item(actual: object, expected: dict[str, object]) -> tuple[bool, bool, bool | None]:
    if not isinstance(actual, dict):
        raise RuntimeVisualReviewError("human review item is malformed")
    if set(actual) != {"package", "locale", "direction", "relative_path", "sha256", "checks", "note"}:
        raise RuntimeVisualReviewError("human review item contains missing or unknown fields")
    for field in ("package", "locale", "direction", "relative_path", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeVisualReviewError(f"human review item {field} does not match trusted capture")

    checks = actual.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(_CHECKS):
        raise RuntimeVisualReviewError("human review checks are missing or contain unknown fields")
    translation = checks.get("translation")
    clipping = checks.get("text_clipping")
    rtl = checks.get("rtl_mirroring")
    if translation not in _FINAL or clipping not in _FINAL:
        raise RuntimeVisualReviewError("translation and text-clipping checks must be PASS or FAIL")
    if expected["direction"] == "rtl":
        if rtl not in _FINAL:
            raise RuntimeVisualReviewError("RTL captures require a PASS or FAIL mirroring review")
        rtl_result: bool | None = rtl == "PASS"
    else:
        if rtl != _NA:
            raise RuntimeVisualReviewError("LTR captures must keep rtl_mirroring NOT_APPLICABLE")
        rtl_result = None
    _clean_note(actual.get("note"))
    return translation == "PASS", clipping == "PASS", rtl_result


def verify_completed_review(
    visual_trust_path: Path,
    visual_report_path: Path,
    review_path: Path,
) -> dict[str, object]:
    """Verify a final human review and compute truthful pass/fail evidence."""
    _trust, captures, trust_digest, visual_digest, count = _load_bound_inputs(
        visual_trust_path, visual_report_path
    )
    review, review_file_sha = _load(review_path)
    if (
        review.get("schema_version") != 1
        or review.get("source") != "local_cuttlefish_visual_human_review_input"
        or review.get("scope") != "CUTTLEFISH_PACKAGE_LOCALE_VISUAL_REVIEW"
        or review.get("runtime_visual_trust_bundle_sha256") != trust_digest
        or review.get("visual_capture_sha256") != visual_digest
        or review.get("capture_count") != count
    ):
        raise RuntimeVisualReviewError("human review belongs to a different or invalid visual evidence set")
    if set(review) != {
        "schema_version",
        "source",
        "scope",
        "runtime_visual_trust_bundle_sha256",
        "visual_capture_sha256",
        "capture_count",
        "reviewer",
        "reviewed_at_utc",
        "items",
    }:
        raise RuntimeVisualReviewError("human review contains missing or unknown top-level fields")

    reviewer = _clean_reviewer(review.get("reviewer"))
    reviewed_at = _clean_reviewed_at(review.get("reviewed_at_utc"))
    items = review.get("items")
    if not isinstance(items, list) or len(items) != count:
        raise RuntimeVisualReviewError("human review item count does not match the trusted capture matrix")

    translation_results: list[bool] = []
    clipping_results: list[bool] = []
    rtl_results: list[bool] = []
    failures: list[dict[str, str]] = []
    for actual, expected in zip(items, captures, strict=True):
        translation_ok, clipping_ok, rtl_ok = _validate_completed_item(actual, expected)
        translation_results.append(translation_ok)
        clipping_results.append(clipping_ok)
        if rtl_ok is not None:
            rtl_results.append(rtl_ok)
        if not translation_ok:
            failures.append({"package": str(expected["package"]), "locale": str(expected["locale"]), "check": "translation"})
        if not clipping_ok:
            failures.append({"package": str(expected["package"]), "locale": str(expected["locale"]), "check": "text_clipping"})
        if rtl_ok is False:
            failures.append({"package": str(expected["package"]), "locale": str(expected["locale"]), "check": "rtl_mirroring"})

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_visual_human_review_evidence",
        "scope": "CUTTLEFISH_PACKAGE_LOCALE_VISUAL_REVIEW",
        "runtime_visual_trust_bundle_sha256": trust_digest,
        "visual_capture_sha256": visual_digest,
        "review_input_file_sha256": review_file_sha,
        "capture_count": count,
        "reviewer": reviewer,
        "reviewed_at_utc": reviewed_at,
        "human_review_complete": True,
        "visual_translation_review_complete": True,
        "visual_translation_review_passed": all(translation_results),
        "text_clipping_review_complete": True,
        "text_clipping_review_passed": all(clipping_results),
        "rtl_visual_review_complete": bool(rtl_results),
        "rtl_visual_mirroring_verified": bool(rtl_results) and all(rtl_results),
        "failed_check_count": len(failures),
        "failed_checks": failures,
        "accessibility_review_complete": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "This is a human attestation bound to exact Cuttlefish PNG evidence, not an automated visual-quality claim.",
            "Accessibility review remains separate and false; screenshots cannot prove focus order, semantics, screen-reader behavior or touch-target quality.",
            "This evidence never authorizes physical-device writes, root, application status promotion or release publication.",
        ],
    }
    payload["runtime_visual_review_evidence_sha256"] = _sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a human review bound to exact SwirPhoneOS Cuttlefish PNG evidence."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("template", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--visual-trust", required=True, type=Path)
        command.add_argument("--visual-report", required=True, type=Path)
        if name == "verify":
            command.add_argument("--review", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        visual_trust = args.visual_trust.resolve(strict=True)
        visual_report = args.visual_report.resolve(strict=True)
        if args.command == "template":
            report = create_review_template(visual_trust, visual_report)
        else:
            report = verify_completed_review(
                visual_trust,
                visual_report,
                args.review.resolve(strict=True),
            )
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeVisualReviewError, OSError, RuntimeError, UnicodeError, ValueError):
        print(
            "Runtime visual review failed: use the exact trusted visual bundle/report and a complete bound human review.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
