import unittest
from retry import retry_once

class Smoke(unittest.TestCase):
    def test_first_attempt_success(self):
        self.assertEqual(retry_once(lambda: 5), 5)
