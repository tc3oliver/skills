#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_runs import load_records, report  # noqa: E402


COLUMNS = (
    "task_id,replicate,arm,passed,elapsed_seconds,input_tokens,output_tokens,"
    "cache_read_tokens,cache_write_tokens,api_cost_usd,bet_attempts,bet_failures,"
    "failed_bet_overhead_seconds\n"
)


def parsed(data: str):
    return load_records(csv.DictReader(io.StringIO(COLUMNS + data)))


class AnalyzeRunsTests(unittest.TestCase):
    def test_pairing_and_cost(self):
        rows = parsed(
            "A,1,baseline,true,10,100,50,0,0,1.0,,,\n"
            "A,1,betfirst,true,5,40,20,0,0,0.5,1,0,0\n"
            "B,1,baseline,false,20,100,100,0,0,2.0,,,\n"
            "B,1,betfirst,false,21,120,100,0,0,2.2,1,1,1\n"
        )
        output = report(rows)
        pair = output["comparisons"]["betfirst_vs_baseline"]
        self.assertEqual(pair["matched_pairs"], 2)
        self.assertAlmostEqual(pair["time_saving_fraction"], 1 - 26 / 30)
        self.assertAlmostEqual(pair["gross_token_saving_fraction"], 1 - 280 / 350)
        self.assertEqual(output["arms"]["betfirst"]["bet_failures"], 1)
        self.assertEqual(output["arms"]["betfirst"]["passed"], 1)

    def test_missing_usage_stays_null(self):
        rows = parsed(
            "A,1,baseline,true,10,,,,,,,,\n"
            "A,1,betfirst,true,5,40,20,,,,,,\n"
        )
        pair = report(rows)["comparisons"]["betfirst_vs_baseline"]
        self.assertIsNone(pair["gross_token_saving_fraction"])
        self.assertIsNone(pair["api_cost_saving_fraction"])

    def test_duplicate_run_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parsed("A,1,baseline,true,10,,,,,,,,\nA,1,baseline,true,10,,,,,,,,\n")

    def test_invalid_cost_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            parsed("A,1,betfirst,true,5,40,20,0,0,-1,1,0,0\n")


if __name__ == "__main__":
    unittest.main()
