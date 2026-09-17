"""Read-only CLI for binding device-profile support readiness evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .device_support_readiness import (
    DeviceSupportReadinessError,
    collect_device_support_readiness_from_files,
)
from .hardware_evidence import HardwareEvidenceError
from .profiles import ProfileError
from .transaction_evidence import TransactionEvidenceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bind metadata profile, read-only hardware correlation and local recovery "
            "journal into a non-authorizing device-support readiness report."
        )
    )
    parser.add_argument("--profile", type=Path, required=True, help="Metadata-only device profile.json")
    parser.add_argument("--journal", type=Path, required=True, help="Validated create-only recovery journal")
    parser.add_argument("--hardware", type=Path, required=True, help="Validated cross-transport read-only hardware evidence")
    args = parser.parse_args(argv)
    try:
        result = collect_device_support_readiness_from_files(
            profile_path=args.profile,
            journal_path=args.journal,
            hardware_path=args.hardware,
        )
    except (
        DeviceSupportReadinessError,
        HardwareEvidenceError,
        ProfileError,
        TransactionEvidenceError,
        OSError,
        ValueError,
    ):
        print(
            "Device support readiness failed: evidence is missing, contradictory, malformed, or not bound to one profile/build.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
