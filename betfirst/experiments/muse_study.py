#!/usr/bin/env python3
"""OpenCode Go / Muse two-stage coding-agent evaluation.

1. Smoke: one buggy fixture + one already-correct fixture, two strategy arms.
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
SMOKE_TASKS = ("cursor-pagination", "ttl-boundary-ok")
SEED = 20261011


def verify_smoke(folder: Path) -> tuple[bool, list[str]]:
    """Check accepted, completed, hash-matched smoke evidence, not just exit 0."""
    failures = []
    try:
        manifest = json.loads((folder / "manifest.json").read_text())
        with (folder / "measured-runs.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except (OSError, ValueError) as exc:
        return False, [f"missing/invalid smoke evidence: {exc}"]

    expected = {
        "driver": "opencode", "model": MODEL, "synthetic": False,
        "selected_arms": list(ARMS), "selected_task_ids": list(SMOKE_TASKS),
        "replicates": 1, "runs": 4, "paired": True,
        "opencode_tool_profile": "diagnostic",
        "skill_sha256": hashlib.sha256(
            (ROOT / "betfirst" / "SKILL.md").read_bytes()).hexdigest(),
        "suite_sha256": hashlib.sha256(SUITE.read_bytes()).hexdigest(),
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            failures.append(f"manifest {key}: mismatch")

    expected_ids = {f"{t}-r1-{a}" for t in SMOKE_TASKS for a in ARMS}
    found_ids = set()
    for row in rows:
        rid = f"{row.get('task_id')}-r{row.get('replicate')}-{row.get('arm')}"
        found_ids.add(rid)
        if row.get("passed") != "true" or row.get("code_accepted") != "true" or row.get("session_success") != "true":
            failures.append(f"{rid}: {row.get('failure_reasons') or 'did not pass'}")
        try:
            outcome = json.loads((folder / rid / "outcome.json").read_text())
            trace = json.loads((folder / rid / "trace_summary.json").read_text())
        except (OSError, ValueError) as exc:
            failures.append(f"{rid}: missing outcome/trace: {exc}")
            continue
        if not outcome.get("passed") or outcome.get("tests_tampered"):
            failures.append(f"{rid}: verification or test integrity failed")
        if row["task_id"] == "ttl-boundary-ok" and outcome.get("workspace_changed"):
            failures.append(f"{rid}: illegal file changes to already-correct task")
        # The model must have produced real agent events, not only a no-op
        # process that happened to pass the negative fixture.
        if not isinstance(trace.get("agent_turns"), int) or trace["agent_turns"] < 1:
            failures.append(f"{rid}: missing real OpenCode agent steps")

    if found_ids != expected_ids or len(rows) != 4:
        failures.append(f"smoke sessions: expected {len(expected_ids)} distinct runs, got {len(rows)}")
    return not failures, failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    for mode in ("smoke", "study"):
        p = sub.add_parser(mode)
        p.add_argument("--output", type=Path, required=True)
        p.add_argument("--acknowledge-isolation", action="store_true",
                       help="I am using an OS-isolated test user/VM with no private source or host credentials")
        if mode == "study":
            p.add_argument("--smoke-dir", type=Path, required=True,
                           help="Successful fresh smoke directory on the same candidate Skill")
            p.add_argument("--hours", type=float, default=2.0,
                           help="Maximum wall time (default/maximum: 2h)")
            p.add_argument("--resume", action="store_true",
                           help="Resume same time budget and manifest; never restart the clock")
    args = parser.parse_args()
    if not args.acknowledge_isolation:
        parser.error("--acknowledge-isolation required: OpenCode permissions do not sandbox Python")
    if args.mode == "study":
        if not 0 < args.hours <= 2:
            parser.error("--hours must be greater than 0 and no more than 2")
        smoke_dir = args.smoke_dir.resolve()
        approved, issues = verify_smoke(smoke_dir)
        if not approved:
            print("NO-GO: smoke is not fully accepted. Do not start the 2h study.")
            for issue in issues:
                print(" -", issue)
            return 2
        if args.output.resolve() == smoke_dir:
            parser.error("study --output must differ from smoke evidence directory")
        print("Smoke gate PASS; starting up to 2 hours of matched Muse sessions", flush=True)

        # 24 rounds cap maximum sessions, not the time. Randomize task order
        # per round and strategy order per pair. Stop at safe pair boundary
        # when insufficient wall time remains for two bounded executions.
        execute(
            SUITE.resolve(), args.output.resolve(), "opencode", MODEL,
            replicates=24, seed=SEED, timeout=180, execute_real=True,
            tool_profile="diagnostic", acknowledge_isolation=True,
            max_turns=30, resume=args.resume,
            selected_arms=list(ARMS), paired=True,
            time_budget_seconds=round(args.hours * 3600),
            verification_timeout=30,
        )
        print(f"Study results: {args.output.resolve()}", flush=True)
        print("Read budget-status.json and measured-runs.csv; compare only fully matched pairs.")
        return 0

    print("Smoke: 2 public tasks x 2 arms = 4 real Muse sessions", flush=True)
    execute(
        SUITE.resolve(), args.output.resolve(), "opencode", MODEL,
        replicates=1, seed=SEED, timeout=180, execute_real=True,
        selected_tasks=list(SMOKE_TASKS), tool_profile="diagnostic",
        acknowledge_isolation=True, max_turns=30,
        selected_arms=list(ARMS), paired=True, verification_timeout=30,
    )
    approved, issues = verify_smoke(args.output.resolve())
    if not approved:
        print("NO-GO: smoke failed; preserve its evidence and inspect the logs.")
        for issue in issues:
            print(" -", issue)
        return 2
    print("SMOKE PASS. Next:")
    print("python3 betfirst/experiments/muse_study.py study "
          f"--smoke-dir '{args.output.resolve()}' "
          "--output '$HOME/betfirst-muse-study/run-YYYYMMDD-HHMMSS' "
          "--acknowledge-isolation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
