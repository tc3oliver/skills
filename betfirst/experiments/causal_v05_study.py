#!/usr/bin/env python3
"""Run the frozen v0.5 causal comparison; never modify prior v0.3/v0.4 evidence."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

from run import execute, load_suite

HERE = Path(__file__).resolve().parent
SUITE = HERE / "suite-v05.json"
MODEL = "opencode-go/muse-spark-1.3-contributor"
ARMS = ("efficiency", "betfirst-v04", "betfirst-v04-nobet")
SEED = 20261011 + 5


def preflight() -> None:
    tasks = load_suite(SUITE)
    if len(tasks) != 12 or {t["difficulty"] for t in tasks} != {"bet-win", "bet-loss", "normal"}:
        raise RuntimeError("v05 cohort must contain exactly 12 tasks of three types")
    if any(sum(t["difficulty"] == kind for t in tasks) != 4 for kind in ("bet-win", "bet-loss", "normal")):
        raise RuntimeError("v05 cohort is unbalanced")
    for task in tasks:
        cwd = SUITE.parent / task["fixture"]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "work"
            shutil.copytree(cwd, work)
            visible = subprocess.run(task["check"], cwd=work, capture_output=True, text=True, timeout=10)
            env = os.environ.copy()
            env["PYTHONPATH"] = str(work) + os.pathsep + env.get("PYTHONPATH", "")
            oracle = subprocess.run([sys.executable, str(SUITE.parent / task["oracle"])],
                                    cwd=work, env=env, capture_output=True, text=True, timeout=10)
            if visible.returncode != 0 or "Ran 0 tests" in visible.stderr:
                raise RuntimeError(f"Invalid visible tests {task['id']}: {visible.stderr}")
            if oracle.returncode == 0:
                raise RuntimeError(f"Oracle fails to detect pristine defect: {task['id']}")
            if "ModuleNotFoundError" in oracle.stderr or "ImportError" in oracle.stderr:
                raise RuntimeError(f"Broken Oracle imports in {task['id']}: {oracle.stderr}")
    print("Frozen v05 preflight PASS (12 visible checks pass, 12 hidden oracles detect defects)", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--hours", type=float, default=2.0)
    p.add_argument("--replicates", type=int, default=2)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--acknowledge-isolation", action="store_true")
    args = p.parse_args()
    if not (0 < args.hours <= 4) or args.replicates != 2:
        p.error("frozen design: 0 < hours <= 4, replicates must be exactly 2")
    if not args.acknowledge_isolation:
        p.error("Requires actual OS isolation; --acknowledge-isolation is not a sandbox")
    preflight()
    out = args.output.expanduser().resolve()
    rows = execute(
        SUITE.resolve(), out, "opencode", MODEL,
        replicates=args.replicates, seed=SEED, timeout=180, execute_real=True,
        selected_arms=list(ARMS), paired=True, tool_profile="diagnostic",
        acknowledge_isolation=True, max_turns=30,
        verification_timeout=30, time_budget_seconds=round(args.hours * 3600),
        resume=args.resume,
    )
    print(f"Evidence: {out}", flush=True)
    print(f"Completed sessions: {len(rows)}/72", flush=True)
    print("Run analyze_v05.py on this directory; only compare complete three-arm groups.", flush=True)


if __name__ == "__main__":
    main()
