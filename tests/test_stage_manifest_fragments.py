from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_workspace import AospWorkspaceError, stage_product_tree


class StageManifestFragmentTests(unittest.TestCase):
    def _product(self, root: Path) -> Path:
        product = root / "product"
        (product / "apps/Test").mkdir(parents=True)
        (product / "stage_manifest.d").mkdir()
        (product / "AndroidProducts.mk").write_text("a\n", encoding="utf-8")
        (product / "swirphoneos_cf_x86_64.mk").write_text("b\n", encoding="utf-8")
        (product / "apps/Test/Android.bp").write_text("android_app {}\n", encoding="utf-8")
        primary = {"schema_version": 1, "files": [
            {"source": "AndroidProducts.mk", "destination": "vendor/swir/products/AndroidProducts.mk"},
            {"source": "swirphoneos_cf_x86_64.mk", "destination": "vendor/swir/products/swirphoneos_cf_x86_64.mk"},
        ]}
        fragment = {"schema_version": 1, "files": [
            {"source": "apps/Test/Android.bp", "destination": "vendor/swir/apps/Test/Android.bp"},
        ]}
        (product / "stage_manifest.json").write_text(json.dumps(primary), encoding="utf-8")
        (product / "stage_manifest.d/test.json").write_text(json.dumps(fragment), encoding="utf-8")
        return product

    def test_fragment_is_included_in_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = stage_product_tree(self._product(root), root / "aosp")
            self.assertEqual(result["file_count"], 3)
            self.assertTrue(any(item["destination"].endswith("vendor/swir/apps/Test/Android.bp") for item in result["files"]))

    def test_duplicate_destination_across_fragment_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = self._product(root)
            fragment = product / "stage_manifest.d/test.json"
            data = json.loads(fragment.read_text(encoding="utf-8"))
            data["files"][0]["destination"] = "vendor/swir/products/AndroidProducts.mk"
            fragment.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AospWorkspaceError):
                stage_product_tree(product, root / "aosp")


if __name__ == "__main__":
    unittest.main()
