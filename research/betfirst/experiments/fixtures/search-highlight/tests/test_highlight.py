import unittest
from highlight import mark
class Smoke(unittest.TestCase):
    def test_ascii(self):
        self.assertEqual(mark("hello world","world"),"hello [world]")
if __name__ == "__main__": unittest.main()
