"""Deterministic host-side planning for a pinned SwirPhoneOS ARM64 GSI build."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .gsi_contract import GsiContract
from .platform import PlatformBaseline


class GsiWorkspaceError(ValueError):
    """Raised when an ARM64 GSI build plan is incomplete or unsafe."""


@dataclass(frozen=True)
class GsiWorkspacePlan:
    workspace: Path
    manifest_url: str
    revision: str
    lunch_choice: str
    jobs: int
    commands: tuple[tuple[str, ...], ...]
    expected_system_image: Path


def _safe_workspace(path: Path) -> Path:
    root = path.expanduser().resolve()
    if root == Path(root.anchor):
        raise GsiWorkspaceError("AOSP GSI workspace must not be a filesystem root.")
    return root


def make_gsi_workspace_plan(
    baseline: PlatformBaseline,
    contract: GsiContract,
    workspace: Path,
    *,
    jobs: int = 8,
) -> GsiWorkspacePlan:
    if not baseline.pinned or baseline.repo_init_revision is None:
        raise GsiWorkspaceError("AOSP baseline is not completely pinned.")
    if baseline.status == "CANDIDATE_NOT_PINNED":
        raise GsiWorkspaceError("Unpinned AOSP candidates cannot create a GSI workspace plan.")
    if not isinstance(jobs, int) or isinstance(jobs, bool) or not 1 <= jobs <= 256:
        raise GsiWorkspaceError("jobs must be an integer between 1 and 256.")
    root = _safe_workspace(workspace)
    build_script = (
        "set -euo pipefail; source build/envsetup.sh; "
        + f"lunch {contract.lunch_choice}; m -j{jobs} systemimage"
    )
    commands = (
        ("repo", "init", "-u", baseline.manifest_url, "-b", baseline.repo_init_revision),
        ("repo", "sync", "-c", "--no-tags", "--optimized-fetch", "--prune", f"-j{jobs}"),
        ("repo", "manifest", "-r", "-o", "swirphoneos-gsi-pinned-manifest.xml"),
        ("python", "-m", "swirphoneos", "stage-product", "--workspace", str(root), "--execute"),
        ("bash", "-lc", build_script),
    )
    return GsiWorkspacePlan(
        workspace=root,
        manifest_url=baseline.manifest_url,
        revision=baseline.repo_init_revision,
        lunch_choice=contract.lunch_choice,
        jobs=jobs,
        commands=commands,
        expected_system_image=root / "out" / "target" / "product" / contract.device / "system.img",
    )


def public_gsi_workspace_plan(plan: GsiWorkspacePlan) -> dict[str, object]:
    return {
        "schema_version": 1,
        "workspace": str(plan.workspace),
        "manifest_url": plan.manifest_url,
        "revision": plan.revision,
        "lunch_choice": plan.lunch_choice,
        "jobs": plan.jobs,
        "commands": [list(command) for command in plan.commands],
        "expected_system_image": str(plan.expected_system_image),
        "build_verified": False,
        "treble_vts_verified": False,
        "physical_device_compatibility_verified": False,
        "install_verified": False,
        "device_write_allowed": False,
        "note": (
            "Plan only. It may build a generic ARM64 system image on a dedicated host, but it "
            "does not test Treble/VTS, install to a phone, or claim one image works on every device."
        ),
    }
