#!/usr/bin/env python3
"""Prospective Muse evaluation: Efficiency vs frozen BetFirst v0.3 vs candidate v0.4."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from run import execute

HERE = Path(__file__).resolve().parent
MODEL = "opencode-go/muse-spark-1.3-contributor"
SMOKE_SUITE = HERE / "suite-v3.json"   # previously seen, never in scored cohort
SUITE = HERE / "suite-v04.json"         # frozen held-out study
ARMS = ("efficiency", "betfirst", "betfirst-v04")
SEED = 20261011


def validate_smoke(folder: Path) -> list[str]:
    problems = []
    try:
        manifest = json.loads((folder / "manifest.json").read_text())
        with (folder / "measured-runs.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        rid = "cursor-pagination-r1-betfirst-v04"
        outcome = json.loads((folder / rid / "outcome.json").read_text())
        trace = json.loads((folder / rid / "trace_summary.json").read_text())
    except (OSError, ValueError) as exc:
        return [f"missing or invalid smoke evidence: {exc}"]
    if manifest.get("selected_task_ids") != ["cursor-pagination"]:
        problems.append("unexpected smoke task")
    if manifest.get("selected_arms") != ["betfirst-v04"]:
        problems.append("unexpected smoke arm")
    if manifest.get("driver") != "opencode" or manifest.get("model") != MODEL:
        problems.append("unexpected driver or model")
    if len(rows) != 1 or rows[0].get("arm") != "betfirst-v04":
        problems.append("smoke did not complete one v0.4 session")
    if outcome.get("agent_exit") != 0 or outcome.get("agent_timeout"):
        problems.append("agent process did not finish normally")
    if outcome.get("oracle_exit") is None or outcome.get("acceptance_exit") is None:
        problems.append("independent acceptance pipeline missing")
    if not isinstance(trace.get("agent_turns"), int) or trace["agent_turns"] < 1:
        problems.append("OpenCode emitted no model steps")
    if not isinstance(trace.get("tool_calls"), int) or trace["tool_calls"] < 1:
        problems.append("OpenCode emitted no tool invocations")
    # Correctness is analyzed in study; smoke verifies wiring only.
    return problems


def launch(output: Path, *, hours: float, replicates: int, resume: bool) -> None:
    smoke = output / "smoke"
    study = output / "study"
    if resume:
        failures = validate_smoke(smoke)
        if failures:
            raise RuntimeError("Cannot resume: smoke incomplete: " + "; ".join(failures))
        print("Reusing stored smoke evidence; retaining original study deadline", flush=True)
    else:
        if output.exists() and any(output.iterdir()):
            raise ValueError("new study output must be empty; never overwrite experiment evidence")
        output.mkdir(parents=True, exist_ok=True)
        print("Smoke: one previously seen v3 coding task, v0.4 arm only", flush=True)
        execute(
            SMOKE_SUITE.resolve(), smoke, "opencode", MODEL,
            replicates=1, seed=SEED, timeout=150, execute_real=True,
            selected_tasks=["cursor-pagination"], selected_arms=["betfirst-v04"],
            tool_profile="diagnostic", acknowledge_isolation=True,
            max_turns=30, verification_timeout=30,
        )
        failures = validate_smoke(smoke)
        if failures:
            raise RuntimeError("Smoke wiring FAILED, study not started: " +
                               "; ".join(failures))
        print("Smoke wiring PASS. Starting held-out cohort.", flush=True)

    execute(
        SUITE.resolve(), study, "opencode", MODEL,
        replicates=replicates, seed=SEED, timeout=180, execute_real=True,
        selected_arms=list(ARMS), paired=True, tool_profile="diagnostic",
        acknowledge_isolation=True, max_turns=30,
        verification_timeout=30, time_budget_seconds=round(hours * 3600),
        resume=resume,
    )
    print("Completed evidence:", study, flush=True)
    print("Only evaluate complete three-arm task+replicate groups.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hours", type=float, default=1.0)
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--acknowledge-isolation", action="store_true")
    args = parser.parse_args()
    if not (0 < args.hours <= 2) or args.replicates < 1:
        parser.error("hours must be (0, 2] and replicates must be positive")
    if not args.acknowledge_isolation:
        parser.error("OS isolation acknowledgment required; OpenCode permissions are not a sandbox")
    launch(args.output.resolve(), hours=args.hours,
           replicates=args.replicates, resume=args.resume)


if __name__ == "__main__":
    main()
