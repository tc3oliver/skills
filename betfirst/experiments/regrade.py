#!/usr/bin/env python3
"""Reclassify an existing evaluation without rerunning any agent or tests.

Creates a new derived report directory; NEVER changes original run evidence.
Recorded exit codes and oracle results are reused as historical observations.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from run import HERE, hashes, load_suite
from test_integrity import inspect_tests
from scoring import classify


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regrade(source: Path, suite: Path, destination: Path) -> dict:
    source, suite, destination = source.resolve(), suite.resolve(), destination.resolve()
    manifest_file = source / "manifest.json"
    rows_file = source / "measured-runs.csv"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("synthetic") is True or manifest.get("driver") not in ("claude", "pi"):
        raise ValueError("regrade requires a real measured-runs.csv experiment")
    if manifest.get("suite_sha256") != _sha(suite):
        raise ValueError("suite SHA mismatch; use the exact suite from the original run")
    tasks = {task["id"]: task for task in load_suite(suite)}
    with rows_file.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        if not columns or "passed" not in columns:
            raise ValueError("malformed measured-runs.csv")
        rows = list(reader)
    columns = list(columns)
    for field in ("code_accepted", "session_success", "failure_reasons"):
        if field not in columns:
            columns.append(field)
    if not rows or len(rows) != manifest.get("runs"):
        raise ValueError("run count differs from immutable manifest")

    fixture_hashes = manifest.get("fixture_hashes")
    verified_fixture_hashes = isinstance(fixture_hashes, dict)
    if verified_fixture_hashes:
        for tid, prior in fixture_hashes.items():
            if tid not in tasks or prior != hashes(suite.parent / tasks[tid]["fixture"]):
                raise ValueError("fixture hashes differ from recorded run")
    changes = []
    revised = []
    seen = set()
    for row in rows:
        tid, arm = row["task_id"], row["arm"]
        try:
            rep = int(row["replicate"])
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid replicate ID") from exc
        if tid not in tasks or arm not in ("baseline", "efficiency", "betfirst") or rep < 1:
            raise ValueError("unexpected task, arm or replicate")
        key = (tid, rep, arm)
        if key in seen:
            raise ValueError("duplicate run")
        seen.add(key)
        run_id = f"{tid}-r{rep}-{arm}"
        existing = source / run_id / "outcome.json"
        recorded = json.loads(existing.read_text(encoding="utf-8"))
        integrity = inspect_tests(suite.parent / tasks[tid]["fixture"], source / run_id / "work")
        # An oracle required by the task must have a recorded successful
        # exit. A missing result is an acceptance failure, not a free pass.
        oracle_exit = recorded.get("oracle_exit")
        if "oracle" in tasks[tid] and oracle_exit is None:
            oracle_exit = -1
        evaluation = classify(
            task=tasks[tid],
            agent_exit=recorded.get("agent_exit"),
            agent_timeout=recorded.get("agent_timeout") is True,
            agent_subtype=recorded.get("agent_subtype") or row.get("agent_subtype"),
            test_exit=recorded.get("acceptance_exit"),
            test_timeout=recorded.get("acceptance_timeout") is True,
            oracle_exit=oracle_exit,
            oracle_timeout=recorded.get("oracle_timeout") is True,
            test_integrity_passed=integrity["passed"],
            workspace_changed=recorded.get("workspace_changed") is True,
        )
        good = evaluation["passed"]
        original_pass = row["passed"].strip().lower()
        if original_pass not in ("true", "false") or (original_pass == "true") != bool(recorded.get("passed")):
            raise ValueError(f"CSV and outcome mismatch: {run_id}")
        updated = dict(row)
        updated["passed"] = str(good).lower()
        updated["code_accepted"] = str(evaluation["code_accepted"]).lower()
        updated["session_success"] = str(evaluation["session_success"]).lower()
        updated["failure_reasons"] = ";".join(evaluation["failure_reasons"])
        revised.append(updated)
        changes.append({
            "run_id": run_id, "original_passed": bool(recorded["passed"]),
            "regraded_passed": good, "tests_changed": recorded.get("tests_changed"),
            "code_accepted": evaluation["code_accepted"],
            "session_success": evaluation["session_success"],
            "failure_reasons": evaluation["failure_reasons"],
            "test_integrity": integrity,
            "agent_exit": recorded.get("agent_exit"),
            "oracle_exit": recorded.get("oracle_exit"),
        })

    if destination == source or destination == suite.parent or destination.exists():
        raise ValueError("destination must be a new directory; never overwrite run evidence")
    if source in destination.parents and len(destination.relative_to(source).parts) != 1:
        raise ValueError("derived output must be directly beneath source or outside it")

    destination.mkdir(parents=True)
    derived_manifest = dict(manifest)
    derived_manifest.update({
        "grading_version": 3,
        "derived_from_manifest_sha256": _sha(manifest_file),
        "derived_from_rows_sha256": _sha(rows_file),
        "original_fixture_hashes_verified": verified_fixture_hashes,
        "regrade_note": (
            "No model/test/oracle rerun. Uses recorded exits, current fixture test AST, "
            "and original worktrees. Results require same original fixture source."
        ),
    })
    (destination / "manifest.json").write_text(json.dumps(derived_manifest, indent=2) + "\n", encoding="utf-8")
    with (destination / "measured-runs.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(revised)
    (destination / "regrade-audit.json").write_text(json.dumps(changes, indent=2) + "\n", encoding="utf-8")
    return {"directory": str(destination), "runs": len(rows),
            "passes_before": sum(x["original_passed"] for x in changes),
            "passes_after": sum(x["regraded_passed"] for x in changes),
            "fixture_hashes_verified": verified_fixture_hashes,
            "changes": [x for x in changes if x["original_passed"] != x["regraded_passed"]]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path, help="Original live experiment run directory")
    p.add_argument("--suite", type=Path, default=HERE / "suite-v2.json")
    p.add_argument("--output", type=Path,
                   help="New derived directory; default SOURCE/regraded-v2")
    args = p.parse_args()
    result = regrade(args.source, args.suite, args.output or args.source / "regraded-v2")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
