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


@dataclass(frozen=True)
class _AppSpec:
    app_id: str
    folder: str
    module: str
    java_package: str
    logic_file: str
    activity_file: str
    host_test: str
    icon_file: str
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
_SPECS = {
    "calculator": _AppSpec(
        "calculator",
        "SwirCalculator",
        "SwirCalculator",
        "org.swir.phoneos.calculator",
        "src/org/swir/phoneos/calculator/CalculatorEngine.java",
        "src/org/swir/phoneos/calculator/MainActivity.java",
        "hosttest/CalculatorEngineHostTest.java",
        "res/drawable/ic_calculator.xml",
        ("basic_math",),
    ),
    "settings": _AppSpec(
        "settings",
        "SwirSettings",
        "SwirSettings",
        "org.swir.phoneos.settings",
        "src/org/swir/phoneos/settings/SettingsCatalog.java",
        "src/org/swir/phoneos/settings/MainActivity.java",
        "hosttest/SettingsCatalogHostTest.java",
        "res/drawable/ic_settings.xml",
        ("system_settings", "search", "device_status"),
    ),
}
_SETTINGS_ACTIONS = frozenset({
    "android.settings.WIFI_SETTINGS",
    "android.settings.BLUETOOTH_SETTINGS",
    "android.settings.DISPLAY_SETTINGS",
    "android.settings.SOUND_SETTINGS",
    "android.settings.SECURITY_SETTINGS",
    "android.settings.PRIVACY_SETTINGS",
    "android.settings.ACCESSIBILITY_SETTINGS",
    "android.settings.LOCALE_SETTINGS",
    "android.settings.INTERNAL_STORAGE_SETTINGS",
    "android.settings.APPLICATION_SETTINGS",
})


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
    sources: set[str] = set()
    destinations: set[str] = set()
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
        if source in sources or destination in destinations:
            raise AndroidAppSourceError("AOSP stage manifest contains duplicate source/destination identities.")
        sources.add(source)
        destinations.add(destination)
    return sources


def _validate_common(
    product_root: Path,
    product_mk: str,
    app,
    spec: _AppSpec,
    staged: set[str],
) -> tuple[int, int, str, str]:
    app_root = product_root / "apps" / spec.folder
    bp = _read(app_root / "Android.bp")
    manifest_text = _read(app_root / "AndroidManifest.xml")
    logic = _read(app_root / spec.logic_file)
    activity = _read(app_root / spec.activity_file)
    _read(app_root / spec.icon_file)
    _read(app_root / spec.host_test)

    required_bp = (
        "android_app {",
        f'name: "{spec.module}"',
        'srcs: ["src/**/*.java"]',
        'resource_dirs: ["res"]',
        'sdk_version: "current"',
        'product_specific: true',
    )
    if any(token not in bp for token in required_bp):
        raise AndroidAppSourceError(f"{spec.module} Android.bp does not match the source contract.")
    if "PRODUCT_PACKAGES" not in product_mk or spec.module not in product_mk:
        raise AndroidAppSourceError(f"{spec.module} is not included in the Cuttlefish product.")

    try:
        manifest = ET.fromstring(manifest_text)
    except ET.ParseError as exc:
        raise AndroidAppSourceError(f"{spec.module} manifest is malformed XML.") from exc
    if manifest.tag != "manifest" or manifest.get("package") != app.package:
        raise AndroidAppSourceError(f"{spec.module} package identity does not match the registry.")
    if app.package != spec.java_package:
        raise AndroidAppSourceError(f"{spec.module} registry package drifted from its source contract.")
    if manifest.findall("uses-permission"):
        raise AndroidAppSourceError(f"{spec.module} source slice must not request Android permissions.")
    android_ns = "{http://schemas.android.com/apk/res/android}"
    application = manifest.find("application")
    if application is None or application.get(android_ns + "supportsRtl") != "true" or application.get(android_ns + "allowBackup") != "false":
        raise AndroidAppSourceError(f"{spec.module} manifest must be RTL-aware and backup-disabled.")

    package_line = f"package {spec.java_package};"
    if package_line not in logic or package_line not in activity:
        raise AndroidAppSourceError(f"{spec.module} Java package identity drifted.")
    if re.search(r"^\s*import\s+android\.", logic, flags=re.MULTILINE):
        raise AndroidAppSourceError(f"{spec.module} host-testable logic must remain pure Java.")
    forbidden = (
        "Runtime.getRuntime",
        "ProcessBuilder",
        "android.permission.INTERNET",
        '"su"',
        "DexClassLoader",
        "System.loadLibrary",
    )
    if any(token in logic or token in activity or token in manifest_text for token in forbidden):
        raise AndroidAppSourceError(f"{spec.module} source contains a forbidden execution/network primitive.")

    english_keys = _string_keys(app_root / "res/values/strings.xml")
    localized = 0
    for locale in _LOCALES:
        keys = _string_keys(app_root / "res" / _RESOURCE_DIR[locale] / "strings.xml")
        if keys != english_keys:
            raise AndroidAppSourceError(f"{spec.module} localization keys drifted for {locale}.")
        localized += 1

    required_stage = set()
    for path in app_root.rglob("*"):
        if path.is_file() and "hosttest" not in path.parts:
            required_stage.add(path.relative_to(product_root).as_posix())
    missing = sorted(required_stage - staged)
    if missing:
        raise AndroidAppSourceError(f"{spec.module} source is not fully staged: {missing}")
    return localized, len(required_stage), logic, activity


def _validate_calculator(logic: str, activity: str) -> None:
    if "java.math.BigDecimal" not in logic or "equalsResult" not in logic:
        raise AndroidAppSourceError("SwirCalculator must retain its host-tested decimal engine.")
    if "DecimalFormatSymbols" not in activity:
        raise AndroidAppSourceError("SwirCalculator must preserve locale-aware decimal display.")


def _validate_settings(logic: str, activity: str) -> None:
    actions = frozenset(re.findall(r'"(android\.settings\.[A-Z_]+)"', logic))
    if actions != _SETTINGS_ACTIONS:
        raise AndroidAppSourceError("SwirSettings routes must match the reviewed public-settings allowlist exactly.")
    if "Build.MODEL" not in activity or "Build.VERSION.RELEASE" not in activity or "Build.VERSION.SDK_INT" not in activity:
        raise AndroidAppSourceError("SwirSettings must expose real build/device status rather than placeholder data.")
    if "startActivity(new Intent(entry.action()))" not in activity:
        raise AndroidAppSourceError("SwirSettings must route through authoritative Android settings intents.")


def validate_android_app_sources(
    product_root: Path = Path("platform/aosp_product"),
    registry_path: Path = Path("system_apps/manifest.json"),
) -> AndroidAppSourceSummary:
    """Validate all checked-in source-ready apps without claiming Android build/runtime evidence."""
    registry: SystemAppRegistry = load_registry(registry_path)
    overclaimed = [app.app_id for app in registry.apps if app.status in {"ANDROID_RUNTIME", "HARDWARE_VERIFIED"}]
    if overclaimed:
        raise AndroidAppSourceError(f"Android runtime/hardware states require runtime evidence, not source validation: {overclaimed}")
    source_apps = [app for app in registry.apps if app.status == "ANDROID_SOURCE"]
    if not source_apps:
        raise AndroidAppSourceError("At least one checked-in Android source app is required.")
    unknown = sorted(app.app_id for app in source_apps if app.app_id not in _SPECS)
    if unknown:
        raise AndroidAppSourceError(f"ANDROID_SOURCE apps have no reviewed source contract: {unknown}")

    product_mk = _read(product_root / "swirphoneos_cf_x86_64.mk")
    staged = _load_stage_sources(product_root)
    localized = 0
    source_files = 0
    target: list[str] = []
    implemented: list[str] = []
    ids: list[str] = []

    for app in source_apps:
        spec = _SPECS[app.app_id]
        count, staged_count, logic, activity = _validate_common(product_root, product_mk, app, spec, staged)
        if app.app_id == "calculator":
            _validate_calculator(logic, activity)
        elif app.app_id == "settings":
            _validate_settings(logic, activity)
        localized += count
        source_files += staged_count
        ids.append(app.app_id)
        target.extend(app.capabilities)
        implemented.extend(spec.implemented_capabilities)

    return AndroidAppSourceSummary(
        source_ready_apps=tuple(ids),
        localized_catalogs=localized,
        source_files=source_files,
        target_capabilities=tuple(dict.fromkeys(target)),
        implemented_capabilities=tuple(dict.fromkeys(implemented)),
    )


def public_android_app_source_summary(summary: AndroidAppSourceSummary) -> dict[str, object]:
    missing = sorted(set(summary.target_capabilities) - set(summary.implemented_capabilities))
    return {
        "schema_version": 1,
        "status": "SOURCE_READY_NOT_BUILT",
        "source_ready_apps": list(summary.source_ready_apps),
        "source_ready_count": len(summary.source_ready_apps),
        "localized_catalogs": summary.localized_catalogs,
        "staged_source_files": summary.source_files,
        "implemented_capabilities": list(summary.implemented_capabilities),
        "target_capabilities": list(summary.target_capabilities),
        "remaining_target_capabilities": missing,
        "android_build_verified": False,
        "runtime_verified": False,
        "device_write_allowed": False,
    }
