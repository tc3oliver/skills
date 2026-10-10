"""Independent compatibility checks for the subtitle-path pilot."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path.cwd()))
from lib import subtitle_filter_path


class Oracle(unittest.TestCase):
    def test_drive_paths(self):
        self.assertEqual(subtitle_filter_path("C:\\media\\input.srt"), "C\\:/media/input.srt")
        self.assertEqual(subtitle_filter_path("d:/media/x.srt"), "d\\:/media/x.srt")
        self.assertEqual(subtitle_filter_path("Z:\\m\\x.srt"), "Z\\:/m/x.srt")

    def test_non_drive_paths(self):
        self.assertEqual(subtitle_filter_path("/tmp/a:b.srt"), "/tmp/a:b.srt")
        self.assertEqual(subtitle_filter_path("rel\\sub.srt"), "rel/sub.srt")
        self.assertEqual(subtitle_filter_path("long:filename"), "long:filename")


if __name__ == "__main__":
    unittest.main()
