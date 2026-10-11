import unittest
from reader import decode_chunks

class Smoke(unittest.TestCase):
    def test_empty_stream(self):
        self.assertEqual(decode_chunks([]), ([], b""))
