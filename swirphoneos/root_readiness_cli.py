"""Read-only CLI for binding SwirRoot recovery/hardware readiness evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .hardware_evidence import HardwareEvidenceError
from .rollback_material_evidence import RollbackMaterialEvidenceError
from .swirroot import SwirRootPolicyError
from .swirroot_readiness import SwirRootReadinessError, collect_swirroot_readiness_from_files
from .transaction_evidence import TransactionEvidenceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind read-only SwirRoot readiness evidence without performing device writes."
    )
    parser.add_argument("--action", required=True, choices=("enable", "unroot"))
    parser.add_argument("--exact-build", required=True, help="Exact SwirPhoneOS build/fingerprint bound to the recovery journal")
    parser.add_argument("--policy", type=Path, default=Path("swirroot/policy.json"))
    parser.add_argument("--journal", type=Path, required=True, help="Validated create-only recovery journal")
    parser.add_argument("--hardware", type=Path, required=True, help="Validated cross-transport read-only hardware evidence")
    parser.add_argument(
        "--artifact-root",
        type=Path,
        required=True,
        help="Absolute trusted directory containing the exact rollback files referenced by the journal",
    )
    args = parser.parse_args(argv)
    try:
        result = collect_swirroot_readiness_from_files(
            action=args.action,
            exact_build=args.exact_build,
            policy_path=args.policy,
            journal_path=args.journal,
            hardware_path=args.hardware,
            artifact_root=args.artifact_root,
        )
    except (
        SwirRootReadinessError,
        SwirRootPolicyError,
        RollbackMaterialEvidenceError,
        TransactionEvidenceError,
        HardwareEvidenceError,
        OSError,
        ValueError,
    ):
        print(
            "SwirRoot readiness failed: evidence or fresh rollback material is missing, changed, contradictory, malformed, or not bound to the requested exact build.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
