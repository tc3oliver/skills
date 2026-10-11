import unittest
from identity import matches
class Smoke(unittest.TestCase):
    def test_ascii(self):
        self.assertTrue(matches(" ALICE ","alice"))
        self.assertFalse(matches("a b","ab"))
if __name__ == "__main__": unittest.main()
