from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.build_evidence import BuildEvidenceError, collect_build_evidence, create_evidence_bundle, load_json_report
from swirphoneos.cuttlefish_evidence import evaluate_runtime_snapshot
from swirphoneos.system_apps import load_registry


class BuildEvidenceTests(unittest.TestCase):
    def _workspace(self, root: Path) -> tuple[Path, Path]:
        workspace = root / "aosp"
        (workspace / ".repo").mkdir(parents=True)
        (workspace / "build").mkdir()
        (workspace / "build" / "envsetup.sh").write_text("# test\n", encoding="utf-8")
        out = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64"
        (out / "system").mkdir(parents=True)
        (out / "boot.img").write_bytes(b"boot-image")
        (out / "system.img").write_bytes(b"system-image")
        (out / "vendor.img").write_bytes(b"vendor-image")
        fingerprint = "Swir/swirphoneos_cf_x86_64/vsoc_x86_64_only:17/CP2A.260605.016/1:userdebug/test-keys"
        (out / "system" / "build.prop").write_text(
            "\n".join((
                f"ro.build.fingerprint={fingerprint}",
                "ro.build.id=CP2A.260605.016",
                "ro.build.version.release=17",
                "ro.build.version.sdk=37",
                "ro.build.version.security_patch=2026-06-05",
                "ro.build.type=userdebug",
            )) + "\n",
            encoding="utf-8",
        )
        manifest = root / "resolved.xml"
        manifest.write_text(
            '<manifest><project name="platform/build" path="build/make" revision="1111111111111111111111111111111111111111"/><project name="platform/frameworks/base" path="frameworks/base" revision="2222222222222222222222222222222222222222"/></manifest>',
            encoding="utf-8",
        )
        return workspace, manifest

    def test_collects_manifest_build_identity_and_artifact_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._workspace(root)
            report = collect_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))
            self.assertTrue(report["build_evidence_complete"])
            self.assertEqual(report["expected_product"], "swirphoneos_cf_x86_64")
            artifacts = {item["path"]: item for item in report["artifacts"]}
            self.assertIn("boot.img", artifacts)
            self.assertEqual(artifacts["boot.img"]["sha256"], hashlib.sha256(b"boot-image").hexdigest())
            self.assertEqual(report["build"]["api_level"], "37")
            self.assertEqual(report["build"]["security_patch"], "2026-06-05")
            self.assertEqual(report["build"]["build_id"], report["baseline_identity"]["build_id"])

    def test_missing_required_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._workspace(root)
            (workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64" / "boot.img").unlink()
            with self.assertRaises(BuildEvidenceError):
                collect_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

    def test_wrong_build_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._workspace(root)
            path = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64" / "system" / "build.prop"
            text = path.read_text(encoding="utf-8").replace("ro.build.id=CP2A.260605.016", "ro.build.id=WRONG.000000.000")
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(BuildEvidenceError):
                collect_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

    def test_wrong_security_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._workspace(root)
            path = workspace / "out" / "target" / "product" / "swirphoneos_cf_x86_64" / "system" / "build.prop"
            text = path.read_text(encoding="utf-8").replace("2026-06-05", "2026-05-05")
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(BuildEvidenceError):
                collect_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))

    def test_bundle_binds_runtime_to_exact_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace, manifest = self._workspace(root)
            build = collect_build_evidence(workspace, manifest, Path("platform/aosp_baseline.json"))
            registry = load_registry(Path("system_apps/manifest.json"))
            required = frozenset(app.package for app in registry.apps if app.source_ready)
            props = {
                "sys.boot_completed": "1\n",
                "ro.product.name": "swirphoneos_cf_x86_64\n",
                "ro.product.device": "vsoc_x86_64_only\n",
                "ro.product.manufacturer": "Swir\n",
                "ro.product.model": "SwirPhoneOS Cuttlefish Developer\n",
                "ro.build.fingerprint": build["build"]["fingerprint"] + "\n",
                "ro.build.id": "CP2A.260605.016\n",
                "ro.build.type": "userdebug\n",
                "ro.build.tags": "test-keys\n",
                "ro.build.version.release": "17\n",
                "ro.build.version.sdk": "37\n",
                "ro.build.version.security_patch": "2026-06-05\n",
                "persist.sys.locale": "en-US\n",
            }
            runtime = evaluate_runtime_snapshot(props, required, registry, required)
            bundle = create_evidence_bundle(build, runtime)
            self.assertTrue(bundle["evidence_bundle_complete"])
            self.assertEqual(len(bundle["bundle_sha256"]), 64)
            runtime["build_fingerprint"] = "mismatch"
            with self.assertRaises(BuildEvidenceError):
                create_evidence_bundle(build, runtime)

    def test_json_loader_rejects_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(BuildEvidenceError):
                load_json_report(path)


if __name__ == "__main__":
    unittest.main()
