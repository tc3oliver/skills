import unittest
from lib import subtitle_filter_path


class SubtitleTests(unittest.TestCase):
    def test_windows_drive(self):
        self.assertEqual(subtitle_filter_path("C:\\media\\input.srt"), "C\\:/media/input.srt")

    def test_posix(self):
        self.assertEqual(subtitle_filter_path("/tmp/input.srt"), "/tmp/input.srt")


if __name__ == "__main__":
    unittest.main()
