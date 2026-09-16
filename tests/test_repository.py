"""Progress consistency checks; never count these as physical-device validation."""
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_weighted_roadmap_is_synchronized(self):
        data = json.loads((ROOT / "progress.json").read_text(encoding="utf-8"))
        milestones = data["milestones"]
        self.assertEqual(len({m["id"] for m in milestones}), len(milestones))
        for item in milestones:
            self.assertIs(type(item["weight"]), int)
            self.assertGreater(item["weight"], 0)
            self.assertIs(type(item["complete"]), bool)
        total = sum(m["weight"] for m in milestones)
        done = sum(m["weight"] for m in milestones if m["complete"])
        self.assertEqual(total, data["total_weight"])
        self.assertEqual(total, 100)
        cells = int(done * 20 / total)
        summary = f"**{done} / {total} weighted milestone points = {done}%**"
        bar = f"`[{'#' * cells}{'.' * (20 - cells)}] {done}%`"
        for name in ("README.md", "ROADMAP.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(summary, text)
            self.assertIn(bar, text)
        roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
        for item in milestones:
            state = "x" if item["complete"] else " "
            self.assertIn(f"| {item['id']} | [{state}] | {item['weight']} |", roadmap)

    def test_branding_is_valid_svg(self):
        tree = ET.parse(ROOT / "branding/swirphoneos.svg")
        self.assertEqual(tree.getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_actions_are_pinned(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for action in re.findall(r"uses:\s*(\S+)", workflow):
            self.assertRegex(action, r"^[\w/-]+@[0-9a-f]{40}$")
        self.assertIn("contents: read", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
