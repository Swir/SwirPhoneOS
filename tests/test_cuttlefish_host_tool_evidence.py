from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from swirphoneos.cuttlefish_host_tool_evidence import (
    CuttlefishHostToolEvidenceError,
    EXPECTED_TOOLS,
    MAX_TOOL_BYTES,
    capture_host_tools,
    load_host_tool_evidence,
    verify_host_tools,
)


@unittest.skipUnless(os.name == "posix", "Cuttlefish host-tool evidence is Linux/POSIX-builder specific")
class CuttlefishHostToolEvidenceTests(unittest.TestCase):
    def _workspace(self, root: Path) -> Path:
        root = root.resolve()
        (root / ".repo").mkdir()
        (root / "build").mkdir()
        (root / "build" / "envsetup.sh").write_text("# test\n", encoding="utf-8")
        bin_dir = root / "out" / "host" / "linux-x86" / "bin"
        bin_dir.mkdir(parents=True)
        for name in EXPECTED_TOOLS:
            path = bin_dir / name
            path.write_bytes(("exact-" + name).encode("ascii"))
            path.chmod(0o755)
        return root

    def test_capture_hashes_exact_workspace_tools_without_raw_paths(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            report = capture_host_tools(root)
            self.assertEqual(report["tool_count"], 2)
            self.assertEqual([item["name"] for item in report["tools"]], list(EXPECTED_TOOLS))
            self.assertEqual(report["workspace_identity_sha256"], hashlib.sha256(str(root).encode()).hexdigest())
            expected = hashlib.sha256(json.dumps(report["tools"], sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(report["toolset_sha256"], expected)
            self.assertFalse(report["tools_executed"])
            self.assertFalse(report["device_write_allowed"])
            self.assertNotIn(str(root), json.dumps(report, sort_keys=True))

    def test_verify_accepts_unchanged_tools_and_rejects_byte_drift(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            evidence = capture_host_tools(root)
            verified = verify_host_tools(root, evidence)
            self.assertTrue(verified["tools_unchanged"])
            launch = root / "out" / "host" / "linux-x86" / "bin" / "launch_cvd"
            launch.write_bytes(b"changed")
            launch.chmod(0o755)
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                verify_host_tools(root, evidence)

    def test_accepts_android17_in_bin_symlink_aliases_and_detects_target_drift(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            bin_dir = root / "out" / "host" / "linux-x86" / "bin"
            cvd = bin_dir / "cvd"
            cvd.write_bytes(b"android-17-cvd")
            cvd.chmod(0o755)
            for name in EXPECTED_TOOLS:
                alias = bin_dir / name
                alias.unlink()
                alias.symlink_to("cvd")

            evidence = capture_host_tools(root)
            self.assertEqual(
                {item["path_identity_sha256"] for item in evidence["tools"]},
                {hashlib.sha256(str(cvd).encode()).hexdigest()},
            )
            self.assertTrue(verify_host_tools(root, evidence)["tools_unchanged"])

            replacement = bin_dir / "cvd-replacement"
            replacement.write_bytes(b"android-17-cvd")
            replacement.chmod(0o755)
            (bin_dir / "launch_cvd").unlink()
            (bin_dir / "launch_cvd").symlink_to("cvd-replacement")
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                verify_host_tools(root, evidence)

    def test_rejects_relative_workspace_symlink_tool_wrong_permissions_and_size(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                capture_host_tools(Path("."))
            launch = root / "out" / "host" / "linux-x86" / "bin" / "launch_cvd"
            original = root / "launch-real"
            original.write_bytes(b"x")
            original.chmod(0o755)
            launch.unlink()
            launch.symlink_to(original)
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                capture_host_tools(root)

        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            stop = root / "out" / "host" / "linux-x86" / "bin" / "stop_cvd"
            stop.chmod(0o775)
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                capture_host_tools(root)
            stop.chmod(0o755)
            with stop.open("wb") as handle:
                handle.truncate(MAX_TOOL_BYTES + 1)
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                capture_host_tools(root)

    def test_loader_rejects_duplicate_keys_symlink_and_forged_fields(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            evidence_path = root / "host-tools.json"
            evidence_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                load_host_tool_evidence(evidence_path.resolve())
            alias = root / "evidence-link.json"
            alias.symlink_to(evidence_path)
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                load_host_tool_evidence(alias)

            report = capture_host_tools(root)
            report["device_write_allowed"] = True
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                verify_host_tools(root, report)
            report = capture_host_tools(root)
            report["unexpected"] = False
            with self.assertRaises(CuttlefishHostToolEvidenceError):
                verify_host_tools(root, report)

    def test_round_trip_strict_json(self) -> None:
        with TemporaryDirectory() as folder:
            root = self._workspace(Path(folder))
            report = capture_host_tools(root)
            evidence_path = root / "host-tools.json"
            evidence_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            loaded = load_host_tool_evidence(evidence_path.resolve())
            verified = verify_host_tools(root, loaded)
            self.assertEqual(verified["toolset_sha256"], report["toolset_sha256"])
            self.assertEqual(verified["tools"], report["tools"])


if __name__ == "__main__":
    unittest.main()
