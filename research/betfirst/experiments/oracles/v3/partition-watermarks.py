import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from consumer import consume
from watermarks import Watermarks
class Oracle(unittest.TestCase):
    def test_interleaved(self):
        w=Watermarks();e=[("a",10,"a10"),("b",1,"b1"),("a",9,"old"),("b",2,"b2"),("a",11,"a11"),("b",1,"dup")]
        self.assertEqual(consume(e,w),["a10","b1","b2","a11"])
        self.assertEqual(consume([("b",3,"b3"),("a",11,"dup")],w),["b3"])
    def test_zero_offset(self):
        self.assertEqual(consume([("c",0,"zero"),("c",0,"dup")]),["zero"])
if __name__ == "__main__": unittest.main()
