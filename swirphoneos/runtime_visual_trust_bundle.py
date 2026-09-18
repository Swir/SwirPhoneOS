"""Bind Cuttlefish PNG capture bytes to one exact trusted runtime review.

This validator reads already-produced evidence and host PNG files only. It does
not run adb, launch an emulator, mutate a phone, or turn screenshots into a
visual-quality, RTL, accessibility, hardware-support, or release claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

from .cuttlefish_evidence import EXPECTED_PRODUCT
from .cuttlefish_visual_evidence import parse_png_dimensions
from .i18n import LOCALES
from .runtime_tool_evidence import MAX_TOOL_BYTES

_MAX_JSON = 16 * 1024 * 1024
_MAX_TOTAL_PNG = 4 * 1024 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\Z")
_LOCALE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?\Z")


class RuntimeVisualTrustBundleError(ValueError):
    pass


def _strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeVisualTrustBundleError("duplicate JSON key")
        result[key] = value
    return result


def _load(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise RuntimeVisualTrustBundleError("unsafe evidence input")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_JSON:
        raise RuntimeVisualTrustBundleError("invalid evidence size")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeVisualTrustBundleError("invalid evidence JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeVisualTrustBundleError("invalid evidence root")
    return value, hashlib.sha256(raw).hexdigest()


def _sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _hex(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise RuntimeVisualTrustBundleError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RuntimeVisualTrustBundleError(f"{field} must be a non-empty list")
    if any(not isinstance(item, str) or not item or len(item) > 256 for item in value) or len(set(value)) != len(value):
        raise RuntimeVisualTrustBundleError(f"{field} contains invalid or duplicate values")
    return list(value)


def _fingerprint_sha(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise RuntimeVisualTrustBundleError("missing build fingerprint")
    try:
        return hashlib.sha256(value.encode("ascii", "strict")).hexdigest()
    except UnicodeError as exc:
        raise RuntimeVisualTrustBundleError("build fingerprint must be ASCII") from exc


def _validate_review_trust(report: dict[str, object]) -> tuple[str, str, str, list[str], list[str], str, str, int]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_runtime_review_trust_bundle"
        or report.get("scope") != "CUTTLEFISH_BUILD_RUNTIME_I18N_AND_EXACT_ADB"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("build_runtime_chain_complete") is not True
        or report.get("locale_review_chain_complete") is not True
        or report.get("runtime_tool_unchanged_across_evidence_window") is not True
    ):
        raise RuntimeVisualTrustBundleError("runtime review trust bundle is invalid or incomplete")
    if any(report.get(key) is not False for key in (
        "rtl_visual_mirroring_verified", "accessibility_review_complete", "visual_translation_review_complete",
        "physical_device_support_claimed", "device_write_allowed", "status_promotion_performed",
    )):
        raise RuntimeVisualTrustBundleError("runtime review trust bundle overclaims review/support state")
    digest = _hex(report.get("runtime_review_trust_bundle_sha256"), "runtime_review_trust_bundle_sha256")
    if _sha({key: value for key, value in report.items() if key != "runtime_review_trust_bundle_sha256"}) != digest:
        raise RuntimeVisualTrustBundleError("runtime review trust bundle digest mismatch")
    fingerprint_sha = _hex(report.get("build_fingerprint_sha256"), "build_fingerprint_sha256")
    manifest_sha = _hex(report.get("app_manifest_sha256"), "app_manifest_sha256")
    packages = _strings(report.get("source_ready_packages"), "source_ready_packages")
    locales = _strings(report.get("tested_locales"), "tested_locales")
    if packages != sorted(packages) or locales != list(LOCALES):
        raise RuntimeVisualTrustBundleError("runtime review package/locale scope is not canonical")
    adb_sha = _hex(report.get("adb_sha256"), "adb_sha256")
    adb_path_sha = _hex(report.get("adb_path_identity_sha256"), "adb_path_identity_sha256")
    adb_size = report.get("adb_size")
    if not isinstance(adb_size, int) or isinstance(adb_size, bool) or not 0 < adb_size <= MAX_TOOL_BYTES:
        raise RuntimeVisualTrustBundleError("runtime review adb size is invalid")
    return digest, fingerprint_sha, manifest_sha, packages, locales, adb_sha, adb_path_sha, adb_size


def _validate_visual(report: dict[str, object], *, fingerprint_sha: str, packages: list[str], locales: list[str]) -> tuple[str, list[dict[str, object]]]:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_cuttlefish_visual_capture_matrix"
        or report.get("expected_product") != EXPECTED_PRODUCT
        or report.get("capture_matrix_complete") is not True
        or report.get("visual_bytes_captured") is not True
        or report.get("original_app_locales_restored") is not True
        or report.get("runtime_state_mutation_performed") is not True
        or report.get("host_evidence_write_performed") is not True
    ):
        raise RuntimeVisualTrustBundleError("visual capture evidence is invalid or incomplete")
    if any(report.get(key) is not False for key in (
        "rtl_visual_mirroring_verified", "accessibility_review_complete", "visual_translation_review_complete",
        "status_promotion_performed", "physical_device_support_claimed", "persistent_device_write_allowed",
    )):
        raise RuntimeVisualTrustBundleError("visual capture evidence overclaims review/support state")
    if report.get("build_fingerprint_sha256") != fingerprint_sha or _fingerprint_sha(report.get("build_fingerprint")) != fingerprint_sha:
        raise RuntimeVisualTrustBundleError("visual capture belongs to a different build")
    if _strings(report.get("tested_packages"), "tested_packages") != packages or _strings(report.get("tested_locales"), "tested_locales") != locales:
        raise RuntimeVisualTrustBundleError("visual capture package/locale scope mismatch")
    expected_rtl = bool([code for code in locales if LOCALES[code].direction == "rtl"])
    if report.get("rtl_runtime_switch_exercised") is not expected_rtl:
        raise RuntimeVisualTrustBundleError("visual capture RTL runtime flag is inconsistent")

    captures = report.get("captures")
    expected_count = len(packages) * len(locales)
    if not isinstance(captures, list) or report.get("capture_count") != expected_count or len(captures) != expected_count:
        raise RuntimeVisualTrustBundleError("visual capture count is incomplete")
    seen: set[tuple[str, str]] = set()
    names: set[str] = set()
    normalized: list[dict[str, object]] = []
    for item in captures:
        if not isinstance(item, dict):
            raise RuntimeVisualTrustBundleError("visual capture record is malformed")
        package, locale = item.get("package"), item.get("locale")
        if package not in packages or locale not in locales or (str(package), str(locale)) in seen:
            raise RuntimeVisualTrustBundleError("visual package/locale pair is invalid or duplicated")
        if item.get("direction") != LOCALES[str(locale)].direction or item.get("foreground_confirmed") is not True:
            raise RuntimeVisualTrustBundleError("visual capture direction/foreground evidence is invalid")
        component = item.get("component")
        if not isinstance(component, str) or not component.startswith(str(package) + "/"):
            raise RuntimeVisualTrustBundleError("visual capture launcher escaped package")
        name = item.get("relative_path")
        if not isinstance(name, str) or PurePosixPath(name).name != name or not name.endswith(".png") or name in names:
            raise RuntimeVisualTrustBundleError("visual capture filename is invalid or duplicated")
        size = item.get("size")
        width, height = item.get("width"), item.get("height")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise RuntimeVisualTrustBundleError("visual capture size is invalid")
        if not isinstance(width, int) or isinstance(width, bool) or not isinstance(height, int) or isinstance(height, bool) or width <= 0 or height <= 0:
            raise RuntimeVisualTrustBundleError("visual capture dimensions are invalid")
        _hex(item.get("sha256"), "visual capture sha256")
        seen.add((str(package), str(locale)))
        names.add(name)
        normalized.append(dict(item))
    if seen != {(package, locale) for locale in locales for package in packages}:
        raise RuntimeVisualTrustBundleError("visual capture matrix does not cover every package/locale pair")
    if _sha(normalized) != report.get("capture_set_sha256"):
        raise RuntimeVisualTrustBundleError("visual capture-set digest mismatch")
    digest = _hex(report.get("visual_capture_sha256"), "visual_capture_sha256")
    if _sha({key: value for key, value in report.items() if key != "visual_capture_sha256"}) != digest:
        raise RuntimeVisualTrustBundleError("visual capture evidence digest mismatch")
    return digest, normalized


def _reverify_directory(root: Path, captures: list[dict[str, object]]) -> tuple[str, int]:
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise RuntimeVisualTrustBundleError("visual capture directory is unsafe")
    root = root.resolve(strict=True)
    expected = {str(item["relative_path"]) for item in captures}
    actual: set[str] = set()
    for child in root.iterdir():
        if child.is_symlink() or not child.is_file():
            raise RuntimeVisualTrustBundleError("visual capture directory contains an unsafe entry")
        actual.add(child.name)
    if actual != expected:
        raise RuntimeVisualTrustBundleError("visual capture directory is not closed to the evidence inventory")
    total = 0
    rechecked: list[dict[str, object]] = []
    by_name = {str(item["relative_path"]): item for item in captures}
    for name in sorted(expected):
        path = root / name
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise RuntimeVisualTrustBundleError("visual capture changed while being reverified")
        item = by_name[name]
        width, height = parse_png_dimensions(raw)
        if len(raw) != item["size"] or hashlib.sha256(raw).hexdigest() != item["sha256"] or width != item["width"] or height != item["height"]:
            raise RuntimeVisualTrustBundleError("visual capture bytes/dimensions no longer match evidence")
        total += len(raw)
        if total > _MAX_TOTAL_PNG:
            raise RuntimeVisualTrustBundleError("visual evidence set exceeds the total byte limit")
        rechecked.append({"relative_path": name, "size": len(raw), "sha256": item["sha256"], "width": width, "height": height})
    return _sha(rechecked), total


def create_runtime_visual_trust_bundle(review_trust_path: Path, visual_report_path: Path, visual_dir: Path) -> dict[str, object]:
    review, review_file_sha = _load(review_trust_path)
    visual, visual_file_sha = _load(visual_report_path)
    review_digest, fingerprint_sha, manifest_sha, packages, locales, adb_sha, adb_path_sha, adb_size = _validate_review_trust(review)
    visual_digest, captures = _validate_visual(visual, fingerprint_sha=fingerprint_sha, packages=packages, locales=locales)
    directory_sha, total_bytes = _reverify_directory(visual_dir, captures)
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_visual_trust_bundle",
        "scope": "CUTTLEFISH_BUILD_RUNTIME_I18N_VISUAL_CAPTURE_AND_EXACT_ADB",
        "expected_product": EXPECTED_PRODUCT,
        "runtime_review_trust_bundle_sha256": review_digest,
        "visual_capture_sha256": visual_digest,
        "build_fingerprint_sha256": fingerprint_sha,
        "app_manifest_sha256": manifest_sha,
        "source_ready_packages": packages,
        "tested_locales": locales,
        "adb_sha256": adb_sha,
        "adb_path_identity_sha256": adb_path_sha,
        "adb_size": adb_size,
        "report_file_sha256": {"runtime_review_trust_bundle": review_file_sha, "visual_capture_evidence": visual_file_sha},
        "capture_count": len(captures),
        "capture_directory_sha256": directory_sha,
        "capture_total_bytes": total_bytes,
        "visual_capture_matrix_complete": True,
        "visual_bytes_reverified": True,
        "rtl_visual_mirroring_verified": False,
        "accessibility_review_complete": False,
        "visual_translation_review_complete": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "This bundle proves exact retained PNG byte continuity for the package/locale capture matrix only.",
            "Human visual translation, RTL mirroring and accessibility review remain required and are intentionally false here.",
            "This evidence never authorizes physical-device writes, flashing, root, application promotion or release publication.",
        ],
    }
    payload["runtime_visual_trust_bundle_sha256"] = _sha(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bind exact Cuttlefish visual capture bytes to the trusted runtime-review chain.")
    parser.add_argument("--runtime-review-trust", required=True, type=Path)
    parser.add_argument("--visual-report", required=True, type=Path)
    parser.add_argument("--visual-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = create_runtime_visual_trust_bundle(args.runtime_review_trust.resolve(), args.visual_report.resolve(), args.visual_dir.resolve())
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeVisualTrustBundleError, OSError, RuntimeError, UnicodeError, ValueError):
        print("Runtime visual trust binding failed: use one exact trusted runtime review and unchanged closed PNG capture directory.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
