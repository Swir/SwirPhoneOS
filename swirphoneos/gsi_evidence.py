"""Tamper-evident build evidence for the SwirPhoneOS ARM64 Generic System Image."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .aosp_workspace import AospWorkspaceError, validate_resolved_manifest
from .platform import PlatformBaseline, load_baseline


class GsiEvidenceError(ValueError):
    """Raised when ARM64 GSI build evidence is incomplete or does not match the pinned baseline."""


_EXPECTED_PRODUCT = "swirphoneos_gsi_arm64"
_EXPECTED_DEVICE = "generic_arm64"
_EXPECTED_ARCH = "arm64"
_EXPECTED_ANDROID_RELEASE = "17"
_EXPECTED_API_LEVEL = "37"
_EXPECTED_BUILD_TYPE = "userdebug"
_BUILD_PROP_CANDIDATES = (Path("system/build.prop"), Path("system/system/build.prop"))
_REQUIRED_BUILD_PROPERTIES = (
    "ro.build.fingerprint",
    "ro.build.id",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.build.type",
)
_MAX_BUILD_PROP_BYTES = 2 * 1024 * 1024


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_build_properties(product_out: Path) -> dict[str, str]:
    build_prop = next((product_out / rel for rel in _BUILD_PROP_CANDIDATES if (product_out / rel).is_file()), None)
    if build_prop is None or build_prop.is_symlink():
        raise GsiEvidenceError("GSI product output does not expose a regular system build.prop.")
    raw = build_prop.read_bytes()
    if not raw or len(raw) > _MAX_BUILD_PROP_BYTES:
        raise GsiEvidenceError("GSI system build.prop has an invalid size.")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise GsiEvidenceError("GSI system build.prop must be UTF-8.") from exc
    props: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in props:
            raise GsiEvidenceError("GSI system build.prop contains a duplicate key.")
        props[key] = value
    if any(not props.get(key) for key in _REQUIRED_BUILD_PROPERTIES):
        raise GsiEvidenceError("GSI system build.prop is missing required build identity.")
    return {key: props[key] for key in _REQUIRED_BUILD_PROPERTIES}


def _validate_build_identity(props: dict[str, str], baseline: PlatformBaseline) -> None:
    expected = {
        "ro.build.id": baseline.candidate_build_id,
        "ro.build.version.release": _EXPECTED_ANDROID_RELEASE,
        "ro.build.version.sdk": _EXPECTED_API_LEVEL,
        "ro.build.version.security_patch": baseline.security_patch_level,
        "ro.build.type": _EXPECTED_BUILD_TYPE,
    }
    mismatches = [key for key, value in expected.items() if props.get(key) != value]
    if mismatches:
        raise GsiEvidenceError(
            "Built GSI identity does not match the pinned Android baseline: "
            + ", ".join(sorted(mismatches))
            + "."
        )
    prefix = f"Swir/{_EXPECTED_PRODUCT}/{_EXPECTED_DEVICE}:"
    fingerprint = props["ro.build.fingerprint"]
    if not fingerprint.startswith(prefix) or not fingerprint.isascii() or len(fingerprint) > 512:
        raise GsiEvidenceError("Built GSI fingerprint does not match the reviewed SwirPhoneOS ARM64 product identity.")


def collect_gsi_build_evidence(
    workspace: Path,
    resolved_manifest: Path,
    baseline_path: Path,
) -> dict[str, object]:
    root = workspace.expanduser().resolve()
    if root == Path(root.anchor) or not (root / ".repo").is_dir() or not (root / "build" / "envsetup.sh").is_file():
        raise GsiEvidenceError("Workspace is not an initialized AOSP checkout.")
    try:
        manifest = validate_resolved_manifest(resolved_manifest)
        baseline = load_baseline(baseline_path)
    except (AospWorkspaceError, OSError, ValueError) as exc:
        raise GsiEvidenceError("Pinned source identity could not be validated for the GSI build.") from exc
    if not baseline.pinned or not baseline.repo_init_revision:
        raise GsiEvidenceError("AOSP baseline is not fully pinned.")

    product_out = root / "out" / "target" / "product" / _EXPECTED_DEVICE
    if not product_out.is_dir():
        raise GsiEvidenceError("Expected generic_arm64 product output directory does not exist.")
    system_image = product_out / "system.img"
    if not system_image.is_file() or system_image.is_symlink():
        raise GsiEvidenceError("Required GSI system.img is missing or unsafe.")
    image_size = system_image.stat().st_size
    if image_size <= 0:
        raise GsiEvidenceError("Required GSI system.img is empty.")

    props = _read_build_properties(product_out)
    _validate_build_identity(props, baseline)
    return {
        "schema_version": 1,
        "source": "local_aosp_gsi_build_output",
        "expected_product": _EXPECTED_PRODUCT,
        "expected_device": _EXPECTED_DEVICE,
        "architecture": _EXPECTED_ARCH,
        "baseline_revision": baseline.repo_init_revision,
        "baseline_identity": {
            "build_id": baseline.candidate_build_id,
            "android_release": _EXPECTED_ANDROID_RELEASE,
            "api_level": _EXPECTED_API_LEVEL,
            "security_patch": baseline.security_patch_level,
            "build_type": _EXPECTED_BUILD_TYPE,
        },
        "resolved_manifest": {
            "project_count": manifest.project_count,
            "unique_path_count": manifest.unique_path_count,
            "sha256": manifest.sha256,
            "all_projects_pinned": manifest.all_projects_pinned,
        },
        "build": {
            "fingerprint": props["ro.build.fingerprint"],
            "build_id": props["ro.build.id"],
            "android_release": props["ro.build.version.release"],
            "api_level": props["ro.build.version.sdk"],
            "security_patch": props["ro.build.version.security_patch"],
            "build_type": props["ro.build.type"],
        },
        "system_image": {
            "path": "system.img",
            "size": image_size,
            "sha256": _sha256_file(system_image),
        },
        "gsi_build_evidence_complete": True,
        "treble_vts_verified": False,
        "physical_device_compatibility_verified": False,
        "install_verified": False,
        "rollback_verified": False,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "release_artifact": False,
        "warnings": [
            "A built GSI system.img is not proof that it can boot safely on an arbitrary Android device.",
            "Treble/VTS compatibility, vendor interface compatibility, boot requirements and recovery remain unverified.",
            "This evidence never authorizes flashing or changes any physical-device support status.",
        ],
    }
