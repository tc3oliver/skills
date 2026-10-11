import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class FixtureSmoke(unittest.TestCase):
    def test_original_behavior(self):
        from solution import encode_frame
        assert encode_frame('a') == b'\x00\x01a'
