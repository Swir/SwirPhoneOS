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
        self.assertEqual(set(summary["source_ready_apps"]), {"calculator", "settings", "files", "device_care"})
        self.assertEqual(summary["source_ready_count"], 4)
        self.assertEqual(summary["localized_catalogs"], 32)
        for capability in (
            "basic_math", "system_settings", "search", "device_status", "browse",
            "copy_move_rename", "share", "safe_delete", "storage_status",
            "battery_status", "thermal_status", "hardware_diagnostics",
        ):
            self.assertIn(capability, summary["implemented_capabilities"])
        self.assertEqual(summary["remaining_target_capabilities"], ["scientific_math"])
        self.assertFalse(summary["android_build_verified"])
        self.assertFalse(summary["runtime_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        product = root / "product"
        shutil.copytree(Path("platform/aosp_product"), product)
        registry = root / "manifest.json"
        shutil.copy2(Path("system_apps/manifest.json"), registry)
        return temp, product, registry

    def test_permission_request_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            manifest = product / "apps/SwirSettings/AndroidManifest.xml"
            text = manifest.read_text(encoding="utf-8").replace(
                "<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application', 1
            )
            manifest.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_broad_storage_permission_primitive_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"
            activity.write_text(activity.read_text(encoding="utf-8") + "\n// MANAGE_EXTERNAL_STORAGE\n", encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_missing_locale_key_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirDeviceCare/res/values-de/strings.xml"
            text = strings.read_text(encoding="utf-8").replace('<string name="refresh">Aktualisieren</string>', "")
            strings.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_registry_must_not_claim_android_runtime(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            data = json.loads(registry.read_text(encoding="utf-8"))
            next(app for app in data["apps"] if app["id"] == "settings")["status"] = "ANDROID_RUNTIME"
            registry.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_unreviewed_settings_action_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            catalog = product / "apps/SwirSettings/src/org/swir/phoneos/settings/SettingsCatalog.java"
            text = catalog.read_text(encoding="utf-8").replace(
                "android.settings.WIFI_SETTINGS", "android.settings.MANAGE_UNKNOWN_APP_SOURCES", 1
            )
            catalog.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_files_must_keep_user_granted_tree_workflow(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"
            text = activity.read_text(encoding="utf-8").replace(
                "Intent.ACTION_OPEN_DOCUMENT_TREE", "Intent.ACTION_OPEN_DOCUMENT", 1
            )
            activity.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_device_care_must_keep_real_thermal_state(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirDeviceCare/src/org/swir/phoneos/device_care/MainActivity.java"
            text = activity.read_text(encoding="utf-8").replace("getCurrentThermalStatus()", "hashCode()", 1)
            activity.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_duplicate_stage_destination_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            stage = product / "stage_manifest.json"
            data = json.loads(stage.read_text(encoding="utf-8"))
            data["files"][1]["destination"] = data["files"][0]["destination"]
            stage.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)


if __name__ == "__main__":
    unittest.main()
