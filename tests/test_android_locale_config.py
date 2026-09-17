from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from swirphoneos.android_locale_config import (
    AndroidLocaleConfigError,
    validate_android_locale_configs,
)
from swirphoneos.i18n import LOCALES


ANDROID_NS = "http://schemas.android.com/apk/res/android"


class AndroidLocaleConfigTests(unittest.TestCase):
    def test_checked_in_suite_declares_exact_shared_locales_and_staging(self):
        summary = validate_android_locale_configs()
        self.assertEqual(summary.app_count, 20)
        self.assertEqual(summary.locale_count, len(LOCALES))
        self.assertEqual(summary.locale_codes, tuple(LOCALES))
        self.assertEqual(summary.staged_config_count, 20)

    def _copy_product(self, temp: str) -> Path:
        target = Path(temp) / "aosp_product"
        shutil.copytree(Path("platform/aosp_product"), target)
        return target

    def test_missing_manifest_locale_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_product(temp)
            path = root / "apps" / "SwirSettings" / "AndroidManifest.xml"
            tree = ET.parse(path)
            app = tree.getroot().find("application")
            self.assertIsNotNone(app)
            del app.attrib[f"{{{ANDROID_NS}}}localeConfig"]
            tree.write(path, encoding="utf-8", xml_declaration=True)
            with self.assertRaises(AndroidLocaleConfigError):
                validate_android_locale_configs(root)

    def test_locale_config_catalog_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_product(temp)
            path = root / "apps" / "SwirClock" / "res" / "xml" / "locales_config.xml"
            tree = ET.parse(path)
            locale = list(tree.getroot())[-1]
            locale.set(f"{{{ANDROID_NS}}}name", "xx")
            tree.write(path, encoding="utf-8", xml_declaration=True)
            with self.assertRaises(AndroidLocaleConfigError):
                validate_android_locale_configs(root)

    def test_missing_exact_staging_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_product(temp)
            (root / "stage_manifest.d" / "runtime-locales.json").unlink()
            with self.assertRaises(AndroidLocaleConfigError):
                validate_android_locale_configs(root)


if __name__ == "__main__":
    unittest.main()
