import unittest
from paging import page
class Smoke(unittest.TestCase):
    def test_tail(self):
        self.assertEqual(page(["a"],0,2),(["a"],None))
if __name__ == "__main__": unittest.main()
