"""Fail-closed, read-only recheck of exact AOSP build artifacts after a run."""
from __future__ import annotations

import argparse, hashlib, json, re, sys
from pathlib import Path, PurePosixPath
from typing import Any

PRODUCT = "swirphoneos_cf_x86_64"
OUT = Path("out/target/product") / PRODUCT
MAX_JSON = 16 * 1024 * 1024
MAX_FILE = 64 * 1024**3
H40 = re.compile(r"[0-9a-f]{40}\Z")
H64 = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED = {"boot.img", "system.img"}
ALLOWED = REQUIRED | {
    "init_boot.img", "vendor_boot.img", "vendor.img", "product.img", "system_ext.img",
    "vbmeta.img", "vbmeta_system.img", "super.img", "android-info.txt", "module-info.json",
}


class AospArtifactContinuityError(ValueError):
    pass


def _sha(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(data).hexdigest()


_canonical_sha = _sha


def _strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise AospArtifactContinuityError("duplicate JSON key")
        out[key] = value
    return out


def _load(path: Path) -> tuple[dict[str, object], str]:
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise AospArtifactContinuityError("unsafe evidence path")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_JSON:
        raise AospArtifactContinuityError("invalid evidence size")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_strict)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AospArtifactContinuityError("invalid evidence JSON") from exc
    if not isinstance(value, dict):
        raise AospArtifactContinuityError("invalid evidence root")
    return value, hashlib.sha256(raw).hexdigest()


def _hex(value: object) -> str:
    if not isinstance(value, str) or H64.fullmatch(value) is None:
        raise AospArtifactContinuityError("invalid SHA-256")
    return value


def _run(report: dict[str, object]) -> tuple[str, str, str, str, str, str]:
    scope = report.get("scope")
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_run_evidence_chain"
        or report.get("expected_product") != PRODUCT
        or scope not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}
        or report.get("build_chain_complete") is not True
        or report.get("run_evidence_complete") is not True
        or (scope == "BUILD_AND_RUNTIME") != (report.get("runtime_chain_complete") is True)
    ):
        raise AospArtifactContinuityError("invalid AOSP run evidence")
    if any(report.get(k) is not False for k in (
        "device_write_allowed", "physical_device_support_claimed", "status_promotion_performed"
    )):
        raise AospArtifactContinuityError("AOSP run exceeds read-only boundary")
    commit = report.get("source_commit")
    fingerprint = report.get("build_fingerprint")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospArtifactContinuityError("invalid source commit")
    if not isinstance(fingerprint, str) or not fingerprint or len(fingerprint) > 1024:
        raise AospArtifactContinuityError("invalid build fingerprint")
    try:
        fingerprint_sha = hashlib.sha256(fingerprint.encode("ascii", "strict")).hexdigest()
    except UnicodeError as exc:
        raise AospArtifactContinuityError("non-ASCII build fingerprint") from exc
    if report.get("build_fingerprint_sha256") != fingerprint_sha:
        raise AospArtifactContinuityError("build fingerprint digest mismatch")
    hashes = report.get("report_file_sha256")
    if not isinstance(hashes, dict):
        raise AospArtifactContinuityError("missing report hash map")
    run_sha = _hex(report.get("run_evidence_sha256"))
    canonical = {k: v for k, v in report.items() if k not in {"run_evidence_sha256", "run_evidence_complete"}}
    if _sha(canonical) != run_sha:
        raise AospArtifactContinuityError("run evidence digest mismatch")
    return run_sha, _hex(report.get("workspace_sha256")), str(scope), commit, fingerprint, _hex(hashes.get("build_evidence"))


def _name(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 128:
        raise AospArtifactContinuityError("invalid artifact path")
    p = PurePosixPath(value)
    if p.is_absolute() or len(p.parts) != 1 or p.name != value or value not in ALLOWED:
        raise AospArtifactContinuityError("unreviewed artifact path")
    return value


def _records(report: dict[str, object], fingerprint: str) -> list[dict[str, object]]:
    identity = report.get("build")
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_build_output"
        or report.get("expected_product") != PRODUCT
        or report.get("build_evidence_complete") is not True
        or report.get("device_write_allowed") is not False
        or report.get("status_promotion_performed") is not False
        or not isinstance(identity, dict)
        or identity.get("fingerprint") != fingerprint
    ):
        raise AospArtifactContinuityError("invalid build evidence")
    req = report.get("required_artifacts")
    items = report.get("artifacts")
    if not isinstance(req, list) or len(req) != 2 or set(req) != REQUIRED or not isinstance(items, list) or not items:
        raise AospArtifactContinuityError("invalid build artifact inventory")
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise AospArtifactContinuityError("malformed artifact record")
        name, size, digest = _name(item.get("path")), item.get("size"), _hex(item.get("sha256"))
        if name in seen or not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_FILE:
            raise AospArtifactContinuityError("invalid artifact record")
        seen.add(name)
        out.append({"path": name, "size": size, "sha256": digest})
    if not REQUIRED.issubset(seen):
        raise AospArtifactContinuityError("missing core image")
    return out


def _root(workspace: Path, expected_sha: str) -> Path:
    if not workspace.is_absolute():
        raise AospArtifactContinuityError("workspace must be absolute")
    root = workspace.resolve(strict=True)
    if root == Path(root.anchor) or not root.is_dir() or (root / ".repo").is_symlink() or not (root / ".repo").is_dir():
        raise AospArtifactContinuityError("unsafe AOSP workspace")
    if not (root / "build/envsetup.sh").is_file() or hashlib.sha256(str(root).encode()).hexdigest() != expected_sha:
        raise AospArtifactContinuityError("AOSP workspace identity mismatch")
    return root


def _rehash(path: Path, size: int, digest: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise AospArtifactContinuityError("unsafe artifact file")
    before = path.stat()
    if before.st_size != size:
        raise AospArtifactContinuityError("artifact size changed")
    h, read = hashlib.sha256(), 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            read += len(chunk)
            if read > size:
                raise AospArtifactContinuityError("artifact changed while reading")
            h.update(chunk)
    after = path.stat()
    if (
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or read != size
        or h.hexdigest() != digest
    ):
        raise AospArtifactContinuityError("artifact bytes changed")
    return {"path": path.name, "size": size, "sha256": digest}


def collect_artifact_continuity(
    workspace: Path, run_path: Path, build_path: Path, *, expected_source_commit: str | None = None
) -> dict[str, object]:
    run, run_file_sha = _load(run_path)
    build, build_file_sha = _load(build_path)
    run_sha, workspace_sha, scope, commit, fingerprint, bound_build_sha = _run(run)
    if expected_source_commit is not None and (H40.fullmatch(expected_source_commit) is None or expected_source_commit != commit):
        raise AospArtifactContinuityError("triggering source commit mismatch")
    if build_file_sha != bound_build_sha:
        raise AospArtifactContinuityError("build evidence file mismatch")
    root = _root(workspace, workspace_sha)
    product = root / OUT
    if product.is_symlink() or not product.is_dir():
        raise AospArtifactContinuityError("unsafe product output")
    product = product.resolve(strict=True)
    product.relative_to(root)
    checked: list[dict[str, object]] = []
    for item in sorted(_records(build, fingerprint), key=lambda x: str(x["path"])):
        candidate = product / str(item["path"])
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(product)
        except (OSError, RuntimeError, ValueError) as exc:
            raise AospArtifactContinuityError("artifact escapes product output") from exc
        if resolved != candidate:
            raise AospArtifactContinuityError("artifact symlink alias")
        checked.append(_rehash(candidate, int(item["size"]), str(item["sha256"])))
    payload: dict[str, object] = {
        "schema_version": 1,
        "source": "local_aosp_artifact_continuity_evidence",
        "operation": "READ_ONLY_POST_RUN_ARTIFACT_RECHECK",
        "source_commit": commit,
        "aosp_run_scope": scope,
        "expected_product": PRODUCT,
        "run_evidence_sha256": run_sha,
        "workspace_identity_sha256": workspace_sha,
        "build_fingerprint": fingerprint,
        "build_evidence_file_sha256": build_file_sha,
        "report_file_sha256": {"aosp_run_evidence": run_file_sha, "build_evidence": build_file_sha},
        "required_artifacts": sorted(REQUIRED),
        "artifacts": checked,
        "artifact_count": len(checked),
        "artifact_set_sha256": _sha(checked),
        "artifact_bytes_unchanged_after_run": True,
        "core_images_unchanged_after_run": True,
        "artifact_continuity_complete": True,
        "device_write_allowed": False,
        "physical_device_support_claimed": False,
        "status_promotion_performed": False,
        "release_artifact_authorized": False,
        "warnings": [
            "Proves retained build-artifact byte continuity only.",
            "Does not prove physical-device compatibility or install/rollback safety.",
            "Does not authorize flashing, root, release publication or roadmap promotion.",
        ],
    }
    payload["artifact_continuity_sha256"] = _sha(payload)
    return payload


def validate_artifact_continuity(report: dict[str, object]) -> str:
    if (
        report.get("schema_version") != 1
        or report.get("source") != "local_aosp_artifact_continuity_evidence"
        or report.get("operation") != "READ_ONLY_POST_RUN_ARTIFACT_RECHECK"
        or report.get("expected_product") != PRODUCT
        or any(report.get(k) is not True for k in (
            "artifact_bytes_unchanged_after_run", "core_images_unchanged_after_run", "artifact_continuity_complete"
        ))
        or any(report.get(k) is not False for k in (
            "device_write_allowed", "physical_device_support_claimed", "status_promotion_performed", "release_artifact_authorized"
        ))
    ):
        raise AospArtifactContinuityError("invalid artifact continuity evidence")
    if report.get("aosp_run_scope") not in {"BUILD_ONLY", "BUILD_AND_RUNTIME"}:
        raise AospArtifactContinuityError("invalid continuity scope")
    commit = report.get("source_commit")
    if not isinstance(commit, str) or H40.fullmatch(commit) is None:
        raise AospArtifactContinuityError("invalid continuity commit")
    for key in ("run_evidence_sha256", "workspace_identity_sha256", "build_evidence_file_sha256", "artifact_set_sha256"):
        _hex(report.get(key))
    items = report.get("artifacts")
    if not isinstance(items, list) or report.get("artifact_count") != len(items):
        raise AospArtifactContinuityError("invalid continuity inventory")
    normalized = sorted(_records({
        "schema_version": 1, "source": "local_aosp_build_output", "expected_product": PRODUCT,
        "build_evidence_complete": True, "device_write_allowed": False, "status_promotion_performed": False,
        "build": {"fingerprint": report.get("build_fingerprint")}, "required_artifacts": report.get("required_artifacts"),
        "artifacts": items,
    }, str(report.get("build_fingerprint", ""))), key=lambda x: str(x["path"]))
    if items != normalized or _sha(normalized) != report.get("artifact_set_sha256"):
        raise AospArtifactContinuityError("continuity inventory digest mismatch")
    hashes = report.get("report_file_sha256")
    if not isinstance(hashes, dict) or set(hashes) != {"aosp_run_evidence", "build_evidence"}:
        raise AospArtifactContinuityError("invalid continuity report hashes")
    _hex(hashes.get("aosp_run_evidence"))
    if hashes.get("build_evidence") != report.get("build_evidence_file_sha256"):
        raise AospArtifactContinuityError("inconsistent build-evidence digest")
    digest = _hex(report.get("artifact_continuity_sha256"))
    if _sha({k: v for k, v in report.items() if k != "artifact_continuity_sha256"}) != digest:
        raise AospArtifactContinuityError("continuity canonical digest mismatch")
    return digest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Re-verify exact SwirPhoneOS AOSP artifacts after a completed run")
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--run-evidence", required=True, type=Path)
    p.add_argument("--build-evidence", required=True, type=Path)
    p.add_argument("--source-commit", required=True)
    a = p.parse_args(argv)
    try:
        report = collect_artifact_continuity(
            a.workspace.resolve(), a.run_evidence.resolve(), a.build_evidence.resolve(), expected_source_commit=a.source_commit
        )
        validate_artifact_continuity(report)
    except (AospArtifactContinuityError, OSError, RuntimeError, UnicodeError, ValueError):
        print("AOSP artifact continuity failed: post-run bytes do not match bound build evidence.", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
