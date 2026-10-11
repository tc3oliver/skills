import unittest
from ledger import Ledger
class Smoke(unittest.TestCase):
    def test_fresh_debit(self):
        ledger=Ledger({"a":50})
        self.assertEqual(ledger.debit("a","x",10)[-1],40)
if __name__ == "__main__": unittest.main()
