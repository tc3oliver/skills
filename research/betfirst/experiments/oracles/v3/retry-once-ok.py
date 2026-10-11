import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from retry import retry_once
class Oracle(unittest.TestCase):
    def test_one_retry_only(self):
        c=[]
        def always_timeout():c.append(1);raise TimeoutError("slow")
        with self.assertRaises(TimeoutError):retry_once(always_timeout)
        self.assertEqual(len(c),2)
    def test_nontransient_propagates(self):
        c=[]
        def denied():c.append(1);raise PermissionError("no")
        with self.assertRaises(PermissionError):retry_once(denied)
        self.assertEqual(len(c),1)
    def test_success_second_call(self):
        calls=[]
        def flaky():
            calls.append(1)
            if len(calls)==1:raise TimeoutError()
            return "ok"
        self.assertEqual(retry_once(flaky),"ok")
        self.assertEqual(len(calls),2)
if __name__ == "__main__": unittest.main()
