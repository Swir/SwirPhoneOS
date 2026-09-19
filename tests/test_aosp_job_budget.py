from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from swirphoneos.build_preflight import (
    ADVISORY_COMMANDS,
    HostSnapshot,
    MAX_PARALLEL_JOBS,
    MIN_FREE_BYTES,
    MIN_RAM_BYTES,
    MIN_RAM_PER_PARALLEL_JOB_BYTES,
    REQUESTED_JOBS_ENV,
    REQUIRED_COMMANDS,
    evaluate_preflight,
    safe_parallel_job_ceiling,
)


ROOT = Path(__file__).resolve().parents[1]
AOSP_WORKFLOW = ROOT / ".github" / "workflows" / "aosp-build-evidence.yml"


def ready_snapshot(*, cpu: int | None = 32, ram: int | None = MIN_RAM_BYTES) -> HostSnapshot:
    return HostSnapshot(
        system="linux",
        machine="x86_64",
        glibc_version="2.39",
        ram_bytes=ram,
        free_bytes=MIN_FREE_BYTES,
        commands={name: True for name in (*REQUIRED_COMMANDS, *ADVISORY_COMMANDS)},
        kvm_available=True,
        repo_launcher_version="2.65",
        logical_cpu_count=cpu,
    )


def check_map(result: dict[str, object]) -> dict[str, bool]:
    checks = result["checks"]
    assert isinstance(checks, list)
    return {
        str(item["id"]): bool(item["passed"])
        for item in checks
        if isinstance(item, dict)
    }


class AospParallelJobBudgetTests(unittest.TestCase):
    def test_default_builder_shape_accepts_sixteen_jobs(self) -> None:
        with patch.dict(os.environ, {REQUESTED_JOBS_ENV: "16"}, clear=False):
            result = evaluate_preflight(ready_snapshot(cpu=32, ram=MIN_RAM_BYTES))
        self.assertTrue(result["ready_for_full_build"])
        capacity = result["build_capacity"]
        self.assertIsInstance(capacity, dict)
        assert isinstance(capacity, dict)
        self.assertEqual(capacity["safe_parallel_job_ceiling"], 16)
        self.assertEqual(capacity["requested_parallel_jobs"], 16)
        self.assertTrue(capacity["request_within_budget"])
        self.assertFalse(capacity["official_aosp_requirement"])
        self.assertTrue(check_map(result)["parallel_jobs_within_host_budget"])

    def test_memory_budget_blocks_oversubscribed_full_build_without_blocking_sync(self) -> None:
        with patch.dict(os.environ, {REQUESTED_JOBS_ENV: "17"}, clear=False):
            result = evaluate_preflight(ready_snapshot(cpu=64, ram=MIN_RAM_BYTES))
        self.assertTrue(result["ready_for_source_sync"])
        self.assertFalse(result["ready_for_full_build"])
        capacity = result["build_capacity"]
        assert isinstance(capacity, dict)
        self.assertEqual(capacity["safe_parallel_job_ceiling"], 16)
        self.assertFalse(capacity["request_within_budget"])
        self.assertFalse(check_map(result)["parallel_jobs_within_host_budget"])

    def test_cpu_budget_is_never_exceeded_even_with_abundant_ram(self) -> None:
        snapshot = ready_snapshot(cpu=8, ram=128 * 1024**3)
        self.assertEqual(safe_parallel_job_ceiling(snapshot), 8)
        with patch.dict(os.environ, {REQUESTED_JOBS_ENV: "9"}, clear=False):
            result = evaluate_preflight(snapshot)
        self.assertFalse(result["ready_for_full_build"])

    def test_budget_never_exceeds_existing_workflow_hard_ceiling(self) -> None:
        snapshot = ready_snapshot(
            cpu=MAX_PARALLEL_JOBS * 2,
            ram=MIN_RAM_PER_PARALLEL_JOB_BYTES * MAX_PARALLEL_JOBS * 2,
        )
        self.assertEqual(safe_parallel_job_ceiling(snapshot), MAX_PARALLEL_JOBS)

    def test_invalid_requested_jobs_fail_closed_without_echoing_untrusted_text(self) -> None:
        with patch.dict(os.environ, {REQUESTED_JOBS_ENV: "16x"}, clear=False):
            result = evaluate_preflight(ready_snapshot())
        self.assertTrue(result["ready_for_source_sync"])
        self.assertFalse(result["ready_for_full_build"])
        capacity = result["build_capacity"]
        assert isinstance(capacity, dict)
        self.assertIsNone(capacity["requested_parallel_jobs"])
        self.assertFalse(capacity["request_valid"])
        self.assertFalse(capacity["request_within_budget"])
        self.assertNotIn("16x", repr(result))

    def test_missing_capacity_facts_fail_closed_only_when_workflow_requests_jobs(self) -> None:
        snapshot = ready_snapshot(cpu=None)
        without_request = dict(os.environ)
        without_request.pop(REQUESTED_JOBS_ENV, None)
        with patch.dict(os.environ, without_request, clear=True):
            local_result = evaluate_preflight(snapshot)
        self.assertTrue(local_result["ready_for_full_build"])
        with patch.dict(os.environ, {REQUESTED_JOBS_ENV: "1"}, clear=False):
            workflow_result = evaluate_preflight(snapshot)
        self.assertFalse(workflow_result["ready_for_full_build"])
        capacity = workflow_result["build_capacity"]
        assert isinstance(capacity, dict)
        self.assertIsNone(capacity["safe_parallel_job_ceiling"])

    def test_existing_aosp_workflow_exports_request_before_preflight(self) -> None:
        text = AOSP_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("SWIR_REQUESTED_JOBS: ${{ inputs.jobs }}", text)
        self.assertIn("python -m swirphoneos build-preflight --workspace", text)
        self.assertLess(
            text.index("SWIR_REQUESTED_JOBS: ${{ inputs.jobs }}"),
            text.index("python -m swirphoneos build-preflight --workspace"),
        )


if __name__ == "__main__":
    unittest.main()
