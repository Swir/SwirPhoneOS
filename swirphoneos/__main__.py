"""Run offline preflight: python -m swirphoneos --profile ... --snapshot ..."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .preflight import DeviceProfile, assess, load_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwirPhoneOS offline preflight; no phone writes.",
                                     epilog="by Swir | https://github.com/Swir")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        profile = DeviceProfile.from_dict(load_json(args.profile))
        report = assess(load_json(args.snapshot), profile)
    except (OSError, ValueError, UnicodeError):
        print("Input rejected: unreadable or invalid profile/snapshot.", file=sys.stderr)
        return 1
    print(json.dumps(report.to_dict(), indent=2))
    return 2  # Expected: all write paths are blocked in this prototype.


if __name__ == "__main__":
    raise SystemExit(main())
