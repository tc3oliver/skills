"""Static guardrails for the v0.3 candidate (not evidence of agent behavior)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BetFirstPolicyTests(unittest.TestCase):
    def test_preserves_mandatory_correctness_and_no_change(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "full PoC", "ABSTAIN", "make no file changes",
            "single high-risk boundary", "original test files",
            "does not prove the full solution correct",
            "do not edit original tests as a workaround",
            "Do not run a probe merely",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

    def test_routes_trace_driven_cases(self):
        data = json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
        cases = {c["id"]: c for c in data["cases"]}
        self.assertEqual(len(cases), len(data["cases"]))
        for task, expected in (
            ("micro-poc-before-full-poc", "BET"),
            ("no-change-includes-tests", "ABSTAIN"),
            ("win-still-checks-invariants", "BET_THEN_VERIFY"),
            ("replay-payload-mismatch", "BET_THEN_VERIFY"),
            ("additive-tests-file-tool-unavailable", "NORMAL_OR_TEMP_PROBE"),
            ("obvious-cheap-fix-no-ceremonial-bet", "NORMAL"),
            ("unsupported-timeout-command", "BET_IF_NATURALLY_BOUNDED"),
        ):
            with self.subTest(task=task):
                self.assertEqual(cases[task]["expected"], expected)

if __name__ == "__main__":
    unittest.main()
