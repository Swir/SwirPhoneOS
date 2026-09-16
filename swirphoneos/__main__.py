"""Run from the repository: python -m swirphoneos status | inspect --adb PATH."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .readiness import evaluate, load_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwirPhoneOS read-only developer tooling — by Swir")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "gate"):
        command = sub.add_parser(name)
        command.add_argument("--ledger", type=Path, default=Path("project.json"))
    inspect = sub.add_parser("inspect", help="Read selected properties from one authorized USB phone")
    inspect.add_argument("--adb", required=True, type=Path, help="Absolute path to a trusted Android SDK adb executable")
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = ReadOnlyAdb(args.adb).inspect()
        else:
            result = evaluate(load_ledger(args.ledger))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 2 if args.command == "gate" and not result["beta_release_allowed"] else 0
    except (DiagnosticError, OSError, ValueError):
        print("Operation failed: check the ledger or trusted ADB path, USB authorization and single-device connection. Raw errors are withheld for privacy.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
