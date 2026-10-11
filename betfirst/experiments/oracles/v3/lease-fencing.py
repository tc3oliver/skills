import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from lease import LeaseStore
class Oracle(unittest.TestCase):
    def test_stale_and_expired(self):
        s=LeaseStore();t1=s.acquire("job","alice",0,10)
        self.assertIsNone(s.acquire("job","bob",9,10))
        t2=s.acquire("job","bob",10,10)
        with self.assertRaises(ValueError):s.commit("job","alice",t1,"stale",11)
        self.assertEqual(s.commit("job","bob",t2,"current",11),"current")
        with self.assertRaises(ValueError):s.commit("job","bob",t2,"too late",21)
        self.assertEqual(s.results["job"],"current")
    def test_old_token_with_same_owner(self):
        s=LeaseStore();a=s.acquire("j","w",0,1);b=s.acquire("j","w",2,3)
        with self.assertRaises(ValueError):s.commit("j","w",a,"bad",3)
        self.assertEqual(s.commit("j","w",b,"good",3),"good")
if __name__ == "__main__": unittest.main()
