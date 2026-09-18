from __future__ import annotations

import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from swirphoneos.cuttlefish_visual_evidence import (
    CuttlefishVisualEvidenceError,
    CuttlefishVisualEvidenceRunner,
    _safe_output_root,
    parse_png_dimensions,
)
from swirphoneos.i18n import LOCALES
from swirphoneos.system_apps import load_registry


def png(width=1080, height=2400):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00" + b"crc!" + b"payload"


class CuttlefishVisualEvidenceTests(unittest.TestCase):
    def test_png_parser_is_bounded_and_requires_ihdr(self):
        self.assertEqual(parse_png_dimensions(png()), (1080, 2400))
        with self.assertRaises(CuttlefishVisualEvidenceError):
            parse_png_dimensions(b"not-png")
        with self.assertRaises(CuttlefishVisualEvidenceError):
            parse_png_dimensions(png(0, 10))

    def test_output_root_is_create_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = _safe_output_root(Path(temp).resolve() / "captures")
            self.assertTrue(root.is_dir())
            with self.assertRaises(CuttlefishVisualEvidenceError):
                _safe_output_root(root)

    def test_allowlist_rejects_physical_and_arbitrary_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            runner = CuttlefishVisualEvidenceRunner(adb)
            self.assertFalse(runner._allowed_text(("-s", "192.168.1.2:5555", "shell", "am", "get-current-user")))
            self.assertFalse(runner._allowed_text(("-s", "127.0.0.1:6520", "shell", "settings", "put", "system", "x", "1")))
            with self.assertRaises(CuttlefishVisualEvidenceError):
                runner._run_png("192.168.1.2:5555")

    def _runner(self, adb: Path):
        registry = load_registry(Path("system_apps/manifest.json"))
        apps = sorted((app for app in registry.apps if app.source_ready), key=lambda app: app.package)
        runner = CuttlefishVisualEvidenceRunner(adb)
        runtime = {
            "runtime_evidence_complete": True,
            "identity_matches": True,
            "expected_product": "swirphoneos_cf_x86_64",
            "build_fingerprint": "Swir/test:17/TEST/1:userdebug/test-keys",
        }
        current = {"component": "", "launch_count": 0, "locales": {app.package: (() if i % 2 == 0 else ("nb", "en")) for i, app in enumerate(apps)}}
        original = dict(current["locales"])

        def evidence_run(args):
            if args[2:7] == ("shell", "cmd", "package", "resolve-activity", "--brief"):
                return f"{args[-1]}/.MainActivity\n"
            raise AssertionError(args)

        def run_text(args):
            if args == ("devices", "-l"):
                return "List of devices attached\n127.0.0.1:6520 device product:swir\n"
            if args[2:] == ("shell", "am", "get-current-user"):
                return "0\n"
            if len(args) == 9 and args[2:6] == ("shell", "cmd", "locale", "get-app-locales"):
                package = args[6]
                return f"Locales for {package} for user 0 are [{','.join(current['locales'][package])}]\n"
            if len(args) in (9, 11) and args[2:6] == ("shell", "cmd", "locale", "set-app-locales"):
                package = args[6]
                current["locales"][package] = () if len(args) == 9 else tuple(args[10].split(","))
                return ""
            if len(args) == 8 and args[2:7] == ("shell", "am", "start", "-W", "-n"):
                current["component"] = args[-1]
                current["launch_count"] += 1
                return f"Status: ok\nActivity: {args[-1]}\nComplete\n"
            if args[2:] == ("shell", "dumpsys", "activity", "activities"):
                return f"mResumedActivity: ActivityRecord{{x u0 {current['component']} t1}}\n"
            raise AssertionError(args)

        runner.evidence._run = evidence_run
        runner._run_text = run_text
        runner._run_png = lambda serial: png()
        return registry, apps, runner, runtime, current, original

    def test_capture_covers_matrix_and_restores_original_locales(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            registry, apps, runner, runtime, current, original = self._runner(adb)
            with patch.object(runner.evidence, "inspect", return_value=runtime):
                report = runner.capture(registry, Path(temp).resolve() / "visual")
            self.assertTrue(report["capture_matrix_complete"])
            self.assertEqual(report["capture_count"], len(apps) * len(LOCALES))
            self.assertEqual(current["locales"], original)
            self.assertEqual(current["launch_count"], len(apps) * len(LOCALES))
            self.assertFalse(report["rtl_visual_mirroring_verified"])
            self.assertFalse(report["accessibility_review_complete"])
            self.assertFalse(report["visual_translation_review_complete"])

    def test_capture_failure_still_restores_locales(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            registry, _apps, runner, runtime, current, original = self._runner(adb)
            base = runner._run_png
            count = {"n": 0}

            def fail(serial):
                count["n"] += 1
                if count["n"] == 3:
                    raise CuttlefishVisualEvidenceError("synthetic")
                return base(serial)

            runner._run_png = fail
            with patch.object(runner.evidence, "inspect", return_value=runtime):
                with self.assertRaises(CuttlefishVisualEvidenceError):
                    runner.capture(registry, Path(temp).resolve() / "visual")
            self.assertEqual(current["locales"], original)


if __name__ == "__main__":
    unittest.main()
