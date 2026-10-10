import unittest
from lib import clips_duration


class ClipTests(unittest.TestCase):
    def test_no_change_needed(self):
        self.assertEqual(clips_duration([1.5, 2, 3.5]), 7.0)
        self.assertEqual(clips_duration([]), 0)


if __name__ == "__main__":
    unittest.main()
