import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from ttl import TTLCache
class Oracle(unittest.TestCase):
    def test_exact_boundary(self):
        t=[5];c=TTLCache(lambda:t[0]);c.put("a",False,10)
        t[0]=14.999;self.assertIs(c.get("a"),False)
        t[0]=15;self.assertIsNone(c.get("a"))
        self.assertEqual(c.data,{})
    def test_replace_and_other_key(self):
        t=[0];c=TTLCache(lambda:t[0]);c.put("x",1,1);c.put("y",2,4)
        t[0]=1;self.assertIsNone(c.get("x"));self.assertEqual(c.get("y"),2)
if __name__ == "__main__": unittest.main()
