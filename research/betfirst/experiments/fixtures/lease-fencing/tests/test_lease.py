import unittest
from lease import LeaseStore
class Smoke(unittest.TestCase):
    def test_first_acquire(self):
        store=LeaseStore();self.assertEqual(store.acquire("x","a",0,10),1)
if __name__ == "__main__": unittest.main()
