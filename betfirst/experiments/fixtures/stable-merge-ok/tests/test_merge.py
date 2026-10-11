import unittest
from merge import merge_sorted
class Smoke(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(merge_sorted([1,3],[2,4]),[1,2,3,4])
if __name__ == "__main__": unittest.main()
