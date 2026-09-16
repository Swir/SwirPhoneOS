"""System-app registry contract checks."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from swirphoneos.system_apps import REQUIRED_APP_IDS, SystemAppRegistryError, load_registry, public_registry_summary, validate_registry
MANIFEST=Path("system_apps/manifest.json")
class SystemAppRegistryTests(unittest.TestCase):
    def setUp(self): self.data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    def test_repository_manifest_contains_exact_essential_suite(self):
        registry=load_registry(MANIFEST); self.assertEqual(registry.app_ids,REQUIRED_APP_IDS); self.assertEqual(len(registry.apps),20)
    def test_source_ready_is_distinct_from_android_runtime(self):
        summary=public_registry_summary(load_registry(MANIFEST)); self.assertEqual(summary["source_ready"],9); self.assertEqual(summary["runtime_implemented"],0); self.assertEqual(summary["hardware_verified"],0); self.assertGreaterEqual(summary["beta_critical_count"],5); self.assertEqual(summary["beta_critical_runtime_implemented"],0)
    def test_source_ready_apps_remain_below_runtime(self):
        states={app.app_id:app.status for app in load_registry(MANIFEST).apps}
        for app_id in ("settings","calculator","files","device_care","update","privacy","clock","notes","calendar"): self.assertEqual(states[app_id],"ANDROID_SOURCE")
    def test_unique_packages(self):
        registry=load_registry(MANIFEST); self.assertEqual(len({app.package for app in registry.apps}),len(registry.apps))
    def test_missing_essential_app_is_rejected(self):
        bad=deepcopy(self.data); bad["apps"]=[app for app in bad["apps"] if app["id"]!="settings"]
        with self.assertRaises(SystemAppRegistryError): validate_registry(bad)
    def test_foreign_namespace_is_rejected(self):
        bad=deepcopy(self.data); bad["apps"][0]["package"]="com.example.phone"
        with self.assertRaises(SystemAppRegistryError): validate_registry(bad)
    def test_duplicate_package_is_rejected(self):
        bad=deepcopy(self.data); bad["apps"][1]["package"]=bad["apps"][0]["package"]
        with self.assertRaises(SystemAppRegistryError): validate_registry(bad)
    def test_fake_hardware_verification_is_rejected_for_non_hardware_app(self):
        bad=deepcopy(self.data); next(app for app in bad["apps"] if app["id"]=="calculator")["status"]="HARDWARE_VERIFIED"
        with self.assertRaises(SystemAppRegistryError): validate_registry(bad)
if __name__=="__main__": unittest.main()
