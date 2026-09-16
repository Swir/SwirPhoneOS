"""Run from the repository: python -m swirphoneos <command>."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .platform import PlatformBaselineError, load_baseline, public_baseline_summary
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

    baseline = sub.add_parser("baseline", help="Validate and show the offline AOSP baseline candidate")
    baseline.add_argument("--file", type=Path, default=Path("platform/aosp_baseline.json"))

    sub.add_parser("studio", help="Open the read-only SwirPhoneStudio developer GUI")

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
        elif args.command == "baseline":
            result = public_baseline_summary(load_baseline(args.file))
        elif args.command == "studio":
            # Lazy import keeps headless status/gate/CI commands independent of Tk.
            from .studio import launch

            return launch()
        else:
            result = evaluate(load_ledger(args.ledger))
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 2 if args.command == "gate" and not result["beta_release_allowed"] else 0
    except (
        DiagnosticError,
        FastbootDiagnosticError,
        PlatformBaselineError,
        ProfileError,
        ImportError,
        RuntimeError,
        OSError,
        ValueError,
    ):
        print(
            "Operation failed: check the project ledger/profile/baseline data, GUI availability or trusted Android SDK tool path, USB mode and single-device connection. Raw errors are withheld for privacy.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
