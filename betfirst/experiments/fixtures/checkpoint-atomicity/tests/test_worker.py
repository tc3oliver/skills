import unittest
from worker import process
from checkpoint import Checkpoint
class Smoke(unittest.TestCase):
    def test_no_crash(self):
        cp=Checkpoint();out=[]
        self.assertEqual(process(["a","b"],cp,out.append),2)
        self.assertEqual(out,["a","b"])
if __name__ == "__main__": unittest.main()
