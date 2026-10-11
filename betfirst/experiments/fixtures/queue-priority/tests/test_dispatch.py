import unittest
from models import Job
from dispatcher import pick
class Smoke(unittest.TestCase):
    def test_single_job(self):
        self.assertEqual(pick([Job("a",1,10)],10).job_id,"a")
if __name__ == "__main__": unittest.main()
