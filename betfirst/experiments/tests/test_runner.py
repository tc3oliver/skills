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


    def test_opencode_permissions_and_cli(self):
        from run import command, opencode_environment
        with tempfile.TemporaryDirectory() as d:
            cmd = command("opencode", "opencode-go/muse-spark-1.3-contributor",
                          "repair", "task", "betfirst")
            self.assertEqual(cmd[:4], ["opencode", "run", "--agent", "build"])
            self.assertIn("--format", cmd)
            self.assertNotIn("--auto", cmd)
            env = opencode_environment(Path(d) / "config", "diagnostic")
            policy = json.loads(env["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(policy["permission"]["external_directory"], "deny")
            self.assertEqual(policy["permission"]["bash"]["*"], "deny")
            self.assertEqual(policy["permission"]["bash"]["python3 *"], "allow")
            self.assertEqual(policy["share"], "disabled")
            self.assertEqual(env["OPENCODE_DISABLE_CLAUDE_CODE"], "1")

    def test_opencode_usage_and_trace(self):
        from trace import summarize_trace
        events = [
            {"type": "step_start"},
            {"type": "tool_use", "part": {"callID": "x", "tool": "bash",
             "state": {"status": "completed", "output": "ok"}}},
            {"type": "step_finish", "part": {"reason": "tool-calls", "tokens":
             {"input": 7, "output": 3, "cache": {"read": 2, "write": 1}}, "cost": 3.5}},
            {"type": "step_start"},
            {"type": "text", "part": {"text": "done"}},
            {"type": "step_finish", "part": {"reason": "stop", "tokens":
             {"input": 5, "output": 4, "cache": {"read": 1, "write": 0}}, "cost": 1.1}},
        ]
        data = "\n".join(json.dumps(e) for e in events)
        actual = usage_from_output(data, "opencode")
        self.assertEqual((actual["input_tokens"], actual["output_tokens"],
                          actual["cache_read_tokens"], actual["cache_write_tokens"]),
                         (12, 7, 3, 1))
        self.assertIsNone(actual["api_cost_usd"])
        summary = summarize_trace(data, "opencode")
        self.assertEqual(summary["agent_turns"], 2)
        self.assertEqual(summary["tool_calls"], 1)
        self.assertTrue(summary["trace_complete"])

    def test_opencode_missing_final_usage_is_unknown(self):
        from trace import summarize_trace
        events = [
            {"type": "step_start"},
            {"type": "step_finish", "part": {"tokens": {"input": 4, "output": 2,
                  "cache": {"read": 0, "write": 0}}}},
            {"type": "step_start"},
            {"type": "text", "part": {"text": "OK"}},
        ]
        data = "\n".join(json.dumps(e) for e in events)
        self.assertTrue(all(v is None for v in usage_from_output(data, "opencode").values()))
        summary = summarize_trace(data, "opencode")
        self.assertEqual(summary["agent_turns"], 2)
        self.assertFalse(summary["trace_complete"])

    def test_two_arm_mock_pilot_and_resume_plan(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "result"
            rows = execute(EXP / "suite.json", dest, "mock", None,
                           1, 42, 15, False, selected_arms=["efficiency", "betfirst"])
            self.assertEqual(len(rows), 6)
            manifest = json.loads((dest / "manifest.json").read_text())
            self.assertEqual(manifest["selected_arms"], ["efficiency", "betfirst"])
            self.assertEqual(manifest["runs"], 6)
            self.assertEqual(len(execute(EXP / "suite.json", dest, "mock", None, 1, 42,
                                         15, False, resume=True,
                                         selected_arms=["efficiency", "betfirst"])), 6)

if __name__ == "__main__":
    unittest.main()
