from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
import unittest

from swirphoneos.aosp_workspace import (
    AospWorkspaceError,
    make_workspace_plan,
    public_manifest_evidence,
    stage_product_tree,
    validate_resolved_manifest,
)
from swirphoneos.platform import PlatformBaseline
from swirphoneos.product_contract import ProductContract


class AospWorkspaceTests(unittest.TestCase):
    def baseline(self) -> PlatformBaseline:
        return PlatformBaseline(
            status="PINNED_NOT_BUILT",
            checked_date="2026-09-16",
            platform="Android 17",
            api_level=37,
            manifest_url="https://android.googlesource.com/platform/manifest",
            tracking_manifest="android-latest-release",
            resolved_release_branch="android17-release",
            candidate_release_tag="android-17.0.0_r1",
            candidate_build_id="BP1A.250305.019",
            security_patch_level="2026-03-05",
            manifest_commit="1" * 40,
            manifest_tree="2" * 40,
            tag_object="3" * 40,
            repo_init_revision="android-17.0.0_r1",
            download_started=False,
            build_completed=False,
            sources=("https://source.android.com/docs/setup/start/build-numbers",),
        )

    def contract(self, root: Path) -> ProductContract:
        return ProductContract(
            "swirphoneos_cf_x86_64",
            "device/google/cuttlefish/vsoc_x86_64_only/phone/aosp_cf.mk",
            "swirphoneos_cf_x86_64-aosp_current-userdebug",
            root / "swirphoneos_cf_x86_64.mk",
            root / "AndroidProducts.mk",
        )

    def test_plan_is_pinned_and_never_claims_device_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = make_workspace_plan(self.baseline(), self.contract(root), root / "aosp", jobs=12)
        self.assertEqual(plan.revision, "android-17.0.0_r1")
        self.assertEqual(plan.jobs, 12)
        self.assertEqual(plan.commands[0][:2], ("repo", "init"))
        self.assertIn("swirphoneos_cf_x86_64-aosp_current-userdebug", plan.commands[-1][-1])

    def test_plan_rejects_unpinned_baseline(self):
        baseline = self.baseline()
        baseline = PlatformBaseline(**{**baseline.__dict__, "manifest_commit": None})
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(AospWorkspaceError):
            make_workspace_plan(baseline, self.contract(Path(temp)), Path(temp) / "aosp")

    def test_plan_rejects_root_workspace_and_bad_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            contract = self.contract(Path(temp))
            with self.assertRaises(AospWorkspaceError):
                make_workspace_plan(self.baseline(), contract, Path(Path(temp).anchor))
            with self.assertRaises(AospWorkspaceError):
                make_workspace_plan(self.baseline(), contract, Path(temp) / "aosp", jobs=0)

    def test_manifest_requires_every_project_to_be_full_sha(self):
        xml = (
            '<manifest><project name="platform/build" path="build" revision="'
            + "1" * 40
            + '" /><project name="platform/frameworks/base" revision="'
            + "2" * 40
            + '" /></manifest>'
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "resolved.xml"
            path.write_text(xml, encoding="utf-8")
            evidence = validate_resolved_manifest(path)
        self.assertEqual(evidence.project_count, 2)
        self.assertEqual(len(evidence.sha256), 64)
        self.assertTrue(public_manifest_evidence(evidence)["all_projects_pinned"])

    def test_manifest_rejects_floating_revision_and_duplicates(self):
        floating = "<manifest><project name='x' path='x' revision='main'/></manifest>"
        duplicate = (
            '<manifest><project name="x" path="x" revision="'
            + "1" * 40
            + '" /><project name="y" path="x" revision="'
            + "2" * 40
            + '" /></manifest>'
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "resolved.xml"
            path.write_text(floating, encoding="utf-8")
            with self.assertRaises(AospWorkspaceError):
                validate_resolved_manifest(path)
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaises(AospWorkspaceError):
                validate_resolved_manifest(path)

    def _fake_checkout(self, root: Path) -> Path:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        (workspace / "build").mkdir()
        (workspace / "build/envsetup.sh").write_text("# test\n", encoding="utf-8")
        return workspace

    def _legacy_product(self, root: Path) -> Path:
        product = root / "product"
        product.mkdir()
        (product / "AndroidProducts.mk").write_text("alpha\n", encoding="utf-8")
        (product / "swirphoneos_cf_x86_64.mk").write_text("beta\n", encoding="utf-8")
        return product

    def test_staging_records_hashes_and_verifies_copied_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = self._legacy_product(root)
            workspace = root / "aosp"
            dry = stage_product_tree(product, workspace)
            self.assertEqual(dry["schema_version"], 4)
            self.assertFalse(dry["executed"])
            self.assertFalse(dry["copy_verified"])
            self.assertEqual(dry["file_count"], 2)
            self.assertEqual(len(dry["staged_content_sha256"]), 64)
            expected = hashlib.sha256(b"alpha\n").hexdigest()
            records = {item["source_relative"]: item for item in dry["files"]}
            self.assertEqual(records["AndroidProducts.mk"]["sha256"], expected)
            self.assertFalse((workspace / "vendor").exists())

            with self.assertRaises(AospWorkspaceError):
                stage_product_tree(product, workspace, execute=True)

            self._fake_checkout(root)
            executed = stage_product_tree(product, workspace, execute=True)
            self.assertTrue(executed["executed"])
            self.assertTrue(executed["copy_verified"])
            self.assertEqual(executed["staged_content_sha256"], dry["staged_content_sha256"])
            self.assertTrue(all(item["copy_verified"] for item in executed["files"]))
            copied = workspace / "vendor/swir/products/AndroidProducts.mk"
            self.assertEqual(copied.read_bytes(), b"alpha\n")

    def test_stage_bundle_digest_changes_when_source_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = self._legacy_product(root)
            first = stage_product_tree(product, root / "aosp-a")["staged_content_sha256"]
            (product / "AndroidProducts.mk").write_text("changed\n", encoding="utf-8")
            second = stage_product_tree(product, root / "aosp-b")["staged_content_sha256"]
            self.assertNotEqual(first, second)

    def test_manifest_whitelist_stages_nested_app_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            (product / "apps/Test").mkdir(parents=True)
            (product / "AndroidProducts.mk").write_text("a\n", encoding="utf-8")
            (product / "swirphoneos_cf_x86_64.mk").write_text("b\n", encoding="utf-8")
            (product / "apps/Test/Android.bp").write_text("android_app {}\n", encoding="utf-8")
            data = {
                "schema_version": 1,
                "files": [
                    {"source": "AndroidProducts.mk", "destination": "vendor/swir/products/AndroidProducts.mk"},
                    {"source": "swirphoneos_cf_x86_64.mk", "destination": "vendor/swir/products/swirphoneos_cf_x86_64.mk"},
                    {"source": "apps/Test/Android.bp", "destination": "vendor/swir/apps/Test/Android.bp"},
                ],
            }
            (product / "stage_manifest.json").write_text(json.dumps(data), encoding="utf-8")
            workspace = self._fake_checkout(root)
            result = stage_product_tree(product, workspace, execute=True)
            self.assertEqual(result["file_count"], 3)
            self.assertTrue(result["copy_verified"])
            self.assertTrue((workspace / "vendor/swir/apps/Test/Android.bp").is_file())

    def test_stage_manifest_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = root / "product"
            product.mkdir()
            (product / "AndroidProducts.mk").write_text("a\n", encoding="utf-8")
            (product / "swirphoneos_cf_x86_64.mk").write_text("b\n", encoding="utf-8")
            data = {
                "schema_version": 1,
                "files": [
                    {"source": "AndroidProducts.mk", "destination": "vendor/swir/products/AndroidProducts.mk"},
                    {"source": "swirphoneos_cf_x86_64.mk", "destination": "../escape.mk"},
                ],
            }
            (product / "stage_manifest.json").write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(AospWorkspaceError):
                stage_product_tree(product, root / "aosp")

    @unittest.skipIf(os.name == "nt", "symlink creation is not reliably available on Windows CI")
    def test_execute_rejects_symlinked_destination_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            product = self._legacy_product(root)
            workspace = self._fake_checkout(root)
            outside = root / "outside"
            outside.mkdir()
            (workspace / "vendor").mkdir()
            (workspace / "vendor" / "swir").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(AospWorkspaceError):
                stage_product_tree(product, workspace, execute=True)


if __name__ == "__main__":
    unittest.main()
