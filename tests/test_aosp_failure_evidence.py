from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_failure_cli import main as failure_cli_main
from swirphoneos.aosp_failure_evidence import (
    AospFailureEvidenceError,
    LEGACY_EVIDENCE_IDS_V1,
    MAX_DIAGNOSTIC_BYTES,
    collect_failure_evidence,
    validate_failure_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "platform" / "aosp_baseline.json"
SOURCE_COMMIT = "a" * 40


class AospFailureEvidenceTests(unittest.TestCase):
    def _collect(self, root: Path, *, phase: str = "BUILD") -> dict[str, object]:
        context = root / "aosp-run-context.txt"
        preflight = root / "builder-preflight.json"
        log = root / "aosp-build-tail.log"
        context.write_text("source_commit=" + SOURCE_COMMIT + "\n", encoding="utf-8")
        preflight.write_text('{"schema_version":1,"ready_for_full_build":true}\n', encoding="utf-8")
        log.write_text("ninja: error: synthetic bounded test failure\n", encoding="utf-8")
        return collect_failure_evidence(
            source_commit=SOURCE_COMMIT,
            phase=phase,
            baseline_path=BASELINE,
            evidence_paths={
                "run_context": context,
                "builder_preflight": preflight,
                "build_evidence": root / "missing-build-evidence.json",
            },
            diagnostic_log=log,
        )

    def test_failure_report_is_deterministic_read_only_and_revalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self._collect(root)
            second = self._collect(root)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], 2)
        self.assertEqual(first["state"], "FAILED_NOT_READY")
        self.assertEqual(first["failed_phase"], "BUILD")
        self.assertFalse(first["build_succeeded"])
        self.assertFalse(first["runtime_succeeded"])
        self.assertFalse(first["status_promotion_allowed"])
        self.assertFalse(first["device_write_allowed"])
        self.assertFalse(first["flash_allowed"])
        self.assertFalse(first["root_allowed"])
        self.assertIn("Kati/Soong/Ninja", first["next_action"])
        inventory = {item["id"]: item for item in first["evidence_inventory"]}
        self.assertTrue(inventory["run_context"]["present"])
        self.assertTrue(inventory["builder_preflight"]["present"])
        self.assertTrue(inventory["build_evidence"]["requested"])
        self.assertFalse(inventory["build_evidence"]["present"])
        self.assertIn("runtime_i18n", inventory)
        self.assertIn("runtime_review", inventory)
        self.assertIn("runtime_trust_bundle", inventory)
        self.assertIn("runtime_review_trust_bundle", inventory)
        self.assertFalse(inventory["runtime_review_trust_bundle"]["requested"])
        self.assertTrue(first["diagnostic_tail"]["present"])
        self.assertIs(validate_failure_evidence(first), first)

    def test_schema_v1_failure_evidence_still_revalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            current = self._collect(Path(temporary))
        legacy = json.loads(json.dumps(current))
        legacy["schema_version"] = 1
        legacy["evidence_inventory"] = [
            item for item in legacy["evidence_inventory"] if item["id"] in LEGACY_EVIDENCE_IDS_V1
        ]
        legacy.pop("failure_evidence_sha256")
        legacy["failure_evidence_sha256"] = hashlib.sha256(
            json.dumps(legacy, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        self.assertIs(validate_failure_evidence(legacy), legacy)

    def test_integrity_digest_rejects_safety_flag_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary))
        changed = json.loads(json.dumps(report))
        changed["device_write_allowed"] = True
        with self.assertRaises(AospFailureEvidenceError):
            validate_failure_evidence(changed)

    def test_integrity_digest_rejects_content_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary))
        changed = json.loads(json.dumps(report))
        changed["next_action"] = "Ignore the pinned build identity."
        with self.assertRaises(AospFailureEvidenceError):
            validate_failure_evidence(changed)

    def test_runtime_review_failure_phases_are_supported_without_success_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for phase in ("APP_I18N", "RUNTIME_REVIEW", "TRUST_BIND"):
                with self.subTest(phase=phase):
                    report = self._collect(root, phase=phase)
                    self.assertEqual(report["failed_phase"], phase)
                    self.assertFalse(report["runtime_succeeded"])
                    self.assertFalse(report["device_write_allowed"])
                    self.assertFalse(report["status_promotion_allowed"])
                    self.assertTrue(report["next_action"])

    def test_invalid_commit_phase_and_unknown_evidence_id_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(AospFailureEvidenceError):
                collect_failure_evidence(
                    source_commit="not-a-sha",
                    phase="BUILD",
                    baseline_path=BASELINE,
                    evidence_paths={},
                )
            with self.assertRaises(AospFailureEvidenceError):
                collect_failure_evidence(
                    source_commit=SOURCE_COMMIT,
                    phase="FLASH_PHONE",
                    baseline_path=BASELINE,
                    evidence_paths={},
                )
            with self.assertRaises(AospFailureEvidenceError):
                collect_failure_evidence(
                    source_commit=SOURCE_COMMIT,
                    phase="BUILD",
                    baseline_path=BASELINE,
                    evidence_paths={"arbitrary": root / "x"},
                )

    def test_oversized_diagnostic_tail_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            log = root / "too-large.log"
            log.write_bytes(b"x" * (MAX_DIAGNOSTIC_BYTES + 1))
            with self.assertRaises(AospFailureEvidenceError):
                collect_failure_evidence(
                    source_commit=SOURCE_COMMIT,
                    phase="BUILD",
                    baseline_path=BASELINE,
                    evidence_paths={},
                    diagnostic_log=log,
                )

    @unittest.skipIf(os.name == "nt", "Windows developer runners may not grant symlink creation privileges")
    def test_symlink_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "real.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "linked.json"
            link.symlink_to(target)
            with self.assertRaises(AospFailureEvidenceError):
                collect_failure_evidence(
                    source_commit=SOURCE_COMMIT,
                    phase="SOURCE_STAGE",
                    baseline_path=BASELINE,
                    evidence_paths={"stage_report": link},
                )

    def test_cli_records_missing_later_phase_files_without_fabricating_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = root / "aosp-run-context.txt"
            context.write_text("requested_jobs=16\n", encoding="utf-8")
            output = StringIO()
            error = StringIO()
            with redirect_stdout(output), redirect_stderr(error):
                code = failure_cli_main([
                    "--source-commit", SOURCE_COMMIT,
                    "--phase", "TRUST_BIND",
                    "--baseline", str(BASELINE),
                    "--run-context", str(context),
                    "--runtime-review", str(root / "not-created-review.json"),
                    "--runtime-trust", str(root / "not-created-trust.json"),
                    "--runtime-review-trust", str(root / "not-created-final.json"),
                ])
            self.assertEqual(code, 0, error.getvalue())
            report = json.loads(output.getvalue())
            self.assertEqual(report["schema_version"], 2)
            self.assertEqual(report["failed_phase"], "TRUST_BIND")
            self.assertFalse(report["build_succeeded"])
            self.assertFalse(report["status_promotion_allowed"])
            inventory = {item["id"]: item for item in report["evidence_inventory"]}
            self.assertTrue(inventory["run_context"]["present"])
            self.assertTrue(inventory["runtime_review"]["requested"])
            self.assertFalse(inventory["runtime_review"]["present"])
            self.assertTrue(inventory["runtime_trust_bundle"]["requested"])
            self.assertTrue(inventory["runtime_review_trust_bundle"]["requested"])
            self.assertFalse(inventory["runtime_review_trust_bundle"]["present"])


if __name__ == "__main__":
    unittest.main()
