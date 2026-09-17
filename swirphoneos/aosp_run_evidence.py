"""Cross-report integrity checks for one SwirPhoneOS AOSP build/runtime run.

This module does not build Android, launch an emulator, mutate a phone or promote
project state. It only validates and hashes already-produced JSON evidence so
artifacts from different runs cannot be mixed without detection.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .cuttlefish_evidence import (
    EXPECTED_ANDROID_RELEASE,
    EXPECTED_API_LEVEL,
    EXPECTED_BUILD_TYPE,
    EXPECTED_PRODUCT,
)
from .system_apps import SystemAppRegistryError, load_registry


class AospRunEvidenceError(ValueError):
    """Raised when one AOSP run contains incomplete or cross-run evidence."""


_MAX_REPORT_BYTES = 16 * 1024 * 1024
_MAX_APP_MANIFEST_BYTES = 2 * 1024 * 1024
_HEX40 = re.compile(r"[0-9a-f]{40}\Z")
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_EXPECTED_LUNCH = f"{EXPECTED_PRODUCT}-aosp_current-userdebug"
_RUNTIME_GROUP = ("runtime", "smoke", "bundle")


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AospRunEvidenceError("AOSP run evidence JSON contains a duplicate key.")
        result[key] = value
    return result


def _load_report(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_file() or path.is_symlink():
        raise AospRunEvidenceError("Evidence input is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_REPORT_BYTES:
        raise AospRunEvidenceError("Evidence input has an invalid size.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospRunEvidenceError("Evidence input must be strict UTF-8 JSON.") from exc
    if not isinstance(value, dict):
        raise AospRunEvidenceError("Evidence input root must be an object.")
    return value, hashlib.sha256(raw).hexdigest()


def _load_app_registry_identity(path: Path) -> tuple[list[str], str]:
    if not path.is_file() or path.is_symlink():
        raise AospRunEvidenceError("System-app manifest is missing or is not a regular file.")
    raw = path.read_bytes()
    if not raw or len(raw) > _MAX_APP_MANIFEST_BYTES:
        raise AospRunEvidenceError("System-app manifest has an invalid size.")
    try:
        registry = load_registry(path)
    except (SystemAppRegistryError, OSError, ValueError) as exc:
        raise AospRunEvidenceError("System-app manifest could not be validated.") from exc
    packages = sorted(app.package for app in registry.apps if app.source_ready)
    if not packages or len(packages) != len(set(packages)):
        raise AospRunEvidenceError("System-app manifest has no unique source-ready package set.")
    return packages, hashlib.sha256(raw).hexdigest()


def _require_hex64(value: object, field: str) -> str:
    text = str(value or "")
    if _HEX64.fullmatch(text) is None:
        raise AospRunEvidenceError(f"{field} must be a lowercase SHA-256 digest.")
    return text


def _require_no_write(report: dict[str, object], key: str = "device_write_allowed") -> None:
    if report.get(key) is not False:
        raise AospRunEvidenceError(f"Evidence report violates the no-write boundary: {key}.")


def _unique_strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AospRunEvidenceError(f"{field} must be a non-empty list.")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 256:
            raise AospRunEvidenceError(f"{field} contains an invalid string.")
        if item in seen:
            raise AospRunEvidenceError(f"{field} contains a duplicate value.")
        seen.add(item)
        result.append(item)
    return result


def _artifact_paths(build: dict[str, object]) -> set[str]:
    artifacts = build.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise AospRunEvidenceError("Build evidence has no artifact inventory.")
    paths: set[str] = set()
    for item in artifacts:
        if not isinstance(item, dict):
            raise AospRunEvidenceError("Build artifact record is invalid.")
        path = item.get("path")
        size = item.get("size")
        digest = item.get("sha256")
        if not isinstance(path, str) or not path or path in paths:
            raise AospRunEvidenceError("Build artifact path is invalid or duplicated.")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise AospRunEvidenceError("Build artifact size is invalid.")
        _require_hex64(digest, "build artifact sha256")
        paths.add(path)
    return paths


def _validate_build_chain(
    source_commit: str,
    preflight: dict[str, object],
    plan: dict[str, object],
    manifest: dict[str, object],
    stage: dict[str, object],
    post_stage: dict[str, object],
    build: dict[str, object],
) -> tuple[str, str, str]:
    if _HEX40.fullmatch(source_commit) is None:
        raise AospRunEvidenceError("Source commit must be an exact lowercase 40-character Git SHA-1.")

    if (
        preflight.get("schema_version") != 1
        or preflight.get("operation") != "READ_ONLY_HOST_PREFLIGHT"
        or preflight.get("ready_for_source_sync") is not True
        or preflight.get("ready_for_full_build") is not True
    ):
        raise AospRunEvidenceError("Builder preflight does not prove a build-ready host.")

    if plan.get("schema_version") != 2:
        raise AospRunEvidenceError("AOSP workspace plan schema is unsupported.")
    _require_no_write(plan)
    if plan.get("build_verified") is not False or plan.get("boot_verified") is not False:
        raise AospRunEvidenceError("Planning evidence must not claim build or boot verification.")
    workspace = plan.get("workspace")
    revision = plan.get("revision")
    if not isinstance(workspace, str) or not workspace:
        raise AospRunEvidenceError("AOSP plan workspace identity is missing.")
    if not isinstance(revision, str) or not revision:
        raise AospRunEvidenceError("AOSP plan revision identity is missing.")
    if plan.get("lunch_choice") != _EXPECTED_LUNCH:
        raise AospRunEvidenceError("AOSP plan lunch target is not the SwirPhoneOS Cuttlefish product.")

    if (
        manifest.get("schema_version") != 1
        or manifest.get("all_projects_pinned") is not True
        or manifest.get("build_verified") is not False
        or manifest.get("boot_verified") is not False
    ):
        raise AospRunEvidenceError("Resolved Repo manifest evidence is incomplete or overclaims runtime state.")
    manifest_sha = _require_hex64(manifest.get("sha256"), "resolved manifest sha256")
    project_count = manifest.get("project_count")
    unique_count = manifest.get("unique_path_count")
    if (
        not isinstance(project_count, int)
        or isinstance(project_count, bool)
        or project_count <= 0
        or unique_count != project_count
    ):
        raise AospRunEvidenceError("Resolved Repo manifest project/path counts are invalid.")

    if (
        stage.get("schema_version") != 5
        or stage.get("executed") is not True
        or stage.get("copy_verified") is not True
        or stage.get("destination_tree_closed") is not True
    ):
        raise AospRunEvidenceError("Pre-build source staging evidence is incomplete.")
    _require_no_write(stage)
    if stage.get("workspace") != workspace:
        raise AospRunEvidenceError("Stage evidence belongs to a different AOSP workspace.")
    stage_digest = _require_hex64(stage.get("staged_content_sha256"), "staged source digest")
    files = stage.get("files")
    if not isinstance(files, list) or not files:
        raise AospRunEvidenceError("Stage evidence has no file inventory.")
    if stage.get("file_count") != len(files) or stage.get("destination_file_count") != len(files):
        raise AospRunEvidenceError("Stage evidence does not prove an exact destination file count.")
    preexisting = stage.get("preexisting_destination_file_count")
    if not isinstance(preexisting, int) or isinstance(preexisting, bool) or not 0 <= preexisting <= len(files):
        raise AospRunEvidenceError("Stage evidence pre-existing destination count is invalid.")
    destinations: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or item.get("copy_verified") is not True:
            raise AospRunEvidenceError("Stage evidence contains an unverified file.")
        destination = item.get("destination_relative")
        if not isinstance(destination, str) or not destination.startswith("vendor/swir/") or destination in destinations:
            raise AospRunEvidenceError("Stage destination is invalid or duplicated.")
        destinations.add(destination)
        size = item.get("size")
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise AospRunEvidenceError("Stage file size is invalid.")
        _require_hex64(item.get("sha256"), "staged file sha256")

    if (
        post_stage.get("schema_version") != 1
        or post_stage.get("stage_report_schema") != 5
        or post_stage.get("post_build_verified") is not True
        or post_stage.get("destination_tree_closed") is not True
    ):
        raise AospRunEvidenceError("Post-build source re-verification evidence is incomplete.")
    _require_no_write(post_stage)
    if post_stage.get("workspace") != workspace or post_stage.get("staged_content_sha256") != stage_digest:
        raise AospRunEvidenceError("Post-build source evidence does not match the staged source bundle.")
    if post_stage.get("file_count") != len(files) or post_stage.get("destination_file_count") != len(files):
        raise AospRunEvidenceError("Post-build source evidence file count does not match staging.")
    _require_hex64(post_stage.get("verification_sha256"), "post-build stage verification sha256")

    if build.get("schema_version") != 1 or build.get("build_evidence_complete") is not True:
        raise AospRunEvidenceError("AOSP build evidence is incomplete.")
    _require_no_write(build)
    if build.get("status_promotion_performed") is not False:
        raise AospRunEvidenceError("Build evidence must not promote project status.")
    if build.get("expected_product") != EXPECTED_PRODUCT or build.get("baseline_revision") != revision:
        raise AospRunEvidenceError("Build product/revision does not match the reviewed AOSP plan.")
    resolved = build.get("resolved_manifest")
    if not isinstance(resolved, dict):
        raise AospRunEvidenceError("Build evidence is missing resolved-manifest identity.")
    if (
        resolved.get("sha256") != manifest_sha
        or resolved.get("project_count") != project_count
        or resolved.get("unique_path_count") != unique_count
        or resolved.get("all_projects_pinned") is not True
    ):
        raise AospRunEvidenceError("Build evidence is bound to different source revisions.")
    identity = build.get("build")
    baseline_identity = build.get("baseline_identity")
    if not isinstance(identity, dict) or not isinstance(baseline_identity, dict):
        raise AospRunEvidenceError("Build evidence is missing pinned build identity.")
    if (
        identity.get("android_release") != EXPECTED_ANDROID_RELEASE
        or identity.get("api_level") != EXPECTED_API_LEVEL
        or identity.get("build_type") != EXPECTED_BUILD_TYPE
        or baseline_identity.get("android_release") != EXPECTED_ANDROID_RELEASE
        or baseline_identity.get("api_level") != EXPECTED_API_LEVEL
        or baseline_identity.get("build_type") != EXPECTED_BUILD_TYPE
        or identity.get("build_id") != baseline_identity.get("build_id")
        or identity.get("security_patch") != baseline_identity.get("security_patch")
    ):
        raise AospRunEvidenceError("Built Android identity is not consistent with the pinned baseline.")
    fingerprint = identity.get("fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise AospRunEvidenceError("Build fingerprint is missing.")
    required_artifacts = _unique_strings(build.get("required_artifacts"), "required_artifacts")
    paths = _artifact_paths(build)
    if set(required_artifacts) != {"boot.img", "system.img"} or not set(required_artifacts).issubset(paths):
        raise AospRunEvidenceError("Required core image artifacts are not fully represented in build evidence.")
    return workspace, stage_digest, fingerprint


def _validate_runtime_chain(
    build: dict[str, object],
    fingerprint: str,
    expected_packages: list[str],
    runtime: dict[str, object],
    smoke: dict[str, object],
    bundle: dict[str, object],
) -> None:
    if runtime.get("schema_version") != 3 or runtime.get("runtime_evidence_complete") is not True:
        raise AospRunEvidenceError("Cuttlefish runtime evidence is incomplete.")
    _require_no_write(runtime)
    if runtime.get("status_promotion_performed") is not False:
        raise AospRunEvidenceError("Runtime evidence must not promote project status.")
    if (
        runtime.get("expected_product") != EXPECTED_PRODUCT
        or runtime.get("build_fingerprint") != fingerprint
        or runtime.get("android_release") != EXPECTED_ANDROID_RELEASE
        or runtime.get("api_level") != EXPECTED_API_LEVEL
        or runtime.get("build_type") != EXPECTED_BUILD_TYPE
        or runtime.get("boot_completed") is not True
        or runtime.get("identity_matches") is not True
    ):
        raise AospRunEvidenceError("Runtime identity does not match the exact built SwirPhoneOS product.")
    expected_fingerprint_digest = hashlib.sha256(fingerprint.encode("ascii")).hexdigest()
    if runtime.get("build_fingerprint_sha256") != expected_fingerprint_digest:
        raise AospRunEvidenceError("Runtime fingerprint digest is inconsistent with the build fingerprint.")
    required_packages = _unique_strings(runtime.get("required_source_ready_packages"), "required_source_ready_packages")
    if sorted(required_packages) != expected_packages:
        raise AospRunEvidenceError("Runtime source-ready package set does not match the checked-in system-app manifest.")
    if runtime.get("missing_required_packages") != [] or runtime.get("missing_launchable_packages") != []:
        raise AospRunEvidenceError("Runtime evidence still reports missing source-ready packages or launchers.")
    if sorted(runtime.get("present_required_packages", [])) != expected_packages:
        raise AospRunEvidenceError("Runtime package presence does not cover the full source-ready set.")
    if sorted(runtime.get("present_launchable_packages", [])) != expected_packages:
        raise AospRunEvidenceError("Runtime launcher presence does not cover the full source-ready set.")

    if smoke.get("schema_version") != 1 or smoke.get("app_smoke_complete") is not True:
        raise AospRunEvidenceError("Cuttlefish application smoke evidence is incomplete.")
    if smoke.get("persistent_device_write_allowed") is not False:
        raise AospRunEvidenceError("Application smoke evidence violates the persistent no-write boundary.")
    if smoke.get("status_promotion_performed") is not False or smoke.get("physical_device_support_claimed") is not False:
        raise AospRunEvidenceError("Application smoke evidence overclaims status or physical support.")
    if (
        smoke.get("expected_product") != EXPECTED_PRODUCT
        or smoke.get("build_fingerprint") != fingerprint
        or smoke.get("build_fingerprint_sha256") != expected_fingerprint_digest
    ):
        raise AospRunEvidenceError("Application smoke evidence belongs to a different build.")
    tested_packages = _unique_strings(smoke.get("tested_packages"), "tested_packages")
    if sorted(tested_packages) != expected_packages:
        raise AospRunEvidenceError("Application smoke did not exercise the checked-in source-ready package set.")
    launch_results = smoke.get("launch_results")
    if not isinstance(launch_results, list) or len(launch_results) != len(expected_packages):
        raise AospRunEvidenceError("Application smoke launch-result count is invalid.")
    launched: set[str] = set()
    for item in launch_results:
        if not isinstance(item, dict):
            raise AospRunEvidenceError("Application smoke launch result is invalid.")
        package = item.get("package")
        component = item.get("component")
        if package not in expected_packages or package in launched:
            raise AospRunEvidenceError("Application smoke launch package is invalid or duplicated.")
        if not isinstance(component, str) or not component.startswith(str(package) + "/"):
            raise AospRunEvidenceError("Application smoke launcher escaped the expected package.")
        if item.get("am_start_status") != "ok" or item.get("foreground_confirmed") is not True:
            raise AospRunEvidenceError("Application smoke did not confirm a successful foreground launch.")
        launched.add(str(package))

    if bundle.get("schema_version") != 1 or bundle.get("evidence_bundle_complete") is not True:
        raise AospRunEvidenceError("Build/runtime evidence bundle is incomplete.")
    _require_no_write(bundle)
    if bundle.get("expected_product") != EXPECTED_PRODUCT:
        raise AospRunEvidenceError("Build/runtime evidence bundle targets a different product.")
    if bundle.get("runtime_status_promotion_performed") is not False or bundle.get("physical_device_support_claimed") is not False:
        raise AospRunEvidenceError("Build/runtime bundle overclaims status or physical support.")
    if bundle.get("build") != build or bundle.get("runtime") != runtime:
        raise AospRunEvidenceError("Build/runtime bundle embeds reports from a different run.")
    bundle_digest = _require_hex64(bundle.get("bundle_sha256"), "build/runtime bundle sha256")
    canonical_bundle = {
        key: value
        for key, value in bundle.items()
        if key not in {"bundle_sha256", "evidence_bundle_complete"}
    }
    expected_bundle_digest = hashlib.sha256(
        json.dumps(canonical_bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if bundle_digest != expected_bundle_digest:
        raise AospRunEvidenceError("Build/runtime evidence bundle canonical digest is invalid.")


def collect_aosp_run_evidence(
    *,
    source_commit: str,
    preflight_path: Path,
    plan_path: Path,
    manifest_path: Path,
    stage_path: Path,
    post_stage_path: Path,
    build_path: Path,
    app_manifest_path: Path,
    runtime_path: Path | None = None,
    smoke_path: Path | None = None,
    bundle_path: Path | None = None,
) -> dict[str, object]:
    """Validate one complete build run and optionally its exact runtime/smoke chain."""
    expected_packages, app_manifest_sha = _load_app_registry_identity(app_manifest_path)
    paths = {
        "builder_preflight": preflight_path,
        "aosp_plan": plan_path,
        "resolved_manifest": manifest_path,
        "stage_report": stage_path,
        "post_build_stage": post_stage_path,
        "build_evidence": build_path,
    }
    runtime_paths = {"runtime": runtime_path, "smoke": smoke_path, "bundle": bundle_path}
    supplied_runtime = [name for name, path in runtime_paths.items() if path is not None]
    if supplied_runtime and len(supplied_runtime) != len(_RUNTIME_GROUP):
        raise AospRunEvidenceError("Runtime evidence is all-or-nothing: runtime, smoke and bundle are all required.")
    if supplied_runtime:
        paths.update({name: path for name, path in runtime_paths.items() if path is not None})

    reports: dict[str, dict[str, object]] = {}
    raw_hashes: dict[str, str] = {}
    for name, path in paths.items():
        report, raw_hash = _load_report(path)
        reports[name] = report
        raw_hashes[name] = raw_hash

    workspace, stage_digest, fingerprint = _validate_build_chain(
        source_commit,
        reports["builder_preflight"],
        reports["aosp_plan"],
        reports["resolved_manifest"],
        reports["stage_report"],
        reports["post_build_stage"],
        reports["build_evidence"],
    )

    runtime_complete = False
    if supplied_runtime:
        _validate_runtime_chain(
            reports["build_evidence"],
            fingerprint,
            expected_packages,
            reports["runtime"],
            reports["smoke"],
            reports["bundle"],
        )
        runtime_complete = True

    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_run_evidence_chain",
        "source_commit": source_commit,
        "scope": "BUILD_AND_RUNTIME" if runtime_complete else "BUILD_ONLY",
        "expected_product": EXPECTED_PRODUCT,
        "workspace_sha256": hashlib.sha256(workspace.encode("utf-8")).hexdigest(),
        "staged_content_sha256": stage_digest,
        "build_fingerprint": fingerprint,
        "build_fingerprint_sha256": hashlib.sha256(fingerprint.encode("ascii")).hexdigest(),
        "app_manifest_sha256": app_manifest_sha,
        "source_ready_packages": expected_packages,
        "report_file_sha256": {name: raw_hashes[name] for name in sorted(raw_hashes)},
        "build_chain_complete": True,
        "runtime_chain_complete": runtime_complete,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "warnings": [
            "This report binds evidence files from one host-side AOSP run; it is not physical-device compatibility evidence.",
            "BUILD_ONLY does not prove Cuttlefish boot. BUILD_AND_RUNTIME still requires interactive UI/accessibility/locale review before Android runtime promotion.",
            "No phone write, flash, root, unlock, release publication or registry status promotion is performed.",
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    payload["run_evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    payload["run_evidence_complete"] = True
    return payload
