"""Fail-closed SwirRoot policy checks."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.swirroot import SwirRootPolicyError, load_policy, public_policy_summary, validate_policy

POLICY = Path("swirroot/policy.json")
FULL_TRANSITION_GATES = {
    "exact_build_match",
    "verified_device_profile",
    "owner_confirmation",
    "rollback_material_verified",
    "journal_available",
    "update_state_safe",
    "expected_nonroot_state_known",
}


class SwirRootPolicyTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_repository_policy_fails_closed(self):
        summary = public_policy_summary(load_policy(POLICY))
        self.assertEqual(summary["default_state"], "UNAVAILABLE")
        self.assertEqual(summary["authorization_default"], "deny")
        self.assertFalse(summary["write_operations_enabled"])
        self.assertFalse(summary["root_available"])
        self.assertEqual(summary["supported_build_count"], 0)

    def test_enable_and_unroot_require_full_recovery_safe_gate_set(self):
        summary = public_policy_summary(load_policy(POLICY))
        self.assertEqual(set(summary["enable_requirements"]), FULL_TRANSITION_GATES)
        self.assertEqual(set(summary["unroot_requirements"]), FULL_TRANSITION_GATES)

    def test_root_writes_without_exact_supported_build_are_rejected(self):
        bad = deepcopy(self.data)
        bad["write_operations_enabled"] = True
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_supported_build_claim_without_enabled_implementation_is_rejected(self):
        bad = deepcopy(self.data)
        bad["supported_builds"] = ["example-build"]
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_authorization_must_be_deny_by_default(self):
        bad = deepcopy(self.data)
        bad["authorization"]["default"] = "allow"
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_required_rollback_gate_cannot_be_removed(self):
        bad = deepcopy(self.data)
        bad["enable_requirements"].remove("rollback_material_verified")
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_expected_nonroot_gate_cannot_be_removed_from_enable(self):
        bad = deepcopy(self.data)
        bad["enable_requirements"].remove("expected_nonroot_state_known")
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_verified_profile_and_update_gate_cannot_be_removed_from_unroot(self):
        for gate in ("verified_device_profile", "update_state_safe"):
            with self.subTest(gate=gate):
                bad = deepcopy(self.data)
                bad["unroot_requirements"].remove(gate)
                with self.assertRaises(SwirRootPolicyError):
                    validate_policy(bad)

    def test_forbidden_exploit_policy_cannot_be_removed(self):
        bad = deepcopy(self.data)
        bad["forbidden_methods"].remove("bootloader_exploit")
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_default_state_cannot_pretend_root_is_off_on_unverified_build(self):
        bad = deepcopy(self.data)
        bad["default_state"] = "ROOT_OFF"
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)

    def test_policy_loader_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "policy.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(SwirRootPolicyError):
                load_policy(path)

    def test_policy_loader_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "policy-real.json"
            target.write_text(POLICY.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "policy-link.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are unavailable in this environment")
            with self.assertRaises(SwirRootPolicyError):
                load_policy(link)

    def test_supported_build_ids_reject_control_characters(self):
        bad = deepcopy(self.data)
        bad["write_operations_enabled"] = True
        bad["supported_builds"] = ["supported\nbuild"]
        with self.assertRaises(SwirRootPolicyError):
            validate_policy(bad)


if __name__ == "__main__":
    unittest.main()
