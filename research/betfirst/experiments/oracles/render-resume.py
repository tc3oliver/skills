"""Independent black-box acceptance; not copied into an agent workspace."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path.cwd()))

from manifest import RenderManifest
from pipeline import build_timeline
from segments import Segment


class Oracle(unittest.TestCase):
    def test_same_title_different_ids_and_reordering(self):
        segments = [
            Segment("2026-10-01/001", "AI Update", "Story one"),
            Segment("2026-10-01/002", "AI Update", "Story two"),
            Segment("2026-10-01/003", "Wrap", "Summary"),
        ]
        manifest, rendered = RenderManifest(), []
        def render(seg):
            rendered.append(seg.segment_id)
            return seg.text + "@" + seg.segment_id
        expected = [s.text + "@" + s.segment_id for s in segments]
        self.assertEqual(build_timeline(segments, manifest, render), expected)
        self.assertEqual(build_timeline(list(reversed(segments)), manifest, render),
                         list(reversed(expected)))
        self.assertEqual(len(rendered), 3, "All completed segments must be reused")

    def test_crash_retry_does_not_skip_unfinished(self):
        segs = [Segment("a", "News", "A"), Segment("b", "News", "B")]
        manifest, calls = RenderManifest(), []
        def flaky(s):
            calls.append(s.segment_id)
            if s.segment_id == "b" and calls.count("b") == 1:
                raise RuntimeError("renderer interrupted")
            return "out-" + s.segment_id
        with self.assertRaises(RuntimeError):
            build_timeline(segs, manifest, flaky)
        self.assertEqual(build_timeline(segs, manifest, flaky), ["out-a", "out-b"])
        self.assertEqual(calls, ["a", "b", "b"])


if __name__ == "__main__":
    unittest.main()
