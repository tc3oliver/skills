import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from models import Job
from dispatcher import pick
class Oracle(unittest.TestCase):
    def test_priority_ages_and_eligibility(self):
        jobs=[Job("low",1,1),Job("high-late",9,6),Job("high-early",9,4),Job("blocked",20,0,retry_at=30)]
        self.assertEqual(pick(jobs,10).job_id,"high-early")
        self.assertEqual(pick(jobs,31).job_id,"blocked")
    def test_empty(self):
        self.assertIsNone(pick([],0))
        self.assertIsNone(pick([Job("x",9,1,100)],5))
if __name__ == "__main__": unittest.main()
