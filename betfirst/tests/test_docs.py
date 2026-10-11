"""Validate the GitHub README images and bilingual documentation without extra dependencies."""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
EXPECTED_SVGS = ("hero.svg", "decision-flow.svg", "before-after.svg")
SVG_NS = "{http://www.w3.org/2000/svg}"


class ReadmeAndAssetTests(unittest.TestCase):
    def test_svg_assets_are_standalone_valid_xml(self):
        for name in EXPECTED_SVGS:
            with self.subTest(asset=name):
                asset = ASSETS / name
                self.assertTrue(asset.is_file())
                tree = ET.parse(asset)
                svg = tree.getroot()
                self.assertEqual(svg.tag, SVG_NS + "svg")
                self.assertTrue(svg.attrib.get("viewBox"))
                self.assertTrue(svg.find(SVG_NS + "title") is not None)
                self.assertTrue(svg.find(SVG_NS + "desc") is not None)
                source = asset.read_text(encoding="utf-8")
                self.assertNotIn("<foreignObject", source)
                self.assertNotIn("http://www.w3.org", source.replace('xmlns="http://www.w3.org/2000/svg"', ""))
                self.assertNotIn("data:image", source)
                self.assertNotIn("<script", source)

    def test_both_languages_link_and_embed_all_assets(self):
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-TW.md").read_text(encoding="utf-8")
        for label, content in (("English", english), ("Traditional Chinese", chinese)):
            with self.subTest(readme=label):
                self.assertIn("README.md", content)
                self.assertIn("README.zh-TW.md", content)
                for image in EXPECTED_SVGS:
                    self.assertIn("./assets/" + image, content)
                self.assertIn("Claude Code", content)
                self.assertIn("Pi", content)
                self.assertIn("evals/README.md", content)
                self.assertIn("scripts/analyze_runs.py", content)
        self.assertIn("33.8% lower wall time", english)
        self.assertIn("negative overhead on three simple tasks", english)
        self.assertIn("v3 has not run yet", english)
        self.assertIn("33.8% 耗時", chinese)
        self.assertIn("簡單任務的負面結果", chinese)
        self.assertIn("尚未進行真實 v3 推論", chinese)
        for content in (english, chinese):
            self.assertIn("experiments/EXPERIMENT_HISTORY.md", content)
            self.assertIn("experiments/V3_PROTOCOL.md", content)

    def test_local_readme_asset_references_resolve(self):
        for name in ("README.md", "README.zh-TW.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            refs = re.findall(r'src="(\./assets/[^"]+)"', text)
            self.assertEqual(len(refs), len(EXPECTED_SVGS))
            for ref in refs:
                self.assertTrue((ROOT / ref).is_file(), ref)


if __name__ == "__main__":
    unittest.main()
