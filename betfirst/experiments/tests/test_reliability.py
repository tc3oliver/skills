"""Reliability regressions: diagnostic tool policy and separate completion semantics."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))

from run import command, execute, prompt_for, TOOL_PROFILES
from scoring import classify
from trace import summarize_trace
from report import report_dir


class ScoringTests(unittest.TestCase):
    def score(self, **overrides):
        baseline = dict(
            task={"id": "render-resume"}, agent_exit=0, agent_timeout=False,
            agent_subtype="success", test_exit=0, test_timeout=False,
            oracle_exit=0, oracle_timeout=False,
            test_integrity_passed=True, workspace_changed=True)
        baseline.update(overrides)
        return classify(**baseline)

    def test_all_checks_and_session_pass(self):
        result = self.score()
        self.assertTrue(result["code_accepted"])
        self.assertTrue(result["session_success"])
        self.assertTrue(result["passed"])

    def test_max_turns_can_still_have_accepted_code(self):
        result = self.score(agent_exit=1, agent_subtype="error_max_turns")
        self.assertTrue(result["code_accepted"])
        self.assertFalse(result["session_success"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["failure_reasons"], ["agent_max_turns"])

    def test_oracle_fail_does_not_count_as_accepted_code(self):
        result = self.score(oracle_exit=1)
        self.assertEqual(result["failure_reasons"], ["oracle_failed"])
        self.assertFalse(result["code_accepted"])
        self.assertTrue(result["session_success"])

    def test_tampered_tests_and_timeout_independent(self):
        result = self.score(test_integrity_passed=False, agent_timeout=True,
                            agent_exit=None, agent_subtype=None)
        self.assertEqual(result["failure_reasons"],
                         ["tests_tampered", "agent_timeout"])

    def test_no_change_contract_still_enforced(self):
        result = self.score(task={"id": "already-correct", "no_change": True})
        self.assertEqual(result["failure_reasons"], ["unexpected_change"])

    def test_error_subtype_does_not_need_nonzero_process_exit(self):
        result = self.score(agent_exit=0, agent_subtype="error_api")
        self.assertEqual(result["failure_reasons"], ["agent_error"])


class ToolProfileTests(unittest.TestCase):
    def test_profiles_have_identical_toolset_for_all_arms(self):
        self.assertEqual(TOOL_PROFILES["restricted"],
                         ("Read", "Edit", "Write", "Bash(python3 -m unittest *)"))
        self.assertIn("Bash(python3 *)", TOOL_PROFILES["diagnostic"])
        old = os.environ.get("OMLX_BIN")
        try:
            os.environ["OMLX_BIN"] = "/fake/omlx"
            result = []
            for arm in ("baseline", "efficiency", "betfirst"):
                prompt = prompt_for({"prompt": "Debug the incident"}, arm, "SKILL", "diagnostic")
                argv = command("claude", "Qwen", prompt, "x", arm, "omlx",
                               "diagnostic", 45)
                self.assertEqual(argv[:6],
                                 ["/fake/omlx", "launch", "claude", "--model", "Qwen", "--"])
                self.assertEqual(argv[argv.index("--allowedTools") + 1:
                                       argv.index("-p")], list(TOOL_PROFILES["diagnostic"]))
                self.assertEqual(argv[argv.index("--max-turns") + 1], "45")
                self.assertNotIn("--dangerously-skip-permissions", argv)
                result.append(tuple(argv[argv.index("--allowedTools") + 1:
                                         argv.index("-p")]))
            self.assertEqual(len(set(result)), 1)
        finally:
            if old is None:
                os.environ.pop("OMLX_BIN", None)
            else:
                os.environ["OMLX_BIN"] = old

    def test_diagnostic_profile_requires_explicit_isolation_ack(self):
        suite = EXP / "suite-v2.json"
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "--acknowledge-isolation"):
                execute(suite, Path(d) / "out", "claude", "Qwen", 1, 42, 10, True,
                        selected_tasks=["render-resume"], tool_profile="diagnostic")
            self.assertFalse((Path(d) / "out").exists())

    def test_diagnostic_profile_is_not_pretend_sandbox(self):
        self.assertNotIn("Bash(rm *)", TOOL_PROFILES["diagnostic"])
        self.assertNotIn("Bash(*)", TOOL_PROFILES["diagnostic"])
        self.assertNotIn("Bash(cat *)", TOOL_PROFILES["diagnostic"])

    def test_subtype_in_terminal_trace(self):
        stream = "\n".join([
            json.dumps({"type": "assistant", "message": {"content": []}}),
            json.dumps({"type": "result", "subtype": "error_max_turns",
                        "num_turns": 31, "is_error": True, "permission_denials": []})
        ])
        result = summarize_trace(stream, "claude")
        self.assertEqual(result["agent_subtype"], "error_max_turns")
        self.assertEqual(result["agent_turns"], 31)
        self.assertEqual(result["agent_is_error"], True)


class ReportTests(unittest.TestCase):
    def test_paired_code_and_session_success_are_separate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text(json.dumps({
                "driver": "claude", "model": "Qwen", "synthetic": False, "runs": 3
            }))
            (root / "measured-runs.csv").write_text(
                "task_id,replicate,arm,passed,elapsed_seconds,input_tokens,output_tokens,"
                "cache_read_tokens,cache_write_tokens,api_cost_usd,"
                "code_accepted,session_success\n"
                "render-resume,1,baseline,false,12,10,10,0,0,0,true,false\n"
                "render-resume,1,efficiency,true,10,10,10,0,0,0,true,true\n"
                "render-resume,1,betfirst,true,8,10,10,0,0,0,true,true\n"
            )
            result = report_dir(root)["comparisons"]["betfirst_vs_baseline"]
            self.assertEqual(result["candidate_code_accepted"], 1)
            self.assertEqual(result["control_code_accepted"], 1)
            self.assertEqual(result["candidate_session_success"], 1)
            self.assertEqual(result["control_session_success"], 0)


if __name__ == "__main__":
    unittest.main()
