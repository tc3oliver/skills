#!/usr/bin/env python3
"""OpenCode Go / Muse two-stage coding-agent evaluation.

1. Smoke: one short buggy fixture to verify OpenCode tools, trace and scoring.
2. Study: same model and two arms, randomized adjacent pairs, <= 2h wall time.

This is exploratory and does NOT amend or regrade the frozen v3 study.
All work must run in a separate OS-isolated account/VM against public fixtures.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from run import execute

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUITE = HERE / "suite-v3.json"
MODEL = "opencode-go/muse-spark-1.3-contributor"
ARMS = ("efficiency", "betfirst")
SMOKE_TASKS = ("cursor-pagination",)
SMOKE_ARMS = ("betfirst",)
SEED = 20261011


def verify_smoke(folder: Path) -> tuple[bool, list[str]]:
    """Lightweight wiring gate: did a real coding agent, tools and judges run?

    This is NOT a skill correctness gate. Oracle FAIL remains in the
    evidence and is a legitimate result for the subsequent 2h study.
    """
    failures = []
    try:
        manifest = json.loads((folder / "manifest.json").read_text())
        with (folder / "measured-runs.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except (OSError, ValueError) as exc:
        return False, [f"missing/invalid smoke evidence: {exc}"]

    expected = {
        "driver": "opencode", "model": MODEL, "synthetic": False,
        "selected_arms": list(SMOKE_ARMS), "selected_task_ids": list(SMOKE_TASKS),
        "replicates": 1, "runs": 1,
        "opencode_tool_profile": "diagnostic",
        "skill_sha256": hashlib.sha256(
            (ROOT / "betfirst" / "SKILL.md").read_bytes()).hexdigest(),
        "suite_sha256": hashlib.sha256(SUITE.read_bytes()).hexdigest(),
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            failures.append(f"manifest {key}: mismatch")

    expected_id = f"{SMOKE_TASKS[0]}-r1-{SMOKE_ARMS[0]}"
    if len(rows) != 1:
        failures.append(f"expected one completed smoke session; got {len(rows)}")
        return False, failures
    row = rows[0]
    rid = f"{row.get('task_id')}-r{row.get('replicate')}-{row.get('arm')}"
    if rid != expected_id:
        failures.append(f"unexpected smoke session {rid}")

    try:
        outcome = json.loads((folder / rid / "outcome.json").read_text())
        trace = json.loads((folder / rid / "trace_summary.json").read_text())
    except (OSError, ValueError) as exc:
        failures.append(f"missing outcome/trace: {exc}")
        return False, failures

    if outcome.get("agent_exit") != 0 or outcome.get("agent_timeout"):
        failures.append("OpenCode process did not finish cleanly")
    if outcome.get("agent_subtype") in ("error_max_turns", "error_missing_trace", "error_runtime"):
        failures.append("OpenCode returned an execution error")
    if outcome.get("acceptance_exit") is None or outcome.get("oracle_exit") is None:
        failures.append("acceptance or independent Oracle was not executed")
    if not isinstance(trace.get("agent_turns"), int) or trace["agent_turns"] < 1:
        failures.append("missing model steps in real JSONL trace")
    if not isinstance(trace.get("tool_calls"), int) or trace["tool_calls"] < 1:
        failures.append("no tool invocation observed; file/tool adapter untested")

    # Intentionally do NOT demand oracle/acceptance PASS here: that is the
    # measured strategy outcome, not evidence of CLI/driver wiring failure.
    return not failures, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("smoke", "study", "launch"):
        p = sub.add_parser(mode)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--acknowledge-isolation", action="store_true",
                       help="I am using an OS-isolated test user/VM with no private source or host credentials")
        if mode in ("study", "launch"):
            if mode == "study":
                p.add_argument("--smoke-dir", type=Path, required=True,
                               help="Completed lightweight smoke using the same candidate Skill")
            p.add_argument("--hours", type=float, default=2.0,
                           help="Maximum wall time (default/maximum: 2h)")
            if mode == "study":
                p.add_argument("--resume", action="store_true",
                               help="Resume same time budget and manifest; never restart the clock")
    args = parser.parse_args()
    if not args.acknowledge_isolation:
        parser.error("--acknowledge-isolation required: OpenCode permissions do not sandbox Python")
    if args.mode in ("study", "launch"):
        if not 0 < args.hours <= 2:
            parser.error("--hours must be greater than 0 and no more than 2")

    if args.mode == "launch":
        root = args.output.resolve()
        if root.exists() and any(root.iterdir()):
            parser.error("launch output directory must be empty or new")
        root.mkdir(parents=True, exist_ok=True)
        smoke_dir, study_dir = root / "smoke", root / "study"
        print("Stage 1: one real Muse coding-agent smoke session", flush=True)
        run_smoke(smoke_dir)
        ok, issues = verify_smoke(smoke_dir)
        if not ok:
            print("NO-GO: driver smoke did not complete correctly.")
            for issue in issues:
                print(" -", issue)
            return 2
        print("SMOKE PASS (driver/tools verified; task correctness evaluated in study).")
        return run_study(study_dir, args.hours)

    if args.mode == "study":
        smoke_dir = args.smoke_dir.resolve()
        approved, issues = verify_smoke(smoke_dir)
        if not approved:
            print("NO-GO: smoke did not establish working OpenCode tools.")
            for issue in issues:
                print(" -", issue)
            return 2
        if args.output.resolve() == smoke_dir:
            parser.error("study --output must differ from smoke evidence directory")
        return run_study(args.output.resolve(), args.hours, resume=args.resume)

    run_smoke(args.output.resolve())
    approved, issues = verify_smoke(args.output.resolve())
    if not approved:
        print("NO-GO: driver smoke failed; keep evidence for diagnosis.")
        for issue in issues:
            print(" -", issue)
        return 2
    print("SMOKE PASS: OpenCode, tools, acceptance and Oracle ran.")
    print("Task correctness is deliberately NOT a smoke gate.")
    return 0


def run_smoke(folder: Path) -> None:
    execute(
        SUITE.resolve(), folder, "opencode", MODEL,
        replicates=1, seed=SEED, timeout=150, execute_real=True,
        selected_tasks=list(SMOKE_TASKS), tool_profile="diagnostic",
        acknowledge_isolation=True, max_turns=25,
        selected_arms=list(SMOKE_ARMS), verification_timeout=20,
    )


def run_study(folder: Path, hours: float, *, resume: bool = False) -> int:
    print(f"Stage 2: up to {hours:g}h Efficiency vs BetFirst paired study",
          flush=True)
    execute(
        SUITE.resolve(), folder, "opencode", MODEL,
        replicates=24, seed=SEED, timeout=180, execute_real=True,
        tool_profile="diagnostic", acknowledge_isolation=True,
        max_turns=30, resume=resume,
        selected_arms=list(ARMS), paired=True,
        time_budget_seconds=round(hours * 3600),
        verification_timeout=30,
    )
    print(f"Study evidence: {folder}", flush=True)
    print("Inspect budget-status.json and measured-runs.csv (matched pairs only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
