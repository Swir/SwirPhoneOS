"""Bind exact Cuttlefish boot, HOME, app-launch and locale-matrix evidence.

This report is emulator/runtime evidence only. It never promotes app status,
claims visual RTL/accessibility quality, or authorizes physical-device writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

from .cuttlefish_evidence import (
    EXPECTED_ANDROID_RELEASE,
    EXPECTED_API_LEVEL,
    EXPECTED_BUILD_TYPE,
    EXPECTED_PRODUCT,
)
from .cuttlefish_smoke import EXPECTED_HOME_PACKAGE
from .i18n import LOCALES
from .system_apps import SystemAppRegistryError, load_registry


_MAX_REPORT_BYTES = 16 * 1024 * 1024
_MAX_APP_MANIFEST_BYTES = 2 * 1024 * 1024


class RuntimeReviewEvidenceError(ValueError):
    """Raised when Cuttlefish runtime review evidence is incomplete or mixed."""


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeReviewEvidenceError("Runtime review JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_json(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeReviewEvidenceError("Runtime review input is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_REPORT_BYTES:
        raise RuntimeReviewEvidenceError("Runtime review input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeReviewEvidenceError("Runtime review input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise RuntimeReviewEvidenceError("Runtime review input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _registry_identity(path: Path) -> tuple[list[str], str]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeReviewEvidenceError("System-app manifest is missing or unsafe.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_APP_MANIFEST_BYTES:
        raise RuntimeReviewEvidenceError("System-app manifest has an invalid size.")
    try:
        registry = load_registry(path)
    except (SystemAppRegistryError, OSError, ValueError) as exc:
        raise RuntimeReviewEvidenceError("System-app manifest could not be validated.") from exc
    packages = sorted(app.package for app in registry.first_beta_apps)
    if not packages or len(packages) != len(set(packages)):
        raise RuntimeReviewEvidenceError("System-app manifest has no unique frozen first-Beta package set.")
    return packages, hashlib.sha256(raw).hexdigest()


def _unique_strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise RuntimeReviewEvidenceError(f"{field} must be a non-empty list.")
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256 or item in seen:
            raise RuntimeReviewEvidenceError(f"{field} contains an invalid or duplicate value.")
        output.append(item)
        seen.add(item)
    return output


def _fingerprint_digest(fingerprint: str) -> str:
    try:
        encoded = fingerprint.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeReviewEvidenceError("Runtime fingerprint must be ASCII.") from exc
    return hashlib.sha256(encoded).hexdigest()


def _validate_runtime(runtime: dict[str, object], packages: list[str]) -> str:
    if runtime.get("schema_version") != 3 or runtime.get("runtime_evidence_complete") is not True:
        raise RuntimeReviewEvidenceError("Cuttlefish runtime evidence is incomplete.")
    if (
        runtime.get("expected_product") != EXPECTED_PRODUCT
        or runtime.get("android_release") != EXPECTED_ANDROID_RELEASE
        or runtime.get("api_level") != EXPECTED_API_LEVEL
        or runtime.get("build_type") != EXPECTED_BUILD_TYPE
        or runtime.get("identity_matches") is not True
        or runtime.get("boot_completed") is not True
    ):
        raise RuntimeReviewEvidenceError("Cuttlefish runtime identity is not the exact expected SwirPhoneOS product.")
    if runtime.get("device_write_allowed") is not False or runtime.get("status_promotion_performed") is not False:
        raise RuntimeReviewEvidenceError("Runtime evidence violates the no-write/no-promotion boundary.")

    fingerprint = runtime.get("build_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise RuntimeReviewEvidenceError("Runtime fingerprint is missing.")
    digest = _fingerprint_digest(fingerprint)
    if runtime.get("build_fingerprint_sha256") != digest:
        raise RuntimeReviewEvidenceError("Runtime fingerprint digest is invalid.")

    required = sorted(_unique_strings(runtime.get("required_source_ready_packages"), "required_source_ready_packages"))
    present = sorted(_unique_strings(runtime.get("present_required_packages"), "present_required_packages"))
    launchable = sorted(_unique_strings(runtime.get("present_launchable_packages"), "present_launchable_packages"))
    if required != packages or present != packages or launchable != packages:
        raise RuntimeReviewEvidenceError("Runtime package inventory does not match the frozen first-Beta app set.")
    if runtime.get("missing_required_packages") != [] or runtime.get("missing_launchable_packages") != []:
        raise RuntimeReviewEvidenceError("Runtime evidence still reports missing required packages or launchers.")
    return fingerprint


def _validate_smoke(smoke: dict[str, object], packages: list[str], fingerprint: str) -> None:
    digest = _fingerprint_digest(fingerprint)
    if smoke.get("schema_version") != 1 or smoke.get("app_smoke_complete") is not True:
        raise RuntimeReviewEvidenceError("Application launch-smoke evidence is incomplete.")
    if (
        smoke.get("expected_product") != EXPECTED_PRODUCT
        or smoke.get("build_fingerprint") != fingerprint
        or smoke.get("build_fingerprint_sha256") != digest
    ):
        raise RuntimeReviewEvidenceError("Application launch-smoke evidence belongs to a different runtime.")
    if (
        smoke.get("status_promotion_performed") is not False
        or smoke.get("physical_device_support_claimed") is not False
        or smoke.get("persistent_device_write_allowed") is not False
        or smoke.get("runtime_state_mutation_performed") is not True
    ):
        raise RuntimeReviewEvidenceError("Application launch-smoke safety flags are invalid.")

    home_component = smoke.get("home_component")
    if (
        smoke.get("home_package") != EXPECTED_HOME_PACKAGE
        or smoke.get("home_resolved") is not True
        or smoke.get("home_am_start_status") != "ok"
        or smoke.get("home_foreground_confirmed") is not True
        or smoke.get("home_surface_complete") is not True
        or not isinstance(home_component, str)
        or not home_component.startswith(EXPECTED_HOME_PACKAGE + "/")
    ):
        raise RuntimeReviewEvidenceError("SwirLauncher was not proven as the exact usable HOME surface.")

    if sorted(_unique_strings(smoke.get("tested_packages"), "tested_packages")) != packages:
        raise RuntimeReviewEvidenceError("Application launch-smoke first-Beta package set is incomplete.")

    results = smoke.get("launch_results")
    if not isinstance(results, list) or len(results) != len(packages):
        raise RuntimeReviewEvidenceError("Application launch-smoke result count is invalid.")
    seen: set[str] = set()
    for item in results:
        if not isinstance(item, dict):
            raise RuntimeReviewEvidenceError("Application launch-smoke result is malformed.")
        package = item.get("package")
        component = item.get("component")
        if package not in packages or package in seen:
            raise RuntimeReviewEvidenceError("Application launch-smoke package is invalid or duplicated.")
        if not isinstance(component, str) or not component.startswith(str(package) + "/"):
            raise RuntimeReviewEvidenceError("Application launch-smoke component escaped its package.")
        if item.get("am_start_status") != "ok" or item.get("foreground_confirmed") is not True:
            raise RuntimeReviewEvidenceError("Application launch-smoke did not prove a foreground launch.")
        seen.add(str(package))


def _validate_i18n(
    i18n: dict[str, object], packages: list[str], fingerprint: str
) -> tuple[list[str], list[str]]:
    digest = _fingerprint_digest(fingerprint)
    if i18n.get("schema_version") != 2 or i18n.get("locale_matrix_complete") is not True:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix evidence is incomplete.")
    if (
        i18n.get("expected_product") != EXPECTED_PRODUCT
        or i18n.get("build_fingerprint") != fingerprint
        or i18n.get("build_fingerprint_sha256") != digest
    ):
        raise RuntimeReviewEvidenceError("Runtime locale-matrix evidence belongs to a different runtime.")
    if (
        i18n.get("original_app_locales_restored") is not True
        or i18n.get("runtime_state_mutation_performed") is not True
        or i18n.get("status_promotion_performed") is not False
        or i18n.get("physical_device_support_claimed") is not False
        or i18n.get("persistent_device_write_allowed") is not False
        or i18n.get("rtl_visual_mirroring_verified") is not False
    ):
        raise RuntimeReviewEvidenceError("Runtime locale-matrix safety/restoration flags are invalid.")
    if i18n.get("home_package") != EXPECTED_HOME_PACKAGE:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix did not bind the SwirLauncher HOME package.")
    if sorted(_unique_strings(i18n.get("first_beta_app_packages"), "first_beta_app_packages")) != packages:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix frozen first-Beta app set is incomplete.")
    locale_packages = _unique_strings(i18n.get("tested_packages"), "tested_packages")
    expected_locale_packages = [EXPECTED_HOME_PACKAGE, *packages]
    if locale_packages != expected_locale_packages:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix must cover SwirLauncher plus the frozen first-Beta apps.")

    locales = _unique_strings(i18n.get("tested_locales"), "tested_locales")
    expected_locales = list(LOCALES)
    if locales != expected_locales:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix locale set/order does not match the shared catalog.")
    rtl = [code for code in expected_locales if LOCALES[code].direction == "rtl"]
    if i18n.get("rtl_locales_exercised") != rtl:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix RTL set does not match the shared catalog.")
    if i18n.get("rtl_runtime_switch_exercised") is not bool(rtl):
        raise RuntimeReviewEvidenceError("Runtime locale-matrix RTL switch flag is inconsistent.")

    results = i18n.get("locale_results")
    expected_count = len(locale_packages) * len(expected_locales)
    if not isinstance(results, list) or len(results) != expected_count:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix result count is invalid.")
    seen: set[tuple[str, str]] = set()
    for item in results:
        if not isinstance(item, dict):
            raise RuntimeReviewEvidenceError("Runtime locale-matrix result is malformed.")
        package = item.get("package")
        locale = item.get("locale")
        component = item.get("component")
        key = (str(package), str(locale))
        if package not in locale_packages or locale not in expected_locales or key in seen:
            raise RuntimeReviewEvidenceError("Runtime locale-matrix package/locale pair is invalid or duplicated.")
        if not isinstance(component, str) or not component.startswith(str(package) + "/"):
            raise RuntimeReviewEvidenceError("Runtime locale-matrix launcher escaped its package.")
        if item.get("foreground_confirmed") is not True:
            raise RuntimeReviewEvidenceError("Runtime locale-matrix did not confirm a foreground launch.")
        seen.add(key)
    if seen != {(package, locale) for locale in expected_locales for package in locale_packages}:
        raise RuntimeReviewEvidenceError("Runtime locale-matrix does not cover every first-Beta UI package/locale pair.")
    return expected_locales, locale_packages


def collect_runtime_review_evidence(
    *,
    runtime_path: Path,
    smoke_path: Path,
    i18n_path: Path,
    app_manifest_path: Path,
) -> dict[str, object]:
    """Validate and bind one exact Cuttlefish runtime review set."""
    packages, manifest_sha = _registry_identity(app_manifest_path)
    runtime, runtime_sha = _load_json(runtime_path)
    smoke, smoke_sha = _load_json(smoke_path)
    i18n, i18n_sha = _load_json(i18n_path)

    fingerprint = _validate_runtime(runtime, packages)
    _validate_smoke(smoke, packages, fingerprint)
    locales, locale_packages = _validate_i18n(i18n, packages, fingerprint)

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_cuttlefish_runtime_review_bundle",
        "expected_product": EXPECTED_PRODUCT,
        "build_fingerprint": fingerprint,
        "build_fingerprint_sha256": _fingerprint_digest(fingerprint),
        "app_manifest_sha256": manifest_sha,
        "source_ready_packages": packages,
        "locale_review_packages": locale_packages,
        "tested_locales": locales,
        "report_file_sha256": {
            "runtime": runtime_sha,
            "smoke": smoke_sha,
            "i18n": i18n_sha,
        },
        "boot_identity_complete": True,
        "home_surface_complete": True,
        "app_launch_matrix_complete": True,
        "locale_matrix_complete": True,
        "original_app_locales_restored": True,
        "rtl_runtime_switch_exercised": bool([code for code in locales if LOCALES[code].direction == "rtl"]),
        "rtl_visual_mirroring_verified": False,
        "accessibility_review_complete": False,
        "visual_translation_review_complete": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This bundle proves exact Cuttlefish boot identity, SwirLauncher HOME resolution/foreground launch, frozen first-Beta app launch smoke and locale switching/restoration across SwirLauncher/Setup plus every frozen first-Beta app.",
            "Post-Beta source-ready apps are intentionally non-blocking while the frozen first-Beta scope is active.",
            "Visual translation quality, RTL mirroring, text expansion, accessibility, fonts/input methods and physical-device behavior still require focused review.",
            "This evidence does not promote any application to ANDROID_RUNTIME automatically and never authorizes physical-device writes.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["runtime_review_sha256"] = hashlib.sha256(canonical).hexdigest()
    payload["runtime_review_evidence_complete"] = True
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind exact Cuttlefish boot, HOME, first-Beta app-launch and locale-matrix evidence without status promotion."
    )
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--smoke", required=True, type=Path)
    parser.add_argument("--i18n", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("system_apps/manifest.json"))
    args = parser.parse_args(argv)
    try:
        report = collect_runtime_review_evidence(
            runtime_path=args.runtime,
            smoke_path=args.smoke,
            i18n_path=args.i18n,
            app_manifest_path=args.manifest,
        )
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (RuntimeReviewEvidenceError, SystemAppRegistryError, OSError, ValueError):
        print(
            "Operation failed: exact Cuttlefish runtime, HOME, first-Beta app-launch, locale-matrix and manifest evidence must agree. Raw errors are withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
