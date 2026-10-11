import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from identity import normalize_user, matches
class Oracle(unittest.TestCase):
    def test_full_casefold(self):
        self.assertTrue(matches("Straße","STRASSE"))
        self.assertTrue(matches("ΜΆΪΟΣ","μάϊοσ"))
        self.assertEqual(normalize_user("  Bob  "),"bob")
        self.assertFalse(matches("a b","ab"))
    def test_type(self):
        with self.assertRaises(TypeError):normalize_user(None)
if __name__ == "__main__": unittest.main()
