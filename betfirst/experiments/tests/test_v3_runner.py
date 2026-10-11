"""Offline v3 publication gate and durable 108-run orchestration tests."""
from __future__ import annotations
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

EXP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EXP))
from run import execute
from v3_report import compute,render_markdown

class ResumeTests(unittest.TestCase):
    def test_interrupted_then_resume_preserves_first_checkpoint(self):
        suite=EXP/"suite-v3.json"
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"live-like-mock"
            first=execute(suite,output,"mock",None,1,42,30,False,
                          selected_tasks=["webhook-signature"],stop_after=1)
            self.assertEqual(len(first),1)
            self.assertEqual(first[0]["passed"],"true")
            checkpoint=(output/"synthetic-smoke.csv").read_bytes()
            self.assertEqual(len(list(csv.DictReader(checkpoint.decode().splitlines()))),1)
            with self.assertRaisesRegex(ValueError,"not empty"):
                execute(suite,output,"mock",None,1,42,30,False,
                        selected_tasks=["webhook-signature"])
            complete=execute(suite,output,"mock",None,1,42,30,False,
                             selected_tasks=["webhook-signature"],resume=True)
            self.assertEqual(len(complete),3)
            self.assertTrue(all(r["passed"]=="true" for r in complete))
            self.assertEqual(len(list(csv.DictReader((output/"synthetic-smoke.csv").open()))),3)
            for arm in ("baseline","efficiency","betfirst"):
                p=output/f"webhook-signature-r1-{arm}"
                self.assertTrue((p/"row.json").is_file())
                self.assertTrue((p/"outcome.json").is_file())
            complete_again=execute(suite,output,"mock",None,1,42,30,False,
                                   selected_tasks=["webhook-signature"],resume=True)
            self.assertEqual(complete_again,complete)

    def test_resume_rejects_changed_plan(self):
        suite=EXP/"suite-v3.json"
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"partial"
            execute(suite,output,"mock",None,1,42,30,False,
                    selected_tasks=["webhook-signature"],stop_after=1)
            with self.assertRaisesRegex(ValueError,"manifest mismatch"):
                execute(suite,output,"mock",None,1,44,30,False,
                        selected_tasks=["webhook-signature"],resume=True)

class FinalReportTests(unittest.TestCase):
    def make_synthetic_full_data(self,root):
        suite=EXP/"suite-v3.json"
        out=root/"output"
        # Smoke only; deliberately transform to fake "live-like" data to
        # test the parser. NEVER publish this fabricated test fixture.
        rows=execute(suite,out,"mock",None,1,42,30,False)
        old=out/"synthetic-smoke.csv"
        old.unlink()
        new=[]
        for row in rows:
            for rep in (1,2,3):
                item=dict(row)
                item.update(replicate=rep,elapsed_seconds="12" if row["arm"]=="baseline" else
                             "10" if row["arm"]=="efficiency" else "8",
                            code_accepted="true",session_success="true",
                            output_tokens=100,input_tokens=0,cache_read_tokens=20,
                            cache_write_tokens=5)
                new.append(item)
        with (out/"measured-runs.csv").open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(new[0]))
            writer.writeheader();writer.writerows(new)
        manifest_path=out/"manifest.json"
        manifest=json.loads(manifest_path.read_text())
        manifest.update(schema=3,synthetic=False,driver="claude",
                        model="FAKE-SYNTHETIC-UNIT-TEST",replicates=3,runs=108,
                        claude_tool_profile="diagnostic")
        manifest_path.write_text(json.dumps(manifest))
        return out

    def test_full_report_and_preset_gate(self):
        with tempfile.TemporaryDirectory() as d:
            out=self.make_synthetic_full_data(Path(d))
            result=compute(out,EXP/"suite-v3.json",bootstrap=250)
            self.assertEqual(result["runs"],108)
            self.assertEqual(result["arm_stats"]["betfirst"]["passed"],36)
            c=result["comparisons"]["betfirst_vs_efficiency"]
            self.assertTrue(c["positive_speedup_claim_gate"])
            self.assertEqual(c["task_median_faster_count"],12)
            self.assertEqual(c["paired_run_faster_count"],36)
            self.assertIn("No extra v4",render_markdown(result))
            self.assertFalse(result["performance_claim_is_causal"])

    def test_reject_incomplete_and_synthetic(self):
        suite=EXP/"suite-v3.json"
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"short"
            execute(suite,out,"mock",None,1,42,30,False,stop_after=1)
            with self.assertRaisesRegex(ValueError,"real completed"):
                compute(out,suite)

if __name__=="__main__":unittest.main()
