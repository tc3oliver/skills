#!/usr/bin/env python3
"""Run a reproducible BetFirst three-arm pilot in fresh task directories.

Mock verifies the harness only, never model behavior. Real Claude/Pi requires
installed authenticated CLI and explicit --execute (possible API charges).
"""
from __future__ import annotations
import argparse
import csv
import datetime
import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import time
import threading
from pathlib import Path
from usage import usage_from_output
from trace import summarize_trace
from test_integrity import inspect_tests
from scoring import classify
from workspace_guard import snapshot_dataset, assert_clean_checkout, unexpected_tool_paths

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARMS = ("baseline", "efficiency", "betfirst", "betfirst-v04")
V04_SKILL = HERE / "candidates" / "v04" / "SKILL.md"
EFFICIENCY = "Avoid redundant file reads, repeated tool calls and unnecessary tests; preserve final validation."
OPENCODE_PERMISSIONS = {
    "*": "deny", "read": "allow", "glob": "allow", "grep": "allow",
    "list": "allow", "edit": "allow",
    "bash": {"*": "deny", "python3 *": "allow"},
    "external_directory": "deny",
}
OPENCODE_CONFIG = {
    "permission": OPENCODE_PERMISSIONS,
    "share": "disabled", "instructions": [], "plugin": [],
}
TOOL_PROFILES = {
    "restricted": ("Read", "Edit", "Write", "Bash(python3 -m unittest *)"),
    "diagnostic": ("Read", "Edit", "Write", "Bash(python3 *)"),
}
COLUMNS = ("task_id", "replicate", "arm", "passed", "elapsed_seconds", "input_tokens",
           "output_tokens", "cache_read_tokens", "cache_write_tokens", "api_cost_usd",
           "bet_attempts", "bet_failures", "failed_bet_overhead_seconds",
           "tool_calls", "tool_errors", "permission_denials",
           "agent_subtype", "agent_turns", "code_accepted", "session_success",
           "failure_reasons")


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
        if "oracle" in task:
            oracle = task["oracle"]
            if not isinstance(oracle, str) or Path(oracle).is_absolute() or ".." in Path(oracle).parts:
                raise ValueError("oracle must be a safe relative path")
            oracle_path = (path.parent / oracle).resolve()
            if not oracle_path.is_relative_to(path.parent.resolve()) or not oracle_path.is_file():
                raise ValueError("oracle must be a file inside the suite directory")
            if oracle_path.is_relative_to(source):
                raise ValueError("oracle must not be included in agent fixture")
        if not isinstance(task.get("prompt"), str) or not task["prompt"].strip():
            raise ValueError("task prompt is required")
        check = task.get("check")
        if not isinstance(check, list) or not check or any(not isinstance(x, str) for x in check):
            raise ValueError("check must be argv string array")
    return tasks


def prompt_for(task: dict, arm: str, skill_text: str, tool_profile: str = "restricted",
               scratch: Path | None = None,
               candidate_skill_text: str | None = None) -> str:
    prompt = task["prompt"].strip()
    if arm != "baseline":
        prompt += "\n\nExecution guidance:\n" + EFFICIENCY
    if arm == "betfirst":
        prompt += "\n\nApply the following BetFirst Skill:\n" + skill_text
    elif arm == "betfirst-v04":
        if not candidate_skill_text:
            raise ValueError("betfirst-v04 requires an explicit candidate Skill")
        prompt += "\n\nApply the following BetFirst Skill v0.4:\n" + candidate_skill_text
    prompt += "\n\nWork only on this task. Preserve original tests; additive regression tests are allowed. Finish with required verification."
    if tool_profile == "diagnostic":
        prompt += ("\n\nAll arms receive identical diagnostic tool permissions: use Python via "
                   "python3 -c or python3 script.py for focused probes. "
                   "Create source files with Write/Edit, not shell heredocs, "
                   "pipelines, mkdir or rm. Keep probes inside the task workspace.")
    if scratch is not None:
        prompt += (
            "\n\nWorkspace boundary: use the current fixture working directory (PWD) "
            "for source and tests; NEVER inspect the parent benchmark checkout "
            "or its hidden oracles. Prefer inline python3 -c probes. "
            "If a temporary probe file is necessary, use only the dedicated "
            "per-session scratch directory " + str(scratch) +
            ". Do not use system /tmp, /private/var or other external paths."
        )
    return prompt


def command(driver: str, model: str | None, prompt: str, tid: str, arm: str,
            claude_launcher: str = "direct", tool_profile: str = "restricted",
            max_turns: int = 30) -> list:
    if driver == "mock":
        return [sys.executable, str(HERE / "mock_agent.py"), tid, arm]
    if not model:
        raise ValueError("--model is required for live agents")
    if driver == "claude":
        if tool_profile not in TOOL_PROFILES:
            raise ValueError("unknown tool profile")
        claude_args = ["--bare", "--permission-mode", "dontAsk",
                       "--allowedTools", *TOOL_PROFILES[tool_profile],
                       "-p", prompt, "--output-format", "stream-json",
                       "--verbose", "--max-turns", str(max_turns)]
        if claude_launcher == "omlx":
            binary = os.environ.get("OMLX_BIN")
            if not binary:
                raise ValueError("OMLX_BIN must point at the omlx executable")
            # The separator is required to avoid oMLX mistaking --tools
            # and other Claude Code options for oMLX's --tools-profile.
            return [binary, "launch", "claude", "--model", model, "--", *claude_args]
        if claude_launcher != "direct":
            raise ValueError("unsupported Claude launcher")
        return ["claude", "--model", model, *claude_args]
    if driver == "pi":
        return ["pi", "--no-context-files", "--no-skills", "--no-extensions",
                "--no-prompt-templates", "--no-session", "-p",
                "--mode", "json", "--model", model, prompt]
    if driver == "opencode":
        # The user-installed CLI has no --dir option. The subprocess runs with
        # cwd=work; --standalone avoids reusing a background server workspace.
        return ["opencode", "run", "--standalone", "--agent", "build",
                "--format", "json", "--model", model, prompt]
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


def opencode_configuration(tool_profile: str) -> dict:
    if tool_profile not in TOOL_PROFILES:
        raise ValueError("invalid OpenCode tool profile")
    permissions = dict(OPENCODE_PERMISSIONS)
    allowed = ("python3 *" if tool_profile == "diagnostic"
               else "python3 -m unittest *")
    permissions["bash"] = {"*": "deny", allowed: "allow"}
    return {**OPENCODE_CONFIG, "permission": permissions}


def opencode_environment(config_dir: Path, tool_profile: str = "restricted",
                         workspace: Path | None = None,
                         scratch: Path | None = None) -> dict[str, str]:
    """Benchmark policy override, not an OS sandbox; isolate at the host layer."""
    config = opencode_configuration(tool_profile)
    config_dir.mkdir(exist_ok=False)
    env = os.environ.copy()
    # Popen(cwd=work) does NOT update inherited PWD/OLDPWD. Certain Node/CLI
    # code paths may trust PWD, which formerly pointed at ~/betfirst-v03.
    if workspace is not None:
        env["PWD"] = str(workspace.resolve())
        env.pop("OLDPWD", None)
    if scratch is not None:
        scratch.mkdir(mode=0o700, parents=False, exist_ok=False)
        for key in ("TMPDIR", "TMP", "TEMP"):
            env[key] = str(scratch.resolve())
    env.update({
        "OPENCODE_CONFIG_DIR": str(config_dir),
        "OPENCODE_CONFIG_CONTENT": json.dumps(config),
        "OPENCODE_PERMISSION": json.dumps(config["permission"]),
        "OPENCODE_DISABLE_CLAUDE_CODE": "1",
        "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
        "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_AUTO_SHARE": "0",
    })
    return env


def run_opencode_cmd(argv: list[str], cwd: Path, stdout: Path, stderr: Path,
                     timeout: int, max_steps: int, env: dict[str, str]) -> tuple:
    """Capture JSONL while enforcing wall time and OpenCode model-step cap."""
    started = time.perf_counter()
    exceeded = threading.Event()
    steps = [0]
    with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=err, text=True,
            errors="replace", start_new_session=True,
        )

        def drain() -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                out.write(line)
                out.flush()
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("type") == "step_start":
                    steps[0] += 1
                    if steps[0] > max_steps:
                        exceeded.set()

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        timed_out = False
        turn_limited = False
        while proc.poll() is None:
            if exceeded.is_set():
                turn_limited = True
                break
            if time.perf_counter() - started >= timeout:
                timed_out = True
                break
            time.sleep(0.05)
        if timed_out or turn_limited:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        proc.wait()
        reader.join(timeout=3)
    return proc.returncode, timed_out, time.perf_counter() - started, turn_limited


def execute(suite: Path, output: Path, driver: str, model: str | None,
            replicates: int, seed: int, timeout: int, execute_real: bool,
            limit: int | None = None, claude_launcher: str = "direct",
            selected_tasks: list[str] | None = None,
            tool_profile: str = "restricted",
            acknowledge_isolation: bool = False, max_turns: int = 30,
            resume: bool = False, stop_after: int | None = None,
            selected_arms: list[str] | None = None,
            paired: bool = False, time_budget_seconds: int | None = None,
            verification_timeout: int | None = None) -> list:
    if driver != "mock" and not execute_real:
        raise ValueError("real CLI execution requires --execute and may incur API cost")
    if driver != "mock" and not model:
        raise ValueError("--model must be explicit for live experiments")
    if stop_after is not None and stop_after < 1:
        raise ValueError("stop-after must be positive")
    if max_turns < 1:
        raise ValueError("max-turns must be positive")
    if time_budget_seconds is not None and time_budget_seconds < 1:
        raise ValueError("time budget must be positive")
    if verification_timeout is not None and verification_timeout < 1:
        raise ValueError("verification timeout must be positive")
    if tool_profile not in TOOL_PROFILES:
        raise ValueError("unknown tool profile")
    if driver not in ("claude", "opencode") and tool_profile != "restricted":
        raise ValueError("diagnostic tool profile requires Claude or OpenCode")
    if driver in ("claude", "opencode") and tool_profile == "diagnostic" and not acknowledge_isolation:
        raise ValueError("diagnostic Python access requires --acknowledge-isolation: run in a dedicated OS-isolated environment, not an unrestricted host account")
    if driver == "opencode" and not acknowledge_isolation:
        raise ValueError("OpenCode requires --acknowledge-isolation: permissions are NOT an OS sandbox")
    if replicates < 1 or timeout < 1 or (limit is not None and limit < 1):
        raise ValueError("replicates, timeout and limit must be positive")
    if resume:
        if not (output / "manifest.json").is_file():
            raise ValueError("resume requires existing manifest.json")
    elif output.exists() and any(output.iterdir()):
        raise ValueError("output exists and is not empty; never overwrite experiment evidence")
    arms = tuple(selected_arms) if selected_arms is not None else ARMS
    if not arms or len(arms) != len(set(arms)) or any(a not in ARMS for a in arms):
        raise ValueError("select distinct known --arm values")
    if paired and len(arms) not in (2, 3):
        raise ValueError("--paired requires two or three --arm selections")
    if time_budget_seconds is not None and not paired:
        raise ValueError("--time-budget-seconds requires --paired, to protect comparison pairs")
    tasks = load_suite(suite)
    if selected_tasks and limit is not None:
        raise ValueError("--task and --limit cannot be used together")
    if selected_tasks:
        requested = set(selected_tasks)
        available = {task["id"] for task in tasks}
        if not requested <= available or len(requested) != len(selected_tasks):
            raise ValueError("duplicate or unknown --task selection")
        tasks = [task for task in tasks if task["id"] in requested]
    if limit:
        tasks = tasks[:limit]
    skill = (ROOT / "betfirst" / "SKILL.md").read_text(encoding="utf-8")
    v04_skill = (V04_SKILL.read_text(encoding="utf-8")
                 if "betfirst-v04" in arms else None)
    # If an Agent previously touched the pristine fixtures/hidden oracles,
    # refusing to restart prevents a corrupted baseline being reused.
    dataset_before = None
    if driver == "opencode":
        assert_clean_checkout(suite, ROOT)
        dataset_before = snapshot_dataset(suite)
    output.mkdir(parents=True, exist_ok=True)
    if paired:
        rng = random.Random(seed)
        plan = []
        # Complete paired comparisons before moving on; rotate every task in
        # each replicate before starting another replicate.
        for rep in range(1, replicates + 1):
            round_tasks = list(tasks)
            rng.shuffle(round_tasks)
            for task in round_tasks:
                pair_arms = list(arms)
                rng.shuffle(pair_arms)
                plan.extend((task, rep, arm) for arm in pair_arms)
    else:
        plan = [(task, rep, arm) for task in tasks
                for rep in range(1, replicates + 1) for arm in arms]
        random.Random(seed).shuffle(plan)
    manifest = {
        "schema": 3, "driver": driver, "model": model, "seed": seed,
        "selected_task_ids": [task["id"] for task in tasks],
        "task_selection": "explicit" if selected_tasks else ("first_N" if limit else "full_suite"),
        "replicates": replicates, "runs": len(plan), "selected_arms": list(arms),
        "paired": paired, "time_budget_seconds": time_budget_seconds,
        "verification_timeout": verification_timeout,
        "synthetic": driver == "mock", "timeout": timeout,
        "claude_launcher": claude_launcher if driver == "claude" else None,
        "claude_tool_profile": tool_profile if driver == "claude" else None,
        "claude_allowed_tools": list(TOOL_PROFILES[tool_profile]) if driver == "claude" else None,
        "claude_max_turns": max_turns if driver == "claude" else None,
        "opencode_max_steps": max_turns if driver == "opencode" else None,
        "opencode_config_sha256": (hashlib.sha256(json.dumps(opencode_configuration(tool_profile), sort_keys=True).encode()).hexdigest()
                                   if driver == "opencode" else None),
        "opencode_tool_profile": tool_profile if driver == "opencode" else None,
        # Protocol revision: isolated scratch is deliberately incompatible with
        # resuming studies created before this mitigation.
        "opencode_scratch_protocol": "session-scratch-v1" if driver == "opencode" else None,
        "suite_sha256": hashlib.sha256(suite.read_bytes()).hexdigest(),
        "fixture_hashes": {t["id"]: hashes(suite.parent / t["fixture"]) for t in tasks},
        "skill_sha256": hashlib.sha256(skill.encode("utf-8")).hexdigest(),
        **({"v04_skill_sha256": hashlib.sha256(v04_skill.encode("utf-8")).hexdigest()}
           if v04_skill is not None else {}),
        "dataset_sha256": (hashlib.sha256(json.dumps(dataset_before, sort_keys=True).encode()).hexdigest()
                           if dataset_before is not None else None),
        "note": "Mock exercises harness only, not agent performance or savings.",
        "run_order": [f"{task['id']}-r{rep}-{arm}" for task,rep,arm in plan],
    }
    csv_name = "synthetic-smoke.csv" if driver == "mock" else "measured-runs.csv"
    existing = {}
    # Durable start ensures --resume does not silently reset the two-hour clock.
    budget_path = output / "budget-start.json"
    budget_start = None
    if time_budget_seconds is not None:
        if resume:
            if not budget_path.is_file():
                raise ValueError("budgeted --resume requires budget-start.json")
            budget_state = json.loads(budget_path.read_text(encoding="utf-8"))
            if budget_state.get("seconds") != time_budget_seconds:
                raise ValueError("time budget mismatch on resume")
            budget_start = float(budget_state["start_epoch"])
        else:
            budget_start = time.time()
            budget_path.write_text(json.dumps({
                "start_epoch": budget_start,
                "started_utc": datetime.datetime.fromtimestamp(
                    budget_start, datetime.timezone.utc).isoformat(),
                "seconds": time_budget_seconds,
            }, indent=2) + "\n", encoding="utf-8")
    if resume:
        prior = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if prior != manifest:
            raise ValueError("resume manifest mismatch; model, skill, fixtures, suite, order and runner flags must match original")
        # A durable per-run record is authoritative when a crash interrupted
        # the CSV atomic checkpoint between writing row.json and the CSV.
        for rid in manifest["run_order"]:
            folder = output / rid
            if not folder.exists():
                continue
            rowfile = folder / "row.json"
            if not rowfile.is_file() or not (folder / "outcome.json").is_file():
                raise ValueError("incomplete run requires manual archive/recovery before resume: " + rid)
            row = json.loads(rowfile.read_text(encoding="utf-8"))
            if row.get("task_id") not in rid or row.get("arm") not in ARMS:
                raise ValueError("invalid resume row: " + rid)
            existing[rid] = row
        csv_path = output / csv_name
        if csv_path.is_file():
            with csv_path.open(encoding="utf-8", newline="") as src:
                persisted = list(csv.DictReader(src))
            for row in persisted:
                rid = f"{row['task_id']}-r{row['replicate']}-{row['arm']}"
                if rid not in existing:
                    raise ValueError("CSV references unfinished run: " + rid)
                if {k: str(existing[rid].get(k) if existing[rid].get(k) is not None else '')
                    for k in COLUMNS} != row:
                    raise ValueError("CSV/checkpoint mismatch: " + rid)
    else:
        (output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def flush_checkpoint(rows: dict) -> None:
        # Atomic replacement keeps a complete CSV after every finished arm.
        target = output / csv_name
        temporary = output / (csv_name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows[rid] for rid in manifest["run_order"] if rid in rows)
        temporary.replace(target)

    results = []
    done = 0
    deadline = (budget_start + time_budget_seconds
                if budget_start is not None else None)
    # A matched group has two or three arms, each with an Agent budget
    # and two independent check budgets. Leave time for atomic checkpoints.
    check_cap = verification_timeout if verification_timeout is not None else timeout
    group_size = len(arms) if paired else 1
    pair_reserve = group_size * (timeout + 2 * check_cap) + 15
    stop_reason = "planned_sessions_complete"
    for index, (task, rep, arm) in enumerate(plan):
        # Check only at pair boundaries so budget never deliberately schedules
        # an unpaired arm. A process failure is still possible, hence keep
        # all finished sessions as immutable evidence.
        if deadline is not None and index % group_size == 0:
            pair_ids = [
                f"{plan[j][0]['id']}-r{plan[j][1]}-{plan[j][2]}"
                for j in range(index, min(index + group_size, len(plan)))
            ]
            if not all(pair_id in existing for pair_id in pair_ids):
                remaining = deadline - time.time()
                if remaining < pair_reserve:
                    stop_reason = "insufficient_time_for_complete_pair"
                    print(f"Budget stop: {remaining:.0f}s left, "
                          f"need {pair_reserve}s for a bounded pair", flush=True)
                    break
        rid = f"{task['id']}-r{rep}-{arm}"
        run_dir = output / rid
        if rid in existing:
            results.append(existing[rid])
            continue
        if run_dir.exists():
            raise ValueError("refusing to overwrite incomplete run: " + rid)
        run_dir.mkdir()
        work = run_dir / "work"
        shutil.copytree(suite.parent / task["fixture"], work, symlinks=False)
        original = hashes(work)
        tests = hashes(work / "tests") if (work / "tests").is_dir() else {}
        scratch = (run_dir / "opencode-tmp") if driver == "opencode" else None
        prompt = prompt_for(task, arm, skill, tool_profile, scratch, v04_skill)
        (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        cmd = command(driver, model, prompt, task["id"], arm, claude_launcher,
                      tool_profile, max_turns)
        turn_limited = False
        try:
            if driver == "opencode":
                # run_opencode_cmd already sets subprocess.cwd=work.
                env = opencode_environment(run_dir / "opencode-config", tool_profile, work, scratch)
                agent_exit, timed_out, agent_time, turn_limited = run_opencode_cmd(
                    cmd, work, run_dir / "agent.stdout", run_dir / "agent.stderr",
                    timeout, max_turns, env)
            else:
                agent_exit, timed_out, agent_time = run_cmd(
                    cmd, work, run_dir / "agent.stdout", run_dir / "agent.stderr", timeout)
        except FileNotFoundError as exc:
            raise RuntimeError("Missing installed agent CLI: " + str(exc.filename)) from exc
        if driver == "opencode":
            recorded = (run_dir / "agent.stdout").read_text(encoding="utf-8")
            violations = unexpected_tool_paths(recorded, work, ROOT, scratch)
            dataset_changed = snapshot_dataset(suite) != dataset_before
            if violations or dataset_changed:
                (run_dir / "benchmark-integrity-error.json").write_text(
                    json.dumps({
                        "external_tool_access": violations,
                        "pristine_dataset_changed": dataset_changed,
                        "explanation": "Do not interpret this run as skill efficacy.",
                    }, indent=2) + "\n", encoding="utf-8")
                raise RuntimeError(
                    f"FATAL benchmark workspace leak in {rid}: "
                    f"external access={len(violations)}, dataset changed={dataset_changed}. "
                    "Keep current outputs; stop study; inspect and restore source fixture."
                )
        test_exit, test_timed_out, check_time = run_cmd(
            task["check"], work, run_dir / "acceptance.stdout", run_dir / "acceptance.stderr", check_cap)
        # Independent oracle: never copied into the agent's work directory.
        # Running it after the visible suite prevents an agent from claiming
        # correctness solely by satisfying the tests it could inspect.
        oracle_exit, oracle_timed_out, oracle_time = None, False, 0.0
        if "oracle" in task:
            oracle_path = (suite.parent / task["oracle"]).resolve()
            oracle_exit, oracle_timed_out, oracle_time = run_cmd(
                [sys.executable, str(oracle_path)], work,
                run_dir / "oracle.stdout", run_dir / "oracle.stderr", check_cap)
        changed_tests = tests != (hashes(work / "tests") if (work / "tests").is_dir() else {})
        integrity = inspect_tests(suite.parent / task["fixture"], work)
        changed = original != hashes(work)
        agent_output = (run_dir / "agent.stdout").read_text(encoding="utf-8")
        use = usage_from_output(agent_output, driver)
        trace = summarize_trace(agent_output, driver)
        if driver == "opencode" and not trace["agent_turns"]:
            trace["agent_subtype"] = "error_missing_trace"
        if turn_limited:
            trace["agent_subtype"] = "error_max_turns"
            trace["trace_complete"] = False
        (run_dir / "trace_summary.json").write_text(
            json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        evaluation = classify(
            task=task, agent_exit=agent_exit, agent_timeout=timed_out,
            agent_subtype=trace["agent_subtype"], test_exit=test_exit,
            test_timeout=test_timed_out, oracle_exit=oracle_exit,
            oracle_timeout=oracle_timed_out,
            test_integrity_passed=integrity["passed"], workspace_changed=changed)
        passed = evaluation["passed"]
        row = {"task_id": task["id"], "replicate": rep, "arm": arm,
               "passed": str(passed).lower(), "elapsed_seconds": round(agent_time + check_time + oracle_time, 6),
               **use, "bet_attempts": trace["bet_attempts"],
               "bet_failures": trace["bet_failures"],
               "failed_bet_overhead_seconds": trace["failed_bet_overhead_seconds"],
               "tool_calls": trace["tool_calls"], "tool_errors": trace["tool_errors"],
               "permission_denials": trace["permission_denials"],
               "agent_subtype": trace["agent_subtype"], "agent_turns": trace["agent_turns"],
               "code_accepted": str(evaluation["code_accepted"]).lower(),
               "session_success": str(evaluation["session_success"]).lower(),
               "failure_reasons": ";".join(evaluation["failure_reasons"])}
        (run_dir / "outcome.json").write_text(json.dumps({
            "passed": passed, "agent_exit": agent_exit, "agent_timeout": timed_out,
            "acceptance_exit": test_exit, "acceptance_timeout": test_timed_out,
            "oracle_exit": oracle_exit, "oracle_timeout": oracle_timed_out,
            "tests_changed": changed_tests, "tests_tampered": not integrity["passed"],
            "test_integrity": integrity, "workspace_changed": changed,
            "agent_seconds": agent_time, "acceptance_seconds": check_time,
            "opencode_turn_limited": turn_limited if driver == "opencode" else None,
            "code_accepted": evaluation["code_accepted"],
            "session_success": evaluation["session_success"],
            "failure_reasons": evaluation["failure_reasons"],
            "agent_subtype": trace["agent_subtype"],
            "agent_turns": trace["agent_turns"],
            "oracle_seconds": oracle_time, "trace_complete": trace["trace_complete"]
        }, indent=2) + "\n", encoding="utf-8")
        (run_dir / "row.json").write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8")
        existing[rid] = row
        results.append(row)
        flush_checkpoint(existing)
        done += 1
        print(f"{rid}: {'PASS' if passed else 'FAIL'}", flush=True)
        if stop_after is not None and done >= stop_after:
            stop_reason = "stop_after"
            break
    if deadline is not None:
        all_saved = list(existing.values())
        pair_counts = {}
        for row in all_saved:
            key = (row["task_id"], row["replicate"])
            pair_counts.setdefault(key, set()).add(row["arm"])
        complete = {key for key, done_arms in pair_counts.items()
                    if set(arms) <= done_arms}
        status = {
            "reason": stop_reason,
            "budget_seconds": time_budget_seconds,
            "elapsed_seconds": round(time.time() - budget_start, 3),
            "completed_sessions": len(all_saved),
            "complete_pairs": len(complete),
            "planned_sessions": len(plan),
            "last_updated_utc": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
        }
        tmp = output / "budget-status.json.tmp"
        tmp.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        tmp.replace(output / "budget-status.json")
        print(f"Budget status: {status['complete_pairs']} complete pairs, "
              f"{status['completed_sessions']} sessions; {stop_reason}", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=HERE / "suite.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--driver", choices=("mock", "claude", "pi", "opencode"), default="mock")
    parser.add_argument("--model")
    parser.add_argument("--claude-launcher", choices=("direct", "omlx"), default="direct",
                        help="Use oMLX launch claude (requires OMLX_BIN) or direct Claude CLI")
    parser.add_argument("--tool-profile", "--claude-tool-profile", dest="claude_tool_profile",
                        choices=tuple(TOOL_PROFILES), default="restricted")
    parser.add_argument("--acknowledge-isolation", action="store_true",
                        help="Explicitly acknowledge the diagnostic profile permits arbitrary Python execution and requires an OS-isolated account or VM")
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--replicates", type=int, default=1)
    parser.add_argument("--paired", action="store_true",
                        help="Run matching pairs adjacent with randomized order")
    parser.add_argument("--time-budget-seconds", type=int,
                        help="Durable wall-time cap; stop before a pair if time cannot cover both arms")
    parser.add_argument("--verification-timeout", type=int,
                        help="Separate per-command timeout for acceptance and Oracle")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--arm", action="append", choices=ARMS,
                        help="Strategy arm to include; repeat for paired studies")
    parser.add_argument("--task", action="append", dest="selected_tasks",
                        help="Select an exact task ID; repeat to select multiple tasks")
    parser.add_argument("--resume", action="store_true",
                        help="Continue matching experiment from durable per-run checkpoints")
    parser.add_argument("--stop-after", type=int,
                        help="Stop after N newly completed arms (useful for offline resume verification)")
    parser.add_argument("--execute", action="store_true", help="Permit actual provider calls and costs")
    args = parser.parse_args()
    execute(args.suite.resolve(), args.output.resolve(), args.driver, args.model,
            args.replicates, args.seed, args.timeout, args.execute, args.limit,
            args.claude_launcher, args.selected_tasks, args.claude_tool_profile,
            args.acknowledge_isolation, args.max_turns, args.resume, args.stop_after,
        args.arm, args.paired, args.time_budget_seconds, args.verification_timeout)


if __name__ == "__main__":
    main()
