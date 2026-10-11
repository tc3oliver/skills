import unittest
from consumer import consume
class Smoke(unittest.TestCase):
    def test_monotonic_single_shard(self):
        self.assertEqual(consume([("a",1,"a1"),("a",1,"dup"),("a",2,"a2")]),["a1","a2"])
if __name__ == "__main__": unittest.main()
