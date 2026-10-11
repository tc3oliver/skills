"""Benchmark dataset integrity guard for live OpenCode experiments.

This detects obvious cross-workspace tool access and checkout mutations.
It is evidence validation, NOT a replacement for an operating-system sandbox:
a shell command can execute arbitrary Python outside CLI permission checks.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def snapshot_dataset(suite: Path) -> dict[str, str]:
    """Fingerprint all fixtures, hidden oracles and suite declaration."""
    root = suite.parent
    roots = [suite, root / "fixtures", root / "oracles"]
    result: dict[str, str] = {}
    for item in roots:
        paths = item.rglob("*") if item.is_dir() else (item,)
        for path in paths:
            if path.is_symlink():
                raise RuntimeError(f"dataset symlink not allowed: {path}")
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def assert_clean_checkout(suite: Path, root: Path) -> None:
    """Avoid starting an experiment on an already-modified fixture/oracle."""
    try:
        rel = suite.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("OpenCode suite must live inside its checked-out repository") from exc
    paths = ["betfirst/experiments/fixtures", "betfirst/experiments/oracles", str(rel)]
    check = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all",
         "--", *paths],
        capture_output=True, text=True, check=False,
    )
    if check.returncode != 0:
        raise RuntimeError(f"unable to verify clean fixture checkout: {check.stderr.strip()}")
    if check.stdout.strip():
        raise RuntimeError(
            "Benchmark fixture/oracle checkout already modified; DO NOT rerun until "
            "changes are inspected and archived:\n" + check.stdout.strip()
        )


def unexpected_tool_paths(output: str, workspace: Path, repo: Path,
                          scratch: Path | None = None) -> list[str]:
    """Detect read/edit/shell targeting checkout or absolute paths outside work.

    Only structured tool calls count. Prompt or model prose is never evidence
    that a tool actually accessed a path.
    """
    bad = []
    workspace = workspace.resolve()
    repo = repo.resolve()
    scratch = scratch.resolve() if scratch is not None else None
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") != "tool_use":
            continue
        part = event.get("part")
        if not isinstance(part, dict):
            continue
        tool = str(part.get("tool", "unknown"))
        state = part.get("state")
        inputs = state.get("input") if isinstance(state, dict) else None
        if not isinstance(inputs, dict):
            continue
        # Any explicit repository path in a tool invocation is a leak:
        # this tree contains hidden oracles and pristine fixture sources.
        if str(repo) in json.dumps(inputs, ensure_ascii=False):
            bad.append(f"{tool}: explicit source checkout reference")
            continue
        for key in ("path", "workdir", "directory", "filePath", "cwd"):
            value = inputs.get(key)
            if not isinstance(value, str) or not value.startswith("/"):
                continue
            try:
                in_workspace = Path(value).resolve().is_relative_to(workspace)
            except (OSError, RuntimeError):
                in_workspace = False
            # Only a dedicated per-session scratch directory is permitted.
            # Never blanket-allow system /tmp: it can contain other sessions.
            in_scratch = (scratch is not None and
                          Path(value).resolve().is_relative_to(scratch))
            if not in_workspace and not in_scratch:
                bad.append(f"{tool}: path outside fixture worktree ({key})")
                break
    return bad
