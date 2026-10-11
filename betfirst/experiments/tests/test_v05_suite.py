"""Frozen v05 protocol preflight: no live model calls."""
from __future__ import annotations
import subprocess
import sys
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from run import load_suite, prompt_for, V04_SKILL, NOBET_SKILL, EXPERIMENT_ARMS

class CausalV05Tests(unittest.TestCase):
    def test_fixture_contract(self):
        suite=HERE/"suite-v05.json"
        tasks=load_suite(suite)
        self.assertEqual(len(tasks),12)
        for kind in ("bet-win","bet-loss","normal"):
            self.assertEqual(sum(t["difficulty"]==kind for t in tasks),4)
        for task in tasks:
            with self.subTest(task=task["id"]):
                cwd=suite.parent/task["fixture"]
                visible=subprocess.run(task["check"],cwd=cwd,capture_output=True,text=True,timeout=10)
                self.assertEqual(visible.returncode,0,visible.stderr)
                oracle=subprocess.run([sys.executable,str(suite.parent/task["oracle"])],
                                      cwd=cwd,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(oracle.returncode,0,"hidden oracle must discriminate unfixed fixture")

    def test_ablation_is_distinct_and_isolated(self):
        self.assertIn("betfirst-v04-nobet",EXPERIMENT_ARMS)
        frozen=(HERE.parent/"SKILL.md").read_text()
        v04=V04_SKILL.read_text()
        nobet=NOBET_SKILL.read_text()
        task={"prompt":"Fix only the bug"}
        candidate=prompt_for(task,"betfirst-v04",frozen,candidate_skill_text=v04)
        ablation=prompt_for(task,"betfirst-v04-nobet",frozen,candidate_skill_text=nobet)
        control=prompt_for(task,"efficiency",frozen)
        self.assertIn(v04,candidate)
        self.assertNotIn(v04,ablation)
        self.assertIn(nobet,ablation)
        self.assertNotIn(nobet,candidate)
        self.assertNotIn(v04,control)
        self.assertNotIn(nobet,control)
        self.assertIn("ABSTAIN",nobet)
        self.assertIn("NORMAL",nobet)

if __name__=="__main__":
    unittest.main()
