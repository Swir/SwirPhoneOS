from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_reproducibility import (
    AospReproducibilityError,
    compare_reproducibility_pair,
    validate_reproducibility_pair,
)


PRODUCT = "swirphoneos_cf_x86_64"
COMMIT = "a" * 40
FINGERPRINT = "swir/swirphoneos_cf_x86_64/swirphoneos_cf_x86_64:17/test/userdebug/test-keys"


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _h(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _run(*, workspace: str, staged: str = _h("stage"), commit: str = COMMIT) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_run_evidence_chain",
        "source_commit": commit,
        "scope": "BUILD_ONLY",
        "expected_product": PRODUCT,
        "workspace_sha256": _h(workspace),
        "staged_content_sha256": staged,
        "build_fingerprint": FINGERPRINT,
        "build_fingerprint_sha256": hashlib.sha256(FINGERPRINT.encode("ascii")).hexdigest(),
        "app_manifest_sha256": _h("app-manifest"),
        "source_ready_packages": ["com.swir.files", "com.swir.settings"],
        "report_file_sha256": {
            "aosp_plan": _h("plan-" + workspace),
            "build_evidence": _h("build-evidence"),
            "builder_preflight": _h("preflight-" + workspace),
            "post_build_stage": _h("post-stage-" + workspace),
            "resolved_manifest": _h("resolved-manifest"),
            "stage_report": _h("stage-report-" + workspace),
        },
        "build_chain_complete": True,
        "runtime_chain_complete": False,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": ["test fixture"],
    }
    payload["run_evidence_sha256"] = _sha(payload)
    payload["run_evidence_complete"] = True
    return payload


def _artifacts(system_digest: str = _h("system")) -> list[dict[str, object]]:
    return [
        {"path": "boot.img", "size": 4096, "sha256": _h("boot")},
        {"path": "system.img", "size": 8192, "sha256": system_digest},
    ]


def _continuity(run: dict[str, object], run_file_sha: str, *, system_digest: str = _h("system")) -> dict[str, object]:
    artifacts = _artifacts(system_digest)
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_artifact_continuity_evidence",
        "operation": "READ_ONLY_POST_RUN_ARTIFACT_RECHECK",
        "source_commit": run["source_commit"],
        "aosp_run_scope": run["scope"],
        "expected_product": PRODUCT,
        "run_evidence_sha256": run["run_evidence_sha256"],
        "workspace_identity_sha256": run["workspace_sha256"],
        "build_fingerprint": FINGERPRINT,
        "build_evidence_file_sha256": run["report_file_sha256"]["build_evidence"],
        "report_file_sha256": {
            "aosp_run_evidence": run_file_sha,
            "build_evidence": run["report_file_sha256"]["build_evidence"],
        },
        "required_artifacts": ["boot.img", "system.img"],
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifact_set_sha256": _sha(artifacts),
        "artifact_bytes_unchanged_after_run": True,
        "core_images_unchanged_after_run": True,
        "artifact_continuity_complete": True,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "release_artifact_authorized": False,
        "warnings": ["test fixture"],
    }
    payload["artifact_continuity_sha256"] = _sha(payload)
    return payload


def _write(path: Path, value: dict[str, object], *, compact: bool = False) -> str:
    if compact:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    else:
        text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AospReproducibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _pair(self, *, system_b: str = _h("system"), staged_b: str = _h("stage")) -> tuple[Path, Path, Path, Path]:
        run_a = _run(workspace="workspace-a")
        run_b = _run(workspace="workspace-b", staged=staged_b)
        run_a_path = self.root / "run-a.json"
        run_b_path = self.root / "run-b.json"
        run_a_file_sha = _write(run_a_path, run_a)
        run_b_file_sha = _write(run_b_path, run_b)
        continuity_a = _continuity(run_a, run_a_file_sha)
        continuity_b = _continuity(run_b, run_b_file_sha, system_digest=system_b)
        continuity_a_path = self.root / "continuity-a.json"
        continuity_b_path = self.root / "continuity-b.json"
        _write(continuity_a_path, continuity_a)
        _write(continuity_b_path, continuity_b)
        return run_a_path, continuity_a_path, run_b_path, continuity_b_path

    def test_matching_independent_pair_is_accepted_without_status_promotion(self) -> None:
        paths = self._pair()
        report = compare_reproducibility_pair(*paths, expected_source_commit=COMMIT)
        digest = validate_reproducibility_pair(report)
        self.assertEqual(report["reproducibility_observation"], "MATCHING_PAIR")
        self.assertTrue(report["same_reviewed_inputs"])
        self.assertTrue(report["artifact_bytes_identical"])
        self.assertEqual(report["artifact_count"], 2)
        self.assertEqual(report["reproducibility_pair_sha256"], digest)
        for key in (
            "device_write_allowed",
            "physical_device_support_claimed",
            "status_promotion_performed",
            "milestone_promoted",
            "beta_gate_passed",
            "release_artifact_authorized",
        ):
            self.assertIs(report[key], False)

    def test_artifact_byte_difference_fails_closed(self) -> None:
        paths = self._pair(system_b=_h("different-system"))
        with self.assertRaisesRegex(AospReproducibilityError, "artifact bytes"):
            compare_reproducibility_pair(*paths, expected_source_commit=COMMIT)

    def test_staged_source_difference_fails_before_artifact_claim(self) -> None:
        paths = self._pair(staged_b=_h("different-stage"))
        with self.assertRaisesRegex(AospReproducibilityError, "reviewed build input mismatch"):
            compare_reproducibility_pair(*paths, expected_source_commit=COMMIT)

    def test_expected_source_commit_is_exact_and_bound_to_both_runs(self) -> None:
        paths = self._pair()
        with self.assertRaisesRegex(AospReproducibilityError, "triggering source commit mismatch"):
            compare_reproducibility_pair(*paths, expected_source_commit="b" * 40)
        with self.assertRaisesRegex(AospReproducibilityError, "invalid expected source commit"):
            compare_reproducibility_pair(*paths, expected_source_commit="main")

    def test_continuity_must_bind_exact_run_file_bytes(self) -> None:
        run_a, continuity_a, run_b, continuity_b = self._pair()
        value = json.loads(run_b.read_text(encoding="utf-8"))
        _write(run_b, value, compact=True)
        with self.assertRaisesRegex(AospReproducibilityError, "exact run-evidence bytes"):
            compare_reproducibility_pair(run_a, continuity_a, run_b, continuity_b, expected_source_commit=COMMIT)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        run_a, continuity_a, run_b, continuity_b = self._pair()
        run_a.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        with self.assertRaisesRegex(AospReproducibilityError, "duplicate JSON key"):
            compare_reproducibility_pair(run_a, continuity_a, run_b, continuity_b, expected_source_commit=COMMIT)

    def test_symlink_evidence_is_rejected(self) -> None:
        run_a, continuity_a, run_b, continuity_b = self._pair()
        link = self.root / "run-a-link.json"
        try:
            link.symlink_to(run_a)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        with self.assertRaisesRegex(AospReproducibilityError, "unsafe evidence path"):
            compare_reproducibility_pair(link, continuity_a, run_b, continuity_b, expected_source_commit=COMMIT)

    def test_tampered_output_report_is_rejected(self) -> None:
        paths = self._pair()
        report = compare_reproducibility_pair(*paths, expected_source_commit=COMMIT)
        report["beta_gate_passed"] = True
        with self.assertRaisesRegex(AospReproducibilityError, "invalid reproducibility-pair evidence"):
            validate_reproducibility_pair(report)


if __name__ == "__main__":
    unittest.main()
