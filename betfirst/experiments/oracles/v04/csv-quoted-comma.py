import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from rows import parse_row

class Oracle(unittest.TestCase):
    def test_quoted_comma(self):
        self.assertEqual(parse_row('"east,west",north'), ["east,west", "north"])
    def test_escaped_quotes(self):
        self.assertEqual(parse_row('"a""b",z'), ['a"b', "z"])
    def test_empty_last_and_linebreak(self):
        self.assertEqual(parse_row("a,b,\r\n"), ["a","b",""])
    def test_unquoted(self):
        self.assertEqual(parse_row("x,y"), ["x","y"])

if __name__ == "__main__":
    unittest.main()
