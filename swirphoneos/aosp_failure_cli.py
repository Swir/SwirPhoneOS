"""CLI wrapper for bounded AOSP failure evidence collection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .aosp_failure_evidence import ALLOWED_PHASES, AospFailureEvidenceError, collect_failure_evidence
from .platform import PlatformBaselineError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create read-only, tamper-evident diagnostics for a failed dedicated AOSP run."
    )
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--phase", required=True, choices=ALLOWED_PHASES)
    parser.add_argument("--baseline", type=Path, default=Path("platform/aosp_baseline.json"))
    parser.add_argument("--run-context", type=Path, default=None)
    parser.add_argument("--preflight", type=Path, default=None)
    parser.add_argument("--plan", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--stage", type=Path, default=None)
    parser.add_argument("--post-stage", type=Path, default=None)
    parser.add_argument("--build", type=Path, default=None)
    parser.add_argument("--runtime", type=Path, default=None)
    parser.add_argument("--smoke", type=Path, default=None)
    parser.add_argument("--bundle", type=Path, default=None)
    parser.add_argument("--run-evidence", type=Path, default=None)
    parser.add_argument("--diagnostic-log", type=Path, default=None)
    args = parser.parse_args(argv)
    evidence_paths = {
        "run_context": args.run_context,
        "builder_preflight": args.preflight,
        "aosp_plan": args.plan,
        "resolved_manifest": args.manifest,
        "stage_report": args.stage,
        "post_build_stage": args.post_stage,
        "build_evidence": args.build,
        "runtime_evidence": args.runtime,
        "app_smoke": args.smoke,
        "runtime_bundle": args.bundle,
        "aosp_run_evidence": args.run_evidence,
    }
    try:
        result = collect_failure_evidence(
            source_commit=args.source_commit,
            phase=args.phase,
            baseline_path=args.baseline,
            evidence_paths=evidence_paths,
            diagnostic_log=args.diagnostic_log,
        )
    except (AospFailureEvidenceError, PlatformBaselineError, OSError, ValueError):
        print(
            "Operation failed: failure evidence input is unsafe, malformed, oversized, or inconsistent with the pinned baseline.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
