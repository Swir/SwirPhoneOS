import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from swirphoneos.aosp_runner_setup import (
    ENV_KEY,
    REQUIRED_RUNNER_LABELS,
    RunnerSetupError,
    apply_local_runner_setup,
    plan_local_runner_setup,
)
from swirphoneos.__main__ import main


class AospRunnerLocalSetupTest(unittest.TestCase):
    def _runner(self, root: Path) -> Path:
        runner = root / "actions-runner"
        runner.mkdir()
        for name in ("config.sh", "run.sh", ".runner"):
            (runner / name).write_text("marker\n", encoding="utf-8")
        return runner

    def test_plan_is_read_only_and_keeps_server_label_claim_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root)
            workspace = root / "aosp-workspace"

            report = plan_local_runner_setup(runner.resolve(), workspace.resolve())

            self.assertFalse(report["mutations_performed"])
            self.assertFalse(report["workspace_exists"])
            self.assertFalse(report["environment_matches"])
            self.assertFalse(report["server_side_label_verified"])
            self.assertFalse(report["build_started"])
            self.assertFalse(report["device_write_allowed"])
            self.assertEqual(report["required_labels"], list(REQUIRED_RUNNER_LABELS))
            self.assertFalse(workspace.exists())
            self.assertFalse((runner / ".env").exists())

    def test_execute_is_idempotent_and_preserves_unrelated_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root)
            workspace = root / "aosp-workspace"
            (runner / ".env").write_text("KEEP_ME=yes\nOLD=value\n", encoding="utf-8")

            first = apply_local_runner_setup(runner.resolve(), workspace.resolve())
            second = apply_local_runner_setup(runner.resolve(), workspace.resolve())

            self.assertTrue(first["mutations_performed"])
            self.assertTrue(second["environment_matches"])
            self.assertTrue(workspace.is_dir())
            lines = (runner / ".env").read_text(encoding="utf-8").splitlines()
            self.assertIn("KEEP_ME=yes", lines)
            self.assertIn("OLD=value", lines)
            swir = [line for line in lines if line.startswith(ENV_KEY + "=")]
            self.assertEqual(swir, [f"{ENV_KEY}={workspace.resolve()}"])

    def test_rejects_workspace_inside_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root).resolve()
            with self.assertRaises(RunnerSetupError):
                plan_local_runner_setup(runner, runner / "aosp")

    def test_rejects_duplicate_workspace_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root)
            (runner / ".env").write_text(
                f"{ENV_KEY}=/one\n{ENV_KEY}=/two\n", encoding="utf-8"
            )
            with self.assertRaises(RunnerSetupError):
                plan_local_runner_setup(runner.resolve(), (root / "aosp").resolve())

    def test_rejects_symlink_environment_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root)
            target = root / "real-env"
            target.write_text("", encoding="utf-8")
            try:
                (runner / ".env").symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")
            with self.assertRaises(RunnerSetupError):
                plan_local_runner_setup(runner.resolve(), (root / "aosp").resolve())

    def test_cli_plan_and_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = self._runner(root).resolve()
            workspace = (root / "aosp").resolve()
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([
                    "runner-local-setup",
                    "--runner-dir",
                    str(runner),
                    "--workspace",
                    str(workspace),
                ])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report["mutations_performed"])
            self.assertFalse(workspace.exists())

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([
                    "runner-local-setup",
                    "--runner-dir",
                    str(runner),
                    "--workspace",
                    str(workspace),
                    "--execute",
                ])
            self.assertEqual(code, 0)
            report = json.loads(output.getvalue())
            self.assertTrue(report["mutations_performed"])
            self.assertTrue(report["environment_matches"])


if __name__ == "__main__":
    unittest.main()
