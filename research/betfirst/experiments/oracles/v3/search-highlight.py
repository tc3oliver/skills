import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from highlight import mark
from tokens import token_start
class Oracle(unittest.TestCase):
    def test_unicode_offsets(self):
        self.assertEqual(mark("科技新聞 AI 新模型","AI"),"科技新聞 [AI] 新模型")
        self.assertEqual(mark("café noir café","noir"),"café [noir] café")
        self.assertEqual(token_start("λβ world","world"),3)
    def test_first_occurrence_and_no_match(self):
        self.assertEqual(mark("go go","go"),"[go] go")
        self.assertEqual(mark("mañana","xyz"),"mañana")
if __name__ == "__main__": unittest.main()
