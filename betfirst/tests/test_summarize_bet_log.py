"""The field-notes numbers must be reproducible from the published raw log."""
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
    def test_published_field_log_matches_the_field_notes(self):
        s = summarize(json.loads(LOG.read_text(encoding="utf-8")))
        self.assertEqual((s["bets"], s["successes"], s["failures"]), (20, 14, 6))
        self.assertEqual(s["bet_seconds"], 1355)
        self.assertEqual(s["over_cap"], ["BET-4", "BET-15", "BET-16", "BET-18"])
        self.assertEqual((s["rollbacks"], s["fallbacks"], s["bets_with_token_usage"]), (0, 5, 0))

    def test_unknown_duration_is_not_summed_as_zero(self):
        s = summarize({"bets": [{"id": "a", "result": "success", "duration_seconds": 5}, {"id": "b", "result": "failure"}]})
        self.assertIsNone(s["bet_seconds"])
        self.assertEqual(s["bets_without_duration"], 1)

    def test_rejects_invalid_logs(self):
        for bad in ({}, {"bets": []}, {"bets": [{"id": "a", "result": "maybe"}]}, {"bets": [{"id": "a", "result": "success"}, {"id": "a", "result": "failure"}]}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    summarize(bad)


if __name__ == "__main__":
    unittest.main()
