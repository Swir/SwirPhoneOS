"""Create and verify human accessibility review attestations for exact Cuttlefish evidence.

This module keeps accessibility review separate from visual translation/RTL review.
It never auto-passes human checks, promotes application status, authorizes releases,
or enables physical-device writes. Every attestation is bound to the exact trusted
Cuttlefish package×locale PNG matrix.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .runtime_visual_review import (
    RuntimeVisualReviewError,
    _clean_note,
    _clean_reviewer,
    _clean_reviewed_at,
    _load,
    _load_bound_inputs,
    _sha,
)

_CHECKS = (
    "spoken_labels",
    "focus_order",
    "touch_targets",
    "keyboard_navigation",
    "state_announcements",
)
_FINAL = {"PASS", "FAIL"}
_PENDING = "PENDING"
_MAX_ASSISTIVE_TECHNOLOGY = 128
_INPUT_METHODS = ["touch", "keyboard"]

RuntimeAccessibilityReviewError = RuntimeVisualReviewError


def _clean_assistive_technology(value: object) -> str:
    if not isinstance(value, str):
        raise RuntimeAccessibilityReviewError("assistive_technology must be text")
    clean = value.strip()
    if (
        not clean
        or len(clean) > _MAX_ASSISTIVE_TECHNOLOGY
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in clean)
    ):
        raise RuntimeAccessibilityReviewError(
            "assistive_technology is empty, too long, or contains control characters"
        )
    return clean


def create_accessibility_template(
    visual_trust_path: Path,
    visual_report_path: Path,
) -> dict[str, object]:
    """Create a deterministic PENDING accessibility review bound to exact PNG evidence."""
    _trust, captures, trust_digest, visual_digest, count = _load_bound_inputs(
        visual_trust_path, visual_report_path
    )
    items: list[dict[str, object]] = []
    for capture in captures:
        items.append(
            {
                **capture,
                "checks": {check: _PENDING for check in _CHECKS},
                "note": "",
            }
        )
    return {
        "schema_version": 1,
        "source": "local_cuttlefish_accessibility_human_review_input",
        "scope": "CUTTLEFISH_PACKAGE_LOCALE_ACCESSIBILITY_REVIEW",
        "runtime_visual_trust_bundle_sha256": trust_digest,
        "visual_capture_sha256": visual_digest,
        "capture_count": count,
        "reviewer": "",
        "reviewed_at_utc": "",
        "assistive_technology": "",
        "input_methods": list(_INPUT_METHODS),
        "items": items,
    }


def _validate_completed_item(
    actual: object,
    expected: dict[str, object],
) -> tuple[dict[str, bool], str]:
    if not isinstance(actual, dict):
        raise RuntimeAccessibilityReviewError("accessibility review item is malformed")
    if set(actual) != {
        "package",
        "locale",
        "direction",
        "relative_path",
        "sha256",
        "checks",
        "note",
    }:
        raise RuntimeAccessibilityReviewError(
            "accessibility review item contains missing or unknown fields"
        )
    for field in ("package", "locale", "direction", "relative_path", "sha256"):
        if actual.get(field) != expected[field]:
            raise RuntimeAccessibilityReviewError(
                f"accessibility review item {field} does not match trusted capture"
            )

    checks = actual.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(_CHECKS):
        raise RuntimeAccessibilityReviewError(
            "accessibility review checks are missing or contain unknown fields"
        )
    results: dict[str, bool] = {}
    for check in _CHECKS:
        value = checks.get(check)
        if value not in _FINAL:
            raise RuntimeAccessibilityReviewError(
                f"accessibility check {check} must be PASS or FAIL"
            )
        results[check] = value == "PASS"
    note = _clean_note(actual.get("note"))
    return results, note


def verify_completed_accessibility_review(
    visual_trust_path: Path,
    visual_report_path: Path,
    review_path: Path,
) -> dict[str, object]:
    """Verify a final human accessibility review and compute truthful pass/fail evidence."""
    _trust, captures, trust_digest, visual_digest, count = _load_bound_inputs(
        visual_trust_path, visual_report_path
    )
    review, review_file_sha = _load(review_path)
    if (
        review.get("schema_version") != 1
        or review.get("source") != "local_cuttlefish_accessibility_human_review_input"
        or review.get("scope") != "CUTTLEFISH_PACKAGE_LOCALE_ACCESSIBILITY_REVIEW"
        or review.get("runtime_visual_trust_bundle_sha256") != trust_digest
        or review.get("visual_capture_sha256") != visual_digest
        or review.get("capture_count") != count
    ):
        raise RuntimeAccessibilityReviewError(
            "accessibility review belongs to a different or invalid visual evidence set"
        )
    if set(review) != {
        "schema_version",
        "source",
        "scope",
        "runtime_visual_trust_bundle_sha256",
        "visual_capture_sha256",
        "capture_count",
        "reviewer",
        "reviewed_at_utc",
        "assistive_technology",
        "input_methods",
        "items",
    }:
        raise RuntimeAccessibilityReviewError(
            "accessibility review contains missing or unknown top-level fields"
        )
    if review.get("input_methods") != _INPUT_METHODS:
        raise RuntimeAccessibilityReviewError(
            "accessibility review input-method scope is not canonical"
        )

    reviewer = _clean_reviewer(review.get("reviewer"))
    reviewed_at = _clean_reviewed_at(review.get("reviewed_at_utc"))
    assistive_technology = _clean_assistive_technology(
        review.get("assistive_technology")
    )
    items = review.get("items")
    if not isinstance(items, list) or len(items) != count:
        raise RuntimeAccessibilityReviewError(
            "accessibility review item count does not match the trusted capture matrix"
        )

    check_results: dict[str, list[bool]] = {check: [] for check in _CHECKS}
    failures: list[dict[str, str]] = []
    for actual, expected in zip(items, captures, strict=True):
        results, note = _validate_completed_item(actual, expected)
        for check, passed in results.items():
            check_results[check].append(passed)
            if not passed:
                failure = {
                    "package": str(expected["package"]),
                    "locale": str(expected["locale"]),
                    "check": check,
                }
                if note:
                    failure["note"] = note
                failures.append(failure)

    all_complete = all(len(values) == count for values in check_results.values())
    all_passed = all(all(values) for values in check_results.values())

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_accessibility_human_review_evidence",
        "scope": "CUTTLEFISH_PACKAGE_LOCALE_ACCESSIBILITY_REVIEW",
        "runtime_visual_trust_bundle_sha256": trust_digest,
        "visual_capture_sha256": visual_digest,
        "review_input_file_sha256": review_file_sha,
        "capture_count": count,
        "reviewer": reviewer,
        "reviewed_at_utc": reviewed_at,
        "assistive_technology": assistive_technology,
        "input_methods": list(_INPUT_METHODS),
        "human_review_complete": all_complete,
        "accessibility_review_complete": all_complete,
        "accessibility_review_passed": all_complete and all_passed,
        "spoken_labels_review_complete": all_complete,
        "spoken_labels_review_passed": all(check_results["spoken_labels"]),
        "focus_order_review_complete": all_complete,
        "focus_order_review_passed": all(check_results["focus_order"]),
        "touch_targets_review_complete": all_complete,
        "touch_targets_review_passed": all(check_results["touch_targets"]),
        "keyboard_navigation_review_complete": all_complete,
        "keyboard_navigation_review_passed": all(check_results["keyboard_navigation"]),
        "state_announcements_review_complete": all_complete,
        "state_announcements_review_passed": all(check_results["state_announcements"]),
        "failed_check_count": len(failures),
        "failed_checks": failures,
        "visual_translation_review_complete": False,
        "rtl_visual_mirroring_verified": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "This is a human accessibility attestation bound to exact Cuttlefish PNG evidence and the reviewed guest state, not an automated accessibility-quality claim.",
            "The reviewer must record the actual accessibility service used; the template does not assume a proprietary service is preinstalled in AOSP.",
            "Visual translation/clipping and RTL mirroring remain separate evidence and are not promoted by this accessibility review.",
            "This evidence never authorizes physical-device writes, root, application status promotion or release publication.",
        ],
    }
    payload["runtime_accessibility_review_evidence_sha256"] = _sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify a human accessibility review bound to exact SwirPhoneOS Cuttlefish evidence."
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
            report = create_accessibility_template(visual_trust, visual_report)
        else:
            report = verify_completed_accessibility_review(
                visual_trust,
                visual_report,
                args.review.resolve(strict=True),
            )
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeAccessibilityReviewError, OSError, RuntimeError, UnicodeError, ValueError):
        print(
            "Runtime accessibility review failed: use the exact trusted visual bundle/report and a complete bound human review.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
