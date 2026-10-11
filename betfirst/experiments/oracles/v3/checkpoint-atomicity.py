import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from worker import process
from checkpoint import Checkpoint
class Oracle(unittest.TestCase):
    def test_commit_after_success_and_resume(self):
        c=Checkpoint();persisted=[];once=[False]
        def sink(value):
            if value=="b" and not once[0]:once[0]=True;raise RuntimeError("disk")
            persisted.append(value)
        with self.assertRaises(RuntimeError):process(["a","b","c"],c,sink)
        self.assertEqual(c.cursor,1)
        self.assertEqual(process(["a","b","c"],c,sink),3)
        self.assertEqual(persisted,["a","b","c"])
    def test_idempotent_no_more_input(self):
        c=Checkpoint();out=[]
        process([1],c,out.append);process([1],c,out.append)
        self.assertEqual(out,[1])
if __name__ == "__main__": unittest.main()
