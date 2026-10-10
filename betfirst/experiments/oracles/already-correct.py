"""Independent no-change checks."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path.cwd()))
from lib import clips_duration


class Oracle(unittest.TestCase):
    def test_duration(self):
        self.assertAlmostEqual(clips_duration([0.1, 0.2, 0.3]), 0.6)
        self.assertEqual(clips_duration([1, 2, 3]), 6)
        self.assertEqual(clips_duration([]), 0)


if __name__ == "__main__":
    unittest.main()
