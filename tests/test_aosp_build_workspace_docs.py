import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "system_apps" / "manifest.json"
BUILD_DOC = ROOT / "docs" / "AOSP_BUILD_WORKSPACE.md"


class AospBuildWorkspaceDocsTest(unittest.TestCase):
    def test_documented_android_source_count_matches_registry(self) -> None:
        manifest = json.loads(REGISTRY.read_text(encoding="utf-8"))
        source_ready = [
            app for app in manifest.get("apps", []) if app.get("status") == "ANDROID_SOURCE"
        ]
        expected_count = len(source_ready)
        self.assertGreater(expected_count, 0)

        text = BUILD_DOC.read_text(encoding="utf-8")
        staged_match = re.search(
            r"required by the (\d+) applications marked `ANDROID_SOURCE`",
            text,
        )
        validator_match = re.search(
            r"validator currently covers all (\d+) source-ready applications",
            text,
        )

        self.assertIsNotNone(staged_match)
        self.assertIsNotNone(validator_match)
        self.assertEqual(int(staged_match.group(1)), expected_count)
        self.assertEqual(int(validator_match.group(1)), expected_count)


if __name__ == "__main__":
    unittest.main()
