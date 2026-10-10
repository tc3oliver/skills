"""Field-note totals and clock disagreements must remain visible and reproducible."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from summarize_bet_log import summarize  # noqa: E402

LOG = ROOT / "evals" / "field-notes" / "signalforge-video-bets.json"


class SummarizeBetLogTests(unittest.TestCase):
    def test_published_field_log_exposes_unreconciled_timing(self):
        s = summarize(json.loads(LOG.read_text(encoding="utf-8")))
        self.assertEqual((s["bets"], s["successes"], s["failures"]), (20, 14, 6))
        self.assertEqual(s["bet_seconds"], 1355)  # recorded, NOT validated elapsed time
        self.assertEqual(s["timestamp_span_seconds"], 1594)
        self.assertFalse(s["timing_reconciled"])
        self.assertEqual(
            [x["id"] for x in s["duration_discrepancies"]],
            ["BET-13", "BET-14", "BET-18", "BET-19", "BET-19c"],
        )
        self.assertEqual(s["over_cap"], ["BET-4", "BET-15", "BET-16", "BET-18"])
        self.assertEqual(s["over_cap_by_timestamp"], ["BET-4", "BET-15", "BET-16"])
        self.assertEqual((s["rollbacks"], s["fallbacks"], s["bets_with_token_usage"]), (0, 5, 0))
        self.assertEqual(s["bets_without_timestamps"], 0)

    def test_unknown_duration_or_timestamps_remain_unknown(self):
        s = summarize({
            "bets": [
                {"id": "a", "result": "success", "duration_seconds": 5},
                {"id": "b", "result": "failure", "started_at": "2026-10-10T00:00:00Z", "ended_at": "2026-10-10T00:00:03Z"},
            ],
        })
        self.assertIsNone(s["bet_seconds"])
        self.assertIsNone(s["timestamp_span_seconds"])
        self.assertEqual(s["bets_without_duration"], 1)
        self.assertEqual(s["bets_without_timestamps"], 1)
        self.assertFalse(s["timing_reconciled"])

    def test_offsets_do_not_create_false_discrepancy(self):
        s = summarize({"bets": [{
            "id": "a", "result": "failure", "duration_seconds": 5,
            "started_at": "2026-10-10T08:00:00+08:00", "ended_at": "2026-10-10T00:00:05Z",
            "tokens_input": 0, "tokens_output": 10,
        }]})
        self.assertTrue(s["timing_reconciled"])
        self.assertEqual(s["timestamp_span_seconds"], 5)
        self.assertEqual(s["bets_with_token_usage"], 1)

    def test_rejects_invalid_logs_and_timestamps(self):
        cases = (
            {},
            {"bets": []},
            {"bets": [{"id": "a", "result": "maybe"}]},
            {"bets": [{"id": "a", "result": "success"}, {"id": "a", "result": "failure"}]},
            {"bets": [{"id": "a", "result": "success", "duration_seconds": -1}]},
            {"bets": [{"id": "a", "result": "success", "duration_seconds": True}]},
            {"bets": [{"id": "a", "result": "success", "duration_seconds": float("nan")}]},
            {"bets": [{"id": "a", "result": "success", "started_at": "2026-10-10T00:00:00Z"}]},
            {"bets": [{"id": "a", "result": "success", "started_at": "2026-10-10T00:00:05Z", "ended_at": "2026-10-10T00:00:00Z"}]},
            {"bets": [{"id": "a", "result": "success", "started_at": "2026-10-10T00:00:00", "ended_at": "2026-10-10T00:00:05"}]},
            {"bets": [{"id": "a", "result": "success", "tokens_input": -1}]},
        )
        for bad in cases:
            with self.subTest(log=bad):
                with self.assertRaises(ValueError):
                    summarize(bad)
        with self.assertRaises(ValueError):
            summarize({"bets": [{"id": "a", "result": "success"}]}, cap_seconds=0)


if __name__ == "__main__":
    unittest.main()
