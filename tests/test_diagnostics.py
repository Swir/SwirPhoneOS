import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from swirphoneos.diagnostics import (
    Device, DiagnosticError, PROPERTIES, ReadOnlyAdb,
    parse_devices, select_device, summarize,
)


class ParsingTests(unittest.TestCase):
    def test_parse_usb_device(self):
        rows = parse_devices("List of devices attached\nSECRET123 device product:avicii model:AC2003\n")
        self.assertEqual(rows, [Device("SECRET123", "device")])

    def test_empty_list_is_valid_but_not_selectable(self):
        self.assertEqual(parse_devices("List of devices attached\n\n"), [])
        with self.assertRaises(DiagnosticError):
            select_device([])

    def test_reject_bad_header(self):
        with self.assertRaises(DiagnosticError):
            parse_devices("garbage")

    def test_reject_malformed_entry(self):
        with self.assertRaises(DiagnosticError):
            parse_devices("List of devices attached\nSECRET_ONLY\n")

    def test_reject_duplicate_serial(self):
        with self.assertRaises(DiagnosticError):
            parse_devices("List of devices attached\nPRIVATE device\nPRIVATE device\n")

    def test_reject_shell_characters(self):
        with self.assertRaises(DiagnosticError):
            parse_devices("List of devices attached\nBAD;COMMAND device\n")

    def test_reject_two_devices_including_offline(self):
        with self.assertRaises(DiagnosticError):
            select_device([Device("ONE", "device"), Device("TWO", "offline")])

    def test_reject_unavailable_states(self):
        for state in ("unauthorized", "offline", "recovery", "sideload", "no", "unknown"):
            with self.subTest(state=state), self.assertRaises(DiagnosticError):
                select_device([Device("PRIVATE", state)])

    def test_reject_network_and_emulator(self):
        for serial in ("emulator-5554", "192.168.0.2:5555"):
            with self.subTest(serial=serial), self.assertRaises(DiagnosticError):
                select_device([Device(serial, "device")])

    def test_repr_does_not_expose_serial(self):
        self.assertNotIn("PRIVATE123", repr(Device("PRIVATE123", "device")))

    def test_unknown_properties_never_authorize_flash(self):
        result = summarize({})
        self.assertIsNone(result["treble_reported"])
        self.assertEqual(result["bootloader_reported"], "unknown")
        self.assertFalse(result["flash_allowed"])

    def test_positive_properties_still_do_not_authorize(self):
        result = summarize({"ro.boot.flash.locked": "0", "ro.treble.enabled": "true"})
        self.assertEqual(result["bootloader_reported"], "unlocked")
        self.assertTrue(result["treble_reported"])
        self.assertFalse(result["flash_allowed"])
        self.assertEqual(result["swirphoneos_support"], "NOT_VALIDATED")

    def test_locked_false_and_invalid_booleans(self):
        result = summarize({"ro.boot.flash.locked": "1", "ro.treble.enabled": "false"})
        self.assertEqual(result["bootloader_reported"], "locked")
        self.assertFalse(result["treble_reported"])
        self.assertIsNone(summarize({"ro.treble.enabled": "yes"})["treble_reported"])

    def test_no_serial_property_in_report(self):
        self.assertNotIn("PRIVATE", json.dumps(summarize({"ro.serialno": "PRIVATE"})))

    def test_reject_terminal_controls_and_multiline(self):
        for value in ("A\nB", "A\x1bB", "A\x7fB", "X" * 257):
            with self.subTest(value=value), self.assertRaises(DiagnosticError):
                summarize({"ro.product.model": value})


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / ("adb.exe" if os.name == "nt" else "adb")
        self.path.write_bytes(b"test placeholder - never executed")
        self.adb = ReadOnlyAdb(self.path)

    def test_require_absolute_existing_executable(self):
        with self.assertRaises(DiagnosticError):
            ReadOnlyAdb(Path("adb"))
        with self.assertRaises(DiagnosticError):
            ReadOnlyAdb(self.path.parent / "other")

    def test_timeout_bounds(self):
        for timeout in (0, -1, 61, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(DiagnosticError):
                ReadOnlyAdb(self.path, timeout)

    @patch("swirphoneos.diagnostics.subprocess.run")
    def test_allowlist_rejects_writes_before_execution(self, run):
        for command in (("reboot",), ("root",), ("shell", "id"), ("flash", "system"),
                        ("-s", "PRIVATE", "shell", "getprop", "ro.serialno")):
            with self.subTest(command=command), self.assertRaises(DiagnosticError):
                self.adb._run(command)
        run.assert_not_called()

    @patch("swirphoneos.diagnostics.subprocess.run")
    def test_no_shell_and_ignore_remote_server_environment(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "List of devices attached\n", "")
        with patch.dict(os.environ, {"ADB_SERVER_SOCKET": "tcp:remote:5037", "ANDROID_SERIAL": "PRIVATE"}):
            self.adb._run(("devices", "-l"))
        options = run.call_args.kwargs
        self.assertFalse(options["shell"])
        self.assertNotIn("ADB_SERVER_SOCKET", options["env"])
        self.assertNotIn("ANDROID_SERIAL", options["env"])
        self.assertEqual(options["timeout"], 10.0)

    @patch("swirphoneos.diagnostics.subprocess.run")
    def test_timeout_error_is_private(self, run):
        run.side_effect = subprocess.TimeoutExpired(["adb", "PRIVATE123"], 1, stderr="SECRET")
        with self.assertRaises(DiagnosticError) as error:
            self.adb._run(("devices", "-l"))
        self.assertNotIn("PRIVATE123", str(error.exception))
        self.assertNotIn("SECRET", str(error.exception))

    @patch("swirphoneos.diagnostics.subprocess.run")
    def test_nonzero_error_is_private(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "SECRET", "PRIVATE123")
        with self.assertRaises(DiagnosticError) as error:
            self.adb._run(("devices", "-l"))
        self.assertNotIn("PRIVATE123", str(error.exception))

    @patch("swirphoneos.diagnostics.subprocess.run")
    def test_limit_response_size(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "X" * 65537, "")
        with self.assertRaises(DiagnosticError):
            self.adb._run(("devices", "-l"))

    def test_inspection_is_read_only_and_rechecks_identity(self):
        outputs = ["List of devices attached\nPRIVATE123 device\n"] + [""] * len(PROPERTIES)
        outputs += ["List of devices attached\nPRIVATE123 device\n"]
        with patch.object(self.adb, "_run", side_effect=outputs) as run:
            report = self.adb.inspect()
        self.assertEqual(run.call_count, len(PROPERTIES) + 2)
        self.assertFalse(report["flash_allowed"])
        self.assertNotIn("PRIVATE123", json.dumps(report))
        for call in run.call_args_list[1:-1]:
            self.assertEqual(call.args[0][2:4], ("shell", "getprop"))

    def test_device_swap_is_rejected(self):
        outputs = ["List of devices attached\nFIRST device\n"] + [""] * len(PROPERTIES)
        outputs += ["List of devices attached\nSECOND device\n"]
        with patch.object(self.adb, "_run", side_effect=outputs), self.assertRaises(DiagnosticError):
            self.adb.inspect()


if __name__ == "__main__":
    unittest.main()
