from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import (
    CuttlefishEvidenceCollector,
    CuttlefishEvidenceError,
    evaluate_runtime_snapshot,
    parse_local_devices,
    parse_packages,
    select_local_device,
)
from swirphoneos.system_apps import load_registry


class CuttlefishEvidenceTests(unittest.TestCase):
    def test_complete_snapshot_requires_boot_product_fingerprint_and_all_source_apps(self):
        registry = load_registry(Path("system_apps/manifest.json"))
        required = frozenset(app.package for app in registry.apps if app.source_ready)
        report = evaluate_runtime_snapshot({
            "sys.boot_completed": "1\n",
            "ro.product.name": "swirphoneos_cf_x86_64\n",
            "ro.build.fingerprint": "swir/test/build:17/ABC/1:userdebug/test-keys\n",
            "ro.build.version.release": "17\n",
            "ro.build.version.security_patch": "2026-09-05\n",
            "persist.sys.locale": "pl-PL\n",
        }, required, registry)
        self.assertTrue(report["runtime_evidence_complete"])
        self.assertEqual(report["missing_required_packages"], [])
        self.assertFalse(report["status_promotion_performed"])
        self.assertFalse(report["device_write_allowed"])
        self.assertEqual(len(report["build_fingerprint_sha256"]), 64)

    def test_missing_package_blocks_runtime_evidence(self):
        registry = load_registry(Path("system_apps/manifest.json"))
        required = {app.package for app in registry.apps if app.source_ready}
        required.remove(next(iter(required)))
        report = evaluate_runtime_snapshot({
            "sys.boot_completed": "1",
            "ro.product.name": "swirphoneos_cf_x86_64",
            "ro.build.fingerprint": "swir/test/build:17/ABC/1:userdebug/test-keys",
        }, frozenset(required), registry)
        self.assertFalse(report["runtime_evidence_complete"])
        self.assertEqual(len(report["missing_required_packages"]), 1)

    def test_only_local_emulator_transports_are_accepted(self):
        device = select_local_device(parse_local_devices("List of devices attached\n127.0.0.1:6520 device product:test\n"))
        self.assertEqual(device.state, "device")
        with self.assertRaises(CuttlefishEvidenceError):
            parse_local_devices("List of devices attached\n192.168.1.20:5555 device\n")

    def test_package_inventory_is_strict(self):
        self.assertEqual(parse_packages("package:org.swir.phoneos.clock\n"), frozenset({"org.swir.phoneos.clock"}))
        with self.assertRaises(CuttlefishEvidenceError):
            parse_packages("unexpected line\n")

    def test_collector_allowlist_rejects_mutating_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            adb = Path(temp) / ("adb.exe" if __import__("os").name == "nt" else "adb")
            adb.write_text("placeholder", encoding="utf-8")
            collector = CuttlefishEvidenceCollector(adb)
            with self.assertRaises(CuttlefishEvidenceError):
                collector._run(("-s", "127.0.0.1:6520", "install", "app.apk"))


if __name__ == "__main__":
    unittest.main()
