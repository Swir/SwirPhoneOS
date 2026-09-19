from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.cuttlefish_host_tool_evidence import capture_host_tools, verify_host_tools
from swirphoneos.cuttlefish_host_tool_trust_bundle import (
    CuttlefishHostToolTrustBundleError,
    create_cuttlefish_host_tool_trust_bundle,
)


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    return path.resolve()


@unittest.skipUnless(os.name == "posix", "Cuttlefish host-tool trust is Linux/POSIX-builder specific")
class CuttlefishHostToolTrustBundleTests(unittest.TestCase):
    def _workspace(self, root: Path) -> Path:
        root = root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / ".repo").mkdir()
        (root / "build").mkdir()
        (root / "build" / "envsetup.sh").write_text("# test\n", encoding="utf-8")
        bindir = root / "out" / "host" / "linux-x86" / "bin"
        bindir.mkdir(parents=True)
        for name in ("launch_cvd", "stop_cvd"):
            path = bindir / name
            path.write_bytes(("trusted-" + name).encode())
            path.chmod(0o755)
        return root

    def _fixtures(self, root: Path) -> tuple[Path, Path, Path, Path]:
        workspace = self._workspace(root / "aosp")
        capture = capture_host_tools(workspace)
        verify = verify_host_tools(workspace, capture)
        fingerprint = "swirphoneos_cf_x86_64/test:userdebug/exact"
        run: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": "BUILD_AND_RUNTIME",
            "workspace_sha256": hashlib.sha256(str(workspace).encode()).hexdigest(),
            "build_fingerprint": fingerprint,
            "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii")).hexdigest(),
            "build_chain_complete": True,
            "runtime_chain_complete": True,
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
        }
        run["run_evidence_sha256"] = hashlib.sha256(json.dumps(run, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
        run["run_evidence_complete"] = True
        return (
            _write(root / "run.json", run),
            _write(root / "capture.json", capture),
            _write(root / "pre.json", verify),
            _write(root / "post.json", verify),
        )

    def test_binds_exact_runtime_to_unchanged_host_tools(self) -> None:
        with TemporaryDirectory() as folder:
            result = create_cuttlefish_host_tool_trust_bundle(*self._fixtures(Path(folder).resolve()))
            self.assertTrue(result["host_tools_unchanged_across_runtime_review"])
            self.assertFalse(result["device_write_allowed"])
            self.assertFalse(result["beta_gate_satisfied"])
            canonical = {k: v for k, v in result.items() if k != "cuttlefish_host_tool_trust_bundle_sha256"}
            expected = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(result["cuttlefish_host_tool_trust_bundle_sha256"], expected)

    def test_rejects_wrong_workspace_or_changed_verification(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, capture, pre, post = self._fixtures(root)
            value = json.loads(capture.read_text())
            value["workspace_identity_sha256"] = "f" * 64
            _write(capture, value)
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, capture, pre, post)

        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, capture, pre, post = self._fixtures(root)
            value = json.loads(post.read_text())
            value["tools"][0]["sha256"] = "e" * 64
            _write(post, value)
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, capture, pre, post)

    def test_rejects_build_only_or_rehashed_tampered_run(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, capture, pre, post = self._fixtures(root)
            value = json.loads(run.read_text())
            value["scope"] = "BUILD_ONLY"
            canonical = {k: v for k, v in value.items() if k not in {"run_evidence_sha256", "run_evidence_complete"}}
            value["run_evidence_sha256"] = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
            _write(run, value)
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, capture, pre, post)

    def test_rejects_duplicate_json_symlink_and_write_claim(self) -> None:
        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, capture, pre, post = self._fixtures(root)
            post.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, capture, pre, post)

        with TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            run, capture, pre, post = self._fixtures(root)
            link = root / "capture-link.json"
            link.symlink_to(capture)
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, link, pre, post)
            value = json.loads(run.read_text())
            value["device_write_allowed"] = True
            _write(run, value)
            with self.assertRaises(CuttlefishHostToolTrustBundleError):
                create_cuttlefish_host_tool_trust_bundle(run, capture, pre, post)


if __name__ == "__main__":
    unittest.main()
