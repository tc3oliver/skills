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

    def test_budgeted_pairs_round_robin_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "budgeted"
            kw = dict(
                suite=EXP / "suite.json", output=out, driver="mock", model=None,
                replicates=2, seed=42, timeout=15, execute_real=False,
                selected_arms=["efficiency", "betfirst"], paired=True,
                time_budget_seconds=200, verification_timeout=5,
            )
            results = execute(**kw)
            self.assertEqual(len(results), 12)
            manifest = json.loads((out / "manifest.json").read_text())
            ids = manifest["run_order"]
            self.assertEqual(len(ids), 12)
            for i in range(0, len(ids), 2):
                parts = [ids[i].rsplit("-", 1)[0], ids[i + 1].rsplit("-", 1)[0]]
                self.assertEqual(parts[0], parts[1])
            status = json.loads((out / "budget-status.json").read_text())
            self.assertEqual(status["complete_pairs"], 6)
            self.assertEqual(status["completed_sessions"], 12)
            self.assertEqual(len(execute(**kw, resume=True)), 12)
            status = json.loads((out / "budget-status.json").read_text())
            self.assertEqual(status["completed_sessions"], 12)
            self.assertEqual(status["reason"], "planned_sessions_complete")

    def test_budget_stops_before_pair_and_never_restarts_on_resume(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "budgeted"
            kw = dict(
                suite=EXP / "suite.json", output=out, driver="mock", model=None,
                replicates=2, seed=42, timeout=15, execute_real=False,
                selected_arms=["efficiency", "betfirst"], paired=True,
                time_budget_seconds=1, verification_timeout=5,
            )
            self.assertEqual(execute(**kw), [])
            status = json.loads((out / "budget-status.json").read_text())
            self.assertEqual(status["completed_sessions"], 0)
            self.assertEqual(status["reason"], "insufficient_time_for_complete_pair")
            self.assertEqual(execute(**kw, resume=True), [])
            self.assertEqual(len(list(out.glob("*/outcome.json"))), 0)

    def test_budget_requires_exactly_two_arms(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "exactly two"):
                execute(
                    EXP / "suite.json", Path(d) / "out",
                    "mock", None, 1, 42, 15, False,
                    selected_arms=["betfirst"], paired=True,
                    time_budget_seconds=200,
                )

    def test_muse_study_gate_rejects_synthetic_smoke(self):
        from muse_study import verify_smoke
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "smoke"
            execute(EXP / "suite.json", out, "mock", None, 1, 42, 15, False)
            ok, issues = verify_smoke(out)
            self.assertFalse(ok)
            self.assertTrue(issues)  # synthetic fixture is not a real single-session OpenCode smoke

    def test_muse_light_smoke_allows_a_real_oracle_fail(self):
        from muse_study import MODEL, ROOT, SUITE, verify_smoke
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            rid = "cursor-pagination-r1-betfirst"
            (folder / rid).mkdir()
            manifest = {
                "driver": "opencode", "model": MODEL, "synthetic": False,
                "selected_arms": ["betfirst"],
                "selected_task_ids": ["cursor-pagination"],
                "replicates": 1, "runs": 1,
                "opencode_tool_profile": "diagnostic",
                "skill_sha256": hashlib.sha256(
                    (ROOT / "betfirst" / "SKILL.md").read_bytes()).hexdigest(),
                "suite_sha256": hashlib.sha256(SUITE.read_bytes()).hexdigest(),
            }
            (folder / "manifest.json").write_text(json.dumps(manifest))
            with (folder / "measured-runs.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=[
                    "task_id", "replicate", "arm", "passed", "failure_reasons"])
                writer.writeheader()
                writer.writerow({
                    "task_id": "cursor-pagination", "replicate": 1,
                    "arm": "betfirst", "passed": "false",
                    "failure_reasons": "oracle_failed"})
            outcome = {
                "agent_exit": 0, "agent_timeout": False, "agent_subtype": None,
                "acceptance_exit": 0, "oracle_exit": 1,
                "passed": False, "code_accepted": False}
            (folder / rid / "outcome.json").write_text(json.dumps(outcome))
            (folder / rid / "trace_summary.json").write_text(
                json.dumps({"agent_turns": 2, "tool_calls": 3}))
            accepted, issues = verify_smoke(folder)
            self.assertTrue(accepted, issues)
            outcome["agent_exit"] = 1
            (folder / rid / "outcome.json").write_text(json.dumps(outcome))
            accepted, issues = verify_smoke(folder)
            self.assertFalse(accepted)
            self.assertTrue(any("process" in issue for issue in issues))

    def test_muse_launch_runs_one_smoke_then_study_without_real_model(self):
        from muse_study import main
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "run"
            with patch("sys.argv", ["muse_study.py", "launch",
                                    "--output", str(root), "--hours", "2",
                                    "--acknowledge-isolation"]), \
                 patch("muse_study.run_smoke") as smoke, \
                 patch("muse_study.verify_smoke", return_value=(True, [])), \
                 patch("muse_study.run_study", return_value=0) as study:
                self.assertEqual(main(), 0)
                smoke.assert_called_once_with(root.resolve() / "smoke")
                study.assert_called_once_with(root.resolve() / "study", 2.0)

if __name__ == "__main__":
    unittest.main()
