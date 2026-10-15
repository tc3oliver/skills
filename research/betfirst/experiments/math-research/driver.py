#!/usr/bin/env python3
"""A/B driver: BetFirst v0.4 (arm A) vs no BetFirst (arm B) on math-engineering tasks.

Runs `~/.local/bin/claude -p` on the user's subscription (no --bare: that mode only
accepts ANTHROPIC_API_KEY). Both arms pass --disable-slash-commands so a globally
installed betfirst Skill is never auto-loaded; arm A receives the exact SKILL.md text in
its prompt, like run.py's prompt_for. Missing usage stays null, never estimated.

Usage: driver.py SUITE.json OUT_DIR [--reps 2] [--seed N] [--only TASK] [--dry-run]
"""
from __future__ import annotations

import argparse, hashlib, json, os, random, shutil, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLAUDE = Path.home() / ".local/bin/claude"
SKILL = Path.home() / ".claude/skills/betfirst/SKILL.md"
ARMS = {"A": "betfirst-v0.4", "B": "control"}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def prompt_for(task: dict, arm: str, skill_text: str) -> str:
    p = task["prompt"].strip()
    if arm == "A":
        p += "\n\nApply the following BetFirst Skill:\n" + skill_text
        # Disclosed protocol overhead: route self-report for arm A only.
        p += ("\n\nRecord your route: write ROUTE.txt whose first word is NORMAL, BET or ABSTAIN;"
              " if BET, add the hypothesis, falsifying observation and probe result.")
    p += ("\n\nWork only in the current directory. Write your final answer where the task says."
          " Finish with the verification the task requires.")
    return p


def argv_for(task: dict, prompt: str, model: str) -> list:
    return [str(CLAUDE), "-p", prompt, "--model", model,
            "--output-format", "stream-json", "--verbose",
            "--disable-slash-commands", "--strict-mcp-config",
            # Skip user settings so user plugins/hooks (ponytail, ctk, ...) load in neither arm.
            "--setting-sources", "project",
            "--permission-mode", "dontAsk",
            "--allowedTools", *task["allowed_tools"],
            "--max-turns", str(task.get("max_turns", 40))]


def summarize(stream: str) -> dict:
    """Parse stream-json: usage from the terminal result event; count tool_use blocks."""
    out = {"input_tokens": None, "output_tokens": None, "cached_tokens": None,
           "cache_write_tokens": None, "tool_calls": 0, "num_turns": None,
           "result_subtype": None, "is_error": None, "model_reported": None}
    for line in stream.splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for block in (e.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    out["tool_calls"] += 1
        elif e.get("type") == "system" and e.get("subtype") == "init":
            out["model_reported"] = e.get("model")
        elif e.get("type") == "result":
            u = e.get("usage") or {}
            for k, src in (("input_tokens", "input_tokens"), ("output_tokens", "output_tokens"),
                           ("cached_tokens", "cache_read_input_tokens"),
                           ("cache_write_tokens", "cache_creation_input_tokens")):
                v = u.get(src)
                out[k] = v if isinstance(v, int) and not isinstance(v, bool) else None
            out["num_turns"] = e.get("num_turns")
            out["result_subtype"] = e.get("subtype")
            out["is_error"] = e.get("is_error")
    return out


def route_from_answer(ws: Path) -> str:
    """Route is self-reported by the agent in ROUTE.txt; 'missing' if absent/invalid."""
    f = ws / "ROUTE.txt"
    if f.is_file():
        r = f.read_text().strip().split()[0:1]
        if r and r[0].upper() in ("NORMAL", "BET", "ABSTAIN"):
            return r[0].upper()
    return "missing"


def instantiate(task: dict) -> dict:
    """Fill {LEAN_PROJECT} in prompt/tools from $JSP_LEAN_PROJECT (the run used a local absolute path)."""
    lp = os.environ.get("JSP_LEAN_PROJECT", "")
    if "{LEAN_PROJECT}" in json.dumps(task) and not lp:
        sys.exit("set JSP_LEAN_PROJECT to the pinned Lean project (see lean-project/)")
    t = json.loads(json.dumps(task).replace("{LEAN_PROJECT}", lp))
    return t


def run_one(task: dict, arm: str, rep: int, out: Path, model: str, skill_text: str,
            suite_dir: Path, dry: bool) -> dict:
    run_id = f"{task['id']}-{arm}-r{rep}"
    rdir = out / run_id
    ws = rdir / "workspace"
    rdir.mkdir(parents=True)
    src = (suite_dir / task["fixture"]).resolve()
    # APFS clonefile: cheap copy even when the fixture holds a mathlib .lake.
    subprocess.run(["cp", "-cR", str(src), str(ws)], check=True)
    prompt = prompt_for(task, arm, skill_text)
    (rdir / "prompt.txt").write_text(prompt)
    argv = argv_for(task, prompt, model)
    t0 = time.time()
    status, stream = "ok", ""
    if not dry:
        with open(rdir / "stdout.jsonl", "w") as so, open(rdir / "stderr.txt", "w") as se:
            p = subprocess.Popen(argv, cwd=ws, stdout=so, stderr=se, start_new_session=True,
                                 stdin=subprocess.DEVNULL)
            try:
                p.wait(timeout=task["timeout_s"])
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                status = "timeout"
        stream = (rdir / "stdout.jsonl").read_text()
    wall_ms = int((time.time() - t0) * 1000)
    use = summarize(stream)
    # Independent oracle: separate process, reads only the workspace, never shown to the agent.
    oracle = (suite_dir / task["oracle"]).resolve()
    t1 = time.time()
    o = subprocess.run([sys.executable, "-I", str(oracle), str(ws)], capture_output=True,
                       text=True, timeout=task.get("oracle_timeout_s", 900))
    (rdir / "oracle.txt").write_text(o.stdout + o.stderr)
    passed = o.returncode == 0
    outcome = "PASS" if passed else ("INCOMPLETE" if status == "timeout" else "FAIL")
    rec = {
        "task_id": task["id"], "run_id": run_id, "arm": arm, "skill_version": ARMS[arm],
        "model": f"{model} (Anthropic, Claude Code {task['_cc_version']}, subscription)",
        "model_reported": use["model_reported"], "route": route_from_answer(ws) if arm == "A" else "n/a",
        "wall_time_ms": wall_ms, "oracle_time_ms": int((time.time() - t1) * 1000),
        "input_tokens": use["input_tokens"], "output_tokens": use["output_tokens"],
        "cached_tokens": use["cached_tokens"], "cache_write_tokens": use["cache_write_tokens"],
        "tool_calls": use["tool_calls"] if stream else None, "num_turns": use["num_turns"],
        "bet_count": None, "probe_time_ms": None,  # filled by trace annotation, else missing
        "outcome": outcome, "verified_result": (o.stdout.strip().splitlines() or [""])[-1][:300],
        "stop_reason": status if status != "ok" else (use["result_subtype"] or "missing"),
        "task_hash": sha(task["prompt"]), "prompt_hash": sha(prompt), "rep": rep,
    }
    (rdir / "record.json").write_text(json.dumps(rec, indent=2))
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--only")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.out.exists():
        sys.exit("refusing to overwrite existing output dir")
    suite = json.loads(a.suite.read_text())
    tasks = [instantiate(t) for t in suite["tasks"] if not a.only or t["id"] == a.only]
    skill_text = SKILL.read_text()
    cc = subprocess.run([str(CLAUDE), "--version"], capture_output=True, text=True).stdout.strip()
    for t in tasks:
        t["_cc_version"] = cc
    plan = [(t, arm, r) for t in tasks for arm in ARMS for r in range(1, a.reps + 1)]
    random.Random(a.seed).shuffle(plan)
    a.out.mkdir(parents=True)
    manifest = {"suite_sha256": sha(a.suite.read_text()), "skill_sha256": sha(skill_text),
                "seed": a.seed, "model": a.model, "claude_code": cc,
                "order": [f"{t['id']}-{arm}-r{r}" for t, arm, r in plan],
                "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "dry_run": a.dry_run}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    with open(a.out / "metrics.jsonl", "a") as m:
        for t, arm, r in plan:
            rec = run_one(t, arm, r, a.out, a.model, skill_text, a.suite.parent, a.dry_run)
            m.write(json.dumps(rec) + "\n")
            m.flush()
            print(rec["run_id"], rec["outcome"], rec["wall_time_ms"], flush=True)


if __name__ == "__main__":
    main()
