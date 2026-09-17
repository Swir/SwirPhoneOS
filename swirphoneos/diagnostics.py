"""Strictly read-only ADB inspection. Reported properties are not trusted identity."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
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
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


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


def _digest_value(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise DiagnosticError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _serial_sha256(serial: str) -> str:
    if not SERIAL.fullmatch(serial):
        raise DiagnosticError("Device serial format changed during inspection.")
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise DiagnosticError("Trusted ADB executable could not be hashed.") from exc
    return digest.hexdigest()


def summarize(
    properties: dict[str, str],
    *,
    transport_serial_sha256: str | None = None,
    tool_sha256: str | None = None,
) -> dict[str, object]:
    values = {key: _value(properties.get(key, "")) for key in PROPERTIES}
    locked = values["ro.boot.flash.locked"]
    treble = values["ro.treble.enabled"]
    return {
        "schema_version": 2,
        "source": "adb_reported_properties_not_hardware_verification",
        "transport_serial_sha256": _digest_value(transport_serial_sha256, "transport_serial_sha256"),
        "tool_sha256": _digest_value(tool_sha256, "tool_sha256"),
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
            "Properties and transport identifiers may be missing or spoofed; this is not a flashing authorization.",
            "The USB serial is not stored; only its SHA-256 digest is retained for cross-transport correlation.",
            "No backup, unlock, reboot, root, erase, flash or restore was attempted.",
        ],
    }


def validate_adb_report(report: object, *, require_provenance: bool = False) -> dict[str, object]:
    """Validate the exact exported ADB observation schema.

    `require_provenance=True` is reserved for evidence that must bind the
    observation to one enumerated transport identifier and one exact adb binary.
    Synthetic/source-only callers may leave the two digest fields unknown.
    """
    expected = summarize({})
    if not isinstance(report, dict) or set(report) != set(expected):
        raise DiagnosticError("ADB report does not match schema v2 exactly.")
    if report["schema_version"] != 2 or report["source"] != expected["source"]:
        raise DiagnosticError("ADB report provenance is invalid.")
    if report["swirphoneos_support"] != "NOT_VALIDATED" or report["flash_allowed"] is not False:
        raise DiagnosticError("ADB report cannot authorize SwirPhoneOS support or flashing.")
    if report["warnings"] != expected["warnings"]:
        raise DiagnosticError("ADB report warnings were modified.")
    for key in ("transport_serial_sha256", "tool_sha256"):
        value = report[key]
        if value is not None and (not isinstance(value, str) or not SHA256.fullmatch(value)):
            raise DiagnosticError("ADB provenance digest is invalid.")
        if require_provenance and value is None:
            raise DiagnosticError("ADB provenance digest is required for cross-transport evidence.")
    for key in ("treble_reported", "dynamic_partitions_reported"):
        if report[key] is not None and type(report[key]) is not bool:
            raise DiagnosticError("ADB reported boolean is invalid.")
    if report["bootloader_reported"] not in ("locked", "unlocked", "unknown"):
        raise DiagnosticError("ADB reported bootloader state is invalid.")
    for key in (
        "manufacturer", "model", "codename", "abi", "board_reported", "hardware_reported",
        "android_release", "build_fingerprint_reported", "reported_security_patch",
        "verified_boot_state_reported", "vbmeta_device_state_reported", "slot_reported",
        "slot_suffix_reported",
    ):
        value = report[key]
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 256
            or not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise DiagnosticError("ADB reported text value is invalid.")
    return report


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
        tool_sha256 = _file_sha256(self.executable)
        device = select_device(parse_devices(self._run(("devices", "-l"))))
        transport_serial_sha256 = _serial_sha256(device.serial)
        properties = {
            key: self._run(("-s", device.serial, "shell", "getprop", key))
            for key in PROPERTIES
        }
        after = select_device(parse_devices(self._run(("devices", "-l"))))
        if after != device:
            raise DiagnosticError("Device identity changed during inspection.")
        if _file_sha256(self.executable) != tool_sha256:
            raise DiagnosticError("Trusted ADB executable changed during inspection.")
        return summarize(
            properties,
            transport_serial_sha256=transport_serial_sha256,
            tool_sha256=tool_sha256,
        )
