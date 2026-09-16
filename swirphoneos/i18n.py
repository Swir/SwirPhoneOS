"""Small extensible translation layer for SwirPhoneStudio."""
from __future__ import annotations

import locale

DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "pl", "no")

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "SwirPhoneStudio",
        "preview": "READ-ONLY developer preview — no flashing, unlocking, erase or reboot commands are available.",
        "profiles": "Validate device profiles",
        "adb": "Inspect phone via ADB",
        "fastboot": "Inspect Fastboot / FastbootD",
        "export": "Export sanitized report",
        "ready": "Ready. Connect exactly one phone only when using USB diagnostics.",
        "working": "Running read-only diagnostics…",
        "success": "Read-only diagnostic completed.",
        "failed": "Diagnostic failed. Check the trusted tool path, USB mode and device authorization.",
        "choose_adb": "Select trusted adb executable",
        "choose_fastboot": "Select trusted fastboot executable",
        "save_report": "Save sanitized diagnostic report",
        "saved": "Sanitized report saved.",
        "nothing_to_export": "Run a diagnostic before exporting a report.",
        "by_swir": "by Swir · github.com/Swir",
    },
    "pl": {
        "app_title": "SwirPhoneStudio",
        "preview": "WERSJA DEWELOPERSKA TYLKO DO ODCZYTU — brak flashowania, odblokowania, kasowania i restartu telefonu.",
        "profiles": "Sprawdź profile urządzeń",
        "adb": "Sprawdź telefon przez ADB",
        "fastboot": "Sprawdź Fastboot / FastbootD",
        "export": "Eksportuj bezpieczny raport",
        "ready": "Gotowe. Podczas diagnostyki USB podłącz dokładnie jeden telefon.",
        "working": "Trwa diagnostyka tylko do odczytu…",
        "success": "Diagnostyka tylko do odczytu zakończona.",
        "failed": "Diagnostyka nie powiodła się. Sprawdź ścieżkę narzędzia, tryb USB i autoryzację telefonu.",
        "choose_adb": "Wybierz zaufany plik adb",
        "choose_fastboot": "Wybierz zaufany plik fastboot",
        "save_report": "Zapisz bezpieczny raport diagnostyczny",
        "saved": "Bezpieczny raport zapisany.",
        "nothing_to_export": "Najpierw uruchom diagnostykę.",
        "by_swir": "by Swir · github.com/Swir",
    },
    "no": {
        "app_title": "SwirPhoneStudio",
        "preview": "SKRIVEBESKYTTET utviklerforhåndsvisning — ingen flashing, opplåsing, sletting eller omstart er tilgjengelig.",
        "profiles": "Valider enhetsprofiler",
        "adb": "Inspiser telefon via ADB",
        "fastboot": "Inspiser Fastboot / FastbootD",
        "export": "Eksporter renset rapport",
        "ready": "Klar. Koble til nøyaktig én telefon ved USB-diagnostikk.",
        "working": "Kjører skrivebeskyttet diagnostikk…",
        "success": "Skrivebeskyttet diagnostikk fullført.",
        "failed": "Diagnostikken mislyktes. Kontroller verktøysti, USB-modus og enhetsgodkjenning.",
        "choose_adb": "Velg klarert adb-program",
        "choose_fastboot": "Velg klarert fastboot-program",
        "save_report": "Lagre renset diagnoserapport",
        "saved": "Renset rapport lagret.",
        "nothing_to_export": "Kjør diagnostikk før rapporten eksporteres.",
        "by_swir": "by Swir · github.com/Swir",
    },
}


def normalize_language(value: str | None) -> str:
    """Map an OS locale such as pl_PL, nb_NO or en-US to a supported language."""
    if not value:
        return DEFAULT_LANGUAGE
    primary = value.replace("-", "_").split("_", 1)[0].lower()
    if primary in {"nb", "nn", "no"}:
        return "no"
    return primary if primary in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def system_language(locale_name: str | None = None) -> str:
    if locale_name is not None:
        return normalize_language(locale_name)
    try:
        detected = locale.getlocale()[0]
    except (ValueError, TypeError):
        detected = None
    return normalize_language(detected)


def tr(key: str, language: str) -> str:
    language = normalize_language(language)
    try:
        return _TRANSLATIONS[language][key]
    except KeyError:
        try:
            return _TRANSLATIONS[DEFAULT_LANGUAGE][key]
        except KeyError as exc:
            raise KeyError(f"Unknown translation key: {key}") from exc
