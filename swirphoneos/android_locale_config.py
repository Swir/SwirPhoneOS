"""Fail-closed Android per-app LocaleConfig contract for SwirPhoneOS.

Every source-ready first-party app must advertise exactly the shared checked-in
locale set through Android's official ``android:localeConfig`` manifest
mechanism. This remains source evidence only; runtime behavior is verified
separately on Cuttlefish.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from .i18n import LOCALES
from .stage_manifest import StageManifestError, load_stage_files
from .system_apps import SystemAppRegistryError, load_registry


_ANDROID_NS = "http://schemas.android.com/apk/res/android"
_ANDROID_NAME = f"{{{_ANDROID_NS}}}name"
_ANDROID_LOCALE_CONFIG = f"{{{_ANDROID_NS}}}localeConfig"
_ANDROID_SUPPORTS_RTL = f"{{{_ANDROID_NS}}}supportsRtl"
_MAX_XML_BYTES = 512 * 1024


class AndroidLocaleConfigError(ValueError):
    """Raised when first-party Android locale metadata is incomplete or unsafe."""


@dataclass(frozen=True)
class AndroidLocaleConfigSummary:
    app_count: int
    locale_count: int
    locale_codes: tuple[str, ...]
    staged_config_count: int


def _read_xml(path: Path) -> ET.Element:
    if not path.is_file() or path.is_symlink():
        raise AndroidLocaleConfigError("Android locale metadata source is missing or unsafe.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_XML_BYTES:
        raise AndroidLocaleConfigError("Android locale metadata source has an invalid size.")
    try:
        return ET.fromstring(raw.decode("utf-8"))
    except (UnicodeError, ET.ParseError) as exc:
        raise AndroidLocaleConfigError("Android locale metadata must be valid strict UTF-8 XML.") from exc


def _discover_source_roots(product_root: Path, packages: set[str]) -> dict[str, Path]:
    apps_root = product_root / "apps"
    if not apps_root.is_dir() or apps_root.is_symlink():
        raise AndroidLocaleConfigError("AOSP application source root is missing or unsafe.")
    roots: dict[str, Path] = {}
    for candidate in sorted(apps_root.iterdir()):
        manifest_path = candidate / "AndroidManifest.xml"
        if not candidate.is_dir() or candidate.is_symlink() or not manifest_path.is_file():
            continue
        manifest = _read_xml(manifest_path)
        package = (manifest.get("package") or "").strip()
        if package in packages:
            if package in roots:
                raise AndroidLocaleConfigError("Duplicate source-ready Android package source was found.")
            roots[package] = candidate
    if set(roots) != packages:
        raise AndroidLocaleConfigError("Source-ready Android LocaleConfig roots are incomplete.")
    return roots


def _validate_config_file(path: Path, expected_locales: tuple[str, ...]) -> None:
    root = _read_xml(path)
    if root.tag != "locale-config" or root.attrib:
        raise AndroidLocaleConfigError("Android LocaleConfig root must be plain <locale-config>.")
    children = list(root)
    if len(children) != len(expected_locales) or any(child.tag != "locale" for child in children):
        raise AndroidLocaleConfigError("Android LocaleConfig must contain exactly one <locale> per shared locale.")
    locales: list[str] = []
    for child in children:
        if set(child.attrib) != {_ANDROID_NAME}:
            raise AndroidLocaleConfigError("Android LocaleConfig locale entry has unexpected attributes.")
        if list(child) or (child.text or "").strip():
            raise AndroidLocaleConfigError("Android LocaleConfig locale entry must be empty.")
        locale = (child.get(_ANDROID_NAME) or "").strip()
        if not locale or locale in locales:
            raise AndroidLocaleConfigError("Android LocaleConfig contains a missing or duplicate locale.")
        locales.append(locale)
    if tuple(locales) != expected_locales:
        raise AndroidLocaleConfigError("Android LocaleConfig locale set/order drifted from the shared catalog.")


def validate_android_locale_configs(
    product_root: Path = Path("platform/aosp_product"),
    registry_path: Path = Path("system_apps/manifest.json"),
) -> AndroidLocaleConfigSummary:
    """Validate app manifests, exact locale lists and AOSP staging coverage."""
    try:
        registry = load_registry(registry_path)
    except SystemAppRegistryError as exc:
        raise AndroidLocaleConfigError(str(exc)) from exc
    source_apps = [app for app in registry.apps if app.source_ready]
    if not source_apps:
        raise AndroidLocaleConfigError("At least one source-ready app is required.")
    expected_locales = tuple(LOCALES)
    if not expected_locales or len(set(expected_locales)) != len(expected_locales):
        raise AndroidLocaleConfigError("Shared locale registry is empty or duplicated.")

    packages = {app.package for app in source_apps}
    roots = _discover_source_roots(product_root, packages)
    expected_stage_pairs: set[tuple[str, str]] = set()

    for app in source_apps:
        root = roots[app.package]
        manifest = _read_xml(root / "AndroidManifest.xml")
        applications = manifest.findall("application")
        if len(applications) != 1:
            raise AndroidLocaleConfigError("Source-ready app manifest must contain exactly one <application>.")
        application = applications[0]
        if application.get(_ANDROID_LOCALE_CONFIG) != "@xml/locales_config":
            raise AndroidLocaleConfigError("Source-ready app must declare android:localeConfig=@xml/locales_config.")
        if application.get(_ANDROID_SUPPORTS_RTL) != "true":
            raise AndroidLocaleConfigError("Source-ready app must keep android:supportsRtl=true.")
        config = root / "res" / "xml" / "locales_config.xml"
        _validate_config_file(config, expected_locales)
        relative_root = root.relative_to(product_root).as_posix()
        source = f"{relative_root}/res/xml/locales_config.xml"
        destination = f"vendor/swir/{source}"
        expected_stage_pairs.add((source, destination))

    try:
        staged = load_stage_files(product_root, max_files=512)
    except StageManifestError as exc:
        raise AndroidLocaleConfigError(str(exc)) from exc
    actual = {(record.source.as_posix(), record.destination.as_posix()) for record in staged}
    if expected_stage_pairs - actual:
        raise AndroidLocaleConfigError("One or more Android LocaleConfig files are absent from exact AOSP staging.")

    return AndroidLocaleConfigSummary(
        app_count=len(source_apps),
        locale_count=len(expected_locales),
        locale_codes=expected_locales,
        staged_config_count=len(expected_stage_pairs),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate exact per-app Android LocaleConfig metadata and staging.")
    parser.add_argument("--product-root", type=Path, default=Path("platform/aosp_product"))
    parser.add_argument("--manifest", type=Path, default=Path("system_apps/manifest.json"))
    args = parser.parse_args(argv)
    try:
        summary = validate_android_locale_configs(args.product_root, args.manifest)
        print(json.dumps({
            "schema_version": 1,
            "source": "checked_in_android_locale_config",
            "app_count": summary.app_count,
            "locale_count": summary.locale_count,
            "locale_codes": list(summary.locale_codes),
            "staged_config_count": summary.staged_config_count,
            "runtime_verified": False,
            "visual_rtl_verified": False,
            "status_promotion_performed": False,
        }, indent=2, ensure_ascii=True))
        return 0
    except (AndroidLocaleConfigError, OSError, ValueError):
        print(
            "Operation failed: every source-ready app must declare and stage an exact shared Android LocaleConfig. Raw errors are withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
