"""Host tests for SwirPhoneStudio's read-only device inventory boundary."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import inspect
import subprocess
from unittest.mock import patch

import pytest

from swirphoneos.studio_device_inventory import (
    DeviceInventoryEvidence,
    DeviceObservation,
    collect_device_inventory,
    parse_adb_devices,
    parse_fastboot_devices,
)


def _tool(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_adb_parser_hashes_serial_and_keeps_bounded_non_unique_metadata() -> None:
    serial = "ABC123PRIVATE"
    output = (
        "List of devices attached\n"
        f"{serial} device product:avicii model:AC2003 device:avicii transport_id:7\n"
    )

    parsed = parse_adb_devices(output)

    assert len(parsed) == 1
    item = parsed[0]
    assert item.transport == "adb"
    assert item.identifier_sha256 == sha256(serial.encode()).hexdigest()
    assert serial not in repr(item)
    assert item.state == "device"
    assert item.product == "avicii"
    assert item.model == "AC2003"
    assert item.device == "avicii"
    assert "transport_id" not in item.to_dict()


def test_adb_parser_preserves_non_ready_state_without_claiming_readiness() -> None:
    parsed = parse_adb_devices("List of devices attached\nSERIAL offline\n")
    assert len(parsed) == 1
    assert parsed[0].state == "offline"


def test_adb_parser_ignores_daemon_noise_and_malformed_lines() -> None:
    output = "* daemon started successfully *\nList of devices attached\nmalformed\n\n"
    assert parse_adb_devices(output) == ()


def test_adb_parser_deduplicates_identifier_deterministically() -> None:
    output = (
        "List of devices attached\n"
        "SERIAL offline\n"
        "SERIAL device model:Final\n"
    )
    parsed = parse_adb_devices(output)
    assert len(parsed) == 1
    assert parsed[0].state == "device"
    assert parsed[0].model == "Final"


def test_fastboot_parser_hashes_serial() -> None:
    serial = "FB-PRIVATE-123"
    parsed = parse_fastboot_devices(f"{serial}\tfastboot\n")
    assert len(parsed) == 1
    assert parsed[0].transport == "fastboot"
    assert parsed[0].identifier_sha256 == sha256(serial.encode()).hexdigest()
    assert serial not in repr(parsed[0])
    assert parsed[0].state == "fastboot"


def test_collect_inventory_executes_only_read_only_device_list_commands(tmp_path: Path) -> None:
    adb = _tool(tmp_path, "adb")
    fastboot = _tool(tmp_path, "fastboot")
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[0] == str(adb):
            stdout = "List of devices attached\nSERIAL device model:AC2003\n"
        else:
            stdout = "FASTBOOT fastboot\n"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    evidence = collect_device_inventory(
        adb_path=adb,
        fastboot_path=fastboot,
        platform_name="linux",
        runner=runner,
    )

    assert calls == [[str(adb), "devices", "-l"], [str(fastboot), "devices"]]
    assert len(evidence.observations) == 2
    report = evidence.to_dict()
    assert report["read_only"] is True
    assert report["physical_verification"] is False
    assert report["support_claim"] is False
    assert report["observation_count"] == 2


def test_collect_inventory_does_nothing_when_paths_are_omitted() -> None:
    called = False

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    evidence = collect_device_inventory(runner=runner)
    assert called is False
    assert evidence.observations == ()
    assert evidence.adb_attempted is False
    assert evidence.fastboot_attempted is False


def test_collect_inventory_rejects_wrong_tool_basename(tmp_path: Path) -> None:
    wrong = _tool(tmp_path, "not-adb")
    with pytest.raises(ValueError, match="requested transport"):
        collect_device_inventory(adb_path=wrong, platform_name="linux")


def test_collect_inventory_rejects_relative_tool_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        collect_device_inventory(adb_path=Path("adb"), platform_name="linux")


def test_collect_inventory_has_bounded_timeout_and_converts_timeout(tmp_path: Path) -> None:
    adb = _tool(tmp_path, "adb")

    def timeout_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    with pytest.raises(TimeoutError, match="adb inventory timed out"):
        collect_device_inventory(adb_path=adb, platform_name="linux", runner=timeout_runner)
    with pytest.raises(ValueError, match="timeout"):
        collect_device_inventory(timeout_seconds=0)
    with pytest.raises(ValueError, match="timeout"):
        collect_device_inventory(timeout_seconds=61)


def test_collect_inventory_fails_closed_on_nonzero_exit(tmp_path: Path) -> None:
    adb = _tool(tmp_path, "adb")

    def failing_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="error")

    with pytest.raises(RuntimeError, match="exit code 1"):
        collect_device_inventory(adb_path=adb, platform_name="linux", runner=failing_runner)


def test_source_does_not_contain_mutating_transport_commands() -> None:
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
        assert command not in source.lower()


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


def test_desktop_inventory_is_explicit_and_uses_only_current_transport_path() -> None:
    from swirphoneos.studio_desktop import inspect_current_devices

    app = _App()
    evidence = DeviceInventoryEvidence(
        observations=(DeviceObservation("adb", "a" * 64, "device", model="AC2003"),),
        adb_attempted=True,
        fastboot_attempted=False,
    )
    with patch("swirphoneos.studio_desktop.collect_device_inventory", return_value=evidence) as collect:
        result = inspect_current_devices(app)  # type: ignore[arg-type]

    assert result == evidence
    collect.assert_called_once_with(adb_path=Path("/reviewed/adb"))
    assert app.status_key == "inventory_complete"
    assert app.updated == 1
    assert "aaaaaaaaaaaa" in app.report
    assert "AC2003" in app.report


def test_desktop_inventory_failure_is_fail_closed_and_localized() -> None:
    from swirphoneos.studio_desktop import inspect_current_devices

    app = _App()
    with patch("swirphoneos.studio_desktop.collect_device_inventory", side_effect=TimeoutError("slow")):
        result = inspect_current_devices(app)  # type: ignore[arg-type]

    assert result is None
    assert app.status_key == "inventory_failed"
    assert app.report == "inventory_failed"


def test_desktop_inventory_requires_reviewed_tool_path_before_execution() -> None:
    from swirphoneos.studio_desktop import inspect_current_devices

    app = _App(path="")
    with patch("swirphoneos.studio_desktop.collect_device_inventory") as collect:
        result = inspect_current_devices(app)  # type: ignore[arg-type]

    assert result is None
    collect.assert_not_called()
    assert app.status_key == "tool_not_found"
