#!/usr/bin/env python3
"""Assemble the t1-statement-gap fixture from pinned upstream clones.

Third-party files (OpenAI model-produced Lean sources, awards catalog text) are copied at
run time instead of being committed. Usage:
  fetch_fixtures.py --math PATH/TO/openai-math --awards PATH/TO/awards [--out bench/fixtures]
Each clone must be checked out at the pinned commit below.
"""
from __future__ import annotations

import argparse, re, shutil, subprocess, sys
from pathlib import Path

MATH_SHA = "1581d4cbdd69a0faf34b2089614fe2a814316a6a"
AWARDS_SHA = "fd8fa66abb4e21df828fdebc25298e9ad75521bd"


def head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--math", type=Path, required=True)
    ap.add_argument("--awards", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "fixtures")
    a = ap.parse_args()
    for repo, sha in ((a.math, MATH_SHA), (a.awards, AWARDS_SHA)):
        if head(repo) != sha:
            sys.exit(f"{repo} is not at pinned commit {sha}")
    t1 = a.out / "t1-statement-gap"
    for sub in ("ComparatorChallenges", "OAI"):
        shutil.rmtree(t1 / sub, ignore_errors=True)
    (t1 / "ComparatorChallenges").mkdir(parents=True)
    for name in ("PinnedDistances.lean", "PinnedDistances.json"):
        shutil.copy2(a.math / "lean/ComparatorChallenges" / name, t1 / "ComparatorChallenges" / name)
    shutil.copytree(a.math / "lean/OAI/Geometry/PinnedDistances", t1 / "OAI/Geometry/PinnedDistances")
    catalog = (a.awards / "problems/catalog-1001-1022.md").read_text(encoding="utf-8")
    m = re.search(r'<a id="JSP-001061"></a>.*?(?=<a id="JSP-001062"></a>)', catalog, re.S)
    if not m:
        sys.exit("JSP-001061 record not found")
    (t1 / "catalog-JSP-001061.md").write_text(m.group(0).rstrip() + "\n", encoding="utf-8")
    print(f"t1 fixture assembled in {t1}")


if __name__ == "__main__":
    main()
