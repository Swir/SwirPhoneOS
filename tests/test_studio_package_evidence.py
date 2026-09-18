from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.studio_package_evidence import (
    StudioPackageEvidenceError,
    collect_studio_package_evidence,
    load_studio_package_evidence,
    validate_studio_package_evidence,
    verify_studio_package_files,
)


_SOURCE_COMMIT = "1" * 40
_REPOSITORY = "Swir/SwirPhoneOS"
_WORKFLOW = ".github/workflows/package-studio.yml"


class StudioPackageEvidenceTests(unittest.TestCase):
    def _package(self, root: Path) -> tuple[Path, Path]:
        dist = root / "dist"
        dist.mkdir()
        exe = dist / "SwirPhoneStudio.exe"
        exe.write_bytes(b"MZ" + b"\x00" * 1022)
        digest = hashlib.sha256(exe.read_bytes()).hexdigest()
        sums = dist / "SHA256SUMS.txt"
        sums.write_text(f"{digest}  SwirPhoneStudio.exe\n", encoding="ascii")
        return exe, sums

    def _report(self, exe: Path, sums: Path) -> dict[str, object]:
        return collect_studio_package_evidence(
            exe,
            sums,
            _SOURCE_COMMIT,
            repository=_REPOSITORY,
            workflow_path=_WORKFLOW,
            run_id=123456,
            run_attempt=1,
            python_version="3.14.0",
            pyinstaller_version="6.22.3",
        )

    def test_collects_exact_package_and_ci_provenance_without_release_credit(self):
        with tempfile.TemporaryDirectory() as temp:
            exe, sums = self._package(Path(temp))
            report = self._report(exe, sums)
            self.assertTrue(report["packaging_evidence_complete"])
            self.assertTrue(report["developer_package_only"])
            self.assertFalse(report["windows_usb_runtime_verified"])
            self.assertFalse(report["release_artifact"])
            self.assertFalse(report["beta_gate_passed"])
            self.assertFalse(report["device_write_allowed"])
            self.assertEqual(report["artifact"]["sha256"], hashlib.sha256(exe.read_bytes()).hexdigest())
            self.assertEqual(report["ci_context"]["repository"], _REPOSITORY)
            self.assertEqual(report["ci_context"]["workflow_path"], _WORKFLOW)
            self.assertEqual(report["toolchain"]["python"], "3.14.0")
            self.assertEqual(report["toolchain"]["pyinstaller"], "6.22.3")
            self.assertEqual(len(report["evidence_sha256"]), 64)

    def test_saved_report_revalidates_against_exact_package_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe, sums = self._package(root)
            report = self._report(exe, sums)
            path = root / "evidence.json"
            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            loaded = load_studio_package_evidence(path)
            verify_studio_package_files(loaded, exe, sums)

    def test_tampered_executable_is_rejected_during_file_revalidation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe, sums = self._package(root)
            report = self._report(exe, sums)
            exe.write_bytes(exe.read_bytes() + b"tamper")
            with self.assertRaises(StudioPackageEvidenceError):
                verify_studio_package_files(report, exe, sums)

    def test_checksum_mismatch_is_rejected_at_collection(self):
        with tempfile.TemporaryDirectory() as temp:
            exe, sums = self._package(Path(temp))
            sums.write_text(f"{'0' * 64}  SwirPhoneStudio.exe\n", encoding="ascii")
            with self.assertRaises(StudioPackageEvidenceError):
                self._report(exe, sums)

    def test_non_pe_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            exe, sums = self._package(Path(temp))
            exe.write_bytes(b"NO" + b"\x00" * 1022)
            digest = hashlib.sha256(exe.read_bytes()).hexdigest()
            sums.write_text(f"{digest}  SwirPhoneStudio.exe\n", encoding="ascii")
            with self.assertRaises(StudioPackageEvidenceError):
                self._report(exe, sums)

    def test_wrong_repository_workflow_commit_and_toolchain_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            exe, sums = self._package(Path(temp))
            bad_kwargs = (
                {"source_commit": "NOT-A-COMMIT"},
                {"repository": "Someone/Else"},
                {"workflow_path": ".github/workflows/other.yml"},
                {"python_version": "3.13.9"},
                {"pyinstaller_version": "6.22.2"},
            )
            for overrides in bad_kwargs:
                kwargs = {
                    "source_commit": _SOURCE_COMMIT,
                    "repository": _REPOSITORY,
                    "workflow_path": _WORKFLOW,
                    "run_id": 123456,
                    "run_attempt": 1,
                    "python_version": "3.14.0",
                    "pyinstaller_version": "6.22.3",
                }
                kwargs.update(overrides)
                with self.subTest(overrides=overrides), self.assertRaises(StudioPackageEvidenceError):
                    collect_studio_package_evidence(exe, sums, kwargs.pop("source_commit"), **kwargs)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(StudioPackageEvidenceError):
                load_studio_package_evidence(path)

    def test_status_promotion_is_rejected_even_with_recomputed_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            exe, sums = self._package(Path(temp))
            report = self._report(exe, sums)
            report["beta_gate_passed"] = True
            unsigned = dict(report)
            unsigned.pop("evidence_sha256")
            canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            report["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
            with self.assertRaises(StudioPackageEvidenceError):
                validate_studio_package_evidence(report)

    def test_packaging_workflow_generates_revalidates_and_uploads_evidence(self):
        workflow = Path(".github/workflows/package-studio.yml").read_text(encoding="utf-8")
        self.assertIn("python -m swirphoneos.studio_package_evidence collect", workflow)
        self.assertIn("python -m swirphoneos.studio_package_evidence verify", workflow)
        self.assertIn("SwirPhoneStudio-evidence.json", workflow)
        self.assertLess(workflow.index("Frozen GUI smoke test"), workflow.index("studio_package_evidence collect"))
        self.assertLess(workflow.index("Record SHA-256"), workflow.index("studio_package_evidence collect"))


if __name__ == "__main__":
    unittest.main()
