"""Host tests for the SwirPhoneStudio physical-device capture wizard."""
from pathlib import Path
import inspect
import sys
import unittest
from unittest.mock import patch

from swirphoneos.i18n import CATALOGS
from swirphoneos.studio_capture_wizard import (
    CaptureWizardController,
    bundled_profiles_root,
)
from swirphoneos.device_capture_session import DeviceCaptureSessionError


class CaptureWizardControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = CaptureWizardController(Path("/reviewed/device_packs"))
        self.session = Path("/tmp/swir-capture")

    def test_rejects_relative_session_path_before_io(self):
        with self.assertRaises(DeviceCaptureSessionError):
            self.controller.status(Path("relative/session"))

    def test_fastboot_requires_prior_adb_capture(self):
        with patch.object(
            self.controller,
            "status",
            return_value={"captured_transports": [], "finalized": False},
        ), patch("swirphoneos.studio_capture_wizard.ReadOnlyFastboot") as fastboot:
            with self.assertRaises(DeviceCaptureSessionError):
                self.controller.capture_fastboot(self.session, Path("/sdk/fastboot"))
            fastboot.assert_not_called()

    def test_finalize_requires_both_transports(self):
        with patch.object(
            self.controller,
            "status",
            return_value={"captured_transports": ["adb"], "finalized": False},
        ), patch("swirphoneos.studio_capture_wizard.finalize_capture_session") as finalize:
            with self.assertRaises(DeviceCaptureSessionError):
                self.controller.finalize(self.session)
            finalize.assert_not_called()

    def test_verify_requires_finalized_bundle(self):
        with patch.object(
            self.controller,
            "status",
            return_value={"captured_transports": ["adb", "fastboot"], "finalized": False},
        ), patch("swirphoneos.studio_capture_wizard.verify_capture_session") as verify:
            with self.assertRaises(DeviceCaptureSessionError):
                self.controller.verify(self.session)
            verify.assert_not_called()

    def test_safe_action_hides_private_error_details(self):
        result = self.controller.safe_action(
            "adb",
            lambda: (_ for _ in ()).throw(
                DeviceCaptureSessionError("/private/serial/path-do-not-display")
            ),
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error_key, "capture_error")
        self.assertIsNone(result.status)
        self.assertNotIn("private", repr(result))

    def test_adb_capture_reuses_strict_read_only_pipeline(self):
        status = {"captured_transports": [], "finalized": False}
        report = {"synthetic": "transport"}
        unified = {"synthetic": "unified"}
        final = {"captured_transports": ["adb"], "finalized": False}
        inspector = unittest.mock.Mock()
        inspector.inspect.return_value = report
        with patch.object(self.controller, "status", return_value=status), \
             patch(
                 "swirphoneos.studio_capture_wizard.discover_profiles",
                 return_value=["profile"],
             ) as profiles, \
             patch("swirphoneos.studio_capture_wizard.ReadOnlyAdb", return_value=inspector) as adb, \
             patch(
                 "swirphoneos.studio_capture_wizard.build_unified_report",
                 return_value=unified,
             ) as build, \
             patch(
                 "swirphoneos.studio_capture_wizard.record_transport_report",
                 return_value=final,
             ) as record:
            self.assertEqual(
                self.controller.capture_adb(self.session, Path("/sdk/adb")),
                final,
            )
        profiles.assert_called_once_with(Path("/reviewed/device_packs"))
        adb.assert_called_once_with(Path("/sdk/adb"))
        build.assert_called_once_with("adb", report, ["profile"])
        record.assert_called_once_with(
            self.session,
            Path("/reviewed/device_packs"),
            transport="adb",
            report=unified,
        )

    def test_fastboot_capture_keeps_partition_hints_explicit(self):
        status = {"captured_transports": ["adb"], "finalized": False}
        inspector = unittest.mock.Mock()
        inspector.inspect.return_value = {"synthetic": "fastboot"}
        with patch.object(self.controller, "status", return_value=status), \
             patch(
                 "swirphoneos.studio_capture_wizard.discover_profiles",
                 return_value=["profile"],
             ), \
             patch(
                 "swirphoneos.studio_capture_wizard.ReadOnlyFastboot",
                 return_value=inspector,
             ), \
             patch(
                 "swirphoneos.studio_capture_wizard.build_unified_report",
                 return_value={"unified": True},
             ), \
             patch(
                 "swirphoneos.studio_capture_wizard.record_transport_report",
                 return_value={
                     "captured_transports": ["adb", "fastboot"],
                     "finalized": False,
                 },
             ):
            self.controller.capture_fastboot(
                self.session,
                Path("/sdk/fastboot"),
                include_partitions=True,
            )
        inspector.inspect.assert_called_once_with(include_partitions=True)


class CaptureWizardPolicyTests(unittest.TestCase):
    def test_frozen_profiles_root_uses_bundled_registry(self):
        with patch.object(sys, "_MEIPASS", "/frozen/runtime", create=True):
            self.assertEqual(
                bundled_profiles_root(),
                Path("/frozen/runtime/device_packs"),
            )

    def test_all_locales_cover_capture_surface(self):
        required = {
            "capture_tools_menu",
            "capture_menu",
            "capture_title",
            "capture_notice",
            "capture_session_path",
            "capture_new_session",
            "capture_open_session",
            "capture_adb_tool",
            "capture_fastboot_tool",
            "capture_partitions",
            "capture_create",
            "capture_capture_adb",
            "capture_capture_fastboot",
            "capture_finalize",
            "capture_verify",
            "capture_manual_transition",
            "capture_status_summary",
            "capture_error",
            "capture_done_verify",
        }
        self.assertEqual(set(CATALOGS), {"en", "pl", "nb", "de", "es", "fr", "pt", "ar"})
        for code, catalog in CATALOGS.items():
            with self.subTest(locale=code):
                self.assertTrue(required.issubset(catalog))

    def test_wizard_source_has_no_device_write_command_surface(self):
        import swirphoneos.studio_capture_wizard as module

        source = inspect.getsource(module).lower()
        forbidden = (
            "adb reboot",
            "fastboot flash",
            "fastboot erase",
            "fastboot format",
            "fastboot boot",
            "flashing unlock",
            "oem unlock",
            "set_active",
            "subprocess.",
            "shell=true",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_frozen_entry_uses_desktop_shell(self):
        entry = Path(__file__).resolve().parents[1] / "packaging" / "studio_entry.py"
        source = entry.read_text(encoding="utf-8")
        self.assertIn("from swirphoneos.studio_desktop import main", source)
        self.assertNotIn("device_capture_session_cli", source)


if __name__ == "__main__":
    unittest.main()
