"""Fail-closed source validation for first-party Android apps staged into AOSP."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET

from .system_apps import SystemAppRegistry, load_registry


class AndroidAppSourceError(ValueError):
    """Raised when checked-in Android application source overclaims or is unsafe/incomplete."""


@dataclass(frozen=True)
class AndroidAppSourceSummary:
    source_ready_apps: tuple[str, ...]
    localized_catalogs: int
    source_files: int
    target_capabilities: tuple[str, ...]
    implemented_capabilities: tuple[str, ...]


_LOCALES = ("en", "pl", "nb", "de", "es", "fr", "pt", "ar")
_RESOURCE_DIR = {
    "en": "values",
    "pl": "values-pl",
    "nb": "values-nb",
    "de": "values-de",
    "es": "values-es",
    "fr": "values-fr",
    "pt": "values-pt",
    "ar": "values-ar",
}
_MAX_TEXT = 1_000_000


def _read(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise AndroidAppSourceError(f"Missing or unsafe Android source file: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AndroidAppSourceError("Android app source must be readable strict UTF-8.") from exc
    if not text or len(text) > _MAX_TEXT:
        raise AndroidAppSourceError("Android app source file has an invalid size.")
    return text


def _string_keys(path: Path) -> set[str]:
    try:
        root = ET.fromstring(_read(path))
    except ET.ParseError as exc:
        raise AndroidAppSourceError("Android string resources are malformed XML.") from exc
    if root.tag != "resources":
        raise AndroidAppSourceError("Android string resource root must be <resources>.")
    keys: set[str] = set()
    for item in root.findall("string"):
        name = (item.get("name") or "").strip()
        if not name or name in keys:
            raise AndroidAppSourceError("Android string resources contain missing/duplicate names.")
        keys.add(name)
    if not keys:
        raise AndroidAppSourceError("Android app must contain localizable strings.")
    return keys


def _load_stage_sources(product_root: Path) -> set[str]:
    path = product_root / "stage_manifest.json"
    try:
        data = json.loads(_read(path))
    except json.JSONDecodeError as exc:
        raise AndroidAppSourceError("AOSP stage manifest is invalid JSON.") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "files"} or data["schema_version"] != 1:
        raise AndroidAppSourceError("AOSP stage manifest schema is invalid.")
    files = data["files"]
    if not isinstance(files, list) or not files:
        raise AndroidAppSourceError("AOSP stage manifest has no files.")
    result: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"source", "destination"}:
            raise AndroidAppSourceError("AOSP stage entry schema is invalid.")
        source = entry["source"]
        destination = entry["destination"]
        if not isinstance(source, str) or not isinstance(destination, str):
            raise AndroidAppSourceError("AOSP stage paths must be strings.")
        src = PurePosixPath(source)
        dst = PurePosixPath(destination)
        if src.is_absolute() or dst.is_absolute() or ".." in src.parts or ".." in dst.parts:
            raise AndroidAppSourceError("AOSP stage paths may not escape their roots.")
        if not destination.startswith("vendor/swir/"):
            raise AndroidAppSourceError("AOSP stage destination must stay under vendor/swir/.")
        if source in result:
            raise AndroidAppSourceError("AOSP stage manifest contains duplicate sources.")
        result.add(source)
    return result


def validate_android_app_sources(
    product_root: Path = Path("platform/aosp_product"),
    registry_path: Path = Path("system_apps/manifest.json"),
) -> AndroidAppSourceSummary:
    """Validate the first source-ready app without claiming an Android build/runtime."""
    registry: SystemAppRegistry = load_registry(registry_path)
    calculator = next((app for app in registry.apps if app.app_id == "calculator"), None)
    if calculator is None or calculator.status != "ANDROID_SOURCE":
        raise AndroidAppSourceError("Calculator registry state must be ANDROID_SOURCE for checked-in app source.")

    app_root = product_root / "apps" / "SwirCalculator"
    bp = _read(app_root / "Android.bp")
    manifest_text = _read(app_root / "AndroidManifest.xml")
    product_mk = _read(product_root / "swirphoneos_cf_x86_64.mk")
    engine = _read(app_root / "src/org/swir/phoneos/calculator/CalculatorEngine.java")
    activity = _read(app_root / "src/org/swir/phoneos/calculator/MainActivity.java")
    _read(app_root / "res/drawable/ic_calculator.xml")
    _read(app_root / "hosttest/CalculatorEngineHostTest.java")

    required_bp = (
        'android_app {',
        'name: "SwirCalculator"',
        'srcs: ["src/**/*.java"]',
        'resource_dirs: ["res"]',
        'sdk_version: "current"',
        'product_specific: true',
    )
    if any(token not in bp for token in required_bp):
        raise AndroidAppSourceError("SwirCalculator Android.bp does not match the source contract.")
    if "PRODUCT_PACKAGES" not in product_mk or "SwirCalculator" not in product_mk:
        raise AndroidAppSourceError("SwirCalculator is not included in the Cuttlefish product.")

    try:
        manifest = ET.fromstring(manifest_text)
    except ET.ParseError as exc:
        raise AndroidAppSourceError("SwirCalculator manifest is malformed XML.") from exc
    if manifest.tag != "manifest" or manifest.get("package") != calculator.package:
        raise AndroidAppSourceError("SwirCalculator package identity does not match the registry.")
    if manifest.findall("uses-permission"):
        raise AndroidAppSourceError("The offline calculator must not request Android permissions.")
    app = manifest.find("application")
    android_ns = "{http://schemas.android.com/apk/res/android}"
    if app is None or app.get(android_ns + "supportsRtl") != "true" or app.get(android_ns + "allowBackup") != "false":
        raise AndroidAppSourceError("SwirCalculator manifest must be RTL-aware and backup-disabled.")

    package_line = "package org.swir.phoneos.calculator;"
    if package_line not in engine or package_line not in activity:
        raise AndroidAppSourceError("SwirCalculator Java package identity drifted.")
    if re.search(r"^\s*import\s+android\.", engine, flags=re.MULTILINE):
        raise AndroidAppSourceError("CalculatorEngine must remain pure Java for host testing.")
    forbidden = ("Runtime.getRuntime", "ProcessBuilder", "android.permission.INTERNET", "\"su\"")
    if any(token in engine or token in activity or token in manifest_text for token in forbidden):
        raise AndroidAppSourceError("SwirCalculator source contains a forbidden execution/network primitive.")

    english_keys = _string_keys(app_root / "res/values/strings.xml")
    localized = 0
    for locale in _LOCALES:
        keys = _string_keys(app_root / "res" / _RESOURCE_DIR[locale] / "strings.xml")
        if keys != english_keys:
            raise AndroidAppSourceError(f"SwirCalculator localization keys drifted for {locale}.")
        localized += 1

    staged = _load_stage_sources(product_root)
    required_stage = set()
    for path in app_root.rglob("*"):
        if path.is_file() and "hosttest" not in path.parts:
            required_stage.add(path.relative_to(product_root).as_posix())
    missing = sorted(required_stage - staged)
    if missing:
        raise AndroidAppSourceError(f"SwirCalculator source is not fully staged: {missing}")

    return AndroidAppSourceSummary(
        source_ready_apps=("calculator",),
        localized_catalogs=localized,
        source_files=len(required_stage),
        target_capabilities=calculator.capabilities,
        implemented_capabilities=("basic_math",),
    )


def public_android_app_source_summary(summary: AndroidAppSourceSummary) -> dict[str, object]:
    missing = sorted(set(summary.target_capabilities) - set(summary.implemented_capabilities))
    return {
        "schema_version": 1,
        "status": "SOURCE_READY_NOT_BUILT",
        "source_ready_apps": list(summary.source_ready_apps),
        "localized_catalogs": summary.localized_catalogs,
        "staged_source_files": summary.source_files,
        "implemented_capabilities": list(summary.implemented_capabilities),
        "target_capabilities": list(summary.target_capabilities),
        "remaining_target_capabilities": missing,
        "android_build_verified": False,
        "runtime_verified": False,
        "device_write_allowed": False,
    }
