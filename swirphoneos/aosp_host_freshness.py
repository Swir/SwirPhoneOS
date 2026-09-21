"""Fail-closed continuity gate for AOSP builder host evidence.

The gate compares two already-captured, read-only ``aosp_host_evidence``
reports.  It proves that a later build window is still using the same
workspace identity, host identity and exact required tool bytes admitted by
an earlier evidence snapshot.  Dynamic capacity counters may drift, but the
later snapshot must still satisfy any explicitly requested safety floors.

This module never executes build tools, installs packages, mutates the AOSP
workspace, starts Cuttlefish, touches a physical device, or promotes project
status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .aosp_host_evidence import AospHostEvidenceError, load_host_evidence

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_GIB = 1024 ** 3


class AospHostFreshnessError(ValueError):
    """Raised when admitted and current host evidence cannot be trusted."""


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise AospHostFreshnessError(f"{field} must be a lowercase SHA-256 digest.")
    return value


def _nonnegative_int(value: object, field: str, *, optional: bool = False) -> int | None:
    if optional and value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AospHostFreshnessError(f"{field} must be a non-negative integer.")
    return value


def verify_host_freshness(
    admitted: dict[str, object],
    current: dict[str, object],
    *,
    admitted_file_sha256: str,
    current_file_sha256: str,
    require_kvm: bool = False,
    min_ram_bytes: int = 0,
    min_free_bytes: int = 0,
    min_free_inodes: int = 0,
) -> dict[str, object]:
    """Return deterministic evidence that the current host still matches admission.

    Both inputs must already have passed ``aosp_host_evidence`` validation.
    Static host/tool/workspace identity must match exactly.  Resource counters
    are intentionally evaluated only on the current snapshot because they are
    expected to change over time.
    """
    if not isinstance(require_kvm, bool):
        raise AospHostFreshnessError("require_kvm must be a boolean.")
    for value, field in (
        (min_ram_bytes, "min_ram_bytes"),
        (min_free_bytes, "min_free_bytes"),
        (min_free_inodes, "min_free_inodes"),
    ):
        _nonnegative_int(value, field)

    admitted_file_sha256 = _digest(admitted_file_sha256, "admitted_file_sha256")
    current_file_sha256 = _digest(current_file_sha256, "current_file_sha256")

    identity_fields = (
        "workspace_identity_sha256",
        "host_identity_sha256",
        "toolchain_sha256",
        "environment_identity_sha256",
    )
    continuity: dict[str, bool] = {}
    for field in identity_fields:
        left = _digest(admitted.get(field), f"admitted.{field}")
        right = _digest(current.get(field), f"current.{field}")
        matches = left == right
        continuity[field] = matches
        if not matches:
            raise AospHostFreshnessError(f"AOSP host freshness rejected identity drift: {field}.")

    if admitted.get("phase") != "PRE_BUILD" or current.get("phase") != "PRE_BUILD":
        raise AospHostFreshnessError("AOSP host freshness requires PRE_BUILD evidence on both sides.")

    for label, report in (("admitted", admitted), ("current", current)):
        if (
            report.get("device_write_allowed") is not False
            or report.get("build_verified") is not False
            or report.get("boot_verified") is not False
            or report.get("physical_device_support_claimed") is not False
            or report.get("status_promotion_performed") is not False
        ):
            raise AospHostFreshnessError(f"{label} host evidence violates the read-only boundary.")

    resources = current.get("resources")
    if not isinstance(resources, dict):
        raise AospHostFreshnessError("Current host resource snapshot is missing.")
    ram_bytes = _nonnegative_int(resources.get("ram_bytes"), "current.resources.ram_bytes", optional=True)
    free_bytes = _nonnegative_int(resources.get("free_bytes"), "current.resources.free_bytes")
    free_inodes = _nonnegative_int(resources.get("free_inodes"), "current.resources.free_inodes", optional=True)

    failures: list[str] = []
    if min_ram_bytes and (ram_bytes is None or ram_bytes < min_ram_bytes):
        failures.append("ram")
    if min_free_bytes and (free_bytes is None or free_bytes < min_free_bytes):
        failures.append("free_bytes")
    if min_free_inodes and (free_inodes is None or free_inodes < min_free_inodes):
        failures.append("free_inodes")
    if require_kvm and current.get("kvm_available") is not True:
        failures.append("kvm")
    if failures:
        raise AospHostFreshnessError(
            "AOSP host freshness rejected current runtime capacity: " + ", ".join(failures) + "."
        )

    result: dict[str, object] = {
        "schema_version": 1,
        "operation": "AOSP_HOST_FRESHNESS_GATE",
        "fresh": True,
        "read_only": True,
        "admitted_evidence_file_sha256": admitted_file_sha256,
        "current_evidence_file_sha256": current_file_sha256,
        "workspace_identity_sha256": current["workspace_identity_sha256"],
        "host_identity_sha256": current["host_identity_sha256"],
        "toolchain_sha256": current["toolchain_sha256"],
        "environment_identity_sha256": current["environment_identity_sha256"],
        "identity_continuity": continuity,
        "requirements": {
            "require_kvm": require_kvm,
            "min_ram_bytes": min_ram_bytes,
            "min_free_bytes": min_free_bytes,
            "min_free_inodes": min_free_inodes,
        },
        "current_resources": {
            "ram_bytes": ram_bytes,
            "free_bytes": free_bytes,
            "free_inodes": free_inodes,
            "kvm_available": current.get("kvm_available") is True,
        },
        "device_write_allowed": False,
        "build_verified": False,
        "boot_verified": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This gate proves host/tool/workspace continuity only; it does not prove an Android build or boot.",
            "Passing this gate does not authorize flashing, unlocking, rooting, device writes, support claims, milestone promotion, or beta readiness.",
        ],
    }
    result["freshness_sha256"] = _canonical_sha(result)
    return result


def verify_files(
    admitted_path: Path,
    current_path: Path,
    *,
    require_kvm: bool = False,
    min_ram_bytes: int = 0,
    min_free_bytes: int = 0,
    min_free_inodes: int = 0,
) -> dict[str, object]:
    try:
        admitted, admitted_raw_sha = load_host_evidence(admitted_path, expected_phase="PRE_BUILD")
        current, current_raw_sha = load_host_evidence(current_path, expected_phase="PRE_BUILD")
    except AospHostEvidenceError as exc:
        raise AospHostFreshnessError(str(exc)) from exc
    return verify_host_freshness(
        admitted,
        current,
        admitted_file_sha256=admitted_raw_sha,
        current_file_sha256=current_raw_sha,
        require_kvm=require_kvm,
        min_ram_bytes=min_ram_bytes,
        min_free_bytes=min_free_bytes,
        min_free_inodes=min_free_inodes,
    )


def _gib_to_bytes(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AospHostFreshnessError("GiB safety floors must be non-negative integers.")
    return value * _GIB


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify exact AOSP builder host freshness without mutation")
    parser.add_argument("--admitted", required=True, type=Path, help="Absolute admitted PRE_BUILD host evidence JSON")
    parser.add_argument("--current", required=True, type=Path, help="Absolute current PRE_BUILD host evidence JSON")
    parser.add_argument("--require-kvm", action="store_true", help="Require readable/writable KVM evidence")
    parser.add_argument("--min-ram-gib", type=int, default=0)
    parser.add_argument("--min-free-gib", type=int, default=0)
    parser.add_argument("--min-free-inodes", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        result = verify_files(
            args.admitted.resolve(),
            args.current.resolve(),
            require_kvm=args.require_kvm,
            min_ram_bytes=_gib_to_bytes(args.min_ram_gib),
            min_free_bytes=_gib_to_bytes(args.min_free_gib),
            min_free_inodes=args.min_free_inodes,
        )
    except AospHostFreshnessError as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
