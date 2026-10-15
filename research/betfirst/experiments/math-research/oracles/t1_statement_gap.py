#!/usr/bin/env python3
"""T1 oracle: ANSWER.md must name the almost-all-pins gap and cite Pins.lean / `pins`."""
import re, sys
from pathlib import Path

f = Path(sys.argv[1]) / "ANSWER.md"
if not f.is_file():
    print("FAIL: ANSWER.md missing"); sys.exit(1)
t = f.read_text()
low = t.lower()
checks = {
    "gap: almost-all-pins / epsilon n": re.search(
        r"almost[- ]all|all but|(ε|epsilon)\s*[·*]?\s*n\b|bad pins?|fraction of pins|counting bridge", low),
    "gap: Comparator controls pair fraction": re.search(r"fraction|ordered pairs|rich pairs", low),
    "cites Pins.lean": "Pins.lean" in t,
    "cites theorem pins": re.search(r"theorem `?pins\b|WeakPinned\.pins\b|`pins`", t),
    "says repo bridges it": re.search(r"already|bridg\w+ (it|this|the)|proves?|proved", low),
}
bad = [k for k, v in checks.items() if not v]
if bad:
    print("FAIL: missing " + "; ".join(bad)); sys.exit(1)
print("PASS: ANSWER.md names the almost-all-pins gap and cites Pins.lean theorem pins")
