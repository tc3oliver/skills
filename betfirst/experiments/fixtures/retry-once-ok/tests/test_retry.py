import unittest
from retry import retry_once
class Smoke(unittest.TestCase):
    def test_success(self):
        self.assertEqual(retry_once(lambda:3),3)
if __name__ == "__main__": unittest.main()
