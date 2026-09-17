from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.android_i18n import (
    AndroidLocalizationError,
    public_android_localization_summary,
    validate_android_localization,
)


class AndroidLocalizationTests(unittest.TestCase):
    def _copy_fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        product = root / "product"
        shutil.copytree(Path("platform/aosp_product"), product)
        registry = root / "manifest.json"
        shutil.copy2(Path("system_apps/manifest.json"), registry)
        return temp, product, registry

    def test_repository_android_localization_is_source_lint_clean(self):
        summary = public_android_localization_summary(validate_android_localization())
        self.assertEqual(summary["status"], "SOURCE_LINT_ONLY_NOT_RUNTIME_VERIFIED")
        self.assertEqual(summary["source_locale"], "en")
        self.assertEqual(summary["locale_count"], 8)
        self.assertEqual(summary["source_ready_app_count"], 17)
        self.assertIn("ar", summary["locales"])
        self.assertGreater(summary["source_string_entries"], 0)
        self.assertGreater(summary["production_java_files_scanned"], 0)
        self.assertTrue(summary["resource_key_parity_verified"])
        self.assertTrue(summary["format_placeholder_parity_verified"])
        self.assertTrue(summary["plural_contract_verified"])
        self.assertTrue(summary["direct_ui_literal_sinks_rejected"])
        self.assertFalse(summary["runtime_locale_switch_verified"])
        self.assertFalse(summary["runtime_rtl_verified"])
        self.assertFalse(summary["android_build_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def test_android_format_placeholder_type_drift_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirDeviceCare/res/values-pl/strings.xml"
            source = strings.read_text(encoding="utf-8")
            self.assertIn("%1$d%%", source)
            strings.write_text(source.replace("%1$d%%", "%1$s%%", 1), encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_android_format_placeholder_index_drift_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirDeviceCare/res/values-ar/strings.xml"
            source = strings.read_text(encoding="utf-8")
            self.assertIn("%1$s %2$s", source)
            strings.write_text(source.replace("%1$s %2$s", "%2$s %2$s", 1), encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_direct_java_ui_literal_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirSettings/src/org/swir/phoneos/settings/MainActivity.java"
            source = activity.read_text(encoding="utf-8")
            activity.write_text(source + '\nclass LocalizationRegression { void bind(android.widget.TextView view) { view.setText("Hardcoded status"); } }\n', encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_ui_literal_inside_comment_is_ignored(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            activity = product / "apps/SwirSettings/src/org/swir/phoneos/settings/MainActivity.java"
            source = activity.read_text(encoding="utf-8")
            activity.write_text(source + '\n// Documentation example only: view.setText("Not executable")\n', encoding="utf-8")
            validate_android_localization(product, registry)

    def test_locale_key_loss_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirContacts/res/values-de/strings.xml"
            source = strings.read_text(encoding="utf-8")
            marker = '<string name="search_hint">'
            self.assertIn(marker, source)
            start = source.index(marker)
            end = source.index("</string>", start) + len("</string>")
            strings.write_text(source[:start] + source[end:], encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_plural_translation_may_use_locale_specific_quantities_but_must_preserve_arguments(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            app = product / "apps/SwirCalculator/res"
            source_plural = '<plurals name="history_count"><item quantity="one">%1$d item</item><item quantity="other">%1$d items</item></plurals>'
            generic_plural = '<plurals name="history_count"><item quantity="other">%1$d items</item></plurals>'
            arabic_plural = '<plurals name="history_count"><item quantity="zero">%1$d items</item><item quantity="two">%1$d items</item><item quantity="few">%1$d items</item><item quantity="many">%1$d items</item><item quantity="other">%1$d items</item></plurals>'
            for directory in ("values", "values-pl", "values-nb", "values-de", "values-es", "values-fr", "values-pt", "values-ar"):
                path = app / directory / "strings.xml"
                text = path.read_text(encoding="utf-8")
                plural = source_plural if directory == "values" else arabic_plural if directory == "values-ar" else generic_plural
                path.write_text(text.replace("</resources>", plural + "\n</resources>"), encoding="utf-8")
            validate_android_localization(product, registry)

            arabic = app / "values-ar/strings.xml"
            arabic.write_text(arabic.read_text(encoding="utf-8").replace("%1$d items", "%1$s items", 1), encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_plural_without_other_is_rejected(self):
        temp, product, registry = self._copy_fixture()
        with temp:
            strings = product / "apps/SwirCalculator/res/values/strings.xml"
            source = strings.read_text(encoding="utf-8")
            plural = '<plurals name="history_count"><item quantity="one">%1$d item</item></plurals>'
            strings.write_text(source.replace("</resources>", plural + "\n</resources>"), encoding="utf-8")
            with self.assertRaises(AndroidLocalizationError):
                validate_android_localization(product, registry)

    def test_clock_display_skeletons_are_nontranslatable_resources(self):
        activity = Path("platform/aosp_product/apps/SwirClock/src/org/swir/phoneos/clock/MainActivity.java").read_text(encoding="utf-8")
        invariants = Path("platform/aosp_product/apps/SwirClock/res/values/invariants.xml").read_text(encoding="utf-8")
        self.assertNotIn('setText("00:00:00")', activity)
        self.assertNotIn('text("00:00:00"', activity)
        self.assertNotIn('text("--:--"', activity)
        self.assertIn("R.string.duration_zero", activity)
        self.assertIn("R.string.clock_placeholder", activity)
        self.assertIn('name="duration_zero" translatable="false"', invariants)
        self.assertIn('name="clock_placeholder" translatable="false"', invariants)


if __name__ == "__main__":
    unittest.main()
