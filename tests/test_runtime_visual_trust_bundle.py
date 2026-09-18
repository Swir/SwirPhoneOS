from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from swirphoneos.i18n import LOCALES
from swirphoneos.runtime_visual_trust_bundle import RuntimeVisualTrustBundleError, create_runtime_visual_trust_bundle
from swirphoneos.system_apps import load_registry


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def png():
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 100, 200) + b"\x08\x06\x00\x00\x00" + b"crc!" + b"payload"


class RuntimeVisualTrustBundleTests(unittest.TestCase):
    def setUp(self):
        registry = load_registry(Path("system_apps/manifest.json"))
        self.packages = sorted(app.package for app in registry.apps if app.source_ready)
        self.locales = list(LOCALES)
        self.fingerprint = "Swir/test:17/TEST/1:userdebug/test-keys"
        self.fp_sha = hashlib.sha256(self.fingerprint.encode("ascii")).hexdigest()

    def _fixture(self, root: Path):
        review = {
            "schema_version": 1, "source": "local_cuttlefish_runtime_review_trust_bundle",
            "scope": "CUTTLEFISH_BUILD_RUNTIME_I18N_AND_EXACT_ADB", "expected_product": "swirphoneos_cf_x86_64",
            "run_evidence_sha256": "1" * 64, "runtime_trust_bundle_sha256": "2" * 64,
            "runtime_review_sha256": "3" * 64, "build_fingerprint_sha256": self.fp_sha,
            "app_manifest_sha256": "4" * 64, "source_ready_packages": self.packages, "tested_locales": self.locales,
            "adb_sha256": "5" * 64, "adb_path_identity_sha256": "6" * 64, "adb_size": 1234,
            "report_file_sha256": {"aosp_run_evidence": "7" * 64, "runtime_trust_bundle": "8" * 64, "runtime_review_evidence": "9" * 64},
            "build_runtime_chain_complete": True, "locale_review_chain_complete": True,
            "runtime_tool_unchanged_across_evidence_window": True, "rtl_visual_mirroring_verified": False,
            "accessibility_review_complete": False, "visual_translation_review_complete": False,
            "physical_device_support_claimed": False, "device_write_allowed": False, "status_promotion_performed": False,
            "warnings": [],
        }
        review["runtime_review_trust_bundle_sha256"] = sha(review)
        review_path = root / "review.json"
        review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")

        visual_dir = root / "visual"
        visual_dir.mkdir()
        data = png()
        captures = []
        index = 0
        for locale in self.locales:
            for package in self.packages:
                index += 1
                name = f"{index:03d}_{package}__{locale}.png"
                (visual_dir / name).write_bytes(data)
                captures.append({
                    "relative_path": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                    "width": 100, "height": 200, "package": package, "locale": locale,
                    "direction": LOCALES[locale].direction, "component": package + "/.MainActivity", "foreground_confirmed": True,
                })
        visual = {
            "schema_version": 1, "source": "local_cuttlefish_visual_capture_matrix", "expected_product": "swirphoneos_cf_x86_64",
            "build_fingerprint": self.fingerprint, "build_fingerprint_sha256": self.fp_sha, "android_user_id": 0,
            "tested_packages": self.packages, "tested_locales": self.locales, "capture_count": len(captures), "captures": captures,
            "capture_set_sha256": sha(captures), "capture_matrix_complete": True, "visual_bytes_captured": True,
            "original_app_locales_restored": True, "rtl_runtime_switch_exercised": True,
            "rtl_visual_mirroring_verified": False, "accessibility_review_complete": False,
            "visual_translation_review_complete": False, "status_promotion_performed": False,
            "physical_device_support_claimed": False, "persistent_device_write_allowed": False,
            "runtime_state_mutation_performed": True, "host_evidence_write_performed": True, "warnings": [],
        }
        visual["visual_capture_sha256"] = sha(visual)
        visual_path = root / "visual.json"
        visual_path.write_text(json.dumps(visual, indent=2), encoding="utf-8")
        return review_path, visual_path, visual_dir

    def test_valid_bundle_rehashes_closed_png_set_without_promoting_review(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = self._fixture(Path(temp).resolve())
            report = create_runtime_visual_trust_bundle(*paths)
            self.assertTrue(report["visual_capture_matrix_complete"])
            self.assertTrue(report["visual_bytes_reverified"])
            self.assertEqual(report["capture_count"], len(self.packages) * len(self.locales))
            self.assertFalse(report["rtl_visual_mirroring_verified"])
            self.assertFalse(report["accessibility_review_complete"])
            self.assertFalse(report["release_artifact_authorized"])

    def test_modified_png_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            review, visual, directory = self._fixture(Path(temp).resolve())
            target = next(directory.iterdir())
            target.write_bytes(target.read_bytes() + b"tamper")
            with self.assertRaises(RuntimeVisualTrustBundleError):
                create_runtime_visual_trust_bundle(review, visual, directory)

    def test_extra_file_breaks_directory_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            review, visual, directory = self._fixture(Path(temp).resolve())
            (directory / "extra.png").write_bytes(png())
            with self.assertRaises(RuntimeVisualTrustBundleError):
                create_runtime_visual_trust_bundle(review, visual, directory)

    def test_visual_overclaim_is_rejected_even_with_recomputed_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            review, visual, directory = self._fixture(Path(temp).resolve())
            data = json.loads(visual.read_text(encoding="utf-8"))
            data["rtl_visual_mirroring_verified"] = True
            data["visual_capture_sha256"] = sha({k: v for k, v in data.items() if k != "visual_capture_sha256"})
            visual.write_text(json.dumps(data, indent=2), encoding="utf-8")
            with self.assertRaises(RuntimeVisualTrustBundleError):
                create_runtime_visual_trust_bundle(review, visual, directory)

    def test_duplicate_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            review, visual, directory = self._fixture(Path(temp).resolve())
            visual.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(RuntimeVisualTrustBundleError):
                create_runtime_visual_trust_bundle(review, visual, directory)


if __name__ == "__main__":
    unittest.main()
