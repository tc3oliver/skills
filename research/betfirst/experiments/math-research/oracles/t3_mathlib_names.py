#!/usr/bin/env python3
"""T3 oracle: NAMES.txt lines `N: name`; each name must prove its requested statement via `exact`."""
import re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lean_common import compile_lean

HEADER = "import Mathlib\nopen Filter Topology\n"
STMTS = {
    1: "∀ {α β : Type} [DecidableEq β] {s : Finset α} {t : α → Finset β}, "
       "(s.biUnion t).card ≤ s.sum (fun a => (t a).card)",
    2: "∀ {x : ℝ}, 0 < x → ∀ (y z : ℝ), x ^ (y + z) = x ^ y * x ^ z",
    3: "∀ {f g : ℕ → ℝ}, (∀ᶠ n in atTop, 0 ≤ f n) → (∀ᶠ n in atTop, f n ≤ g n) → "
       "Tendsto g atTop (𝓝 0) → Tendsto f atTop (𝓝 0)",
    4: "Tendsto (fun n : ℕ => (n : ℝ)) atTop atTop",
    5: "∀ {y : ℝ}, 0 < y → Tendsto (fun x : ℝ => x ^ (-y)) atTop (𝓝 0)",
}
f = Path(sys.argv[1]) / "NAMES.txt"
if not f.is_file():
    print("FAIL: NAMES.txt missing"); sys.exit(1)
names = {}
for line in f.read_text().splitlines():
    m = re.match(r"\s*(\d+)\s*[:.)-]\s*`?([A-Za-z_][\w.'!?]*)`?\s*$", line)
    if m:
        names[int(m.group(1))] = m.group(2)
lines, lineno = [HEADER.rstrip("\n")], {}
for i, st in STMTS.items():
    if i in names:
        lines.append(f"example : {st} := by exact {names[i]}")
        lineno[len(lines) + 1] = i  # header is 2 lines
with tempfile.TemporaryDirectory() as d:
    g = Path(d) / "Names.lean"
    g.write_text("\n".join(lines) + "\n")
    rc, out = compile_lean(g)
bad = {i for i in STMTS if i not in names}
for m in re.finditer(r"Names\.lean:(\d+):\d+: error", out):
    bad.add(lineno.get(int(m.group(1)), -1))
if bad:
    print(f"FAIL: facts not resolved or wrong shape: {sorted(bad)}"); sys.exit(1)
print("PASS: " + ", ".join(f"{i}={names[i]}" for i in sorted(names)))
