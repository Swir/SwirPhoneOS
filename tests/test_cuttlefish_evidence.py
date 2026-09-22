from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from swirphoneos.cuttlefish_evidence import CuttlefishEvidenceCollector, CuttlefishEvidenceError, evaluate_runtime_snapshot, parse_local_devices, parse_packages, parse_resolved_activity, select_local_device
from swirphoneos.system_apps import load_registry


class CuttlefishEvidenceTests(unittest.TestCase):
    def _properties(self):
        return {
            "sys.boot_completed":"1\n",
            "ro.product.name":"swirphoneos_cf_x86_64\n",
            "ro.product.device":"vsoc_x86_64_only\n",
            "ro.product.manufacturer":"Swir\n",
            "ro.product.model":"SwirPhoneOS Cuttlefish Developer\n",
            "ro.build.fingerprint":"Swir/swirphoneos_cf_x86_64/vsoc_x86_64_only:17/CP2A.260605.016/1:userdebug/test-keys\n",
            "ro.build.id":"CP2A.260605.016\n",
            "ro.build.type":"userdebug\n",
            "ro.build.tags":"test-keys\n",
            "ro.build.version.release":"17\n",
            "ro.build.version.sdk":"37\n",
            "ro.build.version.security_patch":"2026-06-05\n",
            "persist.sys.locale":"pl-PL\n",
        }

    def test_complete_snapshot_requires_exact_identity_beta_packages_and_launchers(self):
        registry=load_registry(Path("system_apps/manifest.json")); required=frozenset(app.package for app in registry.first_beta_apps)
        report=evaluate_runtime_snapshot(self._properties(),required,registry,required)
        self.assertTrue(report["runtime_evidence_complete"]); self.assertTrue(report["identity_matches"]); self.assertEqual(report["api_level"],"37")
        self.assertEqual(report["missing_required_packages"],[]); self.assertEqual(report["missing_launchable_packages"],[])
        self.assertEqual(sorted(report["required_source_ready_packages"]), sorted(required))
        self.assertFalse(report["status_promotion_performed"]); self.assertFalse(report["device_write_allowed"]); self.assertEqual(len(report["build_fingerprint_sha256"]),64)

    def test_identity_drift_blocks_runtime_evidence(self):
        registry=load_registry(Path("system_apps/manifest.json")); required=frozenset(app.package for app in registry.first_beta_apps)
        props=self._properties(); props["ro.build.version.sdk"]="36\n"
        report=evaluate_runtime_snapshot(props,required,registry,required)
        self.assertFalse(report["runtime_evidence_complete"]); self.assertFalse(report["identity_checks"]["api_level"])

    def test_missing_or_nonlaunchable_beta_package_blocks_runtime_evidence(self):
        registry=load_registry(Path("system_apps/manifest.json")); required={app.package for app in registry.first_beta_apps}; missing=next(iter(required))
        report=evaluate_runtime_snapshot(self._properties(),frozenset(required),registry,frozenset(required-{missing}))
        self.assertFalse(report["runtime_evidence_complete"]); self.assertEqual(report["missing_launchable_packages"],[missing])

    def test_post_beta_source_ready_package_is_not_a_runtime_gate(self):
        registry=load_registry(Path("system_apps/manifest.json")); required=frozenset(app.package for app in registry.first_beta_apps)
        post_beta=next(app.package for app in registry.apps if app.source_ready and not app.critical_for_beta)
        report=evaluate_runtime_snapshot(self._properties(),required,registry,required)
        self.assertTrue(report["runtime_evidence_complete"])
        self.assertNotIn(post_beta, report["required_source_ready_packages"])

    def test_only_local_emulator_transports_are_accepted(self):
        device=select_local_device(parse_local_devices("List of devices attached\n127.0.0.1:6520 device product:test\n")); self.assertEqual(device.state,"device")
        with self.assertRaises(CuttlefishEvidenceError): parse_local_devices("List of devices attached\n192.168.1.20:5555 device\n")

    def test_package_and_launcher_inventory_is_strict(self):
        self.assertEqual(parse_packages("package:org.swir.phoneos.clock\n"),frozenset({"org.swir.phoneos.clock"}))
        self.assertTrue(parse_resolved_activity("org.swir.phoneos.clock/.MainActivity\n","org.swir.phoneos.clock"))
        self.assertFalse(parse_resolved_activity("No activity found\n","org.swir.phoneos.clock"))
        with self.assertRaises(CuttlefishEvidenceError): parse_resolved_activity("org.other/.MainActivity\n","org.swir.phoneos.clock")

    def test_collector_allowlist_rejects_mutating_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            adb=Path(temp)/("adb.exe" if __import__("os").name=="nt" else "adb"); adb.write_text("placeholder",encoding="utf-8"); collector=CuttlefishEvidenceCollector(adb)
            with self.assertRaises(CuttlefishEvidenceError): collector._run(("-s","127.0.0.1:6520","install","app.apk"))
            with self.assertRaises(CuttlefishEvidenceError): collector._run(("-s","127.0.0.1:6520","shell","am","start","org.swir.phoneos.clock/.MainActivity"))

if __name__=="__main__": unittest.main()
