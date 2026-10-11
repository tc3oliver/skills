"""Prospective v0.4 task fixtures and 3-arm scheduling, no API/model calls."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from run import V04_SKILL, execute, load_suite, prompt_for

EXPECTED = {
    "csv-quoted-comma": False,
    "path-segment-prefix": False,
    "packet-framing": False,
    "namespaced-cache": False,
    "interval-touch-ok": True,
    "retry-exhaustion-ok": True,
}


class V04ProspectiveTests(unittest.TestCase):
    def test_v04_fixtures_have_passable_smoke_and_discriminating_oracles(self):
        suite = HERE / "suite-v04.json"
        tasks = load_suite(suite)
        self.assertEqual({t["id"] for t in tasks}, set(EXPECTED))
        for t in tasks:
            with self.subTest(task=t["id"]):
                work = suite.parent / t["fixture"]
                smoke = subprocess.run(t["check"], cwd=work, text=True,
                                       capture_output=True, timeout=6)
                self.assertEqual(smoke.returncode, 0, smoke.stderr)
                oracle = subprocess.run(
                    [sys.executable, str(suite.parent / t["oracle"])],
                    cwd=work, text=True, capture_output=True, timeout=6)
                self.assertEqual(oracle.returncode == 0, EXPECTED[t["id"]],
                                 oracle.stderr)
                self.assertEqual(bool(t.get("no_change")), t["difficulty"] == "negative")

    def test_v04_policy_is_selective_and_frozen_v03_prompt_unchanged(self):
        frozen = (HERE.parent / "SKILL.md").read_text()
        candidate = V04_SKILL.read_text()
        self.assertLess(len(candidate), len(frozen))
        task = {"prompt": "Fix the test code"}
        e = prompt_for(task, "efficiency", frozen, candidate_skill_text=candidate)
        old = prompt_for(task, "betfirst", frozen, candidate_skill_text=candidate)
        new = prompt_for(task, "betfirst-v04", frozen, candidate_skill_text=candidate)
        self.assertNotIn(candidate, e)
        self.assertNotIn(candidate, old)
        self.assertIn(candidate, new)
        self.assertIn("Apply the following BetFirst Skill:\n" + frozen, old)
        self.assertNotIn("Apply the following BetFirst Skill v0.4", e)
        with self.assertRaisesRegex(ValueError, "explicit candidate"):
            prompt_for(task, "betfirst-v04", frozen)

    def test_three_arm_mock_groups_and_durable_resume(self):
        # Use an *existing* v3 fixture with the synthetic mock because the
        # six novel tasks are reserved for future real-agent evaluation.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "study"
            kw = dict(
                suite=HERE / "suite-v3.json", output=root,
                driver="mock", model=None, replicates=2, seed=20261011,
                timeout=15, execute_real=False,
                selected_tasks=["cursor-pagination"],
                selected_arms=["efficiency", "betfirst", "betfirst-v04"],
                paired=True, time_budget_seconds=180, verification_timeout=5,
            )
            rows = execute(**kw)
            self.assertEqual(len(rows), 6)
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["selected_arms"], kw["selected_arms"])
            self.assertEqual(manifest["v04_skill_sha256"],
                             hashlib.sha256(V04_SKILL.read_bytes()).hexdigest())
            ids = manifest["run_order"]
            self.assertEqual(len(ids), 6)
            for i in (0, 3):
                group = ids[i:i+3]
                suffixes = ("-efficiency", "-betfirst", "-betfirst-v04")
                self.assertTrue(all(any(x.endswith(s) for s in suffixes) for x in group))
                roots = [next(x[:-len(s)] for s in suffixes if x.endswith(s))
                         for x in group]
                self.assertEqual(len(set(roots)), 1)
            budget = json.loads((root / "budget-status.json").read_text())
            self.assertEqual(budget["complete_pairs"], 2)
            self.assertEqual(budget["completed_sessions"], 6)
            self.assertEqual(len(execute(**kw, resume=True)), 6)


if __name__ == "__main__":
    unittest.main()
