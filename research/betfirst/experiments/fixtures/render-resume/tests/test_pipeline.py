import unittest

from manifest import RenderManifest
from pipeline import build_timeline
from segments import Segment


class RenderTests(unittest.TestCase):
    def test_render_and_resume_unique_titles(self):
        segments = [Segment("a-1", "Intro", "Hello"), Segment("b-2", "News", "World")]
        manifest = RenderManifest()
        calls = []
        def render(segment):
            calls.append(segment.segment_id)
            return segment.text.upper()
        self.assertEqual(build_timeline(segments, manifest, render), ["HELLO", "WORLD"])
        self.assertEqual(build_timeline(segments, manifest, render), ["HELLO", "WORLD"])
        self.assertEqual(calls, ["a-1", "b-2"])


if __name__ == "__main__":
    unittest.main()
