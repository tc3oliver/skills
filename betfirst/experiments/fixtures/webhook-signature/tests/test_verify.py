import unittest
from verify import verify
class Smoke(unittest.TestCase):
    def test_wrong_input(self):
        self.assertFalse(verify(b"x",b"body","not-valid"))
if __name__ == "__main__": unittest.main()
