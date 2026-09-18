from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from swirphoneos.design_contract import DesignContractError, SYSTEM_APPS, validate_design_contract


class DesignContractTests(unittest.TestCase):
    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "aosp_product"
        shutil.copytree(Path("platform/aosp_product"), root)
        return temp, root

    def test_repository_design_contract_covers_every_system_app_but_is_source_ready_only(self):
        summary = validate_design_contract()
        self.assertEqual(summary["status"], "SOURCE_CONTRACT_READY_NOT_BUILT")
        self.assertEqual(summary["design_contract"], "swirphoneos-design-v7")
        self.assertEqual(summary["integrated_core_apps"], ["settings", "files", "update", "privacy", "device_care"])
        self.assertEqual(summary["integrated_core_app_count"], 5)
        self.assertEqual(summary["integrated_system_apps"], list(SYSTEM_APPS))
        self.assertEqual(summary["integrated_system_app_count"], 20)
        self.assertEqual(summary["expected_system_app_count"], 20)
        self.assertTrue(summary["all_system_apps_integrated"])
        self.assertEqual(
            summary["tokenized_apps"],
            ["phone", "messages", "camera", "calculator", "settings", "files", "browser", "backup", "update", "privacy", "device_care", "calendar", "clock"],
        )
        self.assertEqual(summary["tokenized_app_count"], 13)
        self.assertEqual(summary["tokenized_core_apps"], ["settings", "files", "update", "privacy", "device_care"])
        self.assertEqual(summary["tokenized_core_app_count"], 5)
        self.assertEqual(summary["expected_core_app_count"], 5)
        self.assertTrue(summary["hardcoded_color_free_cohort_verified"])
        self.assertTrue(summary["all_core_apps_tokenized"])
        self.assertTrue(summary["day_night_tokens_declared"])
        self.assertEqual(summary["minimum_touch_target_token_dp"], 48)
        self.assertFalse(summary["android_build_verified"])
        self.assertFalse(summary["runtime_visual_review_verified"])
        self.assertFalse(summary["accessibility_review_verified"])
        self.assertFalse(summary["device_write_allowed"])

    def test_missing_static_library_link_in_beta_core_app_is_rejected(self):
        temp, root = self._fixture()
        with temp:
            bp = root / "apps/SwirFiles/Android.bp"
            bp.write_text(bp.read_text(encoding="utf-8").replace('    static_libs: ["SwirDesign"],\n', "", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_missing_static_library_link_in_non_core_app_is_rejected(self):
        temp, root = self._fixture()
        with temp:
            bp = root / "apps/SwirPhone/Android.bp"
            bp.write_text(bp.read_text(encoding="utf-8").replace('    static_libs: ["SwirDesign"],\n', "", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_legacy_theme_regression_in_core_app_is_rejected(self):
        temp, root = self._fixture()
        with temp:
            manifest = root / "apps/SwirSettings/AndroidManifest.xml"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("@style/Theme.SwirPhoneOS", "@android:style/Theme.Material.NoActionBar", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_missing_shared_theme_in_non_core_app_is_rejected(self):
        temp, root = self._fixture()
        with temp:
            manifest = root / "apps/SwirRoot/AndroidManifest.xml"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("@style/Theme.SwirPhoneOS", "@android:style/Theme.Material.NoActionBar", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_tokenized_cohort_rejects_direct_color_literals_in_communication_app(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirPhone/src/org/swir/phoneos/phone/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.content.Intent;", "import android.content.Intent;\nimport android.graphics.Color;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_tokenized_cohort_rejects_direct_color_literals_in_core_app(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirSettings/src/org/swir/phoneos/settings/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.os.Build;", "import android.graphics.Color;\nimport android.os.Build;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_calculator_cannot_regress_to_direct_color_literals(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirCalculator/src/org/swir/phoneos/calculator/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.os.Bundle;", "import android.graphics.Color;\nimport android.os.Bundle;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_calculator_must_keep_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirCalculator/src/org/swir/phoneos/calculator/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_calendar_cannot_regress_to_direct_color_literals(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirCalendar/src/org/swir/phoneos/calendar/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.app.Activity;", "import android.app.Activity;\nimport android.graphics.Color;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_clock_cannot_regress_to_direct_color_literals(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirClock/src/org/swir/phoneos/clock/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.content.Intent;", "import android.content.Intent;\nimport android.graphics.Color;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_clock_must_keep_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirClock/src/org/swir/phoneos/clock/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_browser_cannot_regress_to_direct_color_literals(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirBrowser/src/org/swir/phoneos/browser/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.app.DownloadManager;", "import android.app.DownloadManager;\nimport android.graphics.Color;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_browser_must_keep_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirBrowser/src/org/swir/phoneos/browser/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_backup_cannot_regress_to_direct_color_literals(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirBackup/src/org/swir/phoneos/backup/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("import android.net.Uri;", "import android.graphics.Color;\nimport android.net.Uri;", 1), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_backup_must_keep_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirBackup/src/org/swir/phoneos/backup/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_files_cannot_regress_to_legacy_color_literals_after_core_completion(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"
            source.write_text(
                source.read_text(encoding="utf-8").replace(
                    "import android.net.Uri;",
                    "import android.graphics.Color;\nimport android.net.Uri;",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_files_must_keep_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirFiles/src/org/swir/phoneos/files/MainActivity.java"
            source.write_text(
                source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"),
                encoding="utf-8",
            )
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_tokenized_cohort_requires_shared_touch_target_reference(self):
        temp, root = self._fixture()
        with temp:
            source = root / "apps/SwirPrivacy/src/org/swir/phoneos/privacy/MainActivity.java"
            source.write_text(source.read_text(encoding="utf-8").replace("R.dimen.swir_touch_min", "R.dimen.swir_space_lg"), encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_night_palette_must_match_day_token_inventory(self):
        temp, root = self._fixture()
        with temp:
            colors = root / "design/SwirDesign/res/values-night/colors.xml"
            source = colors.read_text(encoding="utf-8")
            source = source.replace('    <color name="swir_success">#77E0A3</color>\n', "", 1)
            colors.write_text(source, encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_stage_fragment_must_keep_exact_design_inventory(self):
        temp, root = self._fixture()
        with temp:
            stage = root / "stage_manifest.d/design.json"
            source = stage.read_text(encoding="utf-8")
            source = source.replace('    {"source":"design/SwirDesign/res/values/dimens.xml","destination":"vendor/swir/design/SwirDesign/res/values/dimens.xml"},\n', "", 1)
            stage.write_text(source, encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)

    def test_duplicate_stage_json_key_is_rejected(self):
        temp, root = self._fixture()
        with temp:
            stage = root / "stage_manifest.d/design.json"
            source = stage.read_text(encoding="utf-8").replace('  "schema_version": 1,', '  "schema_version": 1,\n  "schema_version": 1,', 1)
            stage.write_text(source, encoding="utf-8")
            with self.assertRaises(DesignContractError):
                validate_design_contract(root)


if __name__ == "__main__":
    unittest.main()
