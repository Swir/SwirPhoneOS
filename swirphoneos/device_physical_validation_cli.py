"""Read-only CLI for exact-device physical validation evidence binding."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .device_physical_validation import (
    DevicePhysicalValidationError,
    collect_physical_validation_from_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bind preparation readiness to exact local physical-validation evidence files. "
            "The result is review-only and never authorizes device writes or support promotion."
        )
    )
    parser.add_argument("--readiness", type=Path, required=True, help="Schema-v1 device support readiness JSON")
    parser.add_argument("--record", type=Path, required=True, help="Owner/operator physical validation record JSON")
    parser.add_argument("--evidence-root", type=Path, required=True, help="Absolute directory containing referenced evidence files")
    args = parser.parse_args(argv)
    try:
        report = collect_physical_validation_from_files(
            readiness_path=args.readiness,
            record_path=args.record,
            evidence_root=args.evidence_root,
        )
    except (DevicePhysicalValidationError, OSError, ValueError):
        print(
            "Physical validation failed: readiness, identity/build binding, record schema or referenced evidence is invalid.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
