import unittest
from intervals import overlaps

class Smoke(unittest.TestCase):
    def test_interior_overlap(self):
        self.assertTrue(overlaps(1,4,3,7))
