"""Extensible UI catalogs; native user language first, English fallback."""
from __future__ import annotations

import locale
import os
import sys

CATALOGS = {
    "en": {
        "subtitle": "Flash Studio · Developer diagnostics",
        "notice": "READ ONLY · No phone is certified yet. Installation, backup and restore are unavailable.",
        "adb": "Trusted Android SDK ADB executable",
        "browse": "Browse…", "scan": "Inspect USB phone", "save": "Save report…",
        "ready": "Connect one authorized USB phone, select ADB, then inspect.",
        "running": "Reading device-reported properties… {seconds}s",
        "done": "Report ready — this is NOT proof of compatibility.",
        "scan_failed": "Inspection failed. Check the trusted ADB path, USB authorization and that exactly one USB phone is connected. No raw error output is shown.",
        "unexpected": "Inspection could not complete. No private error details are displayed. Retry after checking your local setup.",
        "save_failed": "Report could not be saved. Choose a NEW .json filename in a writable folder; existing files are never overwritten.",
        "saved": "Report saved locally. Review device-reported values before sharing.",
        "empty": "No diagnostic report yet. Nothing is downloaded, unlocked or flashed.",
        "privacy": "Reports stay local. Review device-reported values before sharing.",
        "language": "Language", "report": "Diagnostic report (JSON)",
        "close": "Close", "github": "by Swir · GitHub", "pick_adb": "Select your trusted ADB executable",
    },
    "pl": {
        "subtitle": "Flash Studio · Diagnostyka deweloperska",
        "notice": "TYLKO ODCZYT · Żaden telefon nie jest jeszcze zatwierdzony. Instalacja, kopia zapasowa i przywracanie są niedostępne.",
        "adb": "Zaufany plik ADB z Android SDK",
        "browse": "Wybierz…", "scan": "Sprawdź telefon USB", "save": "Zapisz raport…",
        "ready": "Podłącz jeden autoryzowany telefon USB, wybierz ADB i rozpocznij odczyt.",
        "running": "Odczytywanie danych zgłaszanych przez telefon… {seconds}s",
        "done": "Raport gotowy — NIE potwierdza zgodności z systemem.",
        "scan_failed": "Odczyt nie powiódł się. Sprawdź zaufaną ścieżkę ADB, autoryzację USB i czy podłączony jest dokładnie jeden telefon USB. Surowe błędy są ukryte.",
        "unexpected": "Nie udało się ukończyć odczytu. Prywatne szczegóły błędu są ukryte. Sprawdź konfigurację i spróbuj ponownie.",
        "save_failed": "Nie można zapisać raportu. Wybierz NOWĄ nazwę .json w folderze z prawem zapisu; istniejące pliki nie są nadpisywane.",
        "saved": "Raport zapisano lokalnie. Sprawdź zgłaszane dane przed udostępnieniem.",
        "empty": "Brak raportu. Program niczego nie pobiera, nie odblokowuje ani nie wgrywa.",
        "privacy": "Raport pozostaje lokalnie. Sprawdź dane z telefonu przed udostępnieniem.",
        "language": "Język", "report": "Raport diagnostyczny (JSON)",
        "close": "Zamknij", "github": "by Swir · GitHub", "pick_adb": "Wybierz zaufany plik ADB",
    },
    "nb": {
        "subtitle": "Flash Studio · Utviklerdiagnostikk",
        "notice": "KUN LESING · Ingen telefon er godkjent ennå. Installasjon, sikkerhetskopiering og gjenoppretting er utilgjengelig.",
        "adb": "Betrodd ADB-program fra Android SDK",
        "browse": "Velg…", "scan": "Undersøk USB-telefon", "save": "Lagre rapport…",
        "ready": "Koble til én autorisert USB-telefon, velg ADB og start kontrollen.",
        "running": "Leser opplysninger fra telefonen… {seconds}s",
        "done": "Rapport klar — dette bekrefter IKKE kompatibilitet.",
        "scan_failed": "Kontrollen mislyktes. Kontroller ADB-filen, USB-autorisasjonen og at nøyaktig én USB-telefon er tilkoblet. Rå feilutdata skjules.",
        "unexpected": "Kontrollen kunne ikke fullføres. Private feildetaljer vises ikke. Kontroller oppsettet og prøv igjen.",
        "save_failed": "Rapporten kunne ikke lagres. Velg et NYTT .json-filnavn i en skrivbar mappe; eksisterende filer overskrives aldri.",
        "saved": "Rapport lagret lokalt. Se gjennom opplysningene før deling.",
        "empty": "Ingen rapport ennå. Ingenting lastes ned, låses opp eller installeres.",
        "privacy": "Rapporten lagres lokalt. Kontroller opplysningene fra telefonen før deling.",
        "language": "Språk", "report": "Diagnoserapport (JSON)",
        "close": "Lukk", "github": "by Swir · GitHub", "pick_adb": "Velg den betrodde ADB-filen",
    },
}


def language_code(value: str | None) -> str:
    code = (value or "").split(".", 1)[0].replace("-", "_").split("_", 1)[0].lower()
    return {"no": "nb"}.get(code, code) if code in (*CATALOGS, "no") else "en"


def detect_language() -> str:
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
        return "en"


def translate(language: str, key: str, **values: object) -> str:
    catalog = CATALOGS.get(language, CATALOGS["en"])
    return catalog.get(key, CATALOGS["en"][key]).format(**values)
