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
        self.assertEqual(summary["design_contract"], "swirphoneos-design-v2")
        self.assertEqual(summary["integrated_core_apps"], ["settings", "files", "update", "privacy", "device_care"])
        self.assertEqual(summary["integrated_core_app_count"], 5)
        self.assertEqual(summary["integrated_system_apps"], list(SYSTEM_APPS))
        self.assertEqual(summary["integrated_system_app_count"], 20)
        self.assertEqual(summary["expected_system_app_count"], 20)
        self.assertTrue(summary["all_system_apps_integrated"])
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
