from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from swirphoneos.cuttlefish_i18n import (
    CuttlefishI18nError,
    CuttlefishI18nRunner,
    parse_app_locales,
    parse_current_user,
)
from swirphoneos.i18n import LOCALES
from swirphoneos.system_apps import load_registry


class CuttlefishI18nTests(unittest.TestCase):
    def test_parsers_require_exact_user_and_package(self):
        self.assertEqual(parse_current_user("0\n"), 0)
        with self.assertRaises(CuttlefishI18nError):
            parse_current_user("User 0")
        self.assertEqual(
            parse_app_locales(
                "Locales for org.swir.phoneos.clock for user 0 are [pl]\n",
                "org.swir.phoneos.clock",
                0,
            ),
            ("pl",),
        )
        self.assertEqual(
            parse_app_locales(
                "Locales for org.swir.phoneos.clock for user 0 are []\n",
                "org.swir.phoneos.clock",
                0,
            ),
            (),
        )
        with self.assertRaises(CuttlefishI18nError):
            parse_app_locales(
                "Locales for org.other for user 0 are [pl]\n",
                "org.swir.phoneos.clock",
                0,
            )
        with self.assertRaises(CuttlefishI18nError):
            parse_app_locales(
                "Locales for org.swir.phoneos.clock for user 0 are [pl,pl]\n",
                "org.swir.phoneos.clock",
                0,
            )

    def test_allowlist_rejects_physical_and_arbitrary_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            runner = CuttlefishI18nRunner(adb)
            with self.assertRaises(CuttlefishI18nError):
                runner._run((
                    "-s", "192.168.1.20:5555", "shell", "cmd", "locale", "set-app-locales",
                    "org.swir.phoneos.clock", "--user", "0", "--locales", "pl",
                ))
            with self.assertRaises(CuttlefishI18nError):
                runner._run(("-s", "127.0.0.1:6520", "shell", "settings", "put", "system", "x", "1"))
            with self.assertRaises(CuttlefishI18nError):
                runner._run(("-s", "127.0.0.1:6520", "reboot"))

    def _make_runner(self, adb: Path):
        registry = load_registry(Path("system_apps/manifest.json"))
        apps = sorted((app for app in registry.apps if app.source_ready), key=lambda app: app.package)
        runner = CuttlefishI18nRunner(adb)
        runtime = {
            "runtime_evidence_complete": True,
            "identity_matches": True,
            "expected_product": "swirphoneos_cf_x86_64",
            "build_fingerprint": "Swir/test:17/TEST/1:userdebug/test-keys",
        }
        current = {
            "component": "",
            "launch_count": 0,
            "locales": {app.package: (() if index % 2 == 0 else ("nb",)) for index, app in enumerate(apps)},
        }
        original = dict(current["locales"])

        def evidence_run(args):
            if args[2:7] == ("shell", "cmd", "package", "resolve-activity", "--brief"):
                return f"{args[-1]}/.MainActivity\n"
            raise AssertionError(args)

        def fake_run(args):
            if args == ("devices", "-l"):
                return "List of devices attached\n127.0.0.1:6520 device product:swir\n"
            if args[2:] == ("shell", "am", "get-current-user"):
                return "0\n"
            if len(args) == 9 and args[2:6] == ("shell", "cmd", "locale", "get-app-locales"):
                package = args[6]
                tags = ",".join(current["locales"][package])
                return f"Locales for {package} for user 0 are [{tags}]\n"
            if len(args) in (9, 11) and args[2:6] == ("shell", "cmd", "locale", "set-app-locales"):
                package = args[6]
                current["locales"][package] = () if len(args) == 9 else (args[10],)
                return ""
            if len(args) == 8 and args[2:7] == ("shell", "am", "start", "-W", "-n"):
                current["component"] = args[-1]
                current["launch_count"] += 1
                return f"Status: ok\nActivity: {args[-1]}\nComplete\n"
            if args[2:] == ("shell", "dumpsys", "activity", "activities"):
                return f"mResumedActivity: ActivityRecord{{abc u0 {current['component']} t12}}\n"
            raise AssertionError(args)

        runner.evidence._run = evidence_run
        runner._run = fake_run
        return registry, apps, runner, runtime, current, original

    def test_exercise_covers_every_package_locale_pair_and_restores_overrides(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            registry, apps, runner, runtime, current, original = self._make_runner(adb)
            with patch.object(runner.evidence, "inspect", return_value=runtime):
                report = runner.exercise(registry)

            self.assertTrue(report["locale_matrix_complete"])
            self.assertTrue(report["original_app_locales_restored"])
            self.assertEqual(report["tested_packages"], [app.package for app in apps])
            self.assertEqual(report["tested_locales"], list(LOCALES))
            self.assertEqual(len(report["locale_results"]), len(apps) * len(LOCALES))
            self.assertEqual(current["locales"], original)
            self.assertEqual(current["launch_count"], len(apps) * len(LOCALES))
            self.assertEqual(
                report["rtl_locales_exercised"],
                [code for code in LOCALES if LOCALES[code].direction == "rtl"],
            )
            self.assertTrue(report["rtl_runtime_switch_exercised"])
            self.assertFalse(report["rtl_visual_mirroring_verified"])
            self.assertFalse(report["physical_device_support_claimed"])

    def test_failure_still_restores_every_captured_locale(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if os.name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            registry, _apps, runner, runtime, current, original = self._make_runner(adb)
            base_run = runner._run

            def fail_after_three_launches(args):
                if len(args) == 8 and args[2:7] == ("shell", "am", "start", "-W", "-n") and current["launch_count"] >= 3:
                    raise CuttlefishI18nError("synthetic launch failure")
                return base_run(args)

            runner._run = fail_after_three_launches
            with patch.object(runner.evidence, "inspect", return_value=runtime):
                with self.assertRaises(CuttlefishI18nError):
                    runner.exercise(registry)
            self.assertEqual(current["locales"], original)


if __name__ == "__main__":
    unittest.main()
