"""Host tests for SwirPhoneStudio's read-only device inventory boundary."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import inspect
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from swirphoneos.studio_device_inventory import (
    DeviceInventoryEvidence,
    DeviceObservation,
    collect_device_inventory,
    parse_adb_devices,
    parse_fastboot_devices,
)


def _platform_name() -> str:
    return "win32" if sys.platform == "win32" else "linux"


def _tool(root: Path, tool: str) -> Path:
    name = f"{tool}.exe" if _platform_name() == "win32" else tool
    path = root / name
    path.write_text("tool fixture\n", encoding="utf-8")
    if _platform_name() != "win32":
        path.chmod(0o755)
    return path


class StudioDeviceInventoryTests(TestCase):
    def test_adb_parser_hashes_serial_and_keeps_bounded_non_unique_metadata(self) -> None:
        serial = "ABC123PRIVATE"
        output = (
            "List of devices attached\n"
            f"{serial} device product:avicii model:AC2003 device:avicii transport_id:7\n"
        )

        parsed = parse_adb_devices(output)

        self.assertEqual(len(parsed), 1)
        item = parsed[0]
        self.assertEqual(item.transport, "adb")
        self.assertEqual(item.identifier_sha256, sha256(serial.encode()).hexdigest())
        self.assertNotIn(serial, repr(item))
        self.assertEqual(item.state, "device")
        self.assertEqual(item.product, "avicii")
        self.assertEqual(item.model, "AC2003")
        self.assertEqual(item.device, "avicii")
        self.assertNotIn("transport_id", item.to_dict())

    def test_adb_parser_preserves_non_ready_state_without_claiming_readiness(self) -> None:
        parsed = parse_adb_devices("List of devices attached\nSERIAL offline\n")
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].state, "offline")

    def test_adb_parser_ignores_daemon_noise_and_malformed_lines(self) -> None:
        output = "* daemon started successfully *\nList of devices attached\nmalformed\n\n"
        self.assertEqual(parse_adb_devices(output), ())

    def test_adb_parser_deduplicates_identifier_deterministically(self) -> None:
        output = (
            "List of devices attached\n"
            "SERIAL offline\n"
            "SERIAL device model:Final\n"
        )
        parsed = parse_adb_devices(output)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].state, "device")
        self.assertEqual(parsed[0].model, "Final")

    def test_fastboot_parser_hashes_serial(self) -> None:
        serial = "FB-PRIVATE-123"
        parsed = parse_fastboot_devices(f"{serial}\tfastboot\n")
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].transport, "fastboot")
        self.assertEqual(parsed[0].identifier_sha256, sha256(serial.encode()).hexdigest())
        self.assertNotIn(serial, repr(parsed[0]))
        self.assertEqual(parsed[0].state, "fastboot")

    def test_collect_inventory_executes_only_read_only_device_list_commands(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            adb = _tool(root, "adb")
            fastboot = _tool(root, "fastboot")
            calls: list[list[str]] = []

            def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                calls.append(command)
                if command[0] == str(adb.resolve()):
                    stdout = "List of devices attached\nSERIAL device model:AC2003\n"
                else:
                    stdout = "FASTBOOT fastboot\n"
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

            evidence = collect_device_inventory(
                adb_path=adb,
                fastboot_path=fastboot,
                platform_name=_platform_name(),
                runner=runner,
            )

            self.assertEqual(
                calls,
                [[str(adb.resolve()), "devices", "-l"], [str(fastboot.resolve()), "devices"]],
            )
            self.assertEqual(len(evidence.observations), 2)
            report = evidence.to_dict()
            self.assertIs(report["read_only"], True)
            self.assertIs(report["physical_verification"], False)
            self.assertIs(report["support_claim"], False)
            self.assertEqual(report["observation_count"], 2)

    def test_collect_inventory_does_nothing_when_paths_are_omitted(self) -> None:
        called = False

        def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal called
            called = True
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        evidence = collect_device_inventory(runner=runner)
        self.assertFalse(called)
        self.assertEqual(evidence.observations, ())
        self.assertFalse(evidence.adb_attempted)
        self.assertFalse(evidence.fastboot_attempted)

    def test_collect_inventory_rejects_wrong_tool_basename(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            wrong_name = "not-adb.exe" if _platform_name() == "win32" else "not-adb"
            wrong = root / wrong_name
            wrong.write_text("fixture\n", encoding="utf-8")
            if _platform_name() != "win32":
                wrong.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "requested transport"):
                collect_device_inventory(adb_path=wrong, platform_name=_platform_name())

    def test_collect_inventory_rejects_relative_tool_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute"):
            collect_device_inventory(adb_path=Path("adb"), platform_name=_platform_name())

    def test_collect_inventory_has_bounded_timeout_and_converts_timeout(self) -> None:
        with TemporaryDirectory() as directory:
            adb = _tool(Path(directory), "adb")

            def timeout_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"])

            with self.assertRaisesRegex(TimeoutError, "adb inventory timed out"):
                collect_device_inventory(
                    adb_path=adb,
                    platform_name=_platform_name(),
                    runner=timeout_runner,
                )
        with self.assertRaisesRegex(ValueError, "timeout"):
            collect_device_inventory(timeout_seconds=0)
        with self.assertRaisesRegex(ValueError, "timeout"):
            collect_device_inventory(timeout_seconds=61)

    def test_collect_inventory_fails_closed_on_nonzero_exit(self) -> None:
        with TemporaryDirectory() as directory:
            adb = _tool(Path(directory), "adb")

            def failing_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="error")

            with self.assertRaisesRegex(RuntimeError, "exit code 1"):
                collect_device_inventory(
                    adb_path=adb,
                    platform_name=_platform_name(),
                    runner=failing_runner,
                )

    def test_source_does_not_contain_mutating_transport_commands(self) -> None:
        source = inspect.getsource(__import__("swirphoneos.studio_device_inventory", fromlist=["*"]))
        forbidden = (
            "adb reboot",
            "adb install",
            "adb push",
            "adb root",
            "fastboot flash",
            "fastboot erase",
            "fastboot reboot",
            "fastboot flashing unlock",
            "fastboot oem unlock",
        )
        for command in forbidden:
            self.assertNotIn(command, source.lower())


class _Value:
    def __init__(self, value: str) -> None:
        self.value = value

    def get(self) -> str:
        return self.value


class _Session:
    busy = False


class _App:
    def __init__(self, transport: str = "adb", path: str = "/reviewed/adb") -> None:
        self._transport = transport
        self.tool_path = _Value(path)
        self.session = _Session()
        self.status_key = "ready"
        self.updated = 0
        self.report = ""

    def transport_code(self) -> str:
        return self._transport

    def update_status(self) -> None:
        self.updated += 1

    def show_report(self, text: str) -> None:
        self.report = text

    def tr(self, key: str, **values: object) -> str:
        if key == "inventory_item":
            return "{transport}|{state}|{identifier}|{model}".format(**values)
        return key


class StudioDeviceInventoryDesktopTests(TestCase):
    def test_desktop_inventory_is_explicit_and_uses_only_current_transport_path(self) -> None:
        from swirphoneos.studio_desktop import inspect_current_devices

        app = _App()
        evidence = DeviceInventoryEvidence(
            observations=(DeviceObservation("adb", "a" * 64, "device", model="AC2003"),),
            adb_attempted=True,
            fastboot_attempted=False,
        )
        with patch("swirphoneos.studio_desktop.collect_device_inventory", return_value=evidence) as collect:
            result = inspect_current_devices(app)  # type: ignore[arg-type]

        self.assertEqual(result, evidence)
        collect.assert_called_once_with(adb_path=Path("/reviewed/adb"))
        self.assertEqual(app.status_key, "inventory_complete")
        self.assertEqual(app.updated, 1)
        self.assertIn("aaaaaaaaaaaa", app.report)
        self.assertIn("AC2003", app.report)

    def test_desktop_inventory_failure_is_fail_closed_and_localized(self) -> None:
        from swirphoneos.studio_desktop import inspect_current_devices

        app = _App()
        with patch("swirphoneos.studio_desktop.collect_device_inventory", side_effect=TimeoutError("slow")):
            result = inspect_current_devices(app)  # type: ignore[arg-type]

        self.assertIsNone(result)
        self.assertEqual(app.status_key, "inventory_failed")
        self.assertEqual(app.report, "inventory_failed")

    def test_desktop_inventory_requires_reviewed_tool_path_before_execution(self) -> None:
        from swirphoneos.studio_desktop import inspect_current_devices

        app = _App(path="")
        with patch("swirphoneos.studio_desktop.collect_device_inventory") as collect:
            result = inspect_current_devices(app)  # type: ignore[arg-type]

        self.assertIsNone(result)
        collect.assert_not_called()
        self.assertEqual(app.status_key, "tool_not_found")
