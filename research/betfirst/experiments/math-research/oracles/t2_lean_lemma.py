#!/usr/bin/env python3
"""T2 oracle: Fiber.lean compiles in the pinned project, statement and preamble unchanged,
no sorry/admit/axiom, axioms of fiber_bound within the standard three."""
import re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lean_common import compile_lean

PREAMBLE = "import Mathlib"
STATEMENT = ("theorem fiber_bound {α β : Type*} [DecidableEq β] (S : Finset α) (f : α → β) "
             "(T : Finset β) (hT : ∀ a ∈ S, f a ∈ T) (c : ℝ) "
             "(hk : ∀ b ∈ T, ((S.filter fun a => f a = b).card : ℝ) ≤ c) : "
             "(S.card : ℝ) ≤ T.card * c")
OK_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def norm(s):
    return " ".join(s.split())


def strip_comments(s):
    s = re.sub(r"/-.*?-/", " ", s, flags=re.S)
    return re.sub(r"--[^\n]*", "", s)


def fail(msg):
    print("FAIL: " + msg); sys.exit(1)


f = Path(sys.argv[1]) / "Fiber.lean"
if not f.is_file():
    fail("Fiber.lean missing")
src = f.read_text()
code = strip_comments(src)
m = re.search(r"theorem\s+fiber_bound\b", code)
if not m:
    fail("theorem fiber_bound not found")
head = norm(code[:m.start()])
if head != PREAMBLE:
    fail(f"preamble changed: {head[:80]!r}")
m2 = re.compile(r":=").search(code, m.start())
if not m2 or norm(code[m.start():m2.start()]) != STATEMENT:
    fail("theorem statement changed")
if re.search(r"\b(sorry|admit|axiom|native_decide|unsafe|implemented_by|extern)\b", code):
    fail("forbidden token (sorry/admit/axiom/...)")
if len(re.findall(r"\btheorem\s+fiber_bound\b", code)) != 1:
    fail("fiber_bound declared more than once")
with tempfile.TemporaryDirectory() as d:
    g = Path(d) / "Check.lean"
    g.write_text(src + "\n#print axioms fiber_bound\n")
    rc, out = compile_lean(g)
if rc != 0 or re.search(r"error", out):
    fail("does not compile: " + out.strip().splitlines()[0][:200] if out.strip() else "does not compile")
mm = re.search(r"'fiber_bound' depends on axioms: \[(.*?)\]", out, re.S)
axioms = {a.strip() for a in mm.group(1).split(",")} if mm else set()
if not mm and "does not depend on any axioms" not in out:
    fail("no axiom report")
if axioms - OK_AXIOMS:
    fail(f"non-standard axioms: {sorted(axioms - OK_AXIOMS)}")
print(f"PASS: fiber_bound compiles at pinned mathlib, statement unchanged, axioms {sorted(axioms)}")
