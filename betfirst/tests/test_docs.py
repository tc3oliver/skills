"""Validate BetFirst's bilingual GitHub landing pages and lightweight assets."""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
EXPECTED_SVGS = ("hero.svg", "decision-flow.svg", "before-after.svg", "x-cover.svg", "x-explainer.svg")
EMBEDDED = ("hero.svg", "before-after.svg")
SVG_NS = "{http://www.w3.org/2000/svg}"


def read_gif_frames(path: Path):
    """Inspect GIF container and decode the first raster with stdlib only."""
    data = path.read_bytes()
    if data[:6] != b"GIF89a":
        raise ValueError("GIF89a header required")
    width = int.from_bytes(data[6:8], "little")
    height = int.from_bytes(data[8:10], "little")
    if not (400 <= width <= 1200 and 150 <= height <= 600):
        raise ValueError("unexpected GIF canvas")
    pos = 13
    packed = data[10]
    if packed & 0x80:
        pos += 3 * (2 ** ((packed & 7) + 1))
    frames = []
    while pos < len(data):
        kind = data[pos]
        pos += 1
        if kind == 0x3B:
            if pos != len(data):
                raise ValueError("trailing bytes after GIF trailer")
            break
        if kind == 0x21:
            pos += 1  # extension label
            while True:
                block = data[pos]
                pos += 1
                if not block:
                    break
                pos += block
            continue
        if kind != 0x2C:
            raise ValueError(f"unknown GIF marker at {pos - 1}: {kind}")
        left, top = int.from_bytes(data[pos:pos+2], "little"), int.from_bytes(data[pos+2:pos+4], "little")
        fw, fh = int.from_bytes(data[pos+4:pos+6], "little"), int.from_bytes(data[pos+6:pos+8], "little")
        flags = data[pos+8]
        pos += 9
        if flags & 0x80:
            pos += 3 * (2 ** ((flags & 7) + 1))
        code_min = data[pos]
        pos += 1
        chunks = bytearray()
        while True:
            block = data[pos]
            pos += 1
            if not block:
                break
            chunks.extend(data[pos:pos+block])
            pos += block
        if left + fw > width or top + fh > height or not fw or not fh:
            raise ValueError("GIF frame out of bounds")
        frames.append((code_min, bytes(chunks), fw * fh))
    else:
        raise ValueError("missing GIF trailer")
    if len(frames) < 6:
        raise ValueError("expected a real multi-frame illustrative animation")
    return frames


def decode_gif_lzw(min_bits: int, encoded: bytes, expected: int):
    """Check that the GIF's first/last raster really decompress to pixel indices."""
    clear, end = 1 << min_bits, (1 << min_bits) + 1
    size, next_code = min_bits + 1, end + 1
    dictionary = {i: bytes([i]) for i in range(clear)}
    bit_pos = 0
    output = bytearray()
    previous = None
    while bit_pos + size <= len(encoded) * 8:
        byte_at = bit_pos // 8
        window = int.from_bytes(encoded[byte_at:byte_at+3], "little")
        code = (window >> (bit_pos % 8)) & ((1 << size) - 1)
        bit_pos += size
        if code == clear:
            dictionary = {i: bytes([i]) for i in range(clear)}
            size, next_code, previous = min_bits + 1, end + 1, None
            continue
        if code == end:
            break
        if code in dictionary:
            entry = dictionary[code]
        elif code == next_code and previous is not None:
            entry = previous + previous[:1]
        else:
            raise ValueError("invalid GIF LZW code")
        output.extend(entry)
        if previous is not None and next_code < 4096:
            dictionary[next_code] = previous + entry[:1]
            next_code += 1
            if next_code == (1 << size) and size < 12:
                size += 1
        previous = entry
    if len(output) != expected:
        raise ValueError(f"GIF decoded {len(output)} pixels; expected {expected}")
    return output


class ReadmeAndAssetTests(unittest.TestCase):
    def test_svg_assets_are_standalone_valid_xml(self):
        for name in EXPECTED_SVGS:
            with self.subTest(asset=name):
                asset = ASSETS / name
                self.assertTrue(asset.is_file())
                tree = ET.parse(asset)
                svg = tree.getroot()
                self.assertEqual(svg.tag, SVG_NS + "svg")
                self.assertTrue(svg.attrib.get("viewBox"))
                self.assertTrue(svg.find(SVG_NS + "title") is not None)
                self.assertTrue(svg.find(SVG_NS + "desc") is not None)
                source = asset.read_text(encoding="utf-8")
                self.assertNotIn("<foreignObject", source)
                self.assertNotIn("http://www.w3.org", source.replace('xmlns="http://www.w3.org/2000/svg"', ""))
                self.assertNotIn("data:image", source)
                self.assertNotIn("<script", source)

    def test_real_multiframe_gif_decodes(self):
        frames = read_gif_frames(ASSETS / "probe-loop.gif")
        for index in (0, -1):
            with self.subTest(frame=index):
                bits, block, area = frames[index]
                decode_gif_lzw(bits, block, area)
        self.assertLess((ASSETS / "probe-loop.gif").stat().st_size, 200_000)

    def test_both_languages_have_product_first_readmes(self):
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (ROOT / "README.zh-TW.md").read_text(encoding="utf-8")
        for label, content in (("English", english), ("Traditional Chinese", chinese)):
            with self.subTest(readme=label):
                self.assertIn("README.md", content)
                self.assertIn("README.zh-TW.md", content)
                self.assertIn("Claude Code", content)
                self.assertIn("Pi", content)
                self.assertNotIn("X 發文圖片與草稿", content)
                self.assertIn("experiments/EXPERIMENT_HISTORY.md", content)
                self.assertIn("experiments/V3_PROTOCOL.md", content)
                self.assertIn("docs/WHY_BETFIRST.md", content)
                for img in EMBEDDED:
                    self.assertIn("./assets/" + img, content)
                self.assertIn("33.8%", content)
                self.assertIn("38.0%", content)
                self.assertIn("12", content)
                self.assertNotIn("v3 has not run yet", content)
                self.assertNotIn("EXPERIMENTAL v0.1", content)
        self.assertIn("exploratory study", english)
        self.assertIn("探索性測試", chinese)
        self.assertIn("no published results yet", english)
        self.assertIn("尚未公布結果", chinese)
        self.assertIn("Make Cheap Bets. Win Big. Lose Small.", english)
        self.assertIn("Make Cheap Bets. Win Big. Lose Small.", chinese)
        self.assertIn("full PoC", english)
        self.assertIn("完整 PoC", chinese)
        self.assertIn("skip only", english)
        self.assertIn("不再必要", chinese)
        self.assertIn("Never gamble with correctness", english)
        self.assertIn("不是程式正確性", chinese)
        self.assertNotIn("X_MEDIA_KIT.md", english)
        self.assertNotIn("X_MEDIA_KIT.md", chinese)
        self.assertNotIn("X launch visuals", english)
        self.assertNotIn("X 發文圖片與草稿", chinese)
        self.assertIn("Ready to try it?", english)
        self.assertIn("下一個問題，先試一個小賭注", chinese)
        self.assertNotIn("Your coding agent is already making bets", english)
        self.assertNotIn("你的 Coding Agent 其實一直都在下注", chinese)
        for asset in ("x-cover.svg", "x-explainer.svg"):
            self.assertTrue((ASSETS / asset).is_file())
        root = (ROOT.parent / "README.md").read_text(encoding="utf-8")
        self.assertIn("complete PoC", root)
        self.assertIn("Make Cheap Bets. Win Big. Lose Small.", root)

    def test_x_cards_are_full_size_and_accurately_labeled(self):
        for name in ("x-cover.svg", "x-explainer.svg"):
            with self.subTest(name=name):
                root = ET.parse(ASSETS / name).getroot()
                self.assertEqual(root.attrib["viewBox"], "0 0 1600 900")
                self.assertEqual(root.attrib["width"], "1600")
                self.assertEqual(root.attrib["height"], "900")
        media_kit = (ROOT / "docs" / "X_MEDIA_KIT.md").read_text(encoding="utf-8")
        self.assertIn("not measured", media_kit.lower())
        self.assertIn("cairosvg", media_kit)
        for asset in ("x-cover.svg", "x-explainer.svg"):
            self.assertIn(asset, media_kit)

    def test_local_readme_asset_references_resolve(self):
        for name in ("README.md", "README.zh-TW.md"):
            source = (ROOT / name).read_text(encoding="utf-8")
            refs = re.findall(r'src="(\./assets/[^"]+)"', source)
            self.assertEqual(len(refs), len(EMBEDDED))
            for ref in refs:
                self.assertTrue((ROOT / ref).is_file(), ref)


if __name__ == "__main__":
    unittest.main()
