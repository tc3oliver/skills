import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from ledger import Ledger
from gateway import post_debit
class Oracle(unittest.TestCase):
    def test_idempotent_and_scoped(self):
        l=Ledger({"a":100,"b":100})
        x=post_debit(l,"a","request",30)
        self.assertEqual(post_debit(l,"a","request",30),x)
        self.assertEqual(l.balances["a"],70)
        self.assertEqual(post_debit(l,"b","request",30)[-1],70)
        self.assertEqual(l.balances["b"],70)
    def test_reuse_with_changed_amount_is_rejected(self):
        l=Ledger({"a":40});l.debit("a","id",5)
        with self.assertRaises(ValueError):l.debit("a","id",6)
        self.assertEqual(l.balances["a"],35)
    def test_reject_insufficient_without_recording(self):
        l=Ledger({"a":1})
        with self.assertRaises(ValueError):l.debit("a","id",2)
        self.assertEqual(l.receipts,{})
if __name__ == "__main__": unittest.main()
