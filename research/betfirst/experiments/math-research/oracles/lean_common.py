"""Shared Lean runner for oracles: compile a file against the pinned lean/ project."""
import os, subprocess, sys

# Pinned Lean project (Lean v4.34.1 + mathlib d13f23b); see ../lean-project/.
LEAN = os.environ["JSP_LEAN_PROJECT"]
LAKE = [os.environ.get("LAKE", "lake"), "+leanprover/lean4:v4.34.1", "-d", LEAN, "env", "lean"]


def compile_lean(path, timeout=600):
    p = subprocess.run(LAKE + [str(path)], capture_output=True, text=True, timeout=timeout,
                       env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.path.expanduser("~")})
    return p.returncode, p.stdout + p.stderr
