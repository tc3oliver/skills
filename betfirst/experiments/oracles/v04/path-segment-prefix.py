import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from route import is_under

class Oracle(unittest.TestCase):
    def test_exact_and_child(self):
        self.assertTrue(is_under("/api", "/api"))
        self.assertTrue(is_under("/api/users", "/api"))
    def test_segment_collision(self):
        self.assertFalse(is_under("/apix", "/api"))
        self.assertFalse(is_under("/api-v2", "/api"))
    def test_root_and_trailing_slash(self):
        self.assertTrue(is_under("/docs", "/"))
        self.assertTrue(is_under("/api/users", "/api/"))
        self.assertFalse(is_under("/apix", "/api/"))
    def test_unrelated(self):
        self.assertFalse(is_under("/web", "/api"))

if __name__ == "__main__":
    unittest.main()
