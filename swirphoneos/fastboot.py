"""Strictly read-only Fastboot/FastbootD inspection.

This module never issues reboot, unlock, erase, flash, format, set_active,
boot, update, wipe, OEM, flashing or snapshot commands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import hashlib
import os
import re
import subprocess

SERIAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GETVARS = (
    "product",
    "current-slot",
    "slot-count",
    "unlocked",
    "is-userspace",
    "secure",
)
PARTITIONS = (
    "boot", "init_boot", "vendor_boot", "dtbo", "vbmeta", "vbmeta_system",
    "vbmeta_vendor", "super", "system", "system_ext", "product", "vendor",
    "odm", "recovery", "userdata",
)
PARTITION_GETVARS = tuple(
    item
    for partition in PARTITIONS
    for item in (f"has-slot:{partition}", f"partition-size:{partition}")
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


def _digest_value(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise FastbootDiagnosticError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _serial_sha256(serial: str) -> str:
    if not SERIAL.fullmatch(serial):
        raise FastbootDiagnosticError("Fastboot serial format changed during inspection.")
    return hashlib.sha256(serial.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise FastbootDiagnosticError("Trusted Fastboot executable could not be hashed.") from exc
    return digest.hexdigest()


def _allowed_getvar(name: str) -> bool:
    return name in GETVARS or name in PARTITION_GETVARS


def parse_getvar(name: str, stdout: str, stderr: str) -> str | None:
    """Extract one requested variable without accepting unrelated device output."""
    if not _allowed_getvar(name):
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


def _reported_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return {
        "yes": True, "true": True, "1": True,
        "no": False, "false": False, "0": False,
    }.get(value.casefold())


def _partition_size(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        size = int(value, 16) if value.lower().startswith("0x") else int(value, 10)
    except ValueError:
        return None
    return size if 0 < size <= (16 * 1024 * 1024 * 1024 * 1024) else None


def _partition_hints(values: dict[str, str | None]) -> list[dict[str, object]]:
    hints: list[dict[str, object]] = []
    for partition in PARTITIONS:
        has_slot = _reported_bool(values.get(f"has-slot:{partition}"))
        size = _partition_size(values.get(f"partition-size:{partition}"))
        if has_slot is not None or size is not None:
            hints.append({
                "name": partition,
                "has_slot_reported": has_slot,
                "size_bytes_reported": size,
            })
    return hints


def summarize_fastboot(
    values: dict[str, str | None],
    *,
    transport_serial_sha256: str | None = None,
    tool_sha256: str | None = None,
) -> dict[str, object]:
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
        "schema_version": 3,
        "source": "fastboot_reported_getvars_not_hardware_verification",
        "transport_serial_sha256": _digest_value(transport_serial_sha256, "transport_serial_sha256"),
        "tool_sha256": _digest_value(tool_sha256, "tool_sha256"),
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
        "partition_hints_reported": _partition_hints(values),
        "swirphoneos_support": "NOT_VALIDATED",
        "flash_allowed": False,
        "warnings": [
            "Fastboot getvars and transport identifiers are device-reported hints, not proof of model identity or compatibility.",
            "The USB serial is not stored; only its SHA-256 digest is retained for cross-transport correlation.",
            "No reboot, unlock, erase, flash, format, boot, relock or restore command was attempted.",
        ],
    }


def validate_fastboot_report(report: object, *, require_provenance: bool = False) -> dict[str, object]:
    expected = summarize_fastboot({})
    if not isinstance(report, dict) or set(report) != set(expected):
        raise FastbootDiagnosticError("Fastboot report does not match schema v3 exactly.")
    if report["schema_version"] != 3 or report["source"] != expected["source"]:
        raise FastbootDiagnosticError("Fastboot report provenance is invalid.")
    if report["swirphoneos_support"] != "NOT_VALIDATED" or report["flash_allowed"] is not False:
        raise FastbootDiagnosticError("Fastboot report cannot authorize SwirPhoneOS support or flashing.")
    if report["warnings"] != expected["warnings"]:
        raise FastbootDiagnosticError("Fastboot report warnings were modified.")
    for key in ("transport_serial_sha256", "tool_sha256"):
        value = report[key]
        if value is not None and (not isinstance(value, str) or not SHA256.fullmatch(value)):
            raise FastbootDiagnosticError("Fastboot provenance digest is invalid.")
        if require_provenance and value is None:
            raise FastbootDiagnosticError("Fastboot provenance digest is required for cross-transport evidence.")
    for key in ("product_reported", "current_slot_reported", "secure_reported"):
        value = report[key]
        if value is not None and (
            not isinstance(value, str) or not value or len(value) > 256
            or not value.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in value)
        ):
            raise FastbootDiagnosticError("Fastboot reported text value is invalid.")
    if report["transport_mode_reported"] not in ("fastbootd", "bootloader-fastboot", "unknown"):
        raise FastbootDiagnosticError("Fastboot transport mode is invalid.")
    if report["bootloader_reported"] not in ("locked", "unlocked", "unknown"):
        raise FastbootDiagnosticError("Fastboot bootloader state is invalid.")
    slot_count = report["slot_count_reported"]
    if slot_count is not None and (type(slot_count) is not int or not 0 <= slot_count <= 8):
        raise FastbootDiagnosticError("Fastboot slot count is invalid.")
    hints = report["partition_hints_reported"]
    if not isinstance(hints, list) or len(hints) > len(PARTITIONS):
        raise FastbootDiagnosticError("Fastboot partition hints are invalid.")
    seen: set[str] = set()
    for item in hints:
        if not isinstance(item, dict) or set(item) != {"name", "has_slot_reported", "size_bytes_reported"}:
            raise FastbootDiagnosticError("Fastboot partition hint schema is invalid.")
        name = item["name"]
        has_slot = item["has_slot_reported"]
        size = item["size_bytes_reported"]
        if name not in PARTITIONS or name in seen:
            raise FastbootDiagnosticError("Fastboot partition hint name is invalid or duplicated.")
        seen.add(name)
        if has_slot is not None and type(has_slot) is not bool:
            raise FastbootDiagnosticError("Fastboot partition slot hint is invalid.")
        if size is not None and (type(size) is not int or not 0 < size <= 16 * 1024**4):
            raise FastbootDiagnosticError("Fastboot partition size hint is invalid.")
    return report


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
            and _allowed_getvar(args[3])
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

    def inspect(self, *, include_partitions: bool = False) -> dict[str, object]:
        tool_sha256 = _file_sha256(self.executable)
        code, stdout, _ = self._run(("devices",))
        if code != 0:
            raise FastbootDiagnosticError("Fastboot device listing failed; raw output is withheld for privacy.")
        device = select_fastboot_device(parse_fastboot_devices(stdout))
        transport_serial_sha256 = _serial_sha256(device.serial)

        names = (*GETVARS, *PARTITION_GETVARS) if include_partitions else GETVARS
        values: dict[str, str | None] = {}
        for name in names:
            code, out, err = self._run(("-s", device.serial, "getvar", name))
            values[name] = parse_getvar(name, out, err) if code == 0 else None

        code, after_stdout, _ = self._run(("devices",))
        if code != 0:
            raise FastbootDiagnosticError("Fastboot identity recheck failed.")
        after = select_fastboot_device(parse_fastboot_devices(after_stdout))
        if after != device:
            raise FastbootDiagnosticError("Fastboot device identity changed during inspection.")
        if _file_sha256(self.executable) != tool_sha256:
            raise FastbootDiagnosticError("Trusted Fastboot executable changed during inspection.")
        return summarize_fastboot(
            values,
            transport_serial_sha256=transport_serial_sha256,
            tool_sha256=tool_sha256,
        )
