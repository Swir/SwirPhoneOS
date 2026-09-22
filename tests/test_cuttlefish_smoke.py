from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from swirphoneos.cuttlefish_smoke import (
    EXPECTED_HOME_PACKAGE,
    CuttlefishAppSmokeRunner,
    CuttlefishSmokeError,
    foreground_contains_component,
    parse_am_start_wait,
)
from swirphoneos.system_apps import load_registry


class CuttlefishSmokeTests(unittest.TestCase):
    def test_am_start_wait_requires_success_and_package_local_activity(self):
        output = "\n".join((
            "Starting: Intent { cmp=org.swir.phoneos.clock/.MainActivity }",
            "Status: ok",
            "LaunchState: COLD",
            "Activity: org.swir.phoneos.clock/.MainActivity",
            "TotalTime: 42",
            "Complete",
        ))
        self.assertEqual(
            parse_am_start_wait(
                output,
                "org.swir.phoneos.clock",
                "org.swir.phoneos.clock/.MainActivity",
            ),
            "ok",
        )
        with self.assertRaises(CuttlefishSmokeError):
            parse_am_start_wait(
                output.replace("Activity: org.swir.phoneos.clock/", "Activity: org.other/"),
                "org.swir.phoneos.clock",
                "org.swir.phoneos.clock/.MainActivity",
            )

    def test_foreground_confirmation_requires_resumed_marker_and_expected_component(self):
        state = "mResumedActivity: ActivityRecord{abc u0 org.swir.phoneos.clock/.MainActivity t12}\n"
        self.assertTrue(
            foreground_contains_component(
                state,
                "org.swir.phoneos.clock",
                "org.swir.phoneos.clock/.MainActivity",
            )
        )
        self.assertFalse(
            foreground_contains_component(
                state.replace("mResumedActivity", "mLastPausedActivity"),
                "org.swir.phoneos.clock",
                "org.swir.phoneos.clock/.MainActivity",
            )
        )

    def test_allowlist_rejects_physical_or_persistent_mutation_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if __import__("os").name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            runner = CuttlefishAppSmokeRunner(adb)
            with self.assertRaises(CuttlefishSmokeError):
                runner._run(("-s", "192.168.1.20:5555", "shell", "am", "start", "-W", "-n", "org.swir.phoneos.clock/.MainActivity"))
            with self.assertRaises(CuttlefishSmokeError):
                runner._run(("-s", "127.0.0.1:6520", "install", "app.apk"))
            with self.assertRaises(CuttlefishSmokeError):
                runner._run(("-s", "127.0.0.1:6520", "shell", "settings", "put", "system", "x", "1"))
            with self.assertRaises(CuttlefishSmokeError):
                runner._run(("-s", "127.0.0.1:6520", "shell", "cmd", "package", "resolve-activity", "--brief", "-a", "android.intent.action.VIEW"))

    def _exercise_report(self, *, home_package: str = EXPECTED_HOME_PACKAGE):
        registry = load_registry(Path("system_apps/manifest.json"))
        beta_apps = sorted(registry.first_beta_apps, key=lambda app: app.package)
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if __import__("os").name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            runner = CuttlefishAppSmokeRunner(adb)
            runtime = {
                "runtime_evidence_complete": True,
                "identity_matches": True,
                "expected_product": "swirphoneos_cf_x86_64",
                "build_fingerprint": "Swir/test:17/TEST/1:userdebug/test-keys",
            }
            runner.evidence._run = lambda args: f"{args[-1]}/.MainActivity\n"
            current = {"component": ""}

            def fake_run(args):
                if args == ("devices", "-l"):
                    return "List of devices attached\n127.0.0.1:6520 device product:swir\n"
                if args[2:] == (
                    "shell",
                    "cmd",
                    "package",
                    "resolve-activity",
                    "--brief",
                    "-a",
                    "android.intent.action.MAIN",
                    "-c",
                    "android.intent.category.HOME",
                ):
                    return f"{home_package}/.MainActivity\n"
                if len(args) == 8 and args[2:7] == ("shell", "am", "start", "-W", "-n"):
                    current["component"] = args[-1]
                    return f"Status: ok\nActivity: {args[-1]}\nComplete\n"
                if args[2:] == ("shell", "dumpsys", "activity", "activities"):
                    return f"mResumedActivity: ActivityRecord{{abc u0 {current['component']} t12}}\n"
                raise AssertionError(args)

            runner._run = fake_run
            with patch.object(runner.evidence, "inspect", return_value=runtime):
                report = runner.exercise(registry)
            return report, beta_apps

    def test_exercise_requires_swirlauncher_home_then_launches_every_first_beta_app(self):
        report, beta_apps = self._exercise_report()
        self.assertTrue(report["home_surface_complete"])
        self.assertTrue(report["home_resolved"])
        self.assertTrue(report["home_foreground_confirmed"])
        self.assertEqual(report["home_package"], EXPECTED_HOME_PACKAGE)
        self.assertTrue(report["home_component"].startswith(EXPECTED_HOME_PACKAGE + "/"))
        self.assertTrue(report["app_smoke_complete"])
        self.assertEqual(report["tested_packages"], [app.package for app in beta_apps])
        self.assertEqual(len(report["launch_results"]), len(beta_apps))
        self.assertTrue(report["runtime_state_mutation_performed"])
        self.assertFalse(report["physical_device_support_claimed"])

    def test_exercise_rejects_wrong_home_package(self):
        with self.assertRaises(CuttlefishSmokeError):
            self._exercise_report(home_package="com.android.launcher3")


if __name__ == "__main__":
    unittest.main()
