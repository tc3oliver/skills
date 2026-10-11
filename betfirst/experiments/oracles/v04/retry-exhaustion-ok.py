import os
import sys
import unittest

sys.path.insert(0, os.getcwd())
from retry import retry_once

class Oracle(unittest.TestCase):
    def test_single_transient_failure_retried_once(self):
        calls=[]
        def op():
            calls.append(1)
            if len(calls) == 1:
                raise TimeoutError()
            return "ok"
        self.assertEqual(retry_once(op),"ok")
        self.assertEqual(len(calls),2)
    def test_two_failures_stop_at_two(self):
        calls=[]
        def op():
            calls.append(1)
            raise TimeoutError()
        with self.assertRaises(TimeoutError):
            retry_once(op)
        self.assertEqual(len(calls),2)
    def test_non_transient_not_retried(self):
        calls=[]
        def op():
            calls.append(1)
            raise ValueError()
        with self.assertRaises(ValueError):
            retry_once(op)
        self.assertEqual(len(calls),1)

if __name__ == "__main__":
    unittest.main()
