"""Fail-closed localization lint for first-party SwirPhoneOS Android source.

This module validates checked-in Android resources only. It does not claim that
an APK was built, launched, visually reviewed, or physically verified.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .i18n import LOCALES, SOURCE_LOCALE
from .system_apps import SystemAppRegistryError, load_registry


class AndroidLocalizationError(ValueError):
    """Raised when Android application localization violates the source contract."""


@dataclass(frozen=True)
class AndroidLocalizationSummary:
    source_locale: str
    locales: tuple[str, ...]
    apps: tuple[str, ...]
    string_entries: int
    plural_entries: int
    java_files_scanned: int


_ALLOWED_PLURAL_QUANTITIES = frozenset({"zero", "one", "two", "few", "many", "other"})
_MAX_RESOURCE_TEXT = 1_000_000
_MAX_JAVA_TEXT = 1_000_000
_FORMAT_TOKEN = re.compile(
    r"%(?:(?P<index>[1-9][0-9]*)\$)?(?P<flags>[-#+ 0,(<]*)?(?P<width>[0-9]*)?(?:\.(?P<precision>[0-9]+))?(?P<kind>[a-zA-Z%])"
)
_DIRECT_UI_LITERAL = re.compile(
    r"\b(?:setText|setTitle|setHint|setMessage|setContentDescription|setPositiveButton|setNegativeButton|setNeutralButton)\s*\(\s*\"((?:\\.|[^\"\\])*)\"",
    re.DOTALL,
)
_TOAST_LITERAL = re.compile(
    r"\bToast\.makeText\s*\([^,]+,\s*\"((?:\\.|[^\"\\])*)\"",
    re.DOTALL,
)


def _read_text(path: Path, *, limit: int) -> str:
    if not path.is_file() or path.is_symlink():
        raise AndroidLocalizationError(f"Missing or unsafe localization source: {path.name}")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AndroidLocalizationError("Localization source must be readable strict UTF-8.") from exc
    if not text or len(text) > limit:
        raise AndroidLocalizationError("Localization source has an invalid size.")
    return text


def _resource_dir(locale_code: str) -> str:
    if locale_code == SOURCE_LOCALE:
        return "values"
    if re.fullmatch(r"[a-z]{2,3}", locale_code):
        return f"values-{locale_code}"
    if not re.fullmatch(r"[A-Za-z0-9-]+", locale_code):
        raise AndroidLocalizationError("Locale code cannot be represented as an Android resource qualifier.")
    return "values-b+" + locale_code.replace("-", "+")


def _resource_text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _format_signature(text: str) -> Counter[tuple[str, str]]:
    """Return an order-independent Android/Java formatter argument signature."""
    signature: Counter[tuple[str, str]] = Counter()
    implicit_index = 0
    for match in _FORMAT_TOKEN.finditer(text):
        kind = match.group("kind")
        if kind == "%":
            continue
        explicit = match.group("index")
        if explicit is None:
            implicit_index += 1
            index = f"implicit:{implicit_index}"
        else:
            index = f"explicit:{int(explicit)}"
        signature[(index, kind)] += 1
    return signature


def _parse_resources(path: Path) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    try:
        root = ET.fromstring(_read_text(path, limit=_MAX_RESOURCE_TEXT))
    except ET.ParseError as exc:
        raise AndroidLocalizationError("Android localization resource XML is malformed.") from exc
    if root.tag != "resources":
        raise AndroidLocalizationError("Android localization resource root must be <resources>.")

    strings: dict[str, str] = {}
    plurals: dict[str, dict[str, str]] = {}
    for child in root:
        if child.tag == "string":
            name = (child.get("name") or "").strip()
            if not name or name in strings:
                raise AndroidLocalizationError("Android string resources contain missing or duplicate names.")
            strings[name] = _resource_text(child)
        elif child.tag == "plurals":
            name = (child.get("name") or "").strip()
            if not name or name in plurals:
                raise AndroidLocalizationError("Android plural resources contain missing or duplicate names.")
            quantities: dict[str, str] = {}
            for item in child.findall("item"):
                quantity = (item.get("quantity") or "").strip()
                if quantity not in _ALLOWED_PLURAL_QUANTITIES or quantity in quantities:
                    raise AndroidLocalizationError("Android plural resource contains an invalid or duplicate quantity.")
                quantities[quantity] = _resource_text(item)
            if "other" not in quantities:
                raise AndroidLocalizationError("Every Android plural resource must define the 'other' quantity.")
            if len(quantities) != len(child.findall("item")):
                raise AndroidLocalizationError("Android plural resources may contain only <item> children.")
            plurals[name] = quantities
    if not strings and not plurals:
        raise AndroidLocalizationError("Android localization catalog is empty.")
    return strings, plurals


def _validate_placeholder_contract(
    source_strings: dict[str, str],
    source_plurals: dict[str, dict[str, str]],
    translated_strings: dict[str, str],
    translated_plurals: dict[str, dict[str, str]],
    locale_code: str,
) -> None:
    if set(translated_strings) != set(source_strings):
        raise AndroidLocalizationError(f"Android string-key coverage drifted for locale {locale_code}.")
    if set(translated_plurals) != set(source_plurals):
        raise AndroidLocalizationError(f"Android plural-key coverage drifted for locale {locale_code}.")

    for name, source_text in source_strings.items():
        if _format_signature(translated_strings[name]) != _format_signature(source_text):
            raise AndroidLocalizationError(f"Android format placeholders drifted for {locale_code}:{name}.")

    for name, translated_quantities in translated_plurals.items():
        source_quantities = source_plurals[name]
        if "other" not in translated_quantities:
            raise AndroidLocalizationError(f"Android plural {locale_code}:{name} has no 'other' quantity.")
        for quantity, translated_text in translated_quantities.items():
            source_text = source_quantities.get(quantity, source_quantities["other"])
            if _format_signature(translated_text) != _format_signature(source_text):
                raise AndroidLocalizationError(
                    f"Android plural format placeholders drifted for {locale_code}:{name}:{quantity}."
                )


def _without_java_comments(text: str) -> str:
    """Remove comments while preserving string literals for UI-literal scanning."""
    out: list[str] = []
    index = 0
    state = "code"
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == '"':
                state = "string"
                out.append(char)
            elif char == "'":
                state = "char"
                out.append(char)
            elif char == "/" and nxt == "/":
                state = "line_comment"
                out.extend("  ")
                index += 1
            elif char == "/" and nxt == "*":
                state = "block_comment"
                out.extend("  ")
                index += 1
            else:
                out.append(char)
        elif state == "string":
            out.append(char)
            if char == "\\" and nxt:
                out.append(nxt)
                index += 1
            elif char == '"':
                state = "code"
        elif state == "char":
            out.append(char)
            if char == "\\" and nxt:
                out.append(nxt)
                index += 1
            elif char == "'":
                state = "code"
        elif state == "line_comment":
            if char == "\n":
                out.append("\n")
                state = "code"
            else:
                out.append(" ")
        else:
            if char == "*" and nxt == "/":
                out.extend("  ")
                index += 1
                state = "code"
            elif char == "\n":
                out.append("\n")
            else:
                out.append(" ")
        index += 1
    return "".join(out)


def _validate_no_direct_ui_literals(app_root: Path) -> int:
    java_files = sorted(path for path in app_root.rglob("*.java") if "hosttest" not in path.parts)
    if not java_files:
        raise AndroidLocalizationError("Source-ready Android app has no production Java source.")
    for path in java_files:
        source = _without_java_comments(_read_text(path, limit=_MAX_JAVA_TEXT))
        for pattern in (_DIRECT_UI_LITERAL, _TOAST_LITERAL):
            for match in pattern.finditer(source):
                if match.group(1).strip():
                    raise AndroidLocalizationError(
                        f"Direct user-facing Java string literal is forbidden in {path.name}; use Android resources."
                    )
    return len(java_files)


def _discover_source_roots(product_root: Path, expected_packages: dict[str, str]) -> dict[str, Path]:
    apps_root = product_root / "apps"
    if not apps_root.is_dir() or apps_root.is_symlink():
        raise AndroidLocalizationError("AOSP application source root is missing or unsafe.")
    discovered: dict[str, Path] = {}
    for candidate in sorted(apps_root.iterdir()):
        manifest_path = candidate / "AndroidManifest.xml"
        if not candidate.is_dir() or candidate.is_symlink() or not manifest_path.is_file():
            continue
        try:
            manifest = ET.fromstring(_read_text(manifest_path, limit=_MAX_RESOURCE_TEXT))
        except ET.ParseError as exc:
            raise AndroidLocalizationError("Android application manifest is malformed XML.") from exc
        package = (manifest.get("package") or "").strip()
        if package in expected_packages:
            if package in discovered:
                raise AndroidLocalizationError("Duplicate source-ready Android package source was found.")
            discovered[package] = candidate
    if set(discovered) != set(expected_packages):
        missing = sorted(set(expected_packages) - set(discovered))
        raise AndroidLocalizationError(f"Source-ready Android localization roots are incomplete: {missing}")
    return discovered


def validate_android_localization(
    product_root: Path = Path("platform/aosp_product"),
    registry_path: Path = Path("system_apps/manifest.json"),
) -> AndroidLocalizationSummary:
    """Validate Android resource parity, format safety, plural shape and Java UI literals."""
    try:
        registry = load_registry(registry_path)
    except SystemAppRegistryError as exc:
        raise AndroidLocalizationError(str(exc)) from exc
    source_apps = [app for app in registry.apps if app.status == "ANDROID_SOURCE"]
    if not source_apps:
        raise AndroidLocalizationError("At least one ANDROID_SOURCE app is required for Android localization lint.")

    expected_packages = {app.package: app.app_id for app in source_apps}
    roots = _discover_source_roots(product_root, expected_packages)
    locale_codes = tuple(LOCALES)
    if SOURCE_LOCALE not in locale_codes:
        raise AndroidLocalizationError("Shared source locale is missing from the locale registry.")

    string_entries = 0
    plural_entries = 0
    java_files_scanned = 0
    validated_apps: list[str] = []
    for app in source_apps:
        app_root = roots[app.package]
        source_path = app_root / "res" / _resource_dir(SOURCE_LOCALE) / "strings.xml"
        source_strings, source_plurals = _parse_resources(source_path)
        string_entries += len(source_strings)
        plural_entries += len(source_plurals)
        for locale_code in locale_codes:
            localized_path = app_root / "res" / _resource_dir(locale_code) / "strings.xml"
            translated_strings, translated_plurals = _parse_resources(localized_path)
            _validate_placeholder_contract(
                source_strings,
                source_plurals,
                translated_strings,
                translated_plurals,
                locale_code,
            )
        java_files_scanned += _validate_no_direct_ui_literals(app_root)
        validated_apps.append(app.app_id)

    return AndroidLocalizationSummary(
        source_locale=SOURCE_LOCALE,
        locales=locale_codes,
        apps=tuple(validated_apps),
        string_entries=string_entries,
        plural_entries=plural_entries,
        java_files_scanned=java_files_scanned,
    )


def public_android_localization_summary(summary: AndroidLocalizationSummary) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "SOURCE_LINT_ONLY_NOT_RUNTIME_VERIFIED",
        "source_locale": summary.source_locale,
        "locale_count": len(summary.locales),
        "locales": list(summary.locales),
        "source_ready_app_count": len(summary.apps),
        "source_ready_apps": list(summary.apps),
        "source_string_entries": summary.string_entries,
        "source_plural_entries": summary.plural_entries,
        "production_java_files_scanned": summary.java_files_scanned,
        "resource_key_parity_verified": True,
        "format_placeholder_parity_verified": True,
        "plural_contract_verified": True,
        "direct_ui_literal_sinks_rejected": True,
        "runtime_locale_switch_verified": False,
        "runtime_rtl_verified": False,
        "android_build_verified": False,
        "device_write_allowed": False,
    }
