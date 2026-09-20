"""Host tests for safe SwirPhoneStudio Android SDK tool discovery."""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from swirphoneos.studio_toolchain import ToolDiscovery, discover_android_tool


class ToolDiscoveryTests(unittest.TestCase):
    @staticmethod
    def _tool(path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("test-only\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_android_sdk_root_precedes_path_without_executing_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adb = self._tool(root / "sdk" / "platform-tools" / "adb")
            which = Mock(return_value=str(root / "other" / "adb"))
            result = discover_android_tool(
                "adb",
                environ={"ANDROID_SDK_ROOT": str(root / "sdk")},
                home=root / "home",
                platform_name="linux",
                which=which,
            )
        self.assertEqual(result, ToolDiscovery("adb", adb.resolve(), "android_sdk_root"))
        which.assert_not_called()

    def test_android_home_is_used_when_primary_sdk_root_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fastboot = self._tool(root / "home-sdk" / "platform-tools" / "fastboot")
            result = discover_android_tool(
                "fastboot",
                environ={
                    "ANDROID_SDK_ROOT": str(root / "missing-sdk"),
                    "ANDROID_HOME": str(root / "home-sdk"),
                },
                home=root / "user",
                platform_name="linux",
                which=lambda _: None,
            )
        self.assertEqual(result, ToolDiscovery("fastboot", fastboot.resolve(), "android_home"))

    def test_windows_default_sdk_location_is_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adb = self._tool(root / "LocalAppData" / "Android" / "Sdk" / "platform-tools" / "adb.exe")
            result = discover_android_tool(
                "adb",
                environ={"LOCALAPPDATA": str(root / "LocalAppData")},
                home=root / "user",
                platform_name="win32",
                which=lambda _: None,
            )
        self.assertEqual(result, ToolDiscovery("adb", adb.resolve(), "default_sdk"))

    def test_path_fallback_requires_exact_executable_name(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adb = self._tool(root / "bin" / "adb")
            result = discover_android_tool(
                "adb",
                environ={},
                home=root / "home",
                platform_name="linux",
                which=lambda _: str(adb),
            )
            wrong = self._tool(root / "bin" / "adb-wrapper")
            rejected = discover_android_tool(
                "adb",
                environ={},
                home=root / "home",
                platform_name="linux",
                which=lambda _: str(wrong),
            )
        self.assertEqual(result, ToolDiscovery("adb", adb.resolve(), "path"))
        self.assertEqual(rejected, ToolDiscovery("adb", None, "not_found"))

    def test_capture_prefill_can_disable_path_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fastboot = self._tool(root / "bin" / "fastboot")
            which = Mock(return_value=str(fastboot))
            result = discover_android_tool(
                "fastboot",
                environ={},
                home=root / "home",
                platform_name="linux",
                which=which,
                include_path=False,
            )
        self.assertEqual(result, ToolDiscovery("fastboot", None, "not_found"))
        which.assert_not_called()

    def test_relative_sdk_root_and_non_executable_posix_candidate_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            adb = root / "bin" / "adb"
            adb.parent.mkdir(parents=True)
            adb.write_text("test-only\n", encoding="utf-8")
            adb.chmod(0o644)
            with patch("swirphoneos.studio_toolchain.os.access", return_value=False):
                result = discover_android_tool(
                    "adb",
                    environ={"ANDROID_SDK_ROOT": "relative/sdk"},
                    home=root / "home",
                    platform_name="linux",
                    which=lambda _: str(adb),
                )
        self.assertEqual(result, ToolDiscovery("adb", None, "not_found"))

    def test_unsupported_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            discover_android_tool("heimdall", environ={}, home=Path("/tmp"), platform_name="linux")

    def test_discovery_implementation_contains_no_process_or_network_execution(self):
        import swirphoneos.studio_toolchain as module

        source = inspect.getsource(module)
        for forbidden in ("subprocess", "os.system", "requests", "urllib", "socket"):
            self.assertNotIn(forbidden, source)


class DesktopIntegrationTests(unittest.TestCase):
    class _Value:
        def __init__(self, value: str = "") -> None:
            self.value = value

        def get(self) -> str:
            return self.value

        def set(self, value: str) -> None:
            self.value = value

    class _App:
        def __init__(self) -> None:
            self.tool_path = DesktopIntegrationTests._Value("/manual/tool")
            self.status_key = "ready"
            self.updated = 0

        def transport_code(self) -> str:
            return "adb"

        def update_status(self) -> None:
            self.updated += 1

    class _Wizard:
        def __init__(self) -> None:
            self.adb_path = DesktopIntegrationTests._Value()
            self.fastboot_path = DesktopIntegrationTests._Value()

    def test_explicit_desktop_detection_populates_path_but_starts_no_scan(self):
        from swirphoneos.studio_desktop import detect_studio_tool

        app = self._App()
        found = ToolDiscovery("adb", Path("/sdk/platform-tools/adb"), "android_sdk_root")
        with patch("swirphoneos.studio_desktop.discover_android_tool", return_value=found) as discover:
            result = detect_studio_tool(app)  # type: ignore[arg-type]
        self.assertEqual(result, found)
        self.assertEqual(app.tool_path.get(), str(found.path))
        self.assertEqual(app.status_key, "tool_found")
        self.assertEqual(app.updated, 1)
        discover.assert_called_once_with("adb", include_path=True)

    def test_failed_detection_preserves_manually_reviewed_path(self):
        from swirphoneos.studio_desktop import detect_studio_tool

        app = self._App()
        missing = ToolDiscovery("adb", None, "not_found")
        with patch("swirphoneos.studio_desktop.discover_android_tool", return_value=missing):
            detect_studio_tool(app)  # type: ignore[arg-type]
        self.assertEqual(app.tool_path.get(), "/manual/tool")
        self.assertEqual(app.status_key, "tool_not_found")

    def test_capture_prefill_uses_sdk_roots_only_and_never_overwrites_owner_value(self):
        from swirphoneos.studio_desktop import prefill_capture_tools

        wizard = self._Wizard()
        wizard.fastboot_path.set("/owner/fastboot")
        adb = ToolDiscovery("adb", Path("/sdk/platform-tools/adb"), "android_home")
        fastboot = ToolDiscovery("fastboot", Path("/sdk/platform-tools/fastboot"), "android_home")
        with patch(
            "swirphoneos.studio_desktop.discover_android_tool",
            side_effect=[adb, fastboot],
        ) as discover:
            results = prefill_capture_tools(wizard)  # type: ignore[arg-type]
        self.assertEqual(results, (adb, fastboot))
        self.assertEqual(wizard.adb_path.get(), str(adb.path))
        self.assertEqual(wizard.fastboot_path.get(), "/owner/fastboot")
        self.assertEqual(
            discover.call_args_list,
            [unittest.mock.call("adb", include_path=False), unittest.mock.call("fastboot", include_path=False)],
        )


if __name__ == "__main__":
    unittest.main()
