import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from wire import frame
from reader import decode_chunks

class Oracle(unittest.TestCase):
    def test_split_header_and_payload(self):
        packet = frame(b"ok")
        self.assertEqual(decode_chunks([packet[:1], packet[1:3], packet[3:]]),
                         ([b"ok"], b""))
    def test_multiple_frames(self):
        self.assertEqual(decode_chunks([frame(b"a")+frame(b"bc")]),
                         ([b"a", b"bc"], b""))
    def test_partial_trailing_frame(self):
        data = frame(b"xyz") + frame(b"pending")[:4]
        self.assertEqual(decode_chunks([data]), ([b"xyz"], frame(b"pending")[:4]))
    def test_zero_length_frame(self):
        self.assertEqual(decode_chunks([frame(b"")]), ([b""], b""))

if __name__ == "__main__":
    unittest.main()
