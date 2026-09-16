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
    def test_repository_calculator_source_is_complete_but_not_runtime_claimed(self):
        summary = public_android_app_source_summary(validate_android_app_sources())
        self.assertEqual(summary["status"], "SOURCE_READY_NOT_BUILT")
        self.assertEqual(summary["source_ready_apps"], ["calculator"])
        self.assertEqual(summary["localized_catalogs"], 8)
        self.assertIn("basic_math", summary["implemented_capabilities"])
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
            manifest = product / "apps/SwirCalculator/AndroidManifest.xml"
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
            strings = product / "apps/SwirCalculator/res/values-de/strings.xml"
            text = strings.read_text(encoding="utf-8").replace('<string name="error">Fehler</string>', "")
            strings.write_text(text, encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)

    def test_registry_must_not_claim_android_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            shutil.copytree(Path("platform/aosp_product"), product)
            data = json.loads(Path("system_apps/manifest.json").read_text(encoding="utf-8"))
            next(app for app in data["apps"] if app["id"] == "calculator")["status"] = "ANDROID_RUNTIME"
            registry = root / "manifest.json"
            registry.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AndroidAppSourceError):
                validate_android_app_sources(product, registry)


if __name__ == "__main__":
    unittest.main()
