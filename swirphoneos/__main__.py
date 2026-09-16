"""Run from the repository: python -m swirphoneos <command>."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .profiles import ProfileError, discover_profiles, public_profile_summary
from .readiness import evaluate, load_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwirPhoneOS read-only developer tooling — by Swir")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "gate"):
        command = sub.add_parser(name)
        command.add_argument("--ledger", type=Path, default=Path("project.json"))

    inspect = sub.add_parser("inspect", help="Read selected properties from one authorized USB phone via ADB")
    inspect.add_argument("--adb", required=True, type=Path, help="Absolute path to a trusted Android SDK adb executable")

    inspect_fastboot = sub.add_parser(
        "inspect-fastboot",
        help="Read a small allowlist of variables from one local USB phone in Fastboot/FastbootD mode",
    )
    inspect_fastboot.add_argument(
        "--fastboot",
        required=True,
        type=Path,
        help="Absolute path to a trusted Android SDK fastboot executable",
    )

    profiles = sub.add_parser("profiles", help="Validate and list metadata-only device profiles")
    profiles.add_argument("--root", type=Path, default=Path("device_packs"))

    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            result = ReadOnlyAdb(args.adb).inspect()
        elif args.command == "inspect-fastboot":
            result = ReadOnlyFastboot(args.fastboot).inspect()
        elif args.command == "profiles":
            registry = discover_profiles(args.root)
            result = {
                "schema_version": 1,
                "profile_count": len(registry),
                "profiles": [public_profile_summary(profile) for profile in registry],
                "flash_allowed": False,
            }
        else:
            result = evaluate(load_ledger(args.ledger))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 2 if args.command == "gate" and not result["beta_release_allowed"] else 0
    except (DiagnosticError, FastbootDiagnosticError, ProfileError, OSError, ValueError):
        print(
            "Operation failed: check the project ledger/profile data or trusted Android SDK tool path, USB mode and single-device connection. Raw errors are withheld for privacy.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
