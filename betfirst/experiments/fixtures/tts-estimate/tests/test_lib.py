import unittest
from lib import estimate_seconds


class TTSEstimateTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(estimate_seconds(100), 20)
        self.assertEqual(estimate_seconds(125), 25)


if __name__ == "__main__":
    unittest.main()
