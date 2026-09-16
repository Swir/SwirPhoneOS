from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos import __version__
from swirphoneos.__main__ import main
from swirphoneos.readiness import evaluate, load_ledger

ROOT = Path(__file__).resolve().parents[1]


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.ledger = load_ledger(ROOT / "project.json")

    def test_actual_ledger_is_blocked(self):
        result = evaluate(self.ledger)
        self.assertEqual(result["progress_percent"], 2)
        self.assertEqual(result["beta_gates_passed"], 0)
        self.assertEqual(result["beta_gates_total"], 9)
        self.assertFalse(result["beta_release_allowed"])

    def test_version_matches_package(self):
        self.assertEqual(self.ledger["version"], __version__)

    def test_invalid_weight_is_rejected(self):
        for value in (0, -1, True, "2", 2.0, 101):
            ledger = deepcopy(self.ledger)
            ledger["milestones"][0]["weight"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate(ledger)

    def test_incorrect_total_rejected(self):
        self.ledger["milestones"][0]["weight"] = 3
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_duplicate_milestone_rejected(self):
        self.ledger["milestones"][1]["id"] = "foundation"
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_completed_milestone_needs_evidence(self):
        self.ledger["milestones"][0]["evidence"] = []
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_missing_gate_rejected(self):
        self.ledger["beta_gates"].pop()
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_unknown_or_duplicate_gate_rejected(self):
        for name in ("fake_gate", "physical_boot"):
            ledger = deepcopy(self.ledger)
            ledger["beta_gates"][0]["id"] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                evaluate(ledger)

    def test_truthy_strings_rejected(self):
        self.ledger["beta_gates"][0]["passed"] = "false"
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_passed_gate_needs_evidence(self):
        self.ledger["beta_gates"][0]["passed"] = True
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_passed_gate_needs_exact_commit(self):
        self.ledger["beta_gates"][0].update(passed=True, evidence=["docs/test.md"])
        with self.assertRaises(ValueError):
            evaluate(self.ledger)

    def test_filled_ledger_cannot_authorize_release(self):
        self.ledger["candidate_commit"] = "a" * 40
        for gate in self.ledger["beta_gates"]:
            gate.update(passed=True, evidence=["example-unverified-reference"])
        result = evaluate(self.ledger)
        self.assertTrue(result["ledger_gates_complete"])
        self.assertFalse(result["beta_release_allowed"])

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaises(ValueError):
                load_ledger(path)

    def test_cli_gate_returns_blocked_code(self):
        with redirect_stdout(StringIO()) as output:
            code = main(["gate", "--ledger", str(ROOT / "project.json")])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(output.getvalue())["beta_release_allowed"])

    def test_cli_status_succeeds(self):
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["status", "--ledger", str(ROOT / "project.json")]), 0)

    def test_cli_missing_ledger_has_private_error(self):
        with redirect_stderr(StringIO()) as output:
            code = main(["status", "--ledger", "PRIVATE_MISSING_PATH.json"])
        self.assertEqual(code, 1)
        self.assertNotIn("PRIVATE_MISSING_PATH", output.getvalue())

    def test_reference_device_does_not_allow_flashing(self):
        path = ROOT / "device_packs/oneplus/avicii/profile.json"
        profile = json.loads(path.read_text())
        self.assertFalse(profile["flash_enabled"])
        self.assertEqual(profile["flash_operations"], [])
        self.assertEqual(profile["validated_builds"], [])


if __name__ == "__main__":
    unittest.main()
