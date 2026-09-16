"""Shared localization runtime for SwirPhoneOS host tools.

The canonical English catalog and all translated catalogs live in
``swirphoneos/locales/catalogs.json`` so languages can be added without
changing Python logic. Missing translated strings fall back to English.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
import json
import locale
import os
import re
from string import Formatter
import sys
from typing import Mapping

_LOCALE_RE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-[A-Za-z]{2}|\-[0-9]{3})?\Z")
_ALLOWED_DIRECTIONS = {"ltr", "rtl"}
_ALIAS = {"no": "nb", "iw": "he", "in": "id", "ji": "yi"}


class LocalizationError(ValueError):
    """Raised when localization data violates the shared contract."""


@dataclass(frozen=True)
class LocaleInfo:
    code: str
    name: str
    direction: str
    strings: Mapping[str, str]


def _pairs_unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LocalizationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _placeholders(text: str) -> frozenset[str]:
    names: set[str] = set()
    try:
        for _, field_name, _, _ in Formatter().parse(text):
            if field_name:
                names.add(field_name.split(".", 1)[0].split("[", 1)[0])
    except ValueError as exc:
        raise LocalizationError("Invalid format placeholder syntax.") from exc
    return frozenset(names)


def _read_catalog_document() -> dict[str, object]:
    path = resources.files("swirphoneos").joinpath("locales", "catalogs.json")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LocalizationError("Localization catalog cannot be read.") from exc
    if len(text) > 1_000_000:
        raise LocalizationError("Localization catalog is oversized.")
    try:
        return json.loads(text, object_pairs_hook=_pairs_unique)
    except json.JSONDecodeError as exc:
        raise LocalizationError("Localization catalog is invalid JSON.") from exc


def _validate_catalog_document(document: object) -> tuple[str, dict[str, LocaleInfo]]:
    if not isinstance(document, dict) or set(document) != {"schema_version", "source_locale", "locales"}:
        raise LocalizationError("Localization document must match schema v1 exactly.")
    if document["schema_version"] != 1:
        raise LocalizationError("Unsupported localization schema.")
    source_locale = document["source_locale"]
    locales = document["locales"]
    if not isinstance(source_locale, str) or not isinstance(locales, dict) or not locales:
        raise LocalizationError("Localization source/locales are invalid.")
    if source_locale not in locales:
        raise LocalizationError("Source locale is missing.")

    parsed: dict[str, LocaleInfo] = {}
    for code, entry in locales.items():
        if not isinstance(code, str) or not _LOCALE_RE.fullmatch(code):
            raise LocalizationError("Locale code is not canonical BCP-47 subset.")
        if not isinstance(entry, dict) or set(entry) != {"name", "direction", "strings"}:
            raise LocalizationError(f"Locale {code} metadata is invalid.")
        name, direction, strings = entry["name"], entry["direction"], entry["strings"]
        if not isinstance(name, str) or not name.strip() or len(name) > 80:
            raise LocalizationError(f"Locale {code} display name is invalid.")
        if direction not in _ALLOWED_DIRECTIONS:
            raise LocalizationError(f"Locale {code} direction is invalid.")
        if not isinstance(strings, dict):
            raise LocalizationError(f"Locale {code} strings must be an object.")
        clean: dict[str, str] = {}
        for key, value in strings.items():
            if not isinstance(key, str) or not key or len(key) > 96 or not key.isascii():
                raise LocalizationError(f"Locale {code} contains an invalid string key.")
            if not isinstance(value, str) or not value.strip() or len(value) > 4096:
                raise LocalizationError(f"Locale {code} contains an invalid translation.")
            if any(ord(ch) < 9 or 13 < ord(ch) < 32 or ord(ch) == 127 for ch in value):
                raise LocalizationError(f"Locale {code} contains control characters.")
            clean[key] = value
        parsed[code] = LocaleInfo(code=code, name=name.strip(), direction=direction, strings=clean)

    source_keys = set(parsed[source_locale].strings)
    if not source_keys:
        raise LocalizationError("Source locale must contain strings.")
    for code, info in parsed.items():
        unknown = set(info.strings) - source_keys
        if unknown:
            raise LocalizationError(f"Locale {code} contains keys absent from the source catalog.")
        for key, text in info.strings.items():
            if _placeholders(text) != _placeholders(parsed[source_locale].strings[key]):
                raise LocalizationError(f"Locale {code} placeholder mismatch for {key}.")
    return source_locale, parsed


SOURCE_LOCALE, LOCALES = _validate_catalog_document(_read_catalog_document())
CATALOGS: dict[str, Mapping[str, str]] = {code: info.strings for code, info in LOCALES.items()}


def _canonicalize(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    raw = raw.split(".", 1)[0].split("@", 1)[0].replace("_", "-")
    if raw in {"C", "POSIX"}:
        return ""
    pieces = [piece for piece in raw.split("-") if piece]
    if not pieces:
        return ""
    pieces[0] = _ALIAS.get(pieces[0].lower(), pieces[0].lower())
    for index in range(1, len(pieces)):
        if len(pieces[index]) == 4 and pieces[index].isalpha():
            pieces[index] = pieces[index].title()
        elif (len(pieces[index]) == 2 and pieces[index].isalpha()) or (
            len(pieces[index]) == 3 and pieces[index].isdigit()
        ):
            pieces[index] = pieces[index].upper()
        else:
            pieces[index] = pieces[index].lower()
    return "-".join(pieces)


def language_code(value: str | None) -> str:
    """Resolve a platform locale to a supported catalog, else English."""
    canonical = _canonicalize(value)
    if canonical in LOCALES:
        return canonical
    if canonical:
        base = canonical.split("-", 1)[0]
        if base in LOCALES:
            return base
    return SOURCE_LOCALE


def detect_language() -> str:
    """Detect the current UI locale without changing process-global locale state."""
    if sys.platform == "win32":
        try:
            import ctypes

            native = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage())
            if native:
                return language_code(native)
        except (AttributeError, OSError):
            pass
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(key):
            return language_code(os.environ[key])
    try:
        return language_code(locale.getlocale()[0])
    except (ValueError, TypeError):
        return SOURCE_LOCALE


def translate(language: str, key: str, **values: object) -> str:
    """Translate one key with English fallback and safe named formatting."""
    source = CATALOGS[SOURCE_LOCALE]
    if key not in source:
        raise LocalizationError(f"Unknown localization key: {key}")
    # Keep CATALOGS patchable for tests/embedding while locale detection remains strict.
    code = language if language in CATALOGS else language_code(language)
    text = CATALOGS.get(code, source).get(key, source[key])
    try:
        return text.format(**values)
    except (KeyError, IndexError, ValueError) as exc:
        raise LocalizationError(f"Invalid formatting values for key: {key}") from exc


def text_direction(language: str) -> str:
    return LOCALES[language_code(language)].direction


def catalog_summary() -> dict[str, object]:
    """Return non-sensitive translation coverage for CI/status surfaces."""
    total = len(LOCALES[SOURCE_LOCALE].strings)
    rows = []
    for code in sorted(LOCALES):
        info = LOCALES[code]
        translated = len(info.strings)
        rows.append(
            {
                "code": code,
                "name": info.name,
                "direction": info.direction,
                "translated": translated,
                "total": total,
                "coverage_percent": round(translated * 100 / total, 1),
            }
        )
    return {
        "schema_version": 1,
        "source_locale": SOURCE_LOCALE,
        "locale_count": len(rows),
        "string_count": total,
        "locales": rows,
    }
