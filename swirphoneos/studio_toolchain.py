"""Safe local Android SDK tool discovery for SwirPhoneStudio.

Discovery only inspects filesystem metadata and environment/path hints. It never
executes ADB/Fastboot, talks to a device, downloads tools, or mutates a phone.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import sys
from typing import Callable, Mapping

_SUPPORTED_TOOLS = frozenset({"adb", "fastboot"})
_MAX_PATH_CHARS = 4096


@dataclass(frozen=True)
class ToolDiscovery:
    """One bounded local discovery result suitable for owner review."""

    tool: str
    path: Path | None
    source: str

    @property
    def found(self) -> bool:
        return self.path is not None


def _expected_filename(tool: str, platform_name: str) -> str:
    return f"{tool}.exe" if platform_name == "win32" else tool


def _validated_candidate(path: Path, tool: str, platform_name: str) -> Path | None:
    """Return a canonical executable candidate without executing it."""
    raw = str(path)
    if not raw or len(raw) > _MAX_PATH_CHARS or not path.is_absolute():
        return None
    try:
        resolved = path.resolve(strict=True)
        if not resolved.is_file():
            return None
    except (OSError, RuntimeError):
        return None

    expected = _expected_filename(tool, platform_name)
    if platform_name == "win32":
        if resolved.name.casefold() != expected.casefold():
            return None
    elif resolved.name != expected or not os.access(resolved, os.X_OK):
        return None
    return resolved


def _sdk_roots(
    environ: Mapping[str, str],
    *,
    home: Path,
    platform_name: str,
) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    for key, source in (("ANDROID_SDK_ROOT", "android_sdk_root"), ("ANDROID_HOME", "android_home")):
        value = environ.get(key, "").strip()
        if value:
            candidate = Path(value).expanduser()
            if candidate.is_absolute():
                roots.append((source, candidate))

    if platform_name == "win32":
        local_app_data = environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            base = Path(local_app_data).expanduser()
            if base.is_absolute():
                roots.append(("default_sdk", base / "Android" / "Sdk"))
    elif platform_name == "darwin":
        if home.is_absolute():
            roots.append(("default_sdk", home / "Library" / "Android" / "sdk"))
    elif home.is_absolute():
        roots.append(("default_sdk", home / "Android" / "Sdk"))

    deduplicated: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for source, root in roots:
        marker = os.path.normcase(str(root)) if platform_name == "win32" else str(root)
        if marker not in seen:
            seen.add(marker)
            deduplicated.append((source, root))
    return deduplicated


def discover_android_tool(
    tool: str,
    *,
    environ: Mapping[str, str] | None = None,
    home: Path | None = None,
    platform_name: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
    include_path: bool = True,
) -> ToolDiscovery:
    """Locate an owner-reviewable ADB/Fastboot candidate without running it.

    Precedence is Android SDK environment variables, the platform's conventional
    SDK directory, then PATH when explicitly allowed by the caller. Invalid,
    relative, missing, wrong-name, and non-executable POSIX candidates fail
    closed. The function never verifies device compatibility or tool provenance.
    """
    normalized = tool.strip().lower()
    if normalized not in _SUPPORTED_TOOLS:
        raise ValueError("Unsupported Android SDK tool.")

    env = os.environ if environ is None else environ
    platform_value = sys.platform if platform_name is None else platform_name
    try:
        home_value = Path.home() if home is None else home
    except (RuntimeError, OSError):
        home_value = Path(".")

    filename = _expected_filename(normalized, platform_value)
    for source, sdk_root in _sdk_roots(env, home=home_value, platform_name=platform_value):
        candidate = _validated_candidate(sdk_root / "platform-tools" / filename, normalized, platform_value)
        if candidate is not None:
            return ToolDiscovery(normalized, candidate, source)

    if include_path:
        try:
            located = which(normalized)
        except (OSError, ValueError):
            located = None
        if located:
            candidate = _validated_candidate(Path(located), normalized, platform_value)
            if candidate is not None:
                return ToolDiscovery(normalized, candidate, "path")

    return ToolDiscovery(normalized, None, "not_found")
