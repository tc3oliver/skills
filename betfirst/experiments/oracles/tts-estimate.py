"""Independent compatibility checks for the duration pilot."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path.cwd()))
from lib import estimate_seconds


class Oracle(unittest.TestCase):
    def test_measured_rate(self):
        for chars, expected in [(0, 0), (5, 1), (100, 20), (250, 50), (13, 3)]:
            with self.subTest(chars=chars):
                self.assertEqual(estimate_seconds(chars), expected)


if __name__ == "__main__":
    unittest.main()
