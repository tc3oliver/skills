"""V3 preregistration and external-oracle checks (never model performance)."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EXP))
from run import execute,load_suite,hashes

EXPECTED={
    "webhook-signature":"low", "cursor-pagination":"low", "unicode-casefold":"low",
    "queue-priority":"diagnostic", "ledger-idempotency":"diagnostic",
    "search-highlight":"diagnostic", "lease-fencing":"stateful",
    "checkpoint-atomicity":"stateful", "partition-watermarks":"stateful",
    "stable-merge-ok":"negative", "ttl-boundary-ok":"negative",
    "retry-once-ok":"negative",
}

class SuiteV3Tests(unittest.TestCase):
    def test_suite_is_complete_and_frozen_category_balance(self):
        suite=EXP/"suite-v3.json"
        tasks=load_suite(suite)
        self.assertEqual({t["id"]:t["difficulty"] for t in tasks},EXPECTED)
        self.assertEqual(len(tasks),12)
        self.assertEqual(sum(t.get("no_change") is True for t in tasks),3)
        self.assertTrue(all("oracle" in t for t in tasks))
        self.assertTrue(all(t["id"] not in ("config-scope","render-resume") for t in tasks))

    def test_oracle_red_on_original_and_green_after_reference_fix(self):
        suite=EXP/"suite-v3.json"
        for task in load_suite(suite):
            with self.subTest(task=task["id"]),tempfile.TemporaryDirectory() as d:
                work=Path(d)/"work"
                shutil.copytree(suite.parent/task["fixture"],work)
                original=hashes(work)
                oracle=[sys.executable,str(suite.parent/task["oracle"])]
                before=subprocess.run(oracle,cwd=work,capture_output=True,text=True,timeout=10)
                self.assertEqual(before.returncode==0, bool(task.get("no_change")),
                                 (task["id"],before.stdout[-800:],before.stderr[-800:]))
                ref=EXP/"oracles"/"v3-reference"/(task["id"]+".py")
                fix=subprocess.run([sys.executable,str(ref)],cwd=work,capture_output=True,text=True,timeout=10)
                self.assertEqual(fix.returncode,0,(task["id"],fix.stderr))
                after=subprocess.run(oracle,cwd=work,capture_output=True,text=True,timeout=10)
                self.assertEqual(after.returncode,0,(task["id"],after.stdout[-900:],after.stderr[-900:]))
                if task.get("no_change"):
                    self.assertEqual(original,hashes(work))
                else:
                    self.assertNotEqual(original,hashes(work))

    def test_full_synthetic_36_run_smoke_passes(self):
        with tempfile.TemporaryDirectory() as d:
            suite=EXP/"suite-v3.json"
            out=Path(d)/"smoke"
            rows=execute(suite,out,"mock",None,1,73,30,False)
            self.assertEqual(len(rows),36)
            self.assertTrue(all(r["passed"]=="true" for r in rows),
                            [r for r in rows if r["passed"]!="true"])
            m=json.loads((out/"manifest.json").read_text())
            self.assertEqual(m["selected_task_ids"],list(EXPECTED))
            self.assertTrue(m["synthetic"])
            self.assertEqual(len(m["fixture_hashes"]),12)

if __name__=="__main__":unittest.main()
