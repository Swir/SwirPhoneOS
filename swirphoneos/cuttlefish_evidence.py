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
EXPECTED_DEVICE = "vsoc_x86_64_only"
EXPECTED_MANUFACTURER = "Swir"
EXPECTED_ANDROID_RELEASE = "17"
EXPECTED_API_LEVEL = "37"
EXPECTED_BUILD_TYPE = "userdebug"
_PROPERTIES = (
    "sys.boot_completed",
    "ro.product.name",
    "ro.product.device",
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.build.fingerprint",
    "ro.build.id",
    "ro.build.type",
    "ro.build.tags",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "persist.sys.locale",
)
_LOCAL_SERIAL = re.compile(r"(?:emulator-[0-9]{1,5}|(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5})\Z")
_PACKAGE = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+\Z")
_COMPONENT = re.compile(r"([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)/(\.?[A-Za-z0-9_.$]+)\Z")


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
    result = []
    seen = set()
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
    result = set()
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


def parse_resolved_activity(output: str, expected_package: str) -> bool:
    if not _PACKAGE.fullmatch(expected_package):
        raise CuttlefishEvidenceError("Invalid package requested for launcher evidence.")
    value = output.strip()
    if not value or value == "No activity found":
        return False
    if "\n" in value or len(value) > 512:
        raise CuttlefishEvidenceError("Launcher-resolution response is malformed.")
    match = _COMPONENT.fullmatch(value)
    if not match or match.group(1) != expected_package:
        raise CuttlefishEvidenceError("Launcher resolved outside the expected package.")
    return True


def _property(raw: str, limit: int = 512) -> str | None:
    value = raw.strip()
    if not value:
        return None
    if len(value) > limit or not value.isascii() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise CuttlefishEvidenceError("Runtime property is malformed.")
    return value


def evaluate_runtime_snapshot(properties: dict[str, str], packages: frozenset[str], registry: SystemAppRegistry, launchable_packages: frozenset[str] | None = None) -> dict[str, object]:
    values = {key: _property(properties.get(key, "")) for key in _PROPERTIES}
    required = sorted(app.package for app in registry.first_beta_apps)
    present = [p for p in required if p in packages]
    missing = [p for p in required if p not in packages]
    launchable = packages if launchable_packages is None else launchable_packages
    present_launchers = [p for p in required if p in launchable]
    missing_launchers = [p for p in required if p not in launchable]
    product = values["ro.product.name"]
    fingerprint = values["ro.build.fingerprint"]
    identity_checks = {
        "product": product == EXPECTED_PRODUCT,
        "device": values["ro.product.device"] == EXPECTED_DEVICE,
        "manufacturer": values["ro.product.manufacturer"] == EXPECTED_MANUFACTURER,
        "android_release": values["ro.build.version.release"] == EXPECTED_ANDROID_RELEASE,
        "api_level": values["ro.build.version.sdk"] == EXPECTED_API_LEVEL,
        "build_type": values["ro.build.type"] == EXPECTED_BUILD_TYPE,
        "build_id_present": bool(values["ro.build.id"]),
    }
    identity_matches = all(identity_checks.values())
    boot_completed = values["sys.boot_completed"] == "1"
    digest = hashlib.sha256(fingerprint.encode("ascii")).hexdigest() if fingerprint else None
    complete = bool(boot_completed and identity_matches and fingerprint and not missing and not missing_launchers)
    return {
        "schema_version": 3,
        "source": "local_cuttlefish_read_only_adb",
        "expected_product": EXPECTED_PRODUCT,
        "reported_product": product,
        "reported_device": values["ro.product.device"],
        "reported_manufacturer": values["ro.product.manufacturer"],
        "reported_model": values["ro.product.model"],
        "identity_checks": identity_checks,
        "identity_matches": identity_matches,
        "boot_completed": boot_completed,
        "android_release": values["ro.build.version.release"],
        "api_level": values["ro.build.version.sdk"],
        "build_id": values["ro.build.id"],
        "build_type": values["ro.build.type"],
        "build_tags": values["ro.build.tags"],
        "reported_security_patch": values["ro.build.version.security_patch"],
        "locale": values["persist.sys.locale"],
        "build_fingerprint": fingerprint,
        "build_fingerprint_sha256": digest,
        "required_source_ready_packages": required,
        "present_required_packages": present,
        "missing_required_packages": missing,
        "present_launchable_packages": present_launchers,
        "missing_launchable_packages": missing_launchers,
        "runtime_evidence_complete": complete,
        "status_promotion_performed": False,
        "device_write_allowed": False,
        "warnings": [
            "This report is emulator runtime evidence only; it is not physical-device compatibility evidence.",
            "First-Beta package presence and launcher resolution do not prove every app feature; interactive runtime testing remains required.",
            "Post-Beta source-ready apps are intentionally non-blocking while the frozen first-Beta scope is active.",
            "No registry status is promoted automatically; evidence must be reviewed with the exact build manifest and artifact hashes.",
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
        permitted = (
            args == ("devices", "-l")
            or (local and len(args) == 5 and args[2:4] == ("shell", "getprop") and args[4] in _PROPERTIES)
            or (local and args[2:] == ("shell", "cmd", "package", "list", "packages"))
            or (local and len(args) == 8 and args[2:7] == ("shell", "cmd", "package", "resolve-activity", "--brief") and bool(_PACKAGE.fullmatch(args[7])))
        )
        if not permitted:
            raise CuttlefishEvidenceError("Command is outside the read-only Cuttlefish evidence allowlist.")
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("ADB_", "ANDROID_ADB_")) and k.upper() != "ANDROID_SERIAL"}
        try:
            result = subprocess.run([str(self.executable), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="strict", timeout=self.timeout, shell=False, check=False, env=env)
        except (OSError, subprocess.SubprocessError, UnicodeError):
            raise CuttlefishEvidenceError("ADB evidence capture failed or timed out; raw output is withheld.") from None
        if result.returncode != 0:
            raise CuttlefishEvidenceError("ADB evidence command failed; raw output is withheld.")
        if len(result.stdout) > 1_000_000:
            raise CuttlefishEvidenceError("ADB evidence response is oversized.")
        return result.stdout

    def inspect(self, registry: SystemAppRegistry) -> dict[str, object]:
        device = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        properties = {key: self._run(("-s", device.serial, "shell", "getprop", key)) for key in _PROPERTIES}
        packages = parse_packages(self._run(("-s", device.serial, "shell", "cmd", "package", "list", "packages")))
        required = sorted(app.package for app in registry.first_beta_apps)
        launchable = set()
        for package in required:
            output = self._run(("-s", device.serial, "shell", "cmd", "package", "resolve-activity", "--brief", package))
            if parse_resolved_activity(output, package):
                launchable.add(package)
        after = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        if after != device:
            raise CuttlefishEvidenceError("ADB transport changed during evidence capture.")
        return evaluate_runtime_snapshot(properties, packages, registry, frozenset(launchable))
