"""Emulator-only locale-matrix evidence for source-ready SwirPhoneOS apps.

The runner is intentionally restricted to one exact local SwirPhoneOS
Cuttlefish instance. It changes only per-app locale overrides and transient
foreground activity state, restores every captured locale override before
returning, and never claims visual RTL/accessibility or physical-device proof.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .cuttlefish_evidence import (
    CuttlefishEvidenceCollector,
    CuttlefishEvidenceError,
    parse_local_devices,
    parse_resolved_activity,
    select_local_device,
)
from .cuttlefish_smoke import (
    CuttlefishSmokeError,
    foreground_contains_component,
    parse_am_start_wait,
)
from .i18n import LOCALES
from .system_apps import SystemAppRegistry, SystemAppRegistryError, load_registry


_COMPONENT = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+/(?:\.?[A-Za-z0-9_.$]+)\Z")
_LOCAL_SERIAL = re.compile(r"(?:emulator-[0-9]{1,5}|(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5})\Z")
_LOCALE_TAG = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?\Z")
_MAX_ADB_OUTPUT = 4 * 1024 * 1024
_MAX_USER_ID = 9999


class CuttlefishI18nError(RuntimeError):
    """Raised when runtime localization evidence is unsafe or incomplete."""


@dataclass(frozen=True)
class LocaleLaunchResult:
    package: str
    locale: str
    component: str
    foreground_confirmed: bool


def parse_current_user(output: str) -> int:
    """Parse the exact bounded output of ``am get-current-user``."""
    text = output.strip()
    if not re.fullmatch(r"[0-9]{1,4}", text):
        raise CuttlefishI18nError("Android current-user response is malformed.")
    user_id = int(text)
    if not 0 <= user_id <= _MAX_USER_ID:
        raise CuttlefishI18nError("Android current-user id is outside the accepted range.")
    return user_id


def _parse_locale_list(text: str) -> tuple[str, ...]:
    if text == "":
        return ()
    parts = tuple(item.strip() for item in text.split(","))
    if any(not item or _LOCALE_TAG.fullmatch(item) is None for item in parts):
        raise CuttlefishI18nError("Android app-locale response contains an invalid language tag.")
    canonical = tuple(item.replace("_", "-") for item in parts)
    if len(set(canonical)) != len(canonical):
        raise CuttlefishI18nError("Android app-locale response contains duplicate language tags.")
    return canonical


def parse_app_locales(output: str, package: str, user_id: int) -> tuple[str, ...]:
    """Parse current AOSP ``cmd locale get-app-locales`` output exactly."""
    if len(output) > 4096:
        raise CuttlefishI18nError("Android app-locale response is oversized.")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        raise CuttlefishI18nError("Android app-locale response must contain exactly one line.")
    prefix = f"Locales for {package} for user {user_id} are ["
    line = lines[0]
    if not line.startswith(prefix) or not line.endswith("]"):
        raise CuttlefishI18nError("Android app-locale response does not match the requested package/user.")
    return _parse_locale_list(line[len(prefix):-1])


def _supported_runtime_locales() -> tuple[str, ...]:
    locales = tuple(LOCALES)
    if not locales or len(set(locales)) != len(locales):
        raise CuttlefishI18nError("Shared localization catalog has no unique runtime locale set.")
    for locale in locales:
        if _LOCALE_TAG.fullmatch(locale) is None:
            raise CuttlefishI18nError("Shared localization catalog contains an unsupported runtime locale tag.")
    return locales


class CuttlefishI18nRunner:
    """Exercise every source-ready app under every checked-in locale on Cuttlefish."""

    def __init__(self, executable: Path, timeout: float = 15.0):
        self.evidence = CuttlefishEvidenceCollector(executable, timeout=min(timeout, 60.0))
        self.executable = self.evidence.executable
        if not 0 < timeout <= 60:
            raise CuttlefishI18nError("ADB timeout must be between 0 and 60 seconds.")
        self.timeout = timeout

    def _run(self, args: tuple[str, ...]) -> str:
        local = len(args) >= 2 and args[0] == "-s" and _LOCAL_SERIAL.fullmatch(args[1]) is not None
        current_user = local and args[2:] == ("shell", "am", "get-current-user")
        get_locale = (
            local
            and len(args) == 9
            and args[2:6] == ("shell", "cmd", "locale", "get-app-locales")
            and bool(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", args[6]))
            and args[7] == "--user"
            and bool(re.fullmatch(r"[0-9]{1,4}", args[8]))
        )
        set_locale_no_value = (
            local
            and len(args) == 9
            and args[2:6] == ("shell", "cmd", "locale", "set-app-locales")
            and bool(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", args[6]))
            and args[7] == "--user"
            and bool(re.fullmatch(r"[0-9]{1,4}", args[8]))
        )
        set_locale_value = (
            local
            and len(args) == 11
            and args[2:6] == ("shell", "cmd", "locale", "set-app-locales")
            and bool(re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", args[6]))
            and args[7] == "--user"
            and bool(re.fullmatch(r"[0-9]{1,4}", args[8]))
            and args[9] == "--locales"
            and bool(_LOCALE_TAG.fullmatch(args[10]))
        )
        component_launch = (
            local
            and len(args) == 8
            and args[2:7] == ("shell", "am", "start", "-W", "-n")
            and _COMPONENT.fullmatch(args[7]) is not None
        )
        activity_state = local and args[2:] == ("shell", "dumpsys", "activity", "activities")
        permitted = (
            args == ("devices", "-l")
            or current_user
            or get_locale
            or set_locale_no_value
            or set_locale_value
            or component_launch
            or activity_state
        )
        if not permitted:
            raise CuttlefishI18nError("Command is outside the emulator-only localization allowlist.")

        env = {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith(("ADB_", "ANDROID_ADB_")) and key.upper() != "ANDROID_SERIAL"
        }
        try:
            result = subprocess.run(
                [str(self.executable), *args],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
                timeout=self.timeout,
                shell=False,
                check=False,
                env=env,
            )
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise CuttlefishI18nError("ADB localization command failed or timed out; raw output is withheld.") from None
        if result.returncode != 0:
            raise CuttlefishI18nError("ADB localization command failed; raw output is withheld.")
        if len(result.stdout) > _MAX_ADB_OUTPUT:
            raise CuttlefishI18nError("ADB localization response is oversized.")
        return result.stdout

    def _get_locales(self, serial: str, package: str, user_id: int) -> tuple[str, ...]:
        return parse_app_locales(
            self._run(
                (
                    "-s", serial, "shell", "cmd", "locale", "get-app-locales",
                    package, "--user", str(user_id),
                )
            ),
            package,
            user_id,
        )

    def _set_locales(self, serial: str, package: str, user_id: int, locales: tuple[str, ...]) -> None:
        if len(locales) > 1:
            raise CuttlefishI18nError("Runtime localization smoke changes at most one locale override at a time.")
        args = [
            "-s", serial, "shell", "cmd", "locale", "set-app-locales",
            package, "--user", str(user_id),
        ]
        if locales:
            args.extend(("--locales", locales[0]))
        self._run(tuple(args))

    def exercise(self, registry: SystemAppRegistry) -> dict[str, object]:
        runtime = self.evidence.inspect(registry)
        if runtime.get("runtime_evidence_complete") is not True or runtime.get("identity_matches") is not True:
            raise CuttlefishI18nError("Exact SwirPhoneOS Cuttlefish runtime evidence is required before locale changes.")

        device = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        user_id = parse_current_user(self._run(("-s", device.serial, "shell", "am", "get-current-user")))
        source_apps = sorted((app for app in registry.apps if app.source_ready), key=lambda app: app.package)
        locales = _supported_runtime_locales()
        if not source_apps:
            raise CuttlefishI18nError("System-app registry has no source-ready packages.")

        original: dict[str, tuple[str, ...]] = {}
        results: list[LocaleLaunchResult] = []
        primary_error: Exception | None = None
        restore_error: Exception | None = None

        try:
            for app in source_apps:
                original[app.package] = self._get_locales(device.serial, app.package, user_id)

            for locale in locales:
                for app in source_apps:
                    self._set_locales(device.serial, app.package, user_id, (locale,))
                    observed = self._get_locales(device.serial, app.package, user_id)
                    if observed != (locale,):
                        raise CuttlefishI18nError("Android did not preserve the requested per-app locale override.")

                    resolution = self.evidence._run(
                        ("-s", device.serial, "shell", "cmd", "package", "resolve-activity", "--brief", app.package)
                    )
                    component = resolution.strip()
                    if not parse_resolved_activity(component, app.package) or _COMPONENT.fullmatch(component) is None:
                        raise CuttlefishI18nError("Localized source-ready app has no package-local launcher activity.")

                    launch_output = self._run(
                        ("-s", device.serial, "shell", "am", "start", "-W", "-n", component)
                    )
                    parse_am_start_wait(launch_output, app.package, component)
                    state = self._run(("-s", device.serial, "shell", "dumpsys", "activity", "activities"))
                    foreground = foreground_contains_component(state, app.package, component)
                    if not foreground:
                        raise CuttlefishI18nError("Localized source-ready app was not confirmed as resumed foreground activity.")
                    results.append(LocaleLaunchResult(app.package, locale, component, foreground))
        except Exception as exc:
            primary_error = exc
        finally:
            for package, saved in reversed(tuple(original.items())):
                try:
                    self._set_locales(device.serial, package, user_id, saved)
                    if self._get_locales(device.serial, package, user_id) != saved:
                        raise CuttlefishI18nError("Original per-app locale override was not restored exactly.")
                except Exception as exc:
                    restore_error = exc
                    break

        if restore_error is not None:
            raise CuttlefishI18nError(
                "Locale restoration failed; discard/reset the disposable Cuttlefish instance before collecting evidence."
            ) from restore_error
        if primary_error is not None:
            if isinstance(primary_error, CuttlefishI18nError):
                raise primary_error
            if isinstance(primary_error, (CuttlefishEvidenceError, CuttlefishSmokeError)):
                raise CuttlefishI18nError(str(primary_error)) from primary_error
            raise CuttlefishI18nError("Runtime localization smoke failed; raw error is withheld.") from primary_error

        after = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        if after != device:
            raise CuttlefishI18nError("ADB transport changed during runtime localization smoke.")

        fingerprint = str(runtime.get("build_fingerprint") or "")
        if not fingerprint:
            raise CuttlefishI18nError("Runtime fingerprint is missing from prerequisite evidence.")

        rtl_locales = [code for code in locales if LOCALES[code].direction == "rtl"]
        expected_count = len(source_apps) * len(locales)
        return {
            "schema_version": 1,
            "source": "local_cuttlefish_runtime_locale_matrix",
            "expected_product": runtime["expected_product"],
            "build_fingerprint": fingerprint,
            "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii")).hexdigest(),
            "android_user_id": user_id,
            "tested_locales": list(locales),
            "rtl_locales_exercised": rtl_locales,
            "tested_packages": [app.package for app in source_apps],
            "locale_results": [
                {
                    "package": item.package,
                    "locale": item.locale,
                    "component": item.component,
                    "foreground_confirmed": item.foreground_confirmed,
                }
                for item in results
            ],
            "locale_matrix_complete": len(results) == expected_count and all(item.foreground_confirmed for item in results),
            "rtl_runtime_switch_exercised": bool(rtl_locales),
            "rtl_visual_mirroring_verified": False,
            "original_app_locales_restored": True,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True,
            "warnings": [
                "This check changes only per-app locale overrides and foreground activity state on one exact disposable local Cuttlefish guest.",
                "Every captured locale override must be restored exactly before evidence is accepted.",
                "Locale switching and launch success do not prove visual translation quality, RTL mirroring, text expansion, accessibility, input methods, fonts, or physical-device behavior.",
                "No package install, system-settings write, root, reboot, flash, erase, registry promotion, or physical-device operation is performed.",
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exercise every source-ready SwirPhoneOS app under every checked-in locale on exact local Cuttlefish."
    )
    parser.add_argument("--adb", required=True, type=Path, help="Absolute path to a trusted Android SDK adb executable")
    parser.add_argument("--manifest", type=Path, default=Path("system_apps/manifest.json"))
    args = parser.parse_args(argv)
    try:
        report = CuttlefishI18nRunner(args.adb).exercise(load_registry(args.manifest))
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (
        CuttlefishI18nError,
        CuttlefishEvidenceError,
        CuttlefishSmokeError,
        SystemAppRegistryError,
        OSError,
        ValueError,
    ):
        print(
            "Operation failed: exact local SwirPhoneOS Cuttlefish runtime is required, every locale/app launch must pass, and all original locale overrides must be restored. Raw errors are withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
