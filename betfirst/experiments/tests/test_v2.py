"""Mixed-difficulty evaluation verification; no model calls and no speedup claims."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))

from run import command, execute, load_suite
from trace import summarize_trace
from usage import usage_from_output


class TraceTests(unittest.TestCase):
    def test_terminal_result_usage_and_deduplicated_tool_events(self):
        data = "\n".join(json.dumps(e) for e in [
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tool1", "name": "Read", "input": {"file_path": "/private"}}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tool1", "name": "Read"}]}},  # replay
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tool1", "is_error": False}]}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tool2", "name": "Bash", "input": {"command": "secret"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tool2", "is_error": True}]}},
            {"type": "result", "subtype": "success",
             "permission_denials": [{"tool_name": "Bash"}],
             "usage": {"input_tokens": 0, "output_tokens": 30,
                       "cache_read_input_tokens": 500, "cache_creation_input_tokens": 50},
             "total_cost_usd": 0.0}
        ])
        summary = summarize_trace(data, "claude")
        self.assertTrue(summary["trace_complete"])
        self.assertEqual(summary["tool_calls"], 2)
        self.assertEqual(summary["tool_results"], 2)
        self.assertEqual(summary["tool_errors"], 1)
        self.assertEqual(summary["permission_denials"], 1)
        self.assertEqual(summary["tools_by_name"], {"Bash": 1, "Read": 1})
        self.assertNotIn("secret", json.dumps(summary))
        self.assertIsNone(summary["bet_attempts"])
        usage = usage_from_output(data, "claude")
        self.assertEqual(usage["cache_read_tokens"], 500)
        self.assertEqual(usage["cache_write_tokens"], 50)
        self.assertEqual(usage["output_tokens"], 30)
        self.assertEqual(usage["api_cost_usd"], 0.0)

    def test_terminated_early_does_not_fabricate_usage_or_tools(self):
        partial = json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "a", "name": "Bash"}]}})
        self.assertIsNone(summarize_trace(partial, "claude")["tool_calls"])
        self.assertIsNone(usage_from_output(partial, "claude")["output_tokens"])

    def test_malformed_stream_is_unknown_not_zero(self):
        self.assertIsNone(summarize_trace('not json\n{"type":"result"}', "claude")["tool_calls"])
        self.assertTrue(all(x is None for x in usage_from_output("bad", "claude").values()))


class RunnerV2Tests(unittest.TestCase):
    def test_launcher_separates_omlx_and_claude_flags(self):
        import os
        old = os.environ.get("OMLX_BIN")
        try:
            os.environ["OMLX_BIN"] = "/tmp/fake/omlx"
            argv = command("claude", "Qwen3.8-27B-oQ4e-mtp", "task", "task", "betfirst", "omlx")
            self.assertEqual(argv[:5], ["/tmp/fake/omlx", "launch", "claude", "--model", "Qwen3.8-27B-oQ4e-mtp"])
            self.assertEqual(argv[5], "--")
            self.assertIn("stream-json", argv)
            self.assertIn("--verbose", argv)
            self.assertNotIn("--dangerously-skip-permissions", argv)
        finally:
            if old is None:
                os.environ.pop("OMLX_BIN", None)
            else:
                os.environ["OMLX_BIN"] = old

    def test_all_five_tasks_pass_synthetic_with_independent_oracles(self):
        suite = EXP / "suite-v2.json"
        tasks = load_suite(suite)
        self.assertEqual(len(tasks), 5)
        self.assertEqual(sum(t["difficulty"] == "diagnostic" for t in tasks), 2)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "out"
            runs = execute(suite, root, "mock", None, 1, 42, 30, False)
            self.assertEqual(len(runs), 15)
            self.assertTrue(all(r["passed"] == "true" for r in runs))
            self.assertTrue(json.loads((root / "manifest.json").read_text())["synthetic"])
            for task in tasks:
                for arm in ("baseline", "efficiency", "betfirst"):
                    folder = root / f"{task['id']}-r1-{arm}"
                    outcome = json.loads((folder / "outcome.json").read_text())
                    self.assertEqual(outcome["oracle_exit"], 0, (task["id"], arm, outcome))
                    self.assertTrue(outcome["passed"])
                    trace = json.loads((folder / "trace_summary.json").read_text())
                    self.assertIsNone(trace["tool_calls"])
                    self.assertIsNone(trace["bet_attempts"])

    def test_selected_diagnostic_only_is_recorded_in_manifest(self):
        suite = EXP / "suite-v2.json"
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "out"
            rows = execute(suite, output, "mock", None, 1, 42, 30, False,
                           selected_tasks=["config-scope"])
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(row["passed"] == "true" for row in rows))
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["task_selection"], "explicit")
            self.assertEqual(manifest["selected_task_ids"], ["config-scope"])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "duplicate or unknown"):
                execute(suite, Path(d) / "out", "mock", None, 1, 42, 30, False,
                        selected_tasks=["nonexistent"])

    def test_diagnostic_oracles_are_initially_red(self):
        suite = EXP / "suite-v2.json"
        tasks = load_suite(suite)
        for task in tasks:
            if task["difficulty"] != "diagnostic":
                continue
            with self.subTest(task=task["id"]), tempfile.TemporaryDirectory() as d:
                workspace = Path(d) / "work"
                shutil.copytree(EXP / task["fixture"], workspace)
                oracle = EXP / task["oracle"]
                result = subprocess.run([sys.executable, str(oracle)], cwd=workspace,
                                        capture_output=True, timeout=15)
                self.assertNotEqual(result.returncode, 0, "Broken fixture must fail hidden acceptance")


if __name__ == "__main__":
    unittest.main()
