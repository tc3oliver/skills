import unittest
from cache import ScopedCache

class Smoke(unittest.TestCase):
    def test_repeat_uses_cache(self):
        c=ScopedCache()
        seen=[]
        def load(ns, key):
            seen.append((ns,key))
            return len(seen)
        self.assertEqual(c.get("east","x",load),1)
        self.assertEqual(c.get("east","x",load),1)
        self.assertEqual(len(seen),1)
