"""Strictly read-only Fastboot/FastbootD inspection.

This module never issues reboot, unlock, erase, flash, format, set_active,
boot, update, wipe, OEM, flashing or snapshot commands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import subprocess

SERIAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}\Z")
GETVARS = (
    "product",
    "current-slot",
    "slot-count",
    "unlocked",
    "is-userspace",
    "secure",
)


class FastbootDiagnosticError(RuntimeError):
    """A safe Fastboot diagnostic failure without exposing raw device output."""


@dataclass(frozen=True)
class FastbootDevice:
    serial: str = field(repr=False)
    state: str = "fastboot"


def parse_fastboot_devices(output: str) -> list[FastbootDevice]:
    """Parse `fastboot devices` conservatively and reject ambiguous rows."""
    result: list[FastbootDevice] = []
    seen: set[str] = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2 or not SERIAL.fullmatch(parts[0]) or parts[1] != "fastboot":
            raise FastbootDiagnosticError("Malformed Fastboot device entry.")
        serial = parts[0]
        if serial in seen:
            raise FastbootDiagnosticError("Duplicate Fastboot device entry; selection is ambiguous.")
        seen.add(serial)
        result.append(FastbootDevice(serial=serial))
    return result


def select_fastboot_device(devices: list[FastbootDevice]) -> FastbootDevice:
    if len(devices) != 1:
        raise FastbootDiagnosticError("Connect exactly one local USB device in Fastboot/FastbootD mode.")
    device = devices[0]
    # Network Fastboot commonly uses host:port. This prototype intentionally
    # limits selection to local USB transports.
    if ":" in device.serial or device.serial.startswith("emulator-"):
        raise FastbootDiagnosticError("Network/emulator Fastboot is not accepted by this prototype.")
    return device


def _clean_value(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if len(value) > 256 or not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise FastbootDiagnosticError("Invalid Fastboot variable response.")
    return value


def parse_getvar(name: str, stdout: str, stderr: str) -> str | None:
    """Extract one requested variable without accepting unrelated device output."""
    if name not in GETVARS:
        raise FastbootDiagnosticError("Fastboot variable is outside the read-only allowlist.")
    matches: list[str] = []
    prefix = f"{name}:"
    for raw in (stdout + "\n" + stderr).splitlines():
        line = raw.strip()
        if line.startswith("(bootloader) "):
            line = line[len("(bootloader) "):].strip()
        if line.startswith(prefix):
            matches.append(line[len(prefix):].strip())
    if not matches:
        return None
    cleaned = [_clean_value(value) for value in matches]
    unique = {value for value in cleaned if value is not None}
    if len(unique) > 1:
        raise FastbootDiagnosticError("Conflicting Fastboot variable responses.")
    return next(iter(unique), None)


def summarize_fastboot(values: dict[str, str | None]) -> dict[str, object]:
    is_userspace = values.get("is-userspace")
    unlocked = values.get("unlocked")
    slot_count_raw = values.get("slot-count")
    try:
        slot_count = int(slot_count_raw) if slot_count_raw is not None else None
    except ValueError:
        slot_count = None
    if slot_count is not None and not 0 <= slot_count <= 8:
        slot_count = None
    return {
        "schema_version": 1,
        "source": "fastboot_reported_getvars_not_hardware_verification",
        "product_reported": values.get("product"),
        "transport_mode_reported": {
            "yes": "fastbootd",
            "true": "fastbootd",
            "1": "fastbootd",
            "no": "bootloader-fastboot",
            "false": "bootloader-fastboot",
            "0": "bootloader-fastboot",
        }.get(is_userspace, "unknown"),
        "bootloader_reported": {
            "yes": "unlocked",
            "true": "unlocked",
            "1": "unlocked",
            "no": "locked",
            "false": "locked",
            "0": "locked",
        }.get(unlocked, "unknown"),
        "current_slot_reported": values.get("current-slot"),
        "slot_count_reported": slot_count,
        "secure_reported": values.get("secure"),
        "swirphoneos_support": "NOT_VALIDATED",
        "flash_allowed": False,
        "warnings": [
            "Fastboot getvars are device-reported hints, not proof of model identity or compatibility.",
            "No partition layout, firmware baseline, recovery path or SwirPhoneOS image is certified by this report.",
            "No reboot, unlock, erase, flash, format, boot, relock or restore command was attempted.",
        ],
    }


class ReadOnlyFastboot:
    """Explicit trusted executable with a tiny non-mutating command allowlist."""

    def __init__(self, executable: Path, timeout: float = 10.0):
        if not executable.is_absolute():
            raise FastbootDiagnosticError("Provide an absolute path to your trusted Android SDK fastboot executable.")
        executable = executable.resolve()
        expected = "fastboot.exe" if os.name == "nt" else "fastboot"
        if executable.name.lower() != expected or not executable.is_file():
            raise FastbootDiagnosticError("Fastboot executable is missing or has an unexpected filename.")
        if not 0 < timeout <= 60:
            raise FastbootDiagnosticError("Fastboot timeout must be between 0 and 60 seconds.")
        self.executable = executable
        self.timeout = timeout

    def _run(self, args: tuple[str, ...]) -> tuple[int, str, str]:
        permitted = args == ("devices",) or (
            len(args) == 4
            and args[0] == "-s"
            and bool(SERIAL.fullmatch(args[1]))
            and args[2] == "getvar"
            and args[3] in GETVARS
        )
        if not permitted:
            raise FastbootDiagnosticError("Command is outside the read-only Fastboot allowlist.")
        env = {
            k: v
            for k, v in os.environ.items()
            if k.upper() != "ANDROID_SERIAL" and not k.upper().startswith("FASTBOOT_")
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
            raise FastbootDiagnosticError("Fastboot failed or timed out; raw output is withheld for privacy.") from None
        if len(result.stdout) + len(result.stderr) > 65536:
            raise FastbootDiagnosticError("Fastboot returned an oversized response.")
        return result.returncode, result.stdout, result.stderr

    def inspect(self) -> dict[str, object]:
        code, stdout, _ = self._run(("devices",))
        if code != 0:
            raise FastbootDiagnosticError("Fastboot device listing failed; raw output is withheld for privacy.")
        device = select_fastboot_device(parse_fastboot_devices(stdout))

        values: dict[str, str | None] = {}
        for name in GETVARS:
            code, out, err = self._run(("-s", device.serial, "getvar", name))
            # Unsupported getvars differ between bootloaders; unknown is safer
            # than treating one missing optional variable as a transport failure.
            values[name] = parse_getvar(name, out, err) if code == 0 else None

        code, after_stdout, _ = self._run(("devices",))
        if code != 0:
            raise FastbootDiagnosticError("Fastboot identity recheck failed.")
        after = select_fastboot_device(parse_fastboot_devices(after_stdout))
        if after != device:
            raise FastbootDiagnosticError("Fastboot device identity changed during inspection.")
        return summarize_fastboot(values)
