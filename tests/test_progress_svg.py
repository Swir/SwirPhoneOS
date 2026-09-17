from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from swirphoneos.progress_svg import (
    CARD_TRACK_WIDTH,
    MINI_TRACK_WIDTH,
    expected_assets,
    render_card,
    render_mini,
    render_template,
    snapshot_from_ledger,
    sync_assets,
)

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


class ProgressSvgTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = snapshot_from_ledger(ROOT / "project.json")

    def test_actual_snapshot_preserves_weighted_ledger_math(self):
        self.assertEqual(self.snapshot.weighted_percent, 2.0)
        self.assertEqual((self.snapshot.completed_milestones, self.snapshot.total_milestones), (1, 10))
        self.assertEqual((self.snapshot.beta_gates_passed, self.snapshot.beta_gates_total), (0, 9))
        self.assertFalse(self.snapshot.beta_release_allowed)

    def test_card_geometry_uses_unrounded_weighted_fraction(self):
        root = parse(render_card(self.snapshot))
        fill = root.find(".//svg:rect[@id='progress-fill']", SVG_NS)
        self.assertIsNotNone(fill)
        self.assertAlmostEqual(float(fill.attrib["width"]), CARD_TRACK_WIDTH * 0.02)
        self.assertEqual(root.attrib["viewBox"], "0 0 1200 180")

    def test_mini_geometry_uses_same_source_fraction(self):
        root = parse(render_mini(self.snapshot))
        fill = root.find(".//svg:rect[@id='progress-fill']", SVG_NS)
        self.assertIsNotNone(fill)
        self.assertAlmostEqual(float(fill.attrib["width"]), MINI_TRACK_WIDTH * 0.02)
        self.assertIn("Beta 0/9", "".join(root.itertext()))

    def test_zero_progress_omits_fill_and_glow_usage(self):
        zero = replace(self.snapshot, weighted_percent=0.0, completed_milestones=0)
        svg = render_card(zero)
        root = parse(svg)
        self.assertIsNone(root.find(".//svg:rect[@id='progress-fill']", SVG_NS))
        self.assertNotIn('filter="url(#swir-glow)" clip-path="url(#card-track-clip)"', svg)

    def test_complete_scope_fill_is_bounded_but_beta_remains_separate(self):
        complete = replace(self.snapshot, weighted_percent=100.0, completed_milestones=self.snapshot.total_milestones)
        root = parse(render_card(complete))
        fill = root.find(".//svg:rect[@id='progress-fill']", SVG_NS)
        self.assertEqual(float(fill.attrib["width"]), CARD_TRACK_WIDTH)
        text = "".join(root.itertext())
        self.assertIn("COMPLETE", text)
        self.assertIn("NOT BETA READY", text)

    def test_unknown_scope_is_na_not_zero_or_complete(self):
        for renderer in (render_card, render_mini):
            text = "".join(parse(renderer(None)).itertext())
            self.assertIn("N/A", text)
            self.assertNotIn("0%", text)
            self.assertNotIn("100%", text)

    def test_long_scope_expands_card_height(self):
        long_snapshot = replace(
            self.snapshot,
            scope_label="Verified weighted engineering progress for a deliberately long named scope that must not collide with the status line",
        )
        root = parse(render_card(long_snapshot))
        self.assertEqual(root.attrib["viewBox"], "0 0 1200 212")
        fill = root.find(".//svg:rect[@id='progress-fill']", SVG_NS)
        self.assertLessEqual(float(fill.attrib["width"]), CARD_TRACK_WIDTH)

    def test_template_is_valid_and_never_contains_live_project_values(self):
        root = parse(render_template())
        text = "".join(root.itertext())
        self.assertIn("TEMPLATE / NOT PROJECT DATA", text)
        self.assertIn("N/A", text)
        self.assertIsNone(root.find(".//svg:rect[@id='progress-fill']", SVG_NS))

    def test_committed_assets_are_deterministic_and_current(self):
        self.assertEqual(sync_assets(ROOT, check=True), [])
        for path, expected in expected_assets(ROOT).items():
            self.assertEqual(path.read_text(encoding="utf-8"), expected)
            ET.fromstring(expected)

    def test_stale_asset_check_fails_without_rewriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project.json").write_bytes((ROOT / "project.json").read_bytes())
            assets = root / "assets/readme"
            assets.mkdir(parents=True)
            stale_card = assets / "progress-card.svg"
            stale_card.write_text("stale", encoding="utf-8")
            stale = sync_assets(root, check=True)
            self.assertIn(stale_card, stale)
            self.assertEqual(stale_card.read_text(encoding="utf-8"), "stale")

    def test_readme_and_roadmap_embed_generated_assets_with_text_fallback(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn('src="assets/readme/progress-card.svg"', readme)
        self.assertIn('src="assets/readme/progress-mini.svg"', roadmap)
        self.assertIn("2% — 1/10 weighted engineering milestones", readme)
        self.assertIn("Beta readiness: 0/9 gates passed", readme)
        self.assertIn("2% — weighted engineering milestones", roadmap)
        self.assertIn("Beta readiness remains **0/9 gates passed**", roadmap)

    def test_readme_pro_v2_and_search_keywords_are_preserved(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("<!-- SWIR-README-STANDARD:v2 -->", readme)
        self.assertIn("## 🔎 Search Keywords", readme)


if __name__ == "__main__":
    unittest.main()
