"""Read-only CLI for exact rollback-material revalidation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .rollback_material_evidence import (
    RollbackMaterialEvidenceError,
    collect_rollback_material_evidence_from_files,
)
from .transaction_evidence import TransactionEvidenceError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-hash rollback files referenced by a validated recovery journal without device access."
    )
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = collect_rollback_material_evidence_from_files(
            args.journal,
            args.artifact_root,
        )
    except (RollbackMaterialEvidenceError, TransactionEvidenceError, OSError, ValueError):
        print(
            "Rollback material recheck failed: files are missing, changed, unsafe, or not bound to the journal.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
