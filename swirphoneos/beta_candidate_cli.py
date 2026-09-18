"""CLI for fail-closed SwirPhoneOS beta-candidate file binding."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .beta_candidate import BetaCandidateError, verify_candidate_bundle_from_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify exact beta-candidate file binding without authorizing publication."
    )
    parser.add_argument("--ledger", type=Path, default=Path("project.json"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_candidate_bundle_from_files(args.ledger, args.manifest, args.root)
    except (BetaCandidateError, OSError, ValueError):
        print(
            "Candidate verification failed: check the exact ledger, manifest, trusted bundle root, "
            "file hashes and mandatory gate references. Raw paths/errors are withheld.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["beta_release_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
