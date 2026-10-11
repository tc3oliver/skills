import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from intervals import overlaps

class Oracle(unittest.TestCase):
    def test_touching_is_not_overlap(self):
        self.assertFalse(overlaps(0,4,4,8))
        self.assertFalse(overlaps(4,8,0,4))
    def test_actual_overlap_and_nested(self):
        self.assertTrue(overlaps(0,4,3,5))
        self.assertTrue(overlaps(0,9,2,4))
    def test_empty(self):
        self.assertFalse(overlaps(3,3,3,8))
    def test_reversed_rejected(self):
        with self.assertRaises(ValueError):
            overlaps(2,1,0,3)

if __name__ == "__main__":
    unittest.main()
