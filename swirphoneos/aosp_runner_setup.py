"""Local, explicit setup helper for a registered self-hosted AOSP runner.

This module only prepares the owner-controlled runner environment file and
workspace directory. It never registers a runner, changes GitHub labels,
installs packages, invokes network tools, runs ADB/Fastboot, or starts a build.
"""
from __future__ import annotations

from pathlib import Path
import os

ENV_KEY = "SWIR_AOSP_WORKSPACE"
MAX_ENV_BYTES = 64 * 1024
REQUIRED_RUNNER_LABELS = ("self-hosted", "linux", "x64", "swir-aosp-builder")
RUNNER_MARKERS = ("config.sh", "run.sh", ".runner")


class RunnerSetupError(ValueError):
    """Raised when local runner setup cannot be performed safely."""


def _contains_control(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _canonical_runner_dir(path: Path) -> Path:
    if not path.is_absolute():
        raise RunnerSetupError("Runner directory must be absolute.")
    if path.is_symlink():
        raise RunnerSetupError("Runner directory must not be a symlink.")
    try:
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RunnerSetupError("Runner directory does not exist.") from exc
    if not canonical.is_dir():
        raise RunnerSetupError("Runner directory must be a directory.")
    for marker in RUNNER_MARKERS:
        marker_path = canonical / marker
        if marker_path.is_symlink() or not marker_path.is_file():
            raise RunnerSetupError(
                "Runner directory must contain registered self-hosted runner markers."
            )
    return canonical


def _workspace_path(path: Path, runner_dir: Path) -> Path:
    if not path.is_absolute():
        raise RunnerSetupError("AOSP workspace must be absolute.")
    raw = str(path)
    if not raw or _contains_control(raw):
        raise RunnerSetupError("AOSP workspace path contains unsafe characters.")

    expanded = path
    home = Path.home().resolve()
    anchor = Path(path.anchor).resolve()
    if expanded == anchor or expanded == home:
        raise RunnerSetupError("AOSP workspace cannot be the filesystem root or user home.")

    # Keep the large AOSP checkout physically separate from the Actions runner.
    try:
        expanded.relative_to(runner_dir)
    except ValueError:
        pass
    else:
        raise RunnerSetupError("AOSP workspace cannot live inside the Actions runner directory.")
    try:
        runner_dir.relative_to(expanded)
    except ValueError:
        pass
    else:
        raise RunnerSetupError("Actions runner directory cannot live inside the AOSP workspace.")

    if expanded.exists() and expanded.is_symlink():
        raise RunnerSetupError("AOSP workspace must not be a symlink.")
    if expanded.exists() and not expanded.is_dir():
        raise RunnerSetupError("AOSP workspace path must be a directory.")
    return expanded


def _read_env(path: Path) -> list[str]:
    if path.is_symlink():
        raise RunnerSetupError("Runner .env must not be a symlink.")
    if not path.exists():
        return []
    if not path.is_file():
        raise RunnerSetupError("Runner .env must be a regular file.")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RunnerSetupError("Runner .env could not be read.") from exc
    if len(raw) > MAX_ENV_BYTES:
        raise RunnerSetupError("Runner .env exceeds the 64 KiB safety bound.")
    try:
        return raw.decode("utf-8", "strict").splitlines()
    except UnicodeError as exc:
        raise RunnerSetupError("Runner .env must be strict UTF-8.") from exc


def _configured_workspace(lines: list[str]) -> str | None:
    prefix = ENV_KEY + "="
    values = [line[len(prefix):] for line in lines if line.startswith(prefix)]
    if not values:
        return None
    if len(values) != 1:
        raise RunnerSetupError("Runner .env contains duplicate SWIR_AOSP_WORKSPACE entries.")
    return values[0]


def plan_local_runner_setup(runner_dir: Path, workspace: Path) -> dict[str, object]:
    """Return a bounded local setup plan without mutating the host."""
    runner = _canonical_runner_dir(runner_dir)
    target = _workspace_path(workspace, runner)
    lines = _read_env(runner / ".env")
    configured = _configured_workspace(lines)
    try:
        target_display = str(target.resolve(strict=True)) if target.exists() else str(target)
    except (OSError, RuntimeError) as exc:
        raise RunnerSetupError("AOSP workspace could not be resolved safely.") from exc
    return {
        "schema_version": 1,
        "operation": "AOSP_RUNNER_LOCAL_SETUP",
        "mutations_performed": False,
        "runner_registered_locally": True,
        "runner_directory": str(runner),
        "workspace": target_display,
        "workspace_exists": target.exists(),
        "environment_file": str(runner / ".env"),
        "environment_matches": configured == target_display,
        "required_labels": list(REQUIRED_RUNNER_LABELS),
        "server_side_label_verified": False,
        "registration_token_required_by_this_tool": False,
        "packages_installed": False,
        "github_registration_performed": False,
        "build_started": False,
        "device_write_allowed": False,
    }


def apply_local_runner_setup(runner_dir: Path, workspace: Path) -> dict[str, object]:
    """Create the workspace and persist only SWIR_AOSP_WORKSPACE in runner .env."""
    runner = _canonical_runner_dir(runner_dir)
    target = _workspace_path(workspace, runner)

    try:
        target.mkdir(parents=True, exist_ok=True)
        target = target.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise RunnerSetupError("AOSP workspace could not be created safely.") from exc
    if target.is_symlink() or not target.is_dir():
        raise RunnerSetupError("AOSP workspace did not resolve to a real directory.")

    env_path = runner / ".env"
    lines = _read_env(env_path)
    prefix = ENV_KEY + "="
    retained = [line for line in lines if not line.startswith(prefix)]
    retained.append(f"{ENV_KEY}={target}")
    payload = ("\n".join(retained).rstrip("\n") + "\n").encode("utf-8")
    if len(payload) > MAX_ENV_BYTES:
        raise RunnerSetupError("Updated runner .env would exceed the 64 KiB safety bound.")

    temp_path = runner / ".env.swirphoneos.tmp"
    if temp_path.exists() or temp_path.is_symlink():
        raise RunnerSetupError("Temporary runner environment path already exists.")
    try:
        with temp_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, env_path)
    except OSError as exc:
        try:
            if temp_path.exists() and not temp_path.is_symlink():
                temp_path.unlink()
        except OSError:
            pass
        raise RunnerSetupError("Runner .env could not be updated atomically.") from exc

    result = plan_local_runner_setup(runner, target)
    result["mutations_performed"] = True
    result["workspace_created_or_verified"] = True
    result["environment_matches"] = True
    result["next_required_action"] = (
        "Verify the registered runner has labels self-hosted,linux,x64,swir-aosp-builder "
        "and restart its service before dispatching AOSP builder admission."
    )
    return result
