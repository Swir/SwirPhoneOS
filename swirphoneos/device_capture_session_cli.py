"""CLI for create-only read-only physical-device capture sessions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .device_capture_session import (
    DeviceCaptureSessionError,
    create_capture_session,
    finalize_capture_session,
    record_transport_report,
    verify_capture_session,
)
from .diagnostics import DiagnosticError, ReadOnlyAdb
from .fastboot import FastbootDiagnosticError, ReadOnlyFastboot
from .identity import IdentityAssessmentError, build_unified_report
from .profiles import ProfileError, discover_profiles


def _absolute(path: Path) -> Path:
    if not path.is_absolute():
        raise DeviceCaptureSessionError("Session directory must be an absolute path.")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "SwirPhoneOS read-only physical-device capture sessions. "
            "This tool never reboots, flashes, unlocks, roots or writes to a phone."
        )
    )
    parser.add_argument(
        "--profiles",
        type=Path,
        default=Path("device_packs"),
        help="Reviewed metadata-only device profile registry.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a new create-only capture session.")
    create.add_argument("--session-dir", type=Path, required=True)

    adb = sub.add_parser("capture-adb", help="Capture one strict read-only ADB observation.")
    adb.add_argument("--session-dir", type=Path, required=True)
    adb.add_argument("--adb", type=Path, required=True, help="Absolute path to trusted adb.")

    fastboot = sub.add_parser("capture-fastboot", help="Capture one strict read-only Fastboot observation.")
    fastboot.add_argument("--session-dir", type=Path, required=True)
    fastboot.add_argument("--fastboot", type=Path, required=True, help="Absolute path to trusted fastboot.")
    fastboot.add_argument(
        "--partitions",
        action="store_true",
        help="Collect only the existing bounded read-only partition size/slot hints.",
    )

    finalize = sub.add_parser("finalize", help="Correlate the two saved captures; never authorizes writes.")
    finalize.add_argument("--session-dir", type=Path, required=True)

    verify = sub.add_parser("verify", help="Re-read every saved evidence byte and verify the capture bundle.")
    verify.add_argument("--session-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        session_dir = _absolute(args.session_dir)
        if args.command == "create":
            result = create_capture_session(session_dir, args.profiles)
        elif args.command == "capture-adb":
            profiles = discover_profiles(args.profiles)
            transport = ReadOnlyAdb(args.adb).inspect()
            unified = build_unified_report("adb", transport, profiles)
            result = record_transport_report(
                session_dir,
                args.profiles,
                transport="adb",
                report=unified,
            )
        elif args.command == "capture-fastboot":
            profiles = discover_profiles(args.profiles)
            transport = ReadOnlyFastboot(args.fastboot).inspect(include_partitions=args.partitions)
            unified = build_unified_report("fastboot", transport, profiles)
            result = record_transport_report(
                session_dir,
                args.profiles,
                transport="fastboot",
                report=unified,
            )
        elif args.command == "finalize":
            result = finalize_capture_session(session_dir, args.profiles)
        else:
            result = verify_capture_session(session_dir, args.profiles)
        print(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=True))
        return 0
    except (
        DeviceCaptureSessionError,
        DiagnosticError,
        FastbootDiagnosticError,
        IdentityAssessmentError,
        ProfileError,
        OSError,
        ValueError,
    ):
        print(
            "Capture failed: verify the reviewed profile registry, trusted Android SDK tool path, "
            "single local USB device, transport mode and create-only session files. "
            "Raw paths, device identifiers and subprocess output are withheld.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
