from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from swirphoneos.__main__ import main


class CliContractTests(unittest.TestCase):
    def test_product_contract_root_argument_remains_wired(self) -> None:
        root = Path(__file__).resolve().parents[1] / "platform" / "aosp_product"
        output = StringIO()
        with redirect_stdout(output), redirect_stderr(StringIO()):
            code = main(["product-contract", "--root", str(root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["schema_version"], 1)

    def test_transaction_plan_evidence_and_journal_cli_are_read_only(self) -> None:
        target = b"target"
        rollback = b"rollback"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "install").mkdir()
            (root / "rollback").mkdir()
            (root / "install" / "target.img").write_bytes(target)
            (root / "rollback" / "stock.img").write_bytes(rollback)
            plan = {
                "schema_version": 1,
                "transaction_id": "cli-review-001",
                "profile_id": "oneplus/avicii",
                "device_codename": "avicii",
                "device_model": "AC2003",
                "expected_current_build": "stock/example",
                "target_build": "swir/example",
                "write_enabled": False,
                "owner_confirmation_required": True,
                "rollback_required": True,
                "install_artifacts": [{
                    "name": "target",
                    "path": "install/target.img",
                    "sha256": hashlib.sha256(target).hexdigest(),
                    "size": len(target),
                    "kind": "install",
                }],
                "rollback_artifacts": [{
                    "name": "stock",
                    "path": "rollback/stock.img",
                    "sha256": hashlib.sha256(rollback).hexdigest(),
                    "size": len(rollback),
                    "kind": "rollback",
                }],
                "notes": "CLI contract test.",
            }
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            plan_output = StringIO()
            with redirect_stdout(plan_output), redirect_stderr(StringIO()):
                self.assertEqual(main(["transaction-plan", "--file", str(plan_path)]), 0)
            plan_result = json.loads(plan_output.getvalue())
            self.assertFalse(plan_result["write_allowed"])

            evidence_output = StringIO()
            with redirect_stdout(evidence_output), redirect_stderr(StringIO()):
                self.assertEqual(main(["transaction-evidence", "--plan", str(plan_path), "--artifacts", str(root)]), 0)
            evidence_result = json.loads(evidence_output.getvalue())
            self.assertTrue(evidence_result["rollback_ready"])
            self.assertFalse(evidence_result["write_allowed"])
            self.assertFalse(evidence_result["owner_confirmation_recorded"])

            journal_path = root / "journal.json"
            create_output = StringIO()
            with redirect_stdout(create_output), redirect_stderr(StringIO()):
                self.assertEqual(main(["transaction-evidence", "--plan", str(plan_path), "--artifacts", str(root), "--journal", str(journal_path)]), 0)
            self.assertTrue(journal_path.is_file())
            self.assertFalse(json.loads(create_output.getvalue())["write_allowed"])

            journal_output = StringIO()
            with redirect_stdout(journal_output), redirect_stderr(StringIO()):
                self.assertEqual(main(["transaction-journal", "--file", str(journal_path)]), 0)
            journal_result = json.loads(journal_output.getvalue())
            self.assertEqual(journal_result["state"], "ARTIFACTS_VERIFIED_READ_ONLY")
            self.assertFalse(journal_result["write_allowed"])
            self.assertFalse(journal_result["owner_confirmation_recorded"])


if __name__ == "__main__":
    unittest.main()
