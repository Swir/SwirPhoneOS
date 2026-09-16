from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.android_apps import (
    AndroidAppSourceError,
    public_android_app_source_summary,
    validate_android_app_sources,
)


class AndroidAppSourceTests(unittest.TestCase):
    def test_repository_source_apps_are_complete_but_not_runtime_claimed(self):
        summary = public_android_app_source_summary(validate_android_app_sources())
        self.assertEqual(summary["status"], "SOURCE_READY_NOT_BUILT")
        self.assertEqual(set(summary["source_ready_apps"]), {"calculator", "settings"})
        self.assertEqual(summary["source_ready_count"], 2)
        self.assertEqual(summary["localized_catalogs"], 16)
        self.assertIn("basic_math", summary["implemented_capabilities"])
        self.assertIn("system_settings", summary["implemented_capabilities"])
        self.assertIn("search", summary["implemented_capabilities"])
        self.assertIn("device_status", summary["implemented_capabilities"])
        self.assertIn("scientific_math", summary["remaining_target_capabilities"])
        self.assertFalse(summary["android_build_verified"])
        self.assertFalse(summary["runtime_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def test_permission_request_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            registry = root / "manifest.json"
            shutil.copy2(Path("system_apps/manifest.json"), registry)
            manifest = product / "apps/SwirSettings/AndroidManifest.xml"
            text = manifest.read_text(encoding="utf-8").replace(
                "<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application', 1
            )
            manifest.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_missing_locale_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            registry = root / "manifest.json"
            shutil.copy2(Path("system_apps/manifest.json"), registry)
            strings = product / "apps/SwirSettings/res/values-de/strings.xml"
            text = strings.read_text(encoding="utf-8").replace('<string name="apps">Apps</string>', "")
            strings.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_registry_must_not_claim_android_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            data = json.loads(Path("system_apps/manifest.json").read_text(encoding="utf-8"))
            next(app for app in data["apps"] if app["id"] == "settings")["status"] = "ANDROID_RUNTIME"
            registry = root / "manifest.json"
            registry.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_unreviewed_settings_action_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            registry = root / "manifest.json"
            shutil.copy2(Path("system_apps/manifest.json"), registry)
            catalog = product / "apps/SwirSettings/src/org/swir/phoneos/settings/SettingsCatalog.java"
            text = catalog.read_text(encoding="utf-8").replace(
                "android.settings.WIFI_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES", 1
            )
            catalog.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_duplicate_stage_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            registry = root / "manifest.json"
            shutil.copy2(Path("system_apps/manifest.json"), registry)
            stage = product / "stage_manifest.json"
            data = json.loads(stage.read_text(encoding="utf-8"))
            data["files"][1]["destination"] = data["files"][0]["destination"]
            stage.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)


if __name__ == "__main__":
    unittest.main()
