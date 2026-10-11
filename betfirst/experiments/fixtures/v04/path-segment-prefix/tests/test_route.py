import unittest
from route import is_under

class Smoke(unittest.TestCase):
    def test_child_path(self):
        self.assertTrue(is_under("/api/users", "/api"))
