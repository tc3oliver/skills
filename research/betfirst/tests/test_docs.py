"""Validate BetFirst distribution boundary and public documentation."""
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[3]

class BetFirstPackagingTests(unittest.TestCase):
    def test_skill_install_is_minimal(self):
        target = REPO / "betfirst"
        self.assertEqual(sorted(p.name for p in target.iterdir()), ["SKILL.md"])
        self.assertIn("name: betfirst", (target / "SKILL.md").read_text(encoding="utf-8"))

    def test_docs_media_and_evidence_live_outside_skill(self):
        for p in ("docs/betfirst/README.md", "docs/betfirst/README.zh-TW.md",
                  "research/betfirst/experiments/V04_RELEASE_RESULTS.md",
                  "media/betfirst/assets/betfirst-v04-animated.svg"):
            self.assertTrue((REPO / p).is_file(), p)

    def test_readme_image_references(self):
        for name in ("README.md", "README.zh-TW.md"):
            root = REPO / "docs/betfirst"
            content = (root / name).read_text(encoding="utf-8")
            for image in ("betfirst-promo.gif", "before-after.svg"):
                link = "../../media/betfirst/assets/" + image
                self.assertIn(link, content)
                self.assertTrue((root / link).is_file())

if __name__ == "__main__":
    unittest.main()
