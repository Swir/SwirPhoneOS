"""System-app registry contract checks."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from swirphoneos.system_apps import (
    EXPECTED_DESIGN_CONTRACT,
    FIRST_BETA_APP_IDS,
    REQUIRED_APP_IDS,
    SystemAppRegistryError,
    load_registry,
    public_registry_summary,
    validate_registry,
)

MANIFEST = Path("system_apps/manifest.json")


class SystemAppRegistryTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_repository_manifest_contains_exact_essential_suite(self):
        registry = load_registry(MANIFEST)
        self.assertEqual(registry.app_ids, REQUIRED_APP_IDS)
        self.assertEqual(len(registry.apps), 20)
        self.assertEqual(registry.design_contract, EXPECTED_DESIGN_CONTRACT)

    def test_source_ready_is_distinct_from_android_runtime(self):
        summary = public_registry_summary(load_registry(MANIFEST))
        self.assertEqual(summary["source_ready"], 20)
        self.assertEqual(summary["runtime_implemented"], 0)
        self.assertEqual(summary["hardware_verified"], 0)
        self.assertEqual(summary["beta_critical_count"], len(FIRST_BETA_APP_IDS))
        self.assertEqual(summary["beta_critical_runtime_implemented"], 0)
        self.assertTrue(summary["first_beta_scope_frozen"])
        self.assertTrue(summary["first_beta_source_ready"])
        self.assertEqual(summary["first_beta_app_ids"], sorted(FIRST_BETA_APP_IDS))

    def test_first_beta_scope_is_finite_and_matches_manifest_flags(self):
        registry = load_registry(MANIFEST)
        flagged = {app.app_id for app in registry.apps if app.critical_for_beta}
        self.assertEqual(flagged, FIRST_BETA_APP_IDS)
        self.assertEqual(
            FIRST_BETA_APP_IDS,
            frozenset({"files", "settings", "update", "privacy", "device_care", "swirroot"}),
        )
        self.assertEqual(
            [app.app_id for app in registry.first_beta_apps],
            sorted(FIRST_BETA_APP_IDS),
        )
        self.assertTrue(registry.first_beta_source_ready)

    def test_all_essential_apps_are_source_ready_but_below_runtime(self):
        states = {app.app_id: app.status for app in load_registry(MANIFEST).apps}
        for app_id in REQUIRED_APP_IDS:
            self.assertEqual(states[app_id], "ANDROID_SOURCE")

    def test_unique_packages(self):
        registry = load_registry(MANIFEST)
        self.assertEqual(len({app.package for app in registry.apps}), len(registry.apps))

    def test_stale_design_contract_identity_is_rejected(self):
        bad = deepcopy(self.data)
        bad["design_contract"] = "swirphoneos-design-v3"
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_missing_essential_app_is_rejected(self):
        bad = deepcopy(self.data)
        bad["apps"] = [app for app in bad["apps"] if app["id"] != "settings"]
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_foreign_namespace_is_rejected(self):
        bad = deepcopy(self.data)
        bad["apps"][0]["package"] = "com.example.phone"
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_duplicate_package_is_rejected(self):
        bad = deepcopy(self.data)
        bad["apps"][1]["package"] = bad["apps"][0]["package"]
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_first_beta_scope_cannot_expand_silently(self):
        bad = deepcopy(self.data)
        next(app for app in bad["apps"] if app["id"] == "browser")["critical_for_beta"] = True
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_first_beta_scope_cannot_drop_required_swirroot(self):
        bad = deepcopy(self.data)
        next(app for app in bad["apps"] if app["id"] == "swirroot")["critical_for_beta"] = False
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_first_beta_app_must_stay_source_ready(self):
        bad = deepcopy(self.data)
        next(app for app in bad["apps"] if app["id"] == "files")["status"] = "HOST_CONTRACT"
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)

    def test_fake_hardware_verification_is_rejected_for_non_hardware_app(self):
        bad = deepcopy(self.data)
        next(app for app in bad["apps"] if app["id"] == "calculator")["status"] = "HARDWARE_VERIFIED"
        with self.assertRaises(SystemAppRegistryError):
            validate_registry(bad)


if __name__ == "__main__":
    unittest.main()
