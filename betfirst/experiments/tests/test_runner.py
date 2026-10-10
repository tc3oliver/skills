"""Experiment runner smoke tests; no provider calls or synthetic savings claims."""
from __future__ import annotations
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))
from run import execute, load_suite, prompt_for
from usage import usage_from_output


class UsageTests(unittest.TestCase):
    def test_claude_json_usage(self):
        actual = usage_from_output(json.dumps({
            "usage": {"input_tokens": 120, "output_tokens": 50,
                      "cache_read_input_tokens": 10, "cache_creation_input_tokens": 3},
            "total_cost_usd": 0.015,
        }), "claude")
        self.assertEqual(actual, {
            "input_tokens": 120, "output_tokens": 50, "cache_read_tokens": 10,
            "cache_write_tokens": 3, "api_cost_usd": 0.015,
        })

    def test_pi_message_end_not_double_counted(self):
        events = [
            {"type": "message_update", "usage": {"input": 100, "output": 5}},
            {"type": "message_end", "message": {"role": "assistant",
             "usage": {"input": 100, "output": 10, "cacheRead": 20,
                       "cacheWrite": 1, "cost": {"total": 0.02}}}},
            {"type": "turn_end", "message": {"role": "assistant",
             "usage": {"input": 100, "output": 10}}},
            {"type": "message_end", "message": {"role": "assistant",
             "usage": {"input": 50, "output": 6, "cacheRead": 10,
                       "cacheWrite": 0, "cost": {"total": 0.01}}}},
        ]
        actual = usage_from_output("\n".join(json.dumps(e) for e in events), "pi")
        self.assertEqual(actual["input_tokens"], 150)
        self.assertEqual(actual["output_tokens"], 16)
        self.assertEqual(actual["cache_read_tokens"], 30)
        self.assertAlmostEqual(actual["api_cost_usd"], 0.03)

    def test_missing_usage_is_unknown_not_zero(self):
        actual = usage_from_output("not json", "claude")
        self.assertTrue(all(value is None for value in actual.values()))
        pi = usage_from_output(json.dumps({
            "type": "message_end", "message": {"role": "assistant",
            "usage": {"input": 3}}
        }), "pi")
        self.assertIsNone(pi["output_tokens"])
        self.assertIsNone(pi["api_cost_usd"])


class RunnerTests(unittest.TestCase):
    def test_three_tasks_three_arms_isolated_and_scored(self):
        tasks = load_suite(EXP / "suite.json")
        self.assertEqual(len(tasks), 3)
        with tempfile.TemporaryDirectory(prefix="betfirst-runner-test-") as d:
            folder = Path(d) / "out"
            rows = execute(EXP / "suite.json", folder, "mock", None, 1, 42, 15, False)
            self.assertEqual(len(rows), 9)
            self.assertTrue(all(row["passed"] == "true" for row in rows))
            self.assertTrue(all(row["input_tokens"] is None for row in rows))
            self.assertTrue((folder / "synthetic-smoke.csv").is_file())
            self.assertFalse((folder / "measured-runs.csv").exists())
            self.assertTrue(json.loads((folder / "manifest.json").read_text())["synthetic"])
            for arm in ("baseline", "efficiency", "betfirst"):
                p = (folder / f"already-correct-r1-{arm}" / "outcome.json")
                self.assertFalse(json.loads(p.read_text())["workspace_changed"])
            with self.assertRaisesRegex(ValueError, "not empty"):
                execute(EXP / "suite.json", folder, "mock", None, 1, 42, 15, False)

    def test_real_execution_needs_explicit_approval(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "requires --execute"):
                execute(EXP / "suite.json", Path(d) / "out", "claude", "sonnet", 1, 42, 1, False)

    def test_injected_skill_only_in_betfirst_arm(self):
        task = load_suite(EXP / "suite.json")[0]
        prompt1 = prompt_for(task, "baseline", "FAKE_SKILL")
        prompt2 = prompt_for(task, "efficiency", "FAKE_SKILL")
        prompt3 = prompt_for(task, "betfirst", "FAKE_SKILL")
        self.assertNotIn("FAKE_SKILL", prompt1)
        self.assertNotIn("FAKE_SKILL", prompt2)
        self.assertIn("FAKE_SKILL", prompt3)
        self.assertNotIn("Execution guidance:", prompt1)
        self.assertIn("Execution guidance:", prompt2)


if __name__ == "__main__":
    unittest.main()
