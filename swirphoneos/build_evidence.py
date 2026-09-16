"""Tamper-evident build/runtime provenance for SwirPhoneOS AOSP evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .aosp_workspace import AospWorkspaceError, validate_resolved_manifest
from .cuttlefish_evidence import EXPECTED_PRODUCT
from .platform import load_baseline


class BuildEvidenceError(ValueError):
    """Raised when build provenance is incomplete, ambiguous or unsafe to trust."""


_EXPECTED_OUT_PARTS = ("out", "target", "product", EXPECTED_PRODUCT)
_REQUIRED_ARTIFACTS = ("boot.img", "system.img")
_OPTIONAL_ARTIFACTS = (
    "init_boot.img",
    "vendor_boot.img",
    "vendor.img",
    "product.img",
    "system_ext.img",
    "vbmeta.img",
    "vbmeta_system.img",
    "super.img",
    "android-info.txt",
    "module-info.json",
)
_BUILD_PROP_CANDIDATES = (Path("system/build.prop"), Path("system/system/build.prop"))
_MAX_JSON_BYTES = 4 * 1024 * 1024
_MAX_BUILD_PROP_BYTES = 2 * 1024 * 1024
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_build_properties(product_out: Path) -> dict[str, str]:
    build_prop = next((product_out / rel for rel in _BUILD_PROP_CANDIDATES if (product_out / rel).is_file()), None)
    if build_prop is None or build_prop.is_symlink():
        raise BuildEvidenceError("Built product does not expose a regular system build.prop.")
    raw = build_prop.read_bytes()
    if not raw or len(raw) > _MAX_BUILD_PROP_BYTES:
        raise BuildEvidenceError("system build.prop has an invalid size.")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise BuildEvidenceError("system build.prop must be UTF-8.") from exc
    props: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key in props:
            raise BuildEvidenceError("system build.prop contains a duplicate key.")
        props[key] = value
    required = ("ro.build.fingerprint", "ro.build.id", "ro.build.version.release", "ro.build.version.sdk", "ro.build.type")
    if any(not props.get(key) for key in required):
        raise BuildEvidenceError("system build.prop is missing required build identity.")
    return {key: props[key] for key in required}


def _artifact_record(path: Path, product_out: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise BuildEvidenceError("Build artifact must be a regular non-symlink file.")
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(product_out.resolve())
    except ValueError as exc:
        raise BuildEvidenceError("Build artifact escapes the expected product output directory.") from exc
    size = resolved.stat().st_size
    if size <= 0:
        raise BuildEvidenceError("Build artifact is empty.")
    return {"path": relative.as_posix(), "size": size, "sha256": _sha256_file(resolved)}


def collect_build_evidence(workspace: Path, resolved_manifest: Path, baseline_path: Path) -> dict[str, object]:
    root = workspace.expanduser().resolve()
    if root == Path(root.anchor) or not (root / ".repo").is_dir() or not (root / "build" / "envsetup.sh").is_file():
        raise BuildEvidenceError("Workspace is not an initialized AOSP checkout.")
    try:
        manifest = validate_resolved_manifest(resolved_manifest)
        baseline = load_baseline(baseline_path)
    except (AospWorkspaceError, OSError, ValueError) as exc:
        raise BuildEvidenceError("Pinned source identity could not be validated.") from exc
    if not baseline.pinned or not baseline.repo_init_revision:
        raise BuildEvidenceError("AOSP baseline is not fully pinned.")
    product_out = root.joinpath(*_EXPECTED_OUT_PARTS)
    if not product_out.is_dir():
        raise BuildEvidenceError("Expected SwirPhoneOS product output directory does not exist.")
    paths = [product_out / name for name in (*_REQUIRED_ARTIFACTS, *_OPTIONAL_ARTIFACTS) if (product_out / name).exists()]
    names = {path.name for path in paths}
    if any(name not in names for name in _REQUIRED_ARTIFACTS):
        raise BuildEvidenceError("Required core AOSP image artifact is missing.")
    artifacts = [_artifact_record(path, product_out) for path in paths]
    props = _read_build_properties(product_out)
    report: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_build_output",
        "expected_product": EXPECTED_PRODUCT,
        "baseline_revision": baseline.repo_init_revision,
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
            "build_type": props["ro.build.type"],
        },
        "artifacts": artifacts,
        "required_artifacts": list(_REQUIRED_ARTIFACTS),
        "build_evidence_complete": True,
        "device_write_allowed": False,
        "status_promotion_performed": False,
        "warnings": [
            "Artifact hashes prove file identity, not hardware compatibility.",
            "This report does not launch Cuttlefish or promote Android runtime status.",
        ],
    }
    return report


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BuildEvidenceError("Evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def load_json_report(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise BuildEvidenceError("Evidence report is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_JSON_BYTES:
        raise BuildEvidenceError("Evidence report has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BuildEvidenceError("Evidence report is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise BuildEvidenceError("Evidence report root must be an object.")
    return value


def create_evidence_bundle(build_report: dict[str, object], runtime_report: dict[str, object]) -> dict[str, object]:
    reasons: list[str] = []
    if build_report.get("schema_version") != 1 or build_report.get("build_evidence_complete") is not True:
        reasons.append("build evidence is not complete")
    if runtime_report.get("schema_version") != 3 or runtime_report.get("runtime_evidence_complete") is not True:
        reasons.append("runtime evidence is not complete")
    if build_report.get("expected_product") != EXPECTED_PRODUCT or runtime_report.get("expected_product") != EXPECTED_PRODUCT:
        reasons.append("product identity does not match the SwirPhoneOS Cuttlefish contract")
    build_identity = build_report.get("build") if isinstance(build_report.get("build"), dict) else {}
    build_fingerprint = build_identity.get("fingerprint") if isinstance(build_identity, dict) else None
    runtime_fingerprint = runtime_report.get("build_fingerprint")
    if not build_fingerprint or build_fingerprint != runtime_fingerprint:
        reasons.append("runtime fingerprint does not match the hashed build output identity")
    runtime_digest = runtime_report.get("build_fingerprint_sha256")
    if build_fingerprint:
        expected_digest = hashlib.sha256(str(build_fingerprint).encode("ascii")).hexdigest()
        if runtime_digest != expected_digest or not _HEX64.fullmatch(str(runtime_digest or "")):
            reasons.append("runtime fingerprint digest is inconsistent")
    if reasons:
        raise BuildEvidenceError("Evidence bundle rejected: " + "; ".join(reasons) + ".")
    payload = {
        "schema_version": 1,
        "expected_product": EXPECTED_PRODUCT,
        "build": build_report,
        "runtime": runtime_report,
        "runtime_status_promotion_performed": False,
        "physical_device_support_claimed": False,
        "device_write_allowed": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["bundle_sha256"] = hashlib.sha256(canonical).hexdigest()
    payload["evidence_bundle_complete"] = True
    return payload
