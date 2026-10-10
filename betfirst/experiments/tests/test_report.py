"""The experiment reporter must never market mock timing as cost savings."""
from __future__ import annotations
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXP))
from report import report_dir

FIELDS = ("task_id", "replicate", "arm", "passed", "elapsed_seconds",
          "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens",
          "api_cost_usd", "bet_attempts", "bet_failures", "failed_bet_overhead_seconds")


class PilotReportTests(unittest.TestCase):
    def test_synthetic_is_explicitly_not_an_experiment_result(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text(json.dumps({"driver": "mock", "runs": 9, "synthetic": True}))
            result = report_dir(root)
            self.assertFalse(result["valid_performance_claim"])
            self.assertEqual(result["comparisons"], {})
            self.assertIn("SYNTHETIC", result["status"])

    def test_live_format_reports_policy_vs_efficiency_with_correctness(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text(json.dumps({"driver": "claude", "model": "test-model", "synthetic": False}))
            rows = []
            for arm, time, passed in (
                ("baseline", 100, "true"), ("efficiency", 80, "true"),
                ("betfirst", 60, "false"),
            ):
                rows.append({
                    "task_id": "task1", "replicate": "1", "arm": arm,
                    "passed": passed, "elapsed_seconds": time,
                    "input_tokens": "", "output_tokens": "", "cache_read_tokens": "",
                    "cache_write_tokens": "", "api_cost_usd": "",
                })
            with (root / "measured-runs.csv").open("w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            result = report_dir(root)
            pair = result["comparisons"]["betfirst_vs_efficiency"]
            self.assertEqual(pair["matched_pairs"], 1)
            self.assertFalse(pair["all_pairs_correct"])
            self.assertAlmostEqual(pair["wall_time_saving_fraction"], 0.25)
            self.assertIsNone(pair["gross_tokens_saving_fraction"])
            self.assertIsNone(pair["api_cost_saving_fraction"])
            self.assertFalse(result["valid_performance_claim"])


if __name__ == "__main__":
    unittest.main()
