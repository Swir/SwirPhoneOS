"""Fail-closed provenance evidence for the packaged SwirPhoneStudio Windows executable."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import sys
from typing import Any


class StudioPackageEvidenceError(ValueError):
    """Raised when Studio package provenance cannot be trusted."""


_SCHEMA_VERSION = 1
_EXPECTED_REPOSITORY = "Swir/SwirPhoneOS"
_EXPECTED_WORKFLOW_PATH = ".github/workflows/package-studio.yml"
_EXPECTED_ARTIFACT_NAME = "SwirPhoneStudio.exe"
_EXPECTED_CHECKSUM_NAME = "SHA256SUMS.txt"
_EXPECTED_PYTHON_PREFIX = "3.14."
_EXPECTED_PYINSTALLER_VERSION = "6.22.3"
_MAX_EXE_BYTES = 512 * 1024 * 1024
_MAX_CHECKSUM_BYTES = 8 * 1024
_MAX_REPORT_BYTES = 256 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_CHECKSUM_LINE = re.compile(r"([0-9a-f]{64})[ \t]+([^\s]+)\Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StudioPackageEvidenceError("Evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def _regular_file(path: Path, *, expected_name: str, max_bytes: int) -> Path:
    candidate = path.expanduser()
    if candidate.name != expected_name:
        raise StudioPackageEvidenceError(f"Expected file name is {expected_name}.")
    if not candidate.is_file() or candidate.is_symlink():
        raise StudioPackageEvidenceError("Evidence input must be a regular non-symlink file.")
    resolved = candidate.resolve()
    size = resolved.stat().st_size
    if size <= 0 or size > max_bytes:
        raise StudioPackageEvidenceError("Evidence input file has an invalid size.")
    return resolved


def _read_checksum(path: Path) -> tuple[str, str]:
    resolved = _regular_file(path, expected_name=_EXPECTED_CHECKSUM_NAME, max_bytes=_MAX_CHECKSUM_BYTES)
    raw = resolved.read_bytes()
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise StudioPackageEvidenceError("SHA256SUMS.txt must be ASCII.") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise StudioPackageEvidenceError("SHA256SUMS.txt must contain exactly one non-empty checksum line.")
    match = _CHECKSUM_LINE.fullmatch(lines[0])
    if match is None or match.group(2) != _EXPECTED_ARTIFACT_NAME:
        raise StudioPackageEvidenceError("SHA256SUMS.txt does not describe the expected Studio executable.")
    return match.group(1), _sha256_file(resolved)


def _runtime_toolchain() -> tuple[str, str]:
    python_version = platform.python_version()
    try:
        pyinstaller_version = importlib.metadata.version("pyinstaller")
    except importlib.metadata.PackageNotFoundError as exc:
        raise StudioPackageEvidenceError("PyInstaller metadata is unavailable in this packaging environment.") from exc
    return python_version, pyinstaller_version


def _validate_toolchain(python_version: str, pyinstaller_version: str) -> None:
    if not python_version.startswith(_EXPECTED_PYTHON_PREFIX):
        raise StudioPackageEvidenceError("Studio packaging evidence requires the pinned Python 3.14 toolchain.")
    if pyinstaller_version != _EXPECTED_PYINSTALLER_VERSION:
        raise StudioPackageEvidenceError("Studio packaging evidence requires the pinned PyInstaller version.")


def _validate_ci_context(
    *,
    source_commit: str,
    repository: str,
    workflow_path: str,
    run_id: int,
    run_attempt: int,
) -> None:
    if not _HEX40.fullmatch(source_commit):
        raise StudioPackageEvidenceError("Source commit must be an exact lowercase Git SHA-1.")
    if repository != _EXPECTED_REPOSITORY:
        raise StudioPackageEvidenceError("Studio package evidence repository identity is not the expected project.")
    if workflow_path != _EXPECTED_WORKFLOW_PATH:
        raise StudioPackageEvidenceError("Studio package evidence workflow path is not the reviewed packaging workflow.")
    if not isinstance(run_id, int) or isinstance(run_id, bool) or run_id <= 0:
        raise StudioPackageEvidenceError("GitHub Actions run id must be a positive integer.")
    if not isinstance(run_attempt, int) or isinstance(run_attempt, bool) or run_attempt <= 0:
        raise StudioPackageEvidenceError("GitHub Actions run attempt must be a positive integer.")


def _canonical_digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def collect_studio_package_evidence(
    exe_path: Path,
    checksums_path: Path,
    source_commit: str,
    *,
    repository: str,
    workflow_path: str,
    run_id: int,
    run_attempt: int,
    python_version: str | None = None,
    pyinstaller_version: str | None = None,
) -> dict[str, object]:
    """Bind one packaged executable to exact bytes, toolchain and CI source identity.

    This is packaging provenance only. It deliberately cannot claim Windows USB runtime,
    phone support, installation readiness, root readiness or beta-gate completion.
    """

    _validate_ci_context(
        source_commit=source_commit,
        repository=repository,
        workflow_path=workflow_path,
        run_id=run_id,
        run_attempt=run_attempt,
    )
    if python_version is None or pyinstaller_version is None:
        detected_python, detected_pyinstaller = _runtime_toolchain()
        python_version = detected_python if python_version is None else python_version
        pyinstaller_version = detected_pyinstaller if pyinstaller_version is None else pyinstaller_version
    _validate_toolchain(python_version, pyinstaller_version)

    exe = _regular_file(exe_path, expected_name=_EXPECTED_ARTIFACT_NAME, max_bytes=_MAX_EXE_BYTES)
    sums = _regular_file(checksums_path, expected_name=_EXPECTED_CHECKSUM_NAME, max_bytes=_MAX_CHECKSUM_BYTES)
    if exe.parent != sums.parent:
        raise StudioPackageEvidenceError("Studio executable and checksum file must be in the same package directory.")
    with exe.open("rb") as handle:
        if handle.read(2) != b"MZ":
            raise StudioPackageEvidenceError("Studio package is not a Windows PE executable.")
    artifact_sha = _sha256_file(exe)
    checksum_artifact_sha, checksum_file_sha = _read_checksum(sums)
    if checksum_artifact_sha != artifact_sha:
        raise StudioPackageEvidenceError("SHA256SUMS.txt does not match the packaged Studio executable bytes.")

    payload: dict[str, object] = {
        "schema_version": _SCHEMA_VERSION,
        "source": "github_actions_windows_x64_package",
        "project": "SwirPhoneOS",
        "component": "SwirPhoneStudio",
        "source_commit": source_commit,
        "ci_context": {
            "provider": "github-actions",
            "repository": repository,
            "workflow_path": workflow_path,
            "run_id": run_id,
            "run_attempt": run_attempt,
        },
        "target": "windows-x64",
        "artifact": {
            "name": _EXPECTED_ARTIFACT_NAME,
            "size": exe.stat().st_size,
            "sha256": artifact_sha,
            "pe_header_verified": True,
        },
        "checksum_file": {
            "name": _EXPECTED_CHECKSUM_NAME,
            "sha256": checksum_file_sha,
            "verified_artifact_sha256": checksum_artifact_sha,
        },
        "toolchain": {
            "python": python_version,
            "pyinstaller": pyinstaller_version,
        },
        "frozen_gui_smoke_gate_required_before_evidence_step": True,
        "packaging_evidence_complete": True,
        "developer_package_only": True,
        "windows_usb_runtime_verified": False,
        "release_artifact": False,
        "beta_gate_passed": False,
        "device_write_allowed": False,
        "warnings": [
            "This proves the packaged executable bytes and packaging CI context only.",
            "Frozen GUI smoke is a packaging gate, not owner-controlled Windows USB ADB/Fastboot evidence.",
            "This report does not authorize flashing, root, device writes or beta release.",
        ],
    }
    payload["evidence_sha256"] = _canonical_digest(payload)
    validate_studio_package_evidence(payload)
    return payload


def validate_studio_package_evidence(report: dict[str, object]) -> None:
    required_keys = {
        "schema_version",
        "source",
        "project",
        "component",
        "source_commit",
        "ci_context",
        "target",
        "artifact",
        "checksum_file",
        "toolchain",
        "frozen_gui_smoke_gate_required_before_evidence_step",
        "packaging_evidence_complete",
        "developer_package_only",
        "windows_usb_runtime_verified",
        "release_artifact",
        "beta_gate_passed",
        "device_write_allowed",
        "warnings",
        "evidence_sha256",
    }
    if set(report) != required_keys:
        raise StudioPackageEvidenceError("Studio package evidence has an unexpected field inventory.")
    if report.get("schema_version") != _SCHEMA_VERSION:
        raise StudioPackageEvidenceError("Unsupported Studio package evidence schema.")
    if report.get("source") != "github_actions_windows_x64_package":
        raise StudioPackageEvidenceError("Studio package evidence source is not trusted.")
    if report.get("project") != "SwirPhoneOS" or report.get("component") != "SwirPhoneStudio":
        raise StudioPackageEvidenceError("Studio package evidence project/component identity is invalid.")
    if report.get("target") != "windows-x64":
        raise StudioPackageEvidenceError("Studio package evidence target is invalid.")

    ci = report.get("ci_context")
    if not isinstance(ci, dict) or set(ci) != {"provider", "repository", "workflow_path", "run_id", "run_attempt"}:
        raise StudioPackageEvidenceError("Studio package CI context is incomplete.")
    if ci.get("provider") != "github-actions":
        raise StudioPackageEvidenceError("Studio package CI provider is invalid.")
    _validate_ci_context(
        source_commit=str(report.get("source_commit") or ""),
        repository=str(ci.get("repository") or ""),
        workflow_path=str(ci.get("workflow_path") or ""),
        run_id=ci.get("run_id"),  # type: ignore[arg-type]
        run_attempt=ci.get("run_attempt"),  # type: ignore[arg-type]
    )

    artifact = report.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {"name", "size", "sha256", "pe_header_verified"}:
        raise StudioPackageEvidenceError("Studio package artifact record is incomplete.")
    if artifact.get("name") != _EXPECTED_ARTIFACT_NAME or artifact.get("pe_header_verified") is not True:
        raise StudioPackageEvidenceError("Studio package artifact identity is invalid.")
    size = artifact.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size > _MAX_EXE_BYTES:
        raise StudioPackageEvidenceError("Studio package artifact size is invalid.")
    artifact_sha = str(artifact.get("sha256") or "")
    if not _HEX64.fullmatch(artifact_sha):
        raise StudioPackageEvidenceError("Studio package artifact SHA-256 is invalid.")

    checksum_file = report.get("checksum_file")
    if not isinstance(checksum_file, dict) or set(checksum_file) != {"name", "sha256", "verified_artifact_sha256"}:
        raise StudioPackageEvidenceError("Studio package checksum record is incomplete.")
    if checksum_file.get("name") != _EXPECTED_CHECKSUM_NAME:
        raise StudioPackageEvidenceError("Studio package checksum file identity is invalid.")
    checksum_sha = str(checksum_file.get("sha256") or "")
    verified_sha = str(checksum_file.get("verified_artifact_sha256") or "")
    if not _HEX64.fullmatch(checksum_sha) or verified_sha != artifact_sha:
        raise StudioPackageEvidenceError("Studio package checksum record is inconsistent.")

    toolchain = report.get("toolchain")
    if not isinstance(toolchain, dict) or set(toolchain) != {"python", "pyinstaller"}:
        raise StudioPackageEvidenceError("Studio package toolchain record is incomplete.")
    _validate_toolchain(str(toolchain.get("python") or ""), str(toolchain.get("pyinstaller") or ""))

    if report.get("frozen_gui_smoke_gate_required_before_evidence_step") is not True:
        raise StudioPackageEvidenceError("Studio package evidence must retain the frozen GUI smoke ordering contract.")
    if report.get("packaging_evidence_complete") is not True or report.get("developer_package_only") is not True:
        raise StudioPackageEvidenceError("Studio package evidence must remain developer-package provenance.")
    for key in ("windows_usb_runtime_verified", "release_artifact", "beta_gate_passed", "device_write_allowed"):
        if report.get(key) is not False:
            raise StudioPackageEvidenceError("Studio package evidence attempted an unauthorized status promotion.")
    warnings = report.get("warnings")
    if not isinstance(warnings, list) or len(warnings) != 3 or any(not isinstance(item, str) or not item for item in warnings):
        raise StudioPackageEvidenceError("Studio package evidence warnings are incomplete.")

    evidence_sha = str(report.get("evidence_sha256") or "")
    if not _HEX64.fullmatch(evidence_sha):
        raise StudioPackageEvidenceError("Studio package evidence digest is invalid.")
    unsigned = dict(report)
    unsigned.pop("evidence_sha256", None)
    if _canonical_digest(unsigned) != evidence_sha:
        raise StudioPackageEvidenceError("Studio package evidence digest does not match the canonical report.")


def verify_studio_package_files(report: dict[str, object], exe_path: Path, checksums_path: Path) -> None:
    """Revalidate a saved report against the exact package bytes it describes."""

    validate_studio_package_evidence(report)
    exe = _regular_file(exe_path, expected_name=_EXPECTED_ARTIFACT_NAME, max_bytes=_MAX_EXE_BYTES)
    sums = _regular_file(checksums_path, expected_name=_EXPECTED_CHECKSUM_NAME, max_bytes=_MAX_CHECKSUM_BYTES)
    if exe.parent != sums.parent:
        raise StudioPackageEvidenceError("Studio executable and checksum file must be in the same package directory.")
    with exe.open("rb") as handle:
        if handle.read(2) != b"MZ":
            raise StudioPackageEvidenceError("Studio package is not a Windows PE executable.")
    checksum_artifact_sha, checksum_file_sha = _read_checksum(sums)
    artifact = report["artifact"]
    checksum_file = report["checksum_file"]
    assert isinstance(artifact, dict) and isinstance(checksum_file, dict)
    actual_sha = _sha256_file(exe)
    if exe.stat().st_size != artifact["size"] or actual_sha != artifact["sha256"]:
        raise StudioPackageEvidenceError("Studio executable bytes no longer match the saved package evidence.")
    if checksum_artifact_sha != actual_sha:
        raise StudioPackageEvidenceError("SHA256SUMS.txt no longer matches the Studio executable.")
    if checksum_file_sha != checksum_file["sha256"]:
        raise StudioPackageEvidenceError("SHA256SUMS.txt bytes no longer match the saved package evidence.")


def load_studio_package_evidence(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise StudioPackageEvidenceError("Studio package evidence must be a regular non-symlink file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_REPORT_BYTES:
        raise StudioPackageEvidenceError("Studio package evidence report has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StudioPackageEvidenceError("Studio package evidence must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise StudioPackageEvidenceError("Studio package evidence root must be an object.")
    validate_studio_package_evidence(value)
    return value


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def _write_report(path: Path, report: dict[str, object]) -> None:
    candidate = path.expanduser()
    if candidate.exists() and candidate.is_symlink():
        raise StudioPackageEvidenceError("Refusing to replace a symlinked evidence output.")
    if not candidate.parent.is_dir():
        raise StudioPackageEvidenceError("Evidence output parent directory does not exist.")
    candidate.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SwirPhoneStudio Windows package provenance evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Create fail-closed evidence for one packaged Studio executable")
    collect.add_argument("--exe", required=True, type=Path)
    collect.add_argument("--checksums", required=True, type=Path)
    collect.add_argument("--source-commit", default=os.environ.get("GITHUB_SHA", ""))
    collect.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    collect.add_argument("--workflow-path", default=_EXPECTED_WORKFLOW_PATH)
    collect.add_argument("--run-id", type=_positive_int, default=os.environ.get("GITHUB_RUN_ID"))
    collect.add_argument("--run-attempt", type=_positive_int, default=os.environ.get("GITHUB_RUN_ATTEMPT"))
    collect.add_argument("--output", required=True, type=Path)

    verify = sub.add_parser("verify", help="Revalidate saved evidence against the exact package bytes")
    verify.add_argument("--report", required=True, type=Path)
    verify.add_argument("--exe", required=True, type=Path)
    verify.add_argument("--checksums", required=True, type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            if args.run_id is None or args.run_attempt is None:
                raise StudioPackageEvidenceError("GitHub Actions run identity is required.")
            report = collect_studio_package_evidence(
                args.exe,
                args.checksums,
                args.source_commit,
                repository=args.repository,
                workflow_path=args.workflow_path,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
            )
            _write_report(args.output, report)
            print(json.dumps({"packaging_evidence_complete": True, "evidence_sha256": report["evidence_sha256"]}, ensure_ascii=True))
        else:
            report = load_studio_package_evidence(args.report)
            verify_studio_package_files(report, args.exe, args.checksums)
            print(json.dumps({"package_bytes_verified": True, "evidence_sha256": report["evidence_sha256"]}, ensure_ascii=True))
        return 0
    except (OSError, StudioPackageEvidenceError, ValueError):
        print("Studio package evidence failed closed; package bytes, checksums, toolchain or CI identity are not trusted.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
