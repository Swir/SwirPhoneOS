from pathlib import Path
import tempfile
import unittest

from swirphoneos.progress_presentation import (
    LEGACY_BRACKET_METER,
    LEGACY_GLYPH_METER,
    presentation_violations,
)

ROOT = Path(__file__).resolve().parents[1]


class ProgressPresentationTests(unittest.TestCase):
    def test_current_maintained_docs_are_svg_only_and_nonduplicated(self):
        self.assertEqual(presentation_violations(ROOT), ())

    def test_legacy_meters_are_rejected_even_without_percent_suffix(self):
        for sample in (
            "[#####-----]",
            "[=====-----] 50%",
            "████░░░░",
            "▓▓▓ 75%",
            "■■■□□□",
        ):
            self.assertTrue(
                LEGACY_BRACKET_METER.search(sample) or LEGACY_GLYPH_METER.search(sample),
                sample,
            )

    def test_structural_markdown_is_not_misclassified_as_progress(self):
        for sample in (
            "- [ ] open gate",
            "- [x] completed checklist item",
            "| --- | --- |",
            "tree ├── assets └── tests",
            "`python -m swirphoneos.progress_svg --check`",
        ):
            self.assertIsNone(LEGACY_BRACKET_METER.search(sample), sample)
            self.assertIsNone(LEGACY_GLYPH_METER.search(sample), sample)

    def test_wrong_asset_placement_and_template_embedding_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                '<img src="assets/readme/progress-mini.svg" />\n'
                '<img src="assets/readme/progress-template.svg" />\n',
                encoding="utf-8",
            )
            (root / "ROADMAP.md").write_text(
                '<img src="assets/readme/progress-card.svg" />\n',
                encoding="utf-8",
            )
            (root / "BUILD_STATUS.md").write_text(
                '<img src="assets/readme/progress-card.svg" />\n',
                encoding="utf-8",
            )
            violations = presentation_violations(root)
            reasons = {(item.path, item.reason) for item in violations}
            self.assertIn(
                ("README.md", "progress template must never be embedded as live project data"),
                reasons,
            )
            self.assertIn(
                ("README.md", "README must embed progress-card.svg exactly once"),
                reasons,
            )
            self.assertIn(
                ("README.md", "README must not duplicate the roadmap mini graphic"),
                reasons,
            )
            self.assertIn(
                ("ROADMAP.md", "ROADMAP must embed progress-mini.svg exactly once"),
                reasons,
            )
            self.assertIn(
                ("ROADMAP.md", "ROADMAP must not duplicate the README card graphic"),
                reasons,
            )
            self.assertIn(
                ("BUILD_STATUS.md", "BUILD_STATUS must not duplicate the authoritative README/ROADMAP graphics"),
                reasons,
            )

    def test_missing_or_symlinked_maintained_surface_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                '<img src="assets/readme/progress-card.svg" />',
                encoding="utf-8",
            )
            (root / "ROADMAP.md").write_text(
                '<img src="assets/readme/progress-mini.svg" />',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                presentation_violations(root)


if __name__ == "__main__":
    unittest.main()
