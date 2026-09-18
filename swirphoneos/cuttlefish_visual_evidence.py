"""Capture bounded visual evidence from one exact local SwirPhoneOS Cuttlefish guest.

The collector is intentionally emulator-only. It changes per-app locale overrides
and transient foreground activity state, restores every captured locale override,
and writes PNG evidence only to a new host directory. It never installs packages,
changes system settings, touches a physical device, or claims that visual quality,
RTL mirroring, accessibility, or translation quality has been reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import sys

from .cuttlefish_evidence import (
    CuttlefishEvidenceCollector,
    CuttlefishEvidenceError,
    parse_local_devices,
    parse_resolved_activity,
    select_local_device,
)
from .cuttlefish_i18n import parse_app_locales, parse_current_user
from .cuttlefish_smoke import CuttlefishSmokeError, foreground_contains_component, parse_am_start_wait
from .i18n import LOCALES
from .system_apps import SystemAppRegistry, SystemAppRegistryError, load_registry

_LOCAL_SERIAL = re.compile(r"(?:emulator-[0-9]{1,5}|(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5})\Z")
_PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\Z")
_COMPONENT = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+/(?:\.?[A-Za-z0-9_.$]+)\Z")
_LOCALE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|[0-9]{3}))?\Z")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MAX_ADB_TEXT = 4 * 1024 * 1024
_MAX_PNG = 32 * 1024 * 1024
_MAX_DIMENSION = 16_384


class CuttlefishVisualEvidenceError(RuntimeError):
    """Raised when visual evidence is unsafe, ambiguous, or incomplete."""


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_png_dimensions(data: bytes) -> tuple[int, int]:
    """Validate the PNG signature/IHDR and return bounded dimensions."""
    if len(data) < 33 or len(data) > _MAX_PNG or not data.startswith(_PNG_SIGNATURE):
        raise CuttlefishVisualEvidenceError("Screenshot is not a bounded PNG image.")
    if data[12:16] != b"IHDR" or struct.unpack(">I", data[8:12])[0] != 13:
        raise CuttlefishVisualEvidenceError("Screenshot PNG is missing a canonical IHDR chunk.")
    width, height = struct.unpack(">II", data[16:24])
    if not 0 < width <= _MAX_DIMENSION or not 0 < height <= _MAX_DIMENSION:
        raise CuttlefishVisualEvidenceError("Screenshot dimensions are outside the accepted range.")
    return width, height


def _locale_list_value(locales: tuple[str, ...]) -> str:
    if len(locales) > 16:
        raise CuttlefishVisualEvidenceError("Too many app locale overrides to restore safely.")
    for locale in locales:
        if _LOCALE.fullmatch(locale) is None:
            raise CuttlefishVisualEvidenceError("App locale override contains an unsupported language tag.")
    if len(set(locales)) != len(locales):
        raise CuttlefishVisualEvidenceError("App locale override contains a duplicate language tag.")
    return ",".join(locales)


def _safe_output_root(path: Path) -> Path:
    if not path.is_absolute():
        raise CuttlefishVisualEvidenceError("Visual evidence output directory must be absolute.")
    if path.exists() or path.is_symlink():
        raise CuttlefishVisualEvidenceError("Visual evidence output directory must be new and create-only.")
    parent = path.parent.resolve(strict=True)
    if parent == Path(parent.anchor) or parent.is_symlink() or not parent.is_dir():
        raise CuttlefishVisualEvidenceError("Visual evidence parent directory is unsafe.")
    path.mkdir(mode=0o700)
    root = path.resolve(strict=True)
    if root.parent != parent or root.is_symlink():
        raise CuttlefishVisualEvidenceError("Visual evidence output directory escaped its parent.")
    return root


def _capture_name(index: int, package: str, locale: str) -> str:
    if _PACKAGE.fullmatch(package) is None or _LOCALE.fullmatch(locale) is None:
        raise CuttlefishVisualEvidenceError("Unsafe package or locale in visual capture filename.")
    return f"{index:03d}_{package}__{locale}.png"


def _write_capture(root: Path, name: str, data: bytes) -> dict[str, object]:
    width, height = parse_png_dimensions(data)
    if PurePosixPath(name).name != name or not name.endswith(".png"):
        raise CuttlefishVisualEvidenceError("Unsafe visual capture filename.")
    path = root / name
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if path.is_symlink() or not path.is_file():
        raise CuttlefishVisualEvidenceError("Visual capture was not persisted as a regular file.")
    stored = path.read_bytes()
    if stored != data:
        raise CuttlefishVisualEvidenceError("Visual capture changed after persistence.")
    return {
        "relative_path": name,
        "size": len(stored),
        "sha256": hashlib.sha256(stored).hexdigest(),
        "width": width,
        "height": height,
    }


class CuttlefishVisualEvidenceRunner:
    """Capture one screenshot for every source-ready package/locale pair."""

    def __init__(self, executable: Path, timeout: float = 20.0):
        self.evidence = CuttlefishEvidenceCollector(executable, timeout=min(timeout, 60.0))
        self.executable = self.evidence.executable
        if not 0 < timeout <= 60:
            raise CuttlefishVisualEvidenceError("ADB timeout must be between 0 and 60 seconds.")
        self.timeout = timeout

    @staticmethod
    def _environment() -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if not key.upper().startswith(("ADB_", "ANDROID_ADB_")) and key.upper() != "ANDROID_SERIAL"
        }

    def _allowed_text(self, args: tuple[str, ...]) -> bool:
        local = len(args) >= 2 and args[0] == "-s" and _LOCAL_SERIAL.fullmatch(args[1]) is not None
        current_user = local and args[2:] == ("shell", "am", "get-current-user")
        get_locale = (
            local and len(args) == 9 and args[2:6] == ("shell", "cmd", "locale", "get-app-locales")
            and _PACKAGE.fullmatch(args[6]) is not None and args[7] == "--user" and args[8].isdigit()
        )
        set_locale_empty = (
            local and len(args) == 9 and args[2:6] == ("shell", "cmd", "locale", "set-app-locales")
            and _PACKAGE.fullmatch(args[6]) is not None and args[7] == "--user" and args[8].isdigit()
        )
        set_locale_value = (
            local and len(args) == 11 and args[2:6] == ("shell", "cmd", "locale", "set-app-locales")
            and _PACKAGE.fullmatch(args[6]) is not None and args[7] == "--user" and args[8].isdigit()
            and args[9] == "--locales" and all(_LOCALE.fullmatch(tag) is not None for tag in args[10].split(","))
            and len(args[10].split(",")) <= 16
        )
        launch = local and len(args) == 8 and args[2:7] == ("shell", "am", "start", "-W", "-n") and _COMPONENT.fullmatch(args[7]) is not None
        state = local and args[2:] == ("shell", "dumpsys", "activity", "activities")
        return args == ("devices", "-l") or current_user or get_locale or set_locale_empty or set_locale_value or launch or state

    def _run_text(self, args: tuple[str, ...]) -> str:
        if not self._allowed_text(args):
            raise CuttlefishVisualEvidenceError("Command is outside the emulator-only visual evidence allowlist.")
        try:
            result = subprocess.run(
                [str(self.executable), *args], stdin=subprocess.DEVNULL, capture_output=True,
                text=True, encoding="utf-8", errors="strict", timeout=self.timeout,
                shell=False, check=False, env=self._environment(),
            )
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise CuttlefishVisualEvidenceError("ADB visual-evidence command failed or timed out; raw output is withheld.") from None
        if result.returncode != 0 or len(result.stdout) > _MAX_ADB_TEXT:
            raise CuttlefishVisualEvidenceError("ADB visual-evidence command failed or returned oversized output.")
        return result.stdout

    def _run_png(self, serial: str) -> bytes:
        if _LOCAL_SERIAL.fullmatch(serial) is None:
            raise CuttlefishVisualEvidenceError("Only a local emulator/Cuttlefish transport may be captured.")
        args = ("-s", serial, "exec-out", "screencap", "-p")
        try:
            result = subprocess.run(
                [str(self.executable), *args], stdin=subprocess.DEVNULL, capture_output=True,
                timeout=self.timeout, shell=False, check=False, env=self._environment(),
            )
        except (OSError, subprocess.SubprocessError):
            raise CuttlefishVisualEvidenceError("ADB screenshot capture failed or timed out; raw output is withheld.") from None
        if result.returncode != 0:
            raise CuttlefishVisualEvidenceError("ADB screenshot capture failed.")
        parse_png_dimensions(result.stdout)
        return result.stdout

    def _get_locales(self, serial: str, package: str, user_id: int) -> tuple[str, ...]:
        return parse_app_locales(
            self._run_text(("-s", serial, "shell", "cmd", "locale", "get-app-locales", package, "--user", str(user_id))),
            package, user_id,
        )

    def _set_locales(self, serial: str, package: str, user_id: int, locales: tuple[str, ...]) -> None:
        value = _locale_list_value(locales)
        args = ["-s", serial, "shell", "cmd", "locale", "set-app-locales", package, "--user", str(user_id)]
        if value:
            args.extend(("--locales", value))
        self._run_text(tuple(args))

    def capture(self, registry: SystemAppRegistry, output_dir: Path) -> dict[str, object]:
        runtime = self.evidence.inspect(registry)
        if runtime.get("runtime_evidence_complete") is not True or runtime.get("identity_matches") is not True:
            raise CuttlefishVisualEvidenceError("Exact complete SwirPhoneOS Cuttlefish runtime evidence is required.")
        fingerprint = runtime.get("build_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise CuttlefishVisualEvidenceError("Runtime fingerprint is missing.")

        apps = sorted((app for app in registry.apps if app.source_ready), key=lambda app: app.package)
        locales = tuple(LOCALES)
        if not apps or not locales or len(set(locales)) != len(locales):
            raise CuttlefishVisualEvidenceError("Source-ready app or locale scope is invalid.")
        root = _safe_output_root(output_dir)
        device = select_local_device(parse_local_devices(self._run_text(("devices", "-l"))))
        user_id = parse_current_user(self._run_text(("-s", device.serial, "shell", "am", "get-current-user")))

        original: dict[str, tuple[str, ...]] = {}
        captures: list[dict[str, object]] = []
        primary_error: Exception | None = None
        restore_error: Exception | None = None
        try:
            for app in apps:
                original[app.package] = self._get_locales(device.serial, app.package, user_id)
            index = 0
            for locale in locales:
                direction = LOCALES[locale].direction
                for app in apps:
                    index += 1
                    self._set_locales(device.serial, app.package, user_id, (locale,))
                    if self._get_locales(device.serial, app.package, user_id) != (locale,):
                        raise CuttlefishVisualEvidenceError("Android did not preserve the requested per-app locale override.")
                    resolved = self.evidence._run(("-s", device.serial, "shell", "cmd", "package", "resolve-activity", "--brief", app.package)).strip()
                    if not parse_resolved_activity(resolved, app.package) or _COMPONENT.fullmatch(resolved) is None:
                        raise CuttlefishVisualEvidenceError("Source-ready app has no package-local launcher activity.")
                    parse_am_start_wait(self._run_text(("-s", device.serial, "shell", "am", "start", "-W", "-n", resolved)), app.package, resolved)
                    state = self._run_text(("-s", device.serial, "shell", "dumpsys", "activity", "activities"))
                    if not foreground_contains_component(state, app.package, resolved):
                        raise CuttlefishVisualEvidenceError("App was not confirmed in the foreground before capture.")
                    record = _write_capture(root, _capture_name(index, app.package, locale), self._run_png(device.serial))
                    record.update({"package": app.package, "locale": locale, "direction": direction, "component": resolved, "foreground_confirmed": True})
                    captures.append(record)
        except Exception as exc:
            primary_error = exc
        finally:
            for package, saved in reversed(tuple(original.items())):
                try:
                    self._set_locales(device.serial, package, user_id, saved)
                    if self._get_locales(device.serial, package, user_id) != saved:
                        raise CuttlefishVisualEvidenceError("Original per-app locale override was not restored exactly.")
                except Exception as exc:
                    restore_error = exc
                    break

        if restore_error is not None:
            raise CuttlefishVisualEvidenceError("Locale restoration failed; discard/reset this disposable Cuttlefish guest.") from restore_error
        if primary_error is not None:
            if isinstance(primary_error, CuttlefishVisualEvidenceError):
                raise primary_error
            if isinstance(primary_error, (CuttlefishEvidenceError, CuttlefishSmokeError)):
                raise CuttlefishVisualEvidenceError(str(primary_error)) from primary_error
            raise CuttlefishVisualEvidenceError("Visual evidence capture failed; raw error is withheld.") from primary_error

        after = select_local_device(parse_local_devices(self._run_text(("devices", "-l"))))
        if after != device:
            raise CuttlefishVisualEvidenceError("ADB transport changed during visual evidence capture.")
        expected = len(apps) * len(locales)
        if len(captures) != expected:
            raise CuttlefishVisualEvidenceError("Visual capture matrix is incomplete.")

        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_cuttlefish_visual_capture_matrix",
            "expected_product": runtime["expected_product"],
            "build_fingerprint": fingerprint,
            "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii", "strict")).hexdigest(),
            "android_user_id": user_id,
            "tested_packages": [app.package for app in apps],
            "tested_locales": list(locales),
            "capture_count": len(captures),
            "captures": captures,
            "capture_set_sha256": _canonical_sha256(captures),
            "capture_matrix_complete": True,
            "visual_bytes_captured": True,
            "original_app_locales_restored": True,
            "rtl_runtime_switch_exercised": bool([code for code in locales if LOCALES[code].direction == "rtl"]),
            "rtl_visual_mirroring_verified": False,
            "accessibility_review_complete": False,
            "visual_translation_review_complete": False,
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True,
            "host_evidence_write_performed": True,
            "warnings": [
                "PNG captures are evidence inputs only; no automated visual-quality or RTL correctness claim is made.",
                "Per-app locale overrides and foreground state are changed only on the disposable local Cuttlefish guest and locale overrides are restored exactly.",
                "No install, system-settings write, root, reboot, flash, erase, application-status promotion, or physical-device operation is performed.",
            ],
        }
        payload["visual_capture_sha256"] = _canonical_sha256(payload)
        return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture bounded package-by-locale PNG evidence from exact local SwirPhoneOS Cuttlefish.")
    parser.add_argument("--adb", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("system_apps/manifest.json"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = CuttlefishVisualEvidenceRunner(args.adb).capture(load_registry(args.manifest), args.output_dir)
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (CuttlefishVisualEvidenceError, CuttlefishEvidenceError, CuttlefishSmokeError, SystemAppRegistryError, OSError, ValueError):
        print("Visual evidence capture failed: exact local Cuttlefish, locale restoration, foreground launch and bounded PNG capture are required.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
