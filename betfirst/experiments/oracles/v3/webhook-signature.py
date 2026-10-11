import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import hashlib, hmac
from verify import verify
class Oracle(unittest.TestCase):
    def test_valid_signatures_and_tamper(self):
        sig="sha256="+hmac.new(b"key",b"payload",hashlib.sha256).hexdigest()
        self.assertTrue(verify(b"key",b"payload",sig))
        self.assertFalse(verify(b"wrong",b"payload",sig))
        self.assertFalse(verify(b"key",b"tampered",sig))
    def test_bad_formats(self):
        digest=hmac.new(b"k",b"x",hashlib.sha256).hexdigest()
        for value in (digest,"SHA256="+digest,"sha256="+digest+" ","sha256="+digest+"0"):
            self.assertFalse(verify(b"k",b"x",value))
if __name__ == "__main__": unittest.main()
