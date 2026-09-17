"""Strictly read-only ADB inspection. Reported properties are not trusted identity."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
import re
import subprocess

PROPERTIES = (
    "ro.product.manufacturer", "ro.product.model", "ro.product.device",
    "ro.product.cpu.abi", "ro.product.board", "ro.boot.hardware",
    "ro.treble.enabled", "ro.boot.flash.locked", "ro.boot.verifiedbootstate",
    "ro.boot.vbmeta.device_state", "ro.boot.slot", "ro.boot.slot_suffix",
    "ro.boot.dynamic_partitions", "ro.build.fingerprint",
    "ro.build.version.release", "ro.build.version.security_patch",
)
SERIAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}\Z")


class DiagnosticError(RuntimeError):
    """A safe diagnostic failure without command output or private identifiers."""


@dataclass(frozen=True)
class Device:
    serial: str = field(repr=False)
    state: str


def parse_devices(output: str) -> list[Device]:
    """Require a complete ADB device list; never silently skip malformed rows."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or lines[0] != "List of devices attached":
        raise DiagnosticError("Invalid ADB device-list response.")
    result: list[Device] = []
    seen: set[str] = set()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2 or not SERIAL.fullmatch(parts[0]):
            raise DiagnosticError("Malformed ADB device entry.")
        serial, state = parts[:2]
        if serial in seen:
            raise DiagnosticError("Duplicate device entry; selection is ambiguous.")
        seen.add(serial)
        result.append(Device(serial, state))
    return result


def select_device(devices: list[Device]) -> Device:
    # Even a second unauthorized/offline phone makes automatic selection unsafe.
    if len(devices) != 1:
        raise DiagnosticError("Connect exactly one Android device and disconnect emulators.")
    device = devices[0]
    if device.state != "device":
        raise DiagnosticError("Device is not online and authorized. Check USB debugging on the phone.")
    if device.serial.startswith("emulator-") or ":" in device.serial:
        raise DiagnosticError("This prototype accepts a single local USB phone, not emulator/network ADB.")
    return device


def _value(raw: str) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if len(value) > 256 or not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise DiagnosticError("Invalid or multiline property response.")
    return value


def summarize(properties: dict[str, str]) -> dict[str, object]:
    values = {key: _value(properties.get(key, "")) for key in PROPERTIES}
    locked = values["ro.boot.flash.locked"]
    treble = values["ro.treble.enabled"]
    return {
        "schema_version": 2,
        "source": "adb_reported_properties_not_hardware_verification",
        "manufacturer": values["ro.product.manufacturer"],
        "model": values["ro.product.model"],
        "codename": values["ro.product.device"],
        "abi": values["ro.product.cpu.abi"],
        "board_reported": values["ro.product.board"],
        "hardware_reported": values["ro.boot.hardware"],
        "android_release": values["ro.build.version.release"],
        "build_fingerprint_reported": values["ro.build.fingerprint"],
        "reported_security_patch": values["ro.build.version.security_patch"],
        "treble_reported": {"true": True, "false": False}.get(treble),
        "bootloader_reported": {"0": "unlocked", "1": "locked"}.get(locked, "unknown"),
        "verified_boot_state_reported": values["ro.boot.verifiedbootstate"],
        "vbmeta_device_state_reported": values["ro.boot.vbmeta.device_state"],
        "slot_reported": values["ro.boot.slot"],
        "slot_suffix_reported": values["ro.boot.slot_suffix"],
        "dynamic_partitions_reported": {"true": True, "false": False}.get(values["ro.boot.dynamic_partitions"]),
        "swirphoneos_support": "NOT_VALIDATED",
        "flash_allowed": False,
        "warnings": [
            "Properties may be missing or spoofed; this is not a flashing authorization.",
            "No device, firmware baseline or partition layout is certified by this report.",
            "No backup, unlock, reboot, root, erase, flash or restore was attempted.",
        ],
    }


class ReadOnlyAdb:
    """Explicit trusted executable only; no PATH lookup and no arbitrary commands."""

    def __init__(self, executable: Path, timeout: float = 10.0):
        if not executable.is_absolute():
            raise DiagnosticError("Provide an absolute path to your trusted Android SDK adb executable.")
        executable = executable.resolve()
        expected = "adb.exe" if os.name == "nt" else "adb"
        if executable.name.lower() != expected or not executable.is_file():
            raise DiagnosticError("ADB executable is missing or has an unexpected filename.")
        if not 0 < timeout <= 60:
            raise DiagnosticError("ADB timeout must be between 0 and 60 seconds.")
        self.executable = executable
        self.timeout = timeout

    def _run(self, args: tuple[str, ...]) -> str:
        permitted = args == ("devices", "-l") or (
            len(args) == 5 and args[0] == "-s" and bool(SERIAL.fullmatch(args[1]))
            and args[2:4] == ("shell", "getprop") and args[4] in PROPERTIES
        )
        if not permitted:
            raise DiagnosticError("Command is outside the read-only allowlist.")
        # Ignore inherited remote-server/selection configuration. ADB may start
        # its local server, but this module never requests a device write.
        env = {k: v for k, v in os.environ.items()
               if not k.upper().startswith(("ADB_", "ANDROID_ADB_"))
               and k.upper() != "ANDROID_SERIAL"}
        try:
            result = subprocess.run(
                [str(self.executable), *args], stdin=subprocess.DEVNULL,
                capture_output=True, text=True, encoding="utf-8", errors="strict",
                timeout=self.timeout, shell=False, check=False, env=env,
            )
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise DiagnosticError("ADB failed or timed out; raw output is withheld for privacy.") from None
        if result.returncode != 0:
            raise DiagnosticError("ADB returned an error; raw output is withheld for privacy.")
        if len(result.stdout) > 65536:
            raise DiagnosticError("ADB returned an oversized response.")
        return result.stdout

    def inspect(self) -> dict[str, object]:
        device = select_device(parse_devices(self._run(("devices", "-l"))))
        properties = {
            key: self._run(("-s", device.serial, "shell", "getprop", key))
            for key in PROPERTIES
        }
        after = select_device(parse_devices(self._run(("devices", "-l"))))
        if after != device:
            raise DiagnosticError("Device identity changed during inspection.")
        return summarize(properties)
