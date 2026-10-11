import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from merge import merge_sorted
class Oracle(unittest.TestCase):
    def test_stable_ties(self):
        a=[(1,"left-1"),(2,"left-2")];b=[(1,"right-1"),(2,"right-2")]
        self.assertEqual(merge_sorted(a,b,key=lambda x:x[0]),[(1,"left-1"),(1,"right-1"),(2,"left-2"),(2,"right-2")])
    def test_empties_duplicates(self):
        self.assertEqual(merge_sorted([],[]),[])
        self.assertEqual(merge_sorted([2,2],[2]),[2,2,2])
if __name__ == "__main__": unittest.main()
