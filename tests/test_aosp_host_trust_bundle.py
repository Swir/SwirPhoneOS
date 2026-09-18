from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_host_evidence import _canonical_sha
from swirphoneos.aosp_host_trust_bundle import (
    AospHostTrustBundleError,
    create_host_trust_bundle,
)


class AospHostTrustBundleTests(unittest.TestCase):
    WORKSPACE_SHA = "a" * 64

    def _host_report(self, phase: str, *, kvm: bool = True) -> dict[str, object]:
        from swirphoneos.build_preflight import REQUIRED_COMMANDS
        tools = []
        for index, name in enumerate(REQUIRED_COMMANDS):
            tools.append({
                "name": name,
                "size": 100 + index,
                "sha256": hashlib.sha256(name.encode("utf-8")).hexdigest(),
                "path_identity_sha256": hashlib.sha256(("/usr/bin/" + name).encode("utf-8")).hexdigest(),
            })
        tools.sort(key=lambda item: item["name"])
        host = {
            "system": "linux",
            "machine": "x86_64",
            "glibc_version": "2.39",
            "kernel_release_sha256": "b" * 64,
            "os_release_sha256": "c" * 64,
        }
        host_sha = _canonical_sha(host)
        toolchain_sha = _canonical_sha(tools)
        env_sha = _canonical_sha({
            "workspace_identity_sha256": self.WORKSPACE_SHA,
            "host_identity_sha256": host_sha,
            "toolchain_sha256": toolchain_sha,
        })
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_host_environment_evidence",
            "operation": "READ_ONLY_BUILD_HOST_IDENTITY",
            "phase": phase,
            "workspace_identity_sha256": self.WORKSPACE_SHA,
            "host": host,
            "host_identity_sha256": host_sha,
            "required_commands": list(REQUIRED_COMMANDS),
            "tools": tools,
            "tool_count": len(tools),
            "toolchain_sha256": toolchain_sha,
            "environment_identity_sha256": env_sha,
            "resources": {
                "ram_bytes": 96 * 1024**3,
                "free_bytes": 500 * 1024**3 if phase == "PRE_BUILD" else 430 * 1024**3,
                "free_inodes": 100000 if phase == "PRE_BUILD" else 90000,
            },
            "kvm_available": kvm,
            "host_evidence_complete": True,
            "device_write_allowed": False,
            "build_verified": False,
            "boot_verified": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["one"],
        }
        payload["host_evidence_sha256"] = _canonical_sha(payload)
        return payload

    def _run_report(self, scope: str = "BUILD_ONLY") -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 1,
            "source": "local_aosp_run_evidence_chain",
            "source_commit": "1" * 40,
            "scope": scope,
            "expected_product": "swirphoneos_cf_x86_64",
            "workspace_sha256": self.WORKSPACE_SHA,
            "staged_content_sha256": "d" * 64,
            "build_fingerprint": "Swir/test/test:17/ID/1:userdebug/test-keys",
            "build_fingerprint_sha256": "e" * 64,
            "app_manifest_sha256": "f" * 64,
            "source_ready_packages": ["org.swir.phoneos.settings"],
            "report_file_sha256": {"resolved_manifest": "0" * 64},
            "build_chain_complete": True,
            "runtime_chain_complete": scope == "BUILD_AND_RUNTIME",
            "device_write_allowed": False,
            "physical_device_support_claimed": False,
            "status_promotion_performed": False,
            "warnings": ["one"],
        }
        payload["run_evidence_sha256"] = _canonical_sha(payload)
        payload["run_evidence_complete"] = True
        return payload

    def _write(self, root: Path, *, scope: str = "BUILD_ONLY", kvm: bool = True) -> dict[str, Path]:
        paths = {"run": root / "run.json", "pre": root / "pre.json", "post": root / "post.json"}
        paths["run"].write_text(json.dumps(self._run_report(scope), sort_keys=True), encoding="utf-8")
        paths["pre"].write_text(json.dumps(self._host_report("PRE_BUILD", kvm=kvm), sort_keys=True), encoding="utf-8")
        paths["post"].write_text(json.dumps(self._host_report("POST_BUILD", kvm=kvm), sort_keys=True), encoding="utf-8")
        return paths

    def _create(self, paths: dict[str, Path]) -> dict[str, object]:
        return create_host_trust_bundle(paths["run"].resolve(), paths["pre"].resolve(), paths["post"].resolve())

    def test_accepts_stable_host_with_resource_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self._create(self._write(Path(temporary)))
        self.assertTrue(result["toolchain_unchanged_across_build_window"])
        self.assertTrue(result["host_environment_unchanged_across_build_window"])
        self.assertTrue(result["workspace_identity_bound"])
        self.assertTrue(result["host_trust_chain_complete"])
        self.assertFalse(result["device_write_allowed"])
        self.assertEqual(len(result["host_trust_bundle_sha256"]), 64)

    def test_accepts_runtime_scope_only_with_kvm(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self._create(self._write(Path(temporary), scope="BUILD_AND_RUNTIME", kvm=True))
        self.assertTrue(result["kvm_available_across_build_window"])
        self.assertEqual(result["aosp_run_scope"], "BUILD_AND_RUNTIME")

    def test_rejects_runtime_scope_without_kvm(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary), scope="BUILD_AND_RUNTIME", kvm=False)
            with self.assertRaises(AospHostTrustBundleError):
                self._create(paths)

    def test_rejects_exact_tool_byte_change_with_recomputed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write(root)
            post = json.loads(paths["post"].read_text(encoding="utf-8"))
            post["tools"][0]["sha256"] = "9" * 64
            post["toolchain_sha256"] = _canonical_sha(sorted(post["tools"], key=lambda item: item["name"]))
            post["environment_identity_sha256"] = _canonical_sha({
                "workspace_identity_sha256": post["workspace_identity_sha256"],
                "host_identity_sha256": post["host_identity_sha256"],
                "toolchain_sha256": post["toolchain_sha256"],
            })
            post.pop("host_evidence_sha256")
            post["host_evidence_sha256"] = _canonical_sha(post)
            paths["post"].write_text(json.dumps(post, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospHostTrustBundleError):
                self._create(paths)

    def test_rejects_workspace_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write(root)
            post = json.loads(paths["post"].read_text(encoding="utf-8"))
            post["workspace_identity_sha256"] = "9" * 64
            post["environment_identity_sha256"] = _canonical_sha({
                "workspace_identity_sha256": post["workspace_identity_sha256"],
                "host_identity_sha256": post["host_identity_sha256"],
                "toolchain_sha256": post["toolchain_sha256"],
            })
            post.pop("host_evidence_sha256")
            post["host_evidence_sha256"] = _canonical_sha(post)
            paths["post"].write_text(json.dumps(post, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospHostTrustBundleError):
                self._create(paths)

    def test_rejects_forged_write_flag_even_with_recomputed_run_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = self._write(root)
            run = json.loads(paths["run"].read_text(encoding="utf-8"))
            run["device_write_allowed"] = True
            run.pop("run_evidence_sha256")
            run.pop("run_evidence_complete")
            run["run_evidence_sha256"] = _canonical_sha(run)
            run["run_evidence_complete"] = True
            paths["run"].write_text(json.dumps(run, sort_keys=True), encoding="utf-8")
            with self.assertRaises(AospHostTrustBundleError):
                self._create(paths)

    def test_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths = self._write(Path(temporary))
            paths["run"].write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(AospHostTrustBundleError):
                self._create(paths)


if __name__ == "__main__":
    unittest.main()
