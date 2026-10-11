import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from paging import page
class Oracle(unittest.TestCase):
    def test_complete_pagination(self):
        source=list(range(11)); cursor=0; results=[]
        for _ in range(10):
            chunk,cursor=page(source,cursor,3)
            self.assertLessEqual(len(chunk),3)
            results.extend(chunk)
            if cursor is None:break
        self.assertEqual(results,source)
    def test_exact_edge_and_invalid(self):
        self.assertEqual(page([1,2,3,4],0,2),([1,2],2))
        self.assertEqual(page([1,2,3,4],2,2),([3,4],None))
        with self.assertRaises(ValueError):page([],0,0)
if __name__ == "__main__": unittest.main()
