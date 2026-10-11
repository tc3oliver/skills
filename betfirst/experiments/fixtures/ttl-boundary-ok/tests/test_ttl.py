import unittest
from ttl import TTLCache
class Smoke(unittest.TestCase):
    def test_before_expiry(self):
        t=[0];c=TTLCache(lambda:t[0]);c.put("a",1,3)
        self.assertEqual(c.get("a"),1)
if __name__ == "__main__": unittest.main()
