import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from cache import ScopedCache

class Oracle(unittest.TestCase):
    def test_cross_namespace(self):
        c=ScopedCache()
        self.assertEqual(c.get("east","x",lambda ns,key: "E"), "E")
        self.assertEqual(c.get("west","x",lambda ns,key: "W"), "W")
    def test_same_scope_memoizes(self):
        c=ScopedCache()
        calls=[]
        def loader(ns,key):
            calls.append((ns,key))
            return 1
        self.assertEqual(c.get("east","y",loader),1)
        self.assertEqual(c.get("east","y",loader),1)
        self.assertEqual(calls,[("east","y")])
    def test_distinct_ids_and_case_sensitive_namespace(self):
        c=ScopedCache()
        self.assertEqual(c.get("east","a",lambda ns,key: 1),1)
        self.assertEqual(c.get("east","b",lambda ns,key: 2),2)
        self.assertEqual(c.get("East","a",lambda ns,key: 3),3)

if __name__ == "__main__":
    unittest.main()
