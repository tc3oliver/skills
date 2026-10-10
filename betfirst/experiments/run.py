#!/usr/bin/env python3
"""Run a reproducible BetFirst three-arm pilot in fresh task directories.

Mock verifies the harness only, never model behavior. Real Claude/Pi requires
installed authenticated CLI and explicit --execute (possible API charges).
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from usage import usage_from_output

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARMS = ("baseline", "efficiency", "betfirst")
EFFICIENCY = "Avoid redundant file reads, repeated tool calls and unnecessary tests; preserve final validation."
COLUMNS = ("task_id", "replicate", "arm", "passed", "elapsed_seconds", "input_tokens",
           "output_tokens", "cache_read_tokens", "cache_write_tokens", "api_cost_usd",
           "bet_attempts", "bet_failures", "failed_bet_overhead_seconds")


def hashes(folder: Path) -> dict:
    result = {}
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError("fixture symlinks are not supported: " + str(path))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            result[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def load_suite(path: Path) -> list:
    obj = json.loads(path.read_text(encoding="utf-8"))
    tasks = obj.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("suite requires a non-empty tasks array")
    found = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("task must be an object")
        tid = task.get("id")
        if not isinstance(tid, str) or not tid.replace("-", "").replace("_", "").isalnum() or tid in found:
            raise ValueError("duplicate or unsafe task id")
        found.add(tid)
        fixture = task.get("fixture")
        if not isinstance(fixture, str) or Path(fixture).is_absolute() or ".." in Path(fixture).parts:
            raise ValueError("unsafe fixture path")
        source = (path.parent / fixture).resolve()
        if not source.is_relative_to(path.parent.resolve()) or not source.is_dir():
            raise ValueError("fixture must be inside suite directory")
        hashes(source)
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            raise ValueError("task prompt is required")
        check = task.get("check")
        if not isinstance(check, list) or not check or any(not isinstance(x, str) for x in check):
            raise ValueError("check must be argv string array")
    return tasks


def prompt_for(task: dict, arm: str, skill_text: str) -> str:
    prompt = task["prompt"].strip()
    if arm != "baseline":
        prompt += "\n\nExecution guidance:\n" + EFFICIENCY
    if arm == "betfirst":
        prompt += "\n\nApply the following BetFirst Skill:\n" + skill_text
    prompt += "\n\nWork only on this task. Preserve all tests under tests/. Finish with required verification."
    return prompt


def command(driver: str, model: str | None, prompt: str, tid: str, arm: str) -> list:
    if driver == "mock":
        return [sys.executable, str(HERE / "mock_agent.py"), tid, arm]
    if not model:
        raise ValueError("--model is required for live agents")
    if driver == "claude":
        return ["claude", "--bare", "-p", "--output-format", "json",
                "--max-turns", "30", "--model", model, prompt]
    if driver == "pi":
        return ["pi", "--no-context-files", "--no-skills", "--no-extensions",
                "--no-prompt-templates", "--no-session", "-p",
                "--mode", "json", "--model", model, prompt]
    raise ValueError("unknown driver")


def run_cmd(argv: list, cwd: Path, stdout: Path, stderr: Path, timeout: int) -> tuple:
    t0 = time.perf_counter()
    with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        expired = False
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            expired, code = True, None
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    return code, expired, time.perf_counter() - t0


def execute(suite: Path, output: Path, driver: str, model: str | None,
            replicates: int, seed: int, timeout: int, execute_real: bool,
            limit: int | None = None) -> list:
    if driver != "mock" and not execute_real:
        raise ValueError("real CLI execution requires --execute and may incur API cost")
    if driver != "mock" and not model:
        raise ValueError("--model must be explicit for live experiments")
    if replicates < 1 or timeout < 1 or (limit is not None and limit < 1):
        raise ValueError("replicates, timeout and limit must be positive")
    if output.exists() and any(output.iterdir()):
        raise ValueError("output exists and is not empty; never overwrite experiment evidence")
    tasks = load_suite(suite)
    if limit:
        tasks = tasks[:limit]
    skill = (ROOT / "betfirst" / "SKILL.md").read_text(encoding="utf-8")
    output.mkdir(parents=True, exist_ok=True)
    plan = [(task, rep, arm) for task in tasks
            for rep in range(1, replicates + 1) for arm in ARMS]
    random.Random(seed).shuffle(plan)
    (output / "manifest.json").write_text(json.dumps({
        "schema": 1, "driver": driver, "model": model, "seed": seed,
        "replicates": replicates, "runs": len(plan),
        "synthetic": driver == "mock", "timeout": timeout,
        "note": "Mock exercises harness only, not agent performance or savings."
    }, indent=2) + "\n", encoding="utf-8")
    results = []
    for task, rep, arm in plan:
        rid = f"{task['id']}-r{rep}-{arm}"
        run_dir = output / rid
        run_dir.mkdir()
        work = run_dir / "work"
        shutil.copytree(suite.parent / task["fixture"], work, symlinks=False)
        original = hashes(work)
        tests = hashes(work / "tests") if (work / "tests").is_dir() else {}
        prompt = prompt_for(task, arm, skill)
        (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        cmd = command(driver, model, prompt, task["id"], arm)
        try:
            agent_exit, timed_out, agent_time = run_cmd(
                cmd, work, run_dir / "agent.stdout", run_dir / "agent.stderr", timeout)
        except FileNotFoundError as exc:
            raise RuntimeError("Missing installed agent CLI: " + str(exc.filename)) from exc
        test_exit, test_timed_out, check_time = run_cmd(
            task["check"], work, run_dir / "acceptance.stdout", run_dir / "acceptance.stderr", timeout)
        changed_tests = tests != (hashes(work / "tests") if (work / "tests").is_dir() else {})
        changed = original != hashes(work)
        passed = (agent_exit == 0 and not timed_out and test_exit == 0
                  and not test_timed_out and not changed_tests)
        if task.get("no_change"):
            passed = passed and not changed
        use = usage_from_output((run_dir / "agent.stdout").read_text(encoding="utf-8"), driver)
        row = {"task_id": task["id"], "replicate": rep, "arm": arm,
               "passed": str(passed).lower(), "elapsed_seconds": round(agent_time + check_time, 6),
               **use, "bet_attempts": None, "bet_failures": None, "failed_bet_overhead_seconds": None}
        results.append(row)
        (run_dir / "outcome.json").write_text(json.dumps({
            "passed": passed, "agent_exit": agent_exit, "agent_timeout": timed_out,
            "acceptance_exit": test_exit, "acceptance_timeout": test_timed_out,
            "tests_changed": changed_tests, "workspace_changed": changed,
            "agent_seconds": agent_time, "acceptance_seconds": check_time
        }, indent=2) + "\n", encoding="utf-8")
        print(f"{rid}: {'PASS' if passed else 'FAIL'}", flush=True)
    csv_name = "synthetic-smoke.csv" if driver == "mock" else "measured-runs.csv"
    with (output / csv_name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=HERE / "suite.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--driver", choices=("mock", "claude", "pi"), default="mock")
    parser.add_argument("--model")
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--execute", action="store_true", help="Permit actual provider calls and costs")
    args = parser.parse_args()
    execute(args.suite.resolve(), args.output.resolve(), args.driver, args.model,
            args.replicates, args.seed, args.timeout, args.execute, args.limit)


if __name__ == "__main__":
    main()
