"""Post-build verification for the exact SwirPhoneOS source staged into AOSP."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


class StageEvidenceError(ValueError):
    """Raised when persisted staging evidence cannot prove unchanged source bytes."""


_MAX_REPORT_BYTES = 8 * 1024 * 1024
_MAX_FILES = 512
_MAX_FILE_BYTES = 2 * 1024 * 1024
_MAX_TOTAL_BYTES = 32 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StageEvidenceError("Stage evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_report(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise StageEvidenceError("Stage report is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_REPORT_BYTES:
        raise StageEvidenceError("Stage report has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StageEvidenceError("Stage report must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise StageEvidenceError("Stage report root must be an object.")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_destination(root: Path, relative_text: str) -> Path:
    posix = PurePosixPath(relative_text)
    if posix.is_absolute() or posix.as_posix() != relative_text:
        raise StageEvidenceError("Stage destination is not a canonical relative POSIX path.")
    if len(posix.parts) < 3 or posix.parts[:2] != ("vendor", "swir"):
        raise StageEvidenceError("Stage destination is outside vendor/swir.")
    if any(part in ("", ".", "..") for part in posix.parts):
        raise StageEvidenceError("Stage destination contains an unsafe path component.")

    current = root
    for index, part in enumerate(posix.parts):
        current = current / part
        if current.is_symlink():
            raise StageEvidenceError("Stage destination traverses a symlink.")
        if index < len(posix.parts) - 1:
            if not current.is_dir():
                raise StageEvidenceError("Stage destination parent is missing or not a directory.")
        elif not current.is_file():
            raise StageEvidenceError("A staged source path is missing or not a regular file.")
    return current


def verify_post_build_stage(report_path: Path, workspace: Path) -> dict[str, object]:
    root = workspace.expanduser().resolve()
    if root == Path(root.anchor) or not (root / ".repo").is_dir() or not (root / "build" / "envsetup.sh").is_file():
        raise StageEvidenceError("Workspace is not an initialized AOSP checkout.")
    report = _load_report(report_path)
    if report.get("schema_version") != 4:
        raise StageEvidenceError("Unsupported stage report schema.")
    if report.get("executed") is not True or report.get("copy_verified") is not True:
        raise StageEvidenceError("Stage report does not prove an executed verified copy.")
    if report.get("device_write_allowed") is not False:
        raise StageEvidenceError("Stage report violates the no-device-write boundary.")
    try:
        reported_workspace = Path(str(report["workspace"])).expanduser().resolve()
    except (KeyError, OSError, RuntimeError) as exc:
        raise StageEvidenceError("Stage report workspace is invalid.") from exc
    if reported_workspace != root:
        raise StageEvidenceError("Stage report belongs to a different AOSP workspace.")
    digest = str(report.get("staged_content_sha256", ""))
    if _HEX64.fullmatch(digest) is None:
        raise StageEvidenceError("Stage report bundle digest is invalid.")
    files = report.get("files")
    if not isinstance(files, list) or not files or len(files) > _MAX_FILES:
        raise StageEvidenceError("Stage report file inventory is invalid.")

    vendor = root / "vendor"
    swir_root = vendor / "swir"
    if vendor.is_symlink() or swir_root.is_symlink() or not vendor.is_dir() or not swir_root.is_dir():
        raise StageEvidenceError("vendor/swir must remain a real directory tree after the build.")

    verified: list[dict[str, object]] = []
    seen: set[str] = set()
    total = 0
    for item in files:
        if not isinstance(item, dict) or item.get("copy_verified") is not True:
            raise StageEvidenceError("Stage report contains an unverified file record.")
        relative = item.get("destination_relative")
        if not isinstance(relative, str):
            raise StageEvidenceError("Stage destination is invalid.")
        if relative in seen:
            raise StageEvidenceError("Stage report contains a duplicate destination.")
        seen.add(relative)
        target = _safe_destination(root, relative)
        size = target.stat().st_size
        expected_size = item.get("size")
        expected_hash = item.get("sha256")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size <= 0:
            raise StageEvidenceError("Stage record size is invalid.")
        if expected_size > _MAX_FILE_BYTES or size != expected_size:
            raise StageEvidenceError("Staged source byte size changed after staging.")
        if not isinstance(expected_hash, str) or _HEX64.fullmatch(expected_hash) is None:
            raise StageEvidenceError("Stage record SHA-256 is invalid.")
        current_hash = _sha256_file(target)
        if current_hash != expected_hash:
            raise StageEvidenceError("Staged source SHA-256 changed after staging.")
        total += size
        if total > _MAX_TOTAL_BYTES:
            raise StageEvidenceError("Staged source inventory exceeds the bounded evidence size.")
        verified.append({"destination_relative": relative, "size": size, "sha256": current_hash})

    canonical = json.dumps(
        {
            "workspace": str(root),
            "staged_content_sha256": digest,
            "files": sorted(verified, key=lambda item: str(item["destination_relative"])),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "workspace": str(root),
        "stage_report_schema": 4,
        "staged_content_sha256": digest,
        "file_count": len(verified),
        "total_bytes": total,
        "post_build_verified": True,
        "verification_sha256": hashlib.sha256(canonical).hexdigest(),
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "note": "Exact staged source bytes were re-read after the build and still match pre-build size/SHA-256 evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify staged SwirPhoneOS AOSP source bytes after build")
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_post_build_stage(args.report, args.workspace)
    except (StageEvidenceError, OSError, ValueError):
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
