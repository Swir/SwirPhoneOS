"""Shared strict loader for bounded AOSP staging manifest files."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath


class StageManifestError(ValueError):
    """Raised when a staging manifest is malformed or escapes the Swir namespace."""


@dataclass(frozen=True)
class StageFile:
    source: PurePosixPath
    destination: PurePosixPath


def _relative(value: object, field: str) -> PurePosixPath:
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        raise StageManifestError(f"Stage {field} must be a non-empty POSIX relative path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise StageManifestError(f"Stage {field} may not escape its root.")
    return path


def _manifest_paths(product_root: Path) -> tuple[Path, ...]:
    primary = product_root / "stage_manifest.json"
    if not primary.exists():
        return ()
    paths = [primary]
    fragments = product_root / "stage_manifest.d"
    if fragments.exists():
        if not fragments.is_dir() or fragments.is_symlink():
            raise StageManifestError("AOSP stage fragment path must be a regular directory.")
        for path in sorted(fragments.iterdir(), key=lambda item: item.name):
            if path.is_symlink() or not path.is_file() or path.suffix != ".json":
                raise StageManifestError("AOSP stage fragment directory may contain only regular .json files.")
            paths.append(path)
    return tuple(paths)


def load_stage_files(product_root: Path, *, max_files: int = 512) -> tuple[StageFile, ...]:
    paths = _manifest_paths(product_root)
    if not paths:
        return ()
    result: list[StageFile] = []
    sources: set[PurePosixPath] = set()
    destinations: set[PurePosixPath] = set()
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise StageManifestError("AOSP stage manifest is unreadable or invalid JSON.") from exc
        if not raw or len(raw) > 262_144:
            raise StageManifestError("AOSP stage manifest has an invalid size.")
        if not isinstance(data, dict) or set(data) != {"schema_version", "files"} or data["schema_version"] != 1:
            raise StageManifestError("AOSP stage manifest must match schema v1 exactly.")
        files = data["files"]
        if not isinstance(files, list) or not files:
            raise StageManifestError("AOSP stage manifest must contain files.")
        for item in files:
            if not isinstance(item, dict) or set(item) != {"source", "destination"}:
                raise StageManifestError("AOSP stage entry must match schema exactly.")
            source = _relative(item["source"], "source")
            destination = _relative(item["destination"], "destination")
            if not destination.as_posix().startswith("vendor/swir/"):
                raise StageManifestError("AOSP stage destination must remain under vendor/swir/.")
            if source in sources or destination in destinations:
                raise StageManifestError("AOSP stage sources and destinations must be unique across all manifests.")
            sources.add(source)
            destinations.add(destination)
            result.append(StageFile(source, destination))
            if len(result) > max_files:
                raise StageManifestError("AOSP stage bundle contains too many files.")
    return tuple(result)
