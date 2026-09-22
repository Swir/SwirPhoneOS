"""Emulator-only HOME and application launch smoke evidence for SwirPhoneOS."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import argparse
import json
import sys

from .cuttlefish_evidence import (
    CuttlefishEvidenceCollector,
    CuttlefishEvidenceError,
    parse_local_devices,
    parse_resolved_activity,
    select_local_device,
)
from .system_apps import SystemAppRegistry, SystemAppRegistryError, load_registry

_COMPONENT = re.compile(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+/(?:\.?[A-Za-z0-9_.$]+)\Z")
_STATUS_LINE = re.compile(r"Status:\s*(\S+)\s*\Z")
_ACTIVITY_LINE = re.compile(r"Activity:\s*(\S+)\s*\Z")
_RESUMED_MARKERS = ("mResumedActivity", "topResumedActivity", "ResumedActivity")
_MAX_ADB_OUTPUT = 4 * 1024 * 1024
EXPECTED_HOME_PACKAGE = "org.swir.phoneos.launcher"
_HOME_ACTION = "android.intent.action.MAIN"
_HOME_CATEGORY = "android.intent.category.HOME"


class CuttlefishSmokeError(RuntimeError):
    """Raised when an emulator-only HOME/app launch smoke check is unsafe or fails."""


@dataclass(frozen=True)
class LaunchResult:
    package: str
    component: str
    status: str
    foreground_confirmed: bool


def _clean_component(value: str, expected_package: str) -> str:
    component = value.strip()
    if not parse_resolved_activity(component, expected_package):
        raise CuttlefishSmokeError("Expected package has no package-local launchable activity.")
    if not _COMPONENT.fullmatch(component):
        raise CuttlefishSmokeError("Resolved launcher component is malformed.")
    return component


def parse_am_start_wait(output: str, expected_package: str, expected_component: str) -> str:
    """Validate bounded `am start -W` output without trusting free-form shell text."""
    if len(output) > 65_536:
        raise CuttlefishSmokeError("Activity launch response is oversized.")
    status = None
    activity = None
    complete = False
    for raw in output.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = _STATUS_LINE.fullmatch(line)
        if match:
            status = match.group(1)
            continue
        match = _ACTIVITY_LINE.fullmatch(line)
        if match:
            activity = match.group(1)
            continue
        if line == "Complete":
            complete = True
    if status != "ok" or not complete:
        raise CuttlefishSmokeError("Android did not report a completed successful activity launch.")
    if activity is not None:
        if not _COMPONENT.fullmatch(activity) or not activity.startswith(expected_package + "/"):
            raise CuttlefishSmokeError("Android reported a launched activity outside the expected package.")
        if activity != expected_component:
            expected_class = expected_component.split("/", 1)[1].lstrip(".")
            actual_class = activity.split("/", 1)[1].lstrip(".")
            if actual_class != expected_class and not actual_class.endswith("." + expected_class):
                raise CuttlefishSmokeError("Android launched an unexpected activity.")
    return status


def foreground_contains_component(output: str, package: str, component: str) -> bool:
    if len(output) > _MAX_ADB_OUTPUT:
        raise CuttlefishSmokeError("Activity-state response is oversized.")
    if not package or not component:
        return False
    for raw in output.splitlines():
        line = raw.strip()
        if any(marker in line for marker in _RESUMED_MARKERS):
            if package in line and (component in line or component.split("/", 1)[1].lstrip(".") in line):
                return True
    return False


class CuttlefishAppSmokeRunner:
    """Verify the exact Swir HOME surface, then launch every source-ready app."""
    def __init__(self, executable: Path, timeout: float = 15.0):
        self.evidence = CuttlefishEvidenceCollector(executable, timeout=min(timeout, 60.0))
        self.executable = self.evidence.executable
        if not 0 < timeout <= 60:
            raise CuttlefishSmokeError("ADB timeout must be between 0 and 60 seconds.")
        self.timeout = timeout

    def _run(self, args: tuple[str, ...]) -> str:
        local = len(args) >= 2 and args[0] == "-s" and bool(
            re.fullmatch(r"(?:emulator-[0-9]{1,5}|(?:127\.0\.0\.1|localhost|0\.0\.0\.0):[0-9]{2,5})", args[1])
        )
        component_launch = (
            local
            and len(args) == 8
            and args[2:7] == ("shell", "am", "start", "-W", "-n")
            and bool(_COMPONENT.fullmatch(args[7]))
        )
        home_resolution = (
            local
            and args[2:] == (
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "-a",
                _HOME_ACTION,
                "-c",
                _HOME_CATEGORY,
            )
        )
        permitted = (
            args == ("devices", "-l")
            or component_launch
            or home_resolution
            or (local and args[2:] == ("shell", "dumpsys", "activity", "activities"))
        )
        if not permitted:
            raise CuttlefishSmokeError("Command is outside the emulator-only app-smoke allowlist.")
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
            raise CuttlefishSmokeError("ADB app-smoke command failed or timed out; raw output is withheld.") from None
        if result.returncode != 0:
            raise CuttlefishSmokeError("ADB app-smoke command failed; raw output is withheld.")
        if len(result.stdout) > _MAX_ADB_OUTPUT:
            raise CuttlefishSmokeError("ADB app-smoke response is oversized.")
        return result.stdout

    def exercise(self, registry: SystemAppRegistry) -> dict[str, object]:
        runtime = self.evidence.inspect(registry)
        if runtime.get("runtime_evidence_complete") is not True or runtime.get("identity_matches") is not True:
            raise CuttlefishSmokeError("Exact SwirPhoneOS Cuttlefish runtime evidence must be complete before launch smoke.")

        device = select_local_device(parse_local_devices(self._run(("devices", "-l"))))

        home_resolution = self._run(
            (
                "-s",
                device.serial,
                "shell",
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "-a",
                _HOME_ACTION,
                "-c",
                _HOME_CATEGORY,
            )
        )
        home_component = _clean_component(home_resolution, EXPECTED_HOME_PACKAGE)
        home_launch_output = self._run(
            ("-s", device.serial, "shell", "am", "start", "-W", "-n", home_component)
        )
        home_status = parse_am_start_wait(home_launch_output, EXPECTED_HOME_PACKAGE, home_component)
        home_activity_state = self._run(
            ("-s", device.serial, "shell", "dumpsys", "activity", "activities")
        )
        home_foreground = foreground_contains_component(
            home_activity_state,
            EXPECTED_HOME_PACKAGE,
            home_component,
        )
        if not home_foreground:
            raise CuttlefishSmokeError("SwirLauncher resolved as HOME but was not confirmed as the resumed foreground activity.")

        source_apps = sorted((app for app in registry.apps if app.source_ready), key=lambda app: app.package)
        results: list[LaunchResult] = []
        for app in source_apps:
            resolution = self.evidence._run(
                ("-s", device.serial, "shell", "cmd", "package", "resolve-activity", "--brief", app.package)
            )
            component = _clean_component(resolution, app.package)
            launch_output = self._run(
                ("-s", device.serial, "shell", "am", "start", "-W", "-n", component)
            )
            status = parse_am_start_wait(launch_output, app.package, component)
            activity_state = self._run(
                ("-s", device.serial, "shell", "dumpsys", "activity", "activities")
            )
            foreground = foreground_contains_component(activity_state, app.package, component)
            if not foreground:
                raise CuttlefishSmokeError("Launched source-ready app was not confirmed as the resumed foreground activity.")
            results.append(LaunchResult(app.package, component, status, foreground))

        after = select_local_device(parse_local_devices(self._run(("devices", "-l"))))
        if after != device:
            raise CuttlefishSmokeError("ADB transport changed during app smoke testing.")

        fingerprint = str(runtime.get("build_fingerprint") or "")
        if not fingerprint:
            raise CuttlefishSmokeError("Runtime fingerprint is missing from prerequisite evidence.")
        home_complete = home_status == "ok" and home_foreground
        return {
            "schema_version": 1,
            "source": "local_cuttlefish_emulator_app_launch_smoke",
            "expected_product": runtime["expected_product"],
            "build_fingerprint": fingerprint,
            "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii")).hexdigest(),
            "home_package": EXPECTED_HOME_PACKAGE,
            "home_component": home_component,
            "home_resolved": True,
            "home_am_start_status": home_status,
            "home_foreground_confirmed": home_foreground,
            "home_surface_complete": home_complete,
            "tested_packages": [result.package for result in results],
            "launch_results": [
                {
                    "package": result.package,
                    "component": result.component,
                    "am_start_status": result.status,
                    "foreground_confirmed": result.foreground_confirmed,
                }
                for result in results
            ],
            "app_smoke_complete": home_complete and len(results) == len(source_apps) and all(result.foreground_confirmed for result in results),
            "status_promotion_performed": False,
            "physical_device_support_claimed": False,
            "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True,
            "warnings": [
                "This check first requires SwirLauncher to resolve as the exact HOME activity, then changes only transient emulator foreground activity state by launching already-installed apps.",
                "It is hard-gated on exact local SwirPhoneOS Cuttlefish identity and is not permitted for physical-device evidence.",
                "Successful HOME/app launch smoke does not prove every app feature, accessibility flow, locale switch or hardware integration.",
                "No package install, root, reboot, flash, erase, settings mutation or registry status promotion is performed.",
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify SwirLauncher HOME and launch-smoke source-ready apps on one exact local SwirPhoneOS Cuttlefish instance."
    )
    parser.add_argument("--adb", required=True, type=Path, help="Absolute path to a trusted Android SDK adb executable")
    parser.add_argument("--manifest", type=Path, default=Path("system_apps/manifest.json"))
    args = parser.parse_args(argv)
    try:
        report = CuttlefishAppSmokeRunner(args.adb).exercise(load_registry(args.manifest))
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 0
    except (CuttlefishSmokeError, CuttlefishEvidenceError, SystemAppRegistryError, OSError, ValueError):
        print(
            "Operation failed: exact local SwirPhoneOS Cuttlefish runtime evidence, SwirLauncher HOME resolution and every source-ready app foreground launch are required. Raw errors are withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
