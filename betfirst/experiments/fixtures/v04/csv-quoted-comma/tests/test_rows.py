import unittest
from rows import parse_row

class Smoke(unittest.TestCase):
    def test_simple_columns(self):
        self.assertEqual(parse_row("alpha,beta,\n"), ["alpha", "beta", ""])
