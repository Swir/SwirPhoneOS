"""Read-only runtime evidence capture for a local SwirPhoneOS Cuttlefish instance."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import re
import subprocess

from .system_apps import SystemAppRegistry

EXPECTED_PRODUCT = "swirphoneos_cf_x86_64"
_PROPERTIES = (
    "sys.boot_completed",
    "ro.product.name",
    "ro.build.fingerprint",
    "ro.build.version.release",
    "ro.build.version.security_patch",
    "persist.sys.locale",
)
_LOCAL_SERIAL = re.compile(r"(?:emulator-[0-9]{1,5}|(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5})\Z")
_PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\Z")


class CuttlefishEvidenceError(RuntimeError):
    """Raised when local emulator evidence is malformed, ambiguous or unsafe to collect."""


@dataclass(frozen=True)
class CuttlefishDevice:
    serial: str = field(repr=False)
    state: str


def parse_local_devices(output: str) -> list[CuttlefishDevice]:
    if len(output) > 65_536:
        raise CuttlefishEvidenceError("ADB device list is oversized.")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines or lines[0] != "List of devices attached":
        raise CuttlefishEvidenceError("Invalid ADB device-list response.")
    result: list[CuttlefishDevice] = []
    seen: set[str] = set()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 2 or not _LOCAL_SERIAL.fullmatch(parts[0]):
            raise CuttlefishEvidenceError("Only a local emulator/Cuttlefish ADB transport is accepted.")
        serial, state = parts[:2]
        if serial in seen:
            raise CuttlefishEvidenceError("Duplicate ADB transport makes evidence ambiguous.")
        seen.add(serial)
        result.append(CuttlefishDevice(serial, state))
    return result


def select_local_device(devices: list[CuttlefishDevice]) -> CuttlefishDevice:
    if len(devices) != 1:
        raise CuttlefishEvidenceError("Exactly one local emulator/Cuttlefish transport is required.")
    if devices[0].state != "device":
        raise CuttlefishEvidenceError("The local emulator/Cuttlefish transport is not online.")
    return devices[0]


def parse_packages(output: str) -> frozenset[str]:
    if len(output) > 1_000_000:
        raise CuttlefishEvidenceError("Package inventory is oversized.")
    result: set[str] = set()
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("package:"):
            raise CuttlefishEvidenceError("Package inventory contains an unexpected line.")
        package = line[len("package:"):]
        if not _PACKAGE.fullmatch(package):
            raise CuttlefishEvidenceError("Package inventory contains an invalid package name.")
        result.add(package)
    return frozenset(result)


def _property(raw: str, limit: int = 512) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if len(value) > limit or not value.isascii() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise CuttlefishEvidenceError("Runtime property is malformed.")
    return value


def evaluate_runtime_snapshot(properties: dict[str, str], packages: frozenset[str], registry: SystemAppRegistry) -> dict[str, object]:
    values = {key: _property(properties.get(key, "")) for key in _PROPERTIES}
    required = sorted(app.package for app in registry.apps if app.source_ready)
    present = [package for package in required if package in packages]
    missing = [package for package in required if package not in packages]
    product = values["ro.product.name"]
    fingerprint = values["ro.build.fingerprint"]
    boot_completed = values["sys.boot_completed"] == "1"
    product_matches = product == EXPECTED_PRODUCT
    fingerprint_sha256 = hashlib.sha256(fingerprint.encode("ascii")).hexdigest() if fingerprint else None
    complete = bool(boot_completed and product_matches and fingerprint and not missing)
    return {
        "schema_version": 1,
        "source": "local_cuttlefish_read_only_adb",
        "expected_product": EXPECTED_PRODUCT,
        "reported_product": product,
        "product_matches": product_matches,
        "boot_completed": boot_completed,
        "android_release": values["ro.build.version.release"],
        "reported_security_patch": values["ro.build.version.security_patch"],
        "locale": values["persist.sys.locale"],
        "build_fingerprint": fingerprint,
        "build_fingerprint_sha256": fingerprint_sha256,
        "required_source_ready_packages": required,
        "present_required_packages": present,
        "missing_required_packages": missing,
        "runtime_evidence_complete": complete,
        "status_promotion_performed": False,
        "device_write_allowed": False,
        "warnings": [
            "This report is emulator runtime evidence only; it is not physical-device compatibility evidence.",
            "No registry status is promoted automatically; evidence must be reviewed with the exact build manifest and CI artifacts.",
            "No install, root, flash, reboot, package mutation or other device write was attempted.",
        ],
    }


class CuttlefishEvidenceCollector:
    """Strict read-only ADB collector limited to a single local emulator transport."""

    def __init__(self, executable: Path, timeout: float = 10.0):
        if not executable.is_absolute():
            raise CuttlefishEvidenceError("Provide an absolute path to a trusted Android SDK adb executable.")
        executable = executable.resolve()
        expected = "adb.exe" if os.name == "nt" else "adb"
        if executable.name.lower() != expected or not executable.is_file():
            raise CuttlefishEvidenceError("ADB executable is missing or has an unexpected filename.")
        if not 0 < timeout <= 60:
            raise CuttlefishEvidenceError("ADB timeout must be between 0 and 60 seconds.")
        self.executable = executable
        self.timeout = timeout

    def _run(self, args: tuple[str, ...]) -> str:
        local = len(args) >= 2 and args[0] == "-s" and bool(_LOCAL_SERIAL.fullmatch(args[1]))
        permitted = args == ("devices", "-l") or (
            local and len(args) == 5 and args[2:4] == ("shell", "getprop") and args[4] in _PROPERTIES
        ) or (
            local and len(args) == 7 and args[2:] == ("shell", "cmd", "package", "list", "packages")
        )
        if not permitted:
            raise CuttlefishEvidenceError("Command is outside the read-only Cuttlefish evidence allowlist.")
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith(("ADB_", "ANDROID_ADB_")) and key.upper() != "ANDROID_SERIAL"}
        try:
            result = subprocess.run(
                [str(self.executable), *args], stdin=subprocess.DEVNULL,
                capture_output=True, text=True, encoding="utf-8", errors="strict",
                timeout=self.timeout, shell=False, check=False, env=env,
            )
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise CuttlefishEvidenceError("ADB evidence capture failed or timed out; raw output is withheld.") from None
        if result.returncode != 0:
            raise CuttlefishEvidenceError("ADB evidence command failed; raw output is withheld.")
        if len(result.stdout) > 1_000_000:
            raise CuttlefishEvidenceError("ADB evidence response is oversized.")
        return result.stdout

    def inspect(self, registry: SystemAppRegistry) -> dict[str, object]:
        device = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        properties = {
            key: self._run(("-s", device.serial, "shell", "getprop", key))
            for key in _PROPERTIES
        }
        packages = parse_packages(self._run(("-s", device.serial, "shell", "cmd", "package", "list", "packages")))
        after = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        if after != device:
            raise CuttlefishEvidenceError("ADB transport changed during evidence capture.")
        return evaluate_runtime_snapshot(properties, packages, registry)
