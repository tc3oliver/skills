#!/usr/bin/env python3
"""Deterministic installer and auditor for the backlog-workflow Claude skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

VERSION = "1.2.0"
MANAGED_BEGIN = f"<!-- backlog-workflow:begin version={VERSION} -->"
MANAGED_END = "<!-- backlog-workflow:end -->"
MANAGED_BLOCK = f"""{MANAGED_BEGIN}
## Backlog Task Execution

- Default workflow mode is manual.
- Planning: align requirements and decompose into Backlog.md tasks without
  implementation. In Claude Code use `/backlog-plan`.
- Execute one task: `/backlog-run <TASK-ID>`; automatic: `/backlog-auto [TASK-ID]`.
- Read `.agent-workflow/WORKFLOW.md` for development policy and
  `.agent-workflow/PROJECT.md` for repository configuration.
- Backlog.md canonical instructions (`backlog instructions ...`) define how
  Backlog.md is operated; do not duplicate their mechanics. Prefer the Backlog.md
  CLI (`backlog task ...`) for task mutation; do not parse/rewrite
  `backlog/tasks/*.md` for normal task operations.
- Product requirements in the files listed in `.agent-workflow/PROJECT.md` remain
  authoritative. Do not expose internal autonomous-development mechanics in
  public README or product documentation.
{MANAGED_END}"""

REQUIREMENT_LIST_LIMIT = 30

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_DIR / "templates" / "project"

MANAGED_FILES = (
    Path(".agent-workflow/VERSION"),
    Path(".agent-workflow/config.yml"),
    Path(".agent-workflow/WORKFLOW.md"),
    Path(".agent-workflow/TASK-POLICY.md"),
    Path(".claude/skills/backlog-plan/SKILL.md"),
    Path(".claude/skills/backlog-run/SKILL.md"),
    Path(".claude/skills/backlog-auto/SKILL.md"),
    Path(".claude/skills/grilling/SKILL.md"),
    Path(".claude/skills/grilling/LICENSE"),
)

# Exact SHA-256 of the managed `.agent-workflow/TASK-TEMPLATE.md` shipped by
# backlog-workflow 1.0.x. Used only to prove an existing file is our deprecated
# managed copy before removing it during upgrade; an unmanaged/user-owned file
# never matches and is always preserved.
LEGACY_TASK_TEMPLATE_HASH = "297584e59adb52f2d57897aea727c5664815e6302eeba2a05691ac79050f4046"

EXCLUDED_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".cache",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "coverage",
    "target",
    "__pycache__",
    "backlog",
    ".backlog",
}


class InstallError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def resolve_project_root(project: str | None) -> Path:
    start = Path(project or os.getcwd()).expanduser().resolve()
    if not start.exists() or not start.is_dir():
        return start
    proc = run(["git", "rev-parse", "--show-toplevel"], start)
    if proc.returncode == 0 and proc.stdout.strip():
        return Path(proc.stdout.strip()).resolve()
    return start


def semver_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", value)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def template_text(relative: Path) -> str:
    return read_text(TEMPLATE_ROOT / relative)


MAX_PARALLEL_TASKS_PATTERN = re.compile(r"(?m)^([ \t]*max_parallel_tasks:[ \t]*)(\d+)[ \t]*$")


def render_config_yml(root: Path) -> str:
    """Render `.agent-workflow/config.yml`, preserving a project's own
    `automatic.max_parallel_tasks` value across upgrades. Every other line
    always matches the current template — only this one user-tunable field
    survives a template refresh.
    """
    template = template_text(Path(".agent-workflow/config.yml"))
    destination = root / ".agent-workflow/config.yml"
    if not destination.exists():
        return template
    match = MAX_PARALLEL_TASKS_PATTERN.search(read_text(destination))
    if not match:
        return template
    return MAX_PARALLEL_TASKS_PATTERN.sub(rf"\g<1>{match.group(2)}", template, count=1)


def expected_managed_text(root: Path, relative: Path) -> str:
    if relative == Path(".agent-workflow/config.yml"):
        return render_config_yml(root)
    return template_text(relative)


def workflow_managed(root: Path) -> bool:
    workflow = root / ".agent-workflow/WORKFLOW.md"
    return workflow.exists() and "Managed by backlog-workflow" in read_text(workflow)


def is_owned_managed_file(root: Path, relative: Path) -> bool:
    path = root / relative
    if not path.exists():
        return True
    text = read_text(path)
    if relative == Path(".agent-workflow/VERSION"):
        return workflow_managed(root) or text.strip() == VERSION
    if relative == Path(".claude/skills/grilling/LICENSE"):
        sibling = root / ".claude/skills/grilling/SKILL.md"
        return sibling.exists() and "Bundled by backlog-workflow" in read_text(sibling)
    if relative == Path(".claude/skills/grilling/SKILL.md"):
        return "Bundled by backlog-workflow" in text
    return "Managed by backlog-workflow" in text


def has_managed_block(path: Path) -> bool:
    return path.exists() and "<!-- backlog-workflow:begin" in read_text(path)


def choose_claude_file(root: Path) -> Path:
    root_file = root / "CLAUDE.md"
    nested_file = root / ".claude/CLAUDE.md"
    if has_managed_block(root_file):
        return root_file
    if has_managed_block(nested_file):
        return nested_file
    if root_file.exists() or not nested_file.exists():
        return root_file
    return nested_file


def entry_files(root: Path) -> list[Path]:
    """Instruction files that receive the managed block.

    Always manages CLAUDE.md (or `.claude/CLAUDE.md` when that is the only one
    present) and AGENTS.md. AGENTS.md is the cross-agent convention (Codex,
    Cursor, and others read it), so it is created when absent so those tools
    discover the workflow.
    """
    return [choose_claude_file(root), root / "AGENTS.md"]


def inspect_managed_block(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "missing-file", None
    text = read_text(path)
    begins = list(re.finditer(r"<!-- backlog-workflow:begin version=[^>]+ -->", text))
    ends = list(re.finditer(re.escape(MANAGED_END), text))
    if not begins and not ends:
        return "missing-block", text
    if len(begins) != 1 or len(ends) != 1 or begins[0].start() > ends[0].start():
        return "malformed-block", text
    block = text[begins[0].start() : ends[0].end()]
    return ("clean" if block == MANAGED_BLOCK else "drift"), text


def render_entry_file(path: Path) -> str:
    if not path.exists():
        return MANAGED_BLOCK + "\n"
    text = read_text(path)
    begins = list(re.finditer(r"<!-- backlog-workflow:begin version=[^>]+ -->", text))
    ends = list(re.finditer(re.escape(MANAGED_END), text))
    if not begins and not ends:
        separator = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + separator + MANAGED_BLOCK + "\n"
    if len(begins) != 1 or len(ends) != 1 or begins[0].start() > ends[0].start():
        raise InstallError(f"Malformed or duplicate backlog-workflow block in {path}")
    return text[: begins[0].start()] + MANAGED_BLOCK + text[ends[0].end() :]


def backlog_workspace_exists(root: Path) -> bool:
    candidates = [
        root / "backlog/config.yml",
        root / ".backlog/config.yml",
        root / "backlog.config.yml",
    ]
    if any(path.exists() for path in candidates):
        return True
    for directory in (root / "backlog/tasks", root / ".backlog/tasks"):
        if directory.exists():
            return True
    return False


def inside_git_repo(root: Path) -> bool:
    proc = run(["git", "rev-parse", "--is-inside-work-tree"], root)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def init_backlog_workspace(root: Path, backlog_cli: str) -> str:
    """Create a Backlog.md workspace non-interactively using the verified CLI.

    Returns a status note. `backlog_cli` is the already-verified Backlog.md
    command (for example `backlog`, `npx backlog`, or `npx backlog.md`); it is
    used verbatim so initialization never depends on a hardcoded npx.
    """
    cmd = backlog_init_command(backlog_cli, detect_project_name(root), inside_git_repo(root))

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        raise InstallError("backlog init timed out after 300s") from None
    if proc.returncode != 0:
        detail = " ".join((proc.stdout or "").split())[-300:]
        raise InstallError(f"backlog init failed (exit {proc.returncode}): {detail}")
    if not backlog_workspace_exists(root):
        raise InstallError("backlog init reported success but no workspace was created")
    return "backlog workspace initialized"


def parse_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except (OSError, json.JSONDecodeError):
        return {}


def detect_project_name(root: Path) -> str:
    package_json = root / "package.json"
    if package_json.exists():
        name = parse_json(package_json).get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = read_text(pyproject)
        project = re.search(r"(?ms)^\[project\].*?^name\s*=\s*[\"']([^\"']+)", text)
        poetry = re.search(r"(?ms)^\[tool\.poetry\].*?^name\s*=\s*[\"']([^\"']+)", text)
        match = project or poetry
        if match:
            return match.group(1).strip()

    cargo = root / "Cargo.toml"
    if cargo.exists():
        match = re.search(r"(?ms)^\[package\].*?^name\s*=\s*[\"']([^\"']+)", read_text(cargo))
        if match:
            return match.group(1).strip()

    go_mod = root / "go.mod"
    if go_mod.exists():
        match = re.search(r"^module\s+(\S+)", read_text(go_mod), re.MULTILINE)
        if match:
            return match.group(1).rstrip("/").split("/")[-1]

    return root.name


def detect_default_branch(root: Path) -> str:
    proc = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip().split("/", 1)[-1]
    proc = run(["git", "symbolic-ref", "--short", "HEAD"], root)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    for candidate in ("main", "master"):
        proc = run(["git", "show-ref", "--verify", f"refs/heads/{candidate}"], root)
        if proc.returncode == 0:
            return candidate
    return "not detected"


def backlog_cli_candidates(root: Path) -> list[str]:
    """Ordered Backlog.md CLI command candidates to probe, deduped.

    `npx backlog` is included only when backlog.md is installed locally
    (`node_modules/.bin/backlog`); a bare `npx backlog` otherwise resolves to the
    unrelated npm `backlog` package, so it is never assumed without a local bin.
    Every candidate is still verified by `verify_backlog_cli` before use.
    """
    candidates: list[str] = []
    local_bin = (root / "node_modules/.bin/backlog").exists() or (
        root / "node_modules/.bin/backlog.cmd"
    ).exists()
    if local_bin:
        candidates.append("npx backlog")
    if shutil.which("backlog"):
        candidates.append("backlog")
    for path in (root / "CLAUDE.md", root / ".claude/CLAUDE.md", root / "AGENTS.md"):
        if not path.exists():
            continue
        text = read_text(path)
        for cand in ("npx backlog.md", "npx backlog"):
            if re.search(rf"(?m)(?:^|[`$\s]){re.escape(cand)}\s", text):
                candidates.append(cand)
    package_json = root / "package.json"
    if package_json.exists():
        data = parse_json(package_json)
        deps: dict[str, object] = {}
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            value = data.get(key)
            if isinstance(value, dict):
                deps.update(value)
        if "backlog.md" in deps:
            candidates.append("npx backlog.md")
    if shutil.which("npx"):
        candidates.append("npx backlog.md")
    seen: set[str] = set()
    ordered: list[str] = []
    for cand in candidates:
        if cand not in seen:
            seen.add(cand)
            ordered.append(cand)
    return ordered


def verify_backlog_cli(command: str, root: Path) -> bool:
    """Probe a candidate command read-only and confirm it is Backlog.md.

    Rejects any `backlog` binary that is not Backlog.md (for example the
    unrelated npm `backlog` package). A candidate is accepted only when
    `instructions overview` exits 0 and emits the Backlog.md overview header.
    """
    parts = command.split()
    if not parts or not shutil.which(parts[0]):
        return False
    try:
        proc = subprocess.run(
            parts + ["instructions", "overview"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    if proc.returncode != 0:
        return False
    return "## backlog.md overview" in (proc.stdout or "").lower()


def resolve_backlog_cli(root: Path) -> str | None:
    """Return the first candidate that verifies as Backlog.md, else None."""
    for candidate in backlog_cli_candidates(root):
        if verify_backlog_cli(candidate, root):
            return candidate
    return None


def recorded_backlog_cli(project_md_text: str | None) -> str | None:
    """Return the Backlog CLI command recorded in PROJECT.md, if any."""
    if not project_md_text:
        return None
    match = re.search(r"(?m)^- Backlog CLI:\s*`?([^`\n]+?)`?\s*$", project_md_text)
    if not match:
        return None
    value = match.group(1).strip()
    return None if value == "not detected" else value


def effective_backlog_cli(root: Path, project_md_text: str | None) -> str | None:
    """The verified Backlog CLI to use for this project.

    PROJECT.md is project-owned configuration: when it already records a Backlog
    CLI command, verify that command first and keep using it as long as it still
    works. Only fall back to candidate discovery when nothing is recorded or the
    recorded command no longer verifies. This prevents installing a second valid
    CLI later from creating false drift.
    """
    recorded = recorded_backlog_cli(project_md_text)
    if recorded and verify_backlog_cli(recorded, root):
        return recorded
    return resolve_backlog_cli(root)


def backlog_init_command(backlog_cli: str, project_name: str, in_git_repo: bool) -> list[str]:
    """Build the `init` invocation from the verified Backlog CLI command.

    Works for a global `backlog`, a local `npx backlog`, and one-off
    `npx backlog.md`. `--yes` is inserted for npx invocations so a one-off run
    does not prompt.
    """
    parts = backlog_cli.split()
    if parts and parts[0] == "npx":
        parts = ["npx", "--yes", *parts[1:]]
    cmd = [*parts, "init", project_name, "--defaults", "--agent-instructions", "none"]
    if not in_git_repo:
        cmd.append("--no-git")
    return cmd


def detect_task_prefix(root: Path) -> str:
    for path in (root / "backlog.config.yml", root / "backlog/config.yml", root / ".backlog/config.yml"):
        if not path.exists():
            continue
        text = read_text(path)
        match = re.search(r"(?mi)^\s*(?:task[_-]?prefix|prefix)\s*:\s*[\"']?([A-Za-z0-9_-]+)", text)
        if match:
            return match.group(1)
    return "not detected"


def iter_project_files(root: Path, max_depth: int = 5) -> Iterable[Path]:
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts)
        if depth >= max_depth:
            dirnames[:] = []
        else:
            dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIRS]
        for filename in filenames:
            yield current_path / filename


def detect_requirement_sources(root: Path) -> list[str]:
    patterns = ("prd", "requirement", "spec", "architecture", "adr", "decision", "design-doc")
    results: list[str] = []
    for path in iter_project_files(root):
        relative = path.relative_to(root)
        lowered = str(relative).lower()
        if path.suffix.lower() not in {".md", ".txt", ".rst", ".adoc"}:
            continue
        if any(pattern in lowered for pattern in patterns):
            results.append(relative.as_posix())
    return sorted(dict.fromkeys(results))


def add_command(commands: dict[str, str], key: str, value: str) -> None:
    if commands.get(key) in (None, "not detected"):
        commands[key] = value


def detect_validation_commands(root: Path) -> dict[str, str]:
    commands = {key: "not detected" for key in ("setup", "format", "lint", "typecheck", "tests", "build")}

    package_json = root / "package.json"
    if package_json.exists():
        data = parse_json(package_json)
        scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
        package_runner = "npm run"
        if (root / "pnpm-lock.yaml").exists():
            package_runner = "pnpm"
        elif (root / "yarn.lock").exists():
            package_runner = "yarn"
        elif (root / "bun.lock").exists() or (root / "bun.lockb").exists():
            package_runner = "bun run"
        install = "npm ci"
        if package_runner == "pnpm":
            install = "pnpm install --frozen-lockfile"
        elif package_runner == "yarn":
            install = "yarn install --frozen-lockfile"
        elif package_runner == "bun run":
            install = "bun install --frozen-lockfile"
        add_command(commands, "setup", install)

        aliases = {
            "format": ("format", "fmt", "format:check"),
            "lint": ("lint",),
            "typecheck": ("typecheck", "type-check", "check-types"),
            "tests": ("test", "test:unit"),
            "build": ("build",),
        }
        for category, names in aliases.items():
            for name in names:
                if name in scripts:
                    add_command(commands, category, f"{package_runner} {name}")
                    break

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = read_text(pyproject)
        if "[tool.ruff" in text:
            add_command(commands, "lint", "ruff check .")
            add_command(commands, "format", "ruff format --check .")
        if "[tool.mypy" in text:
            add_command(commands, "typecheck", "mypy .")
        if "[tool.pytest" in text or "pytest" in text:
            add_command(commands, "tests", "pytest")
        if (root / "poetry.lock").exists():
            add_command(commands, "setup", "poetry install")
        elif (root / "uv.lock").exists():
            add_command(commands, "setup", "uv sync")

    makefile = root / "Makefile"
    if makefile.exists():
        text = read_text(makefile)
        for key, targets in {
            "setup": ("setup", "install"),
            "format": ("format", "fmt"),
            "lint": ("lint",),
            "typecheck": ("typecheck", "type-check"),
            "tests": ("test", "tests"),
            "build": ("build",),
        }.items():
            for target in targets:
                if re.search(rf"(?m)^{re.escape(target)}\s*:", text):
                    add_command(commands, key, f"make {target}")
                    break

    if (root / "Cargo.toml").exists():
        add_command(commands, "format", "cargo fmt --check")
        add_command(commands, "lint", "cargo clippy --all-targets --all-features -- -D warnings")
        add_command(commands, "tests", "cargo test")
        add_command(commands, "build", "cargo build")

    if (root / "go.mod").exists():
        add_command(commands, "format", "test -z \"$(gofmt -l .)\"")
        add_command(commands, "tests", "go test ./...")
        add_command(commands, "build", "go build ./...")

    return commands


def detect_adoption_mode(root: Path) -> str:
    meaningful = 0
    code_extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".kt", ".cs", ".rb", ".php"}
    for path in iter_project_files(root, max_depth=3):
        if path.suffix.lower() in code_extensions:
            meaningful += 1
            if meaningful >= 3:
                return "existing"
    return "existing" if backlog_workspace_exists(root) else "new"


def render_project_md(root: Path, backlog_cli: str) -> str:
    requirements = detect_requirement_sources(root)
    commands = detect_validation_commands(root)
    shown = requirements[:REQUIREMENT_LIST_LIMIT]
    requirement_lines = (
        "\n".join(f"- `{path}` — detected candidate; verify authority before use" for path in shown)
        if shown
        else "- None detected. Product implementation tasks require an explicit authoritative source before passing the Ready Gate."
    )
    if len(requirements) > len(shown):
        requirement_lines += (
            f"\n- _{len(requirements) - len(shown)} further candidates detected but not listed;"
            " add the authoritative ones manually._"
        )
    return f"""<!-- Generated by backlog-workflow {VERSION}; project-maintained after creation -->

# Project Workflow Configuration

## Identity

- Project: {detect_project_name(root)}
- Adoption mode: {detect_adoption_mode(root)}
- Task prefix: {detect_task_prefix(root)}
- Default branch: {detect_default_branch(root)}
- Backlog CLI: `{backlog_cli}`

## Requirement sources

{requirement_lines}

## Validation commands

- Setup: `{commands['setup']}`
- Format: `{commands['format']}`
- Lint: `{commands['lint']}`
- Typecheck: `{commands['typecheck']}`
- Tests: `{commands['tests']}`
- Build: `{commands['build']}`

## Project-specific constraints

- Preserve repository rules from applicable `CLAUDE.md`, `AGENTS.md`, and `.claude/rules/` files.
- Add only constraints supported by repository evidence.

## Documentation synchronization

- Keep authoritative requirement sources and any Requirement Matrix synchronized with implementation changes.
- Record exact project-specific paths here when confirmed.

## Notes

- Commands marked `not detected` must not be invented during task execution.
- Verify detected requirement candidates before treating them as authoritative.
- Update this file when project commands, requirement locations, or delivery rules change.
"""


def stale_project_facts(root: Path, text: str, backlog_cli: str | None) -> list[str]:
    """Report recorded PROJECT.md facts that no longer match repository evidence.

    PROJECT.md stays user-owned, so this only warns; it never rewrites the file.
    A recorded value is compared only when the generated line is still present and
    the project has not deliberately replaced it with something else. `backlog_cli`
    is the verified command (None when no candidate verified); it is passed in so
    audit does not probe twice.
    """
    findings: list[str] = []
    checks = (
        ("Default branch", detect_default_branch(root)),
        ("Task prefix", detect_task_prefix(root)),
    )
    for label, detected in checks:
        if detected == "not detected":
            continue
        match = re.search(rf"(?m)^- {re.escape(label)}:\s*`?([^`\n]+?)`?\s*$", text)
        if not match:
            continue
        recorded = match.group(1).strip()
        if recorded == "not detected":
            findings.append(f"PROJECT.md {label} is 'not detected' but {detected!r} is now detectable")
        elif recorded != detected:
            findings.append(f"PROJECT.md {label} records {recorded!r} but repository evidence shows {detected!r}")
    if backlog_cli:
        match = re.search(r"(?m)^- Backlog CLI:\s*`?([^`\n]+?)`?\s*$", text)
        if match:
            recorded = match.group(1).strip()
            if recorded == "not detected":
                findings.append(f"PROJECT.md Backlog CLI is 'not detected' but {backlog_cli!r} is now verified")
            elif recorded != backlog_cli:
                findings.append(
                    f"PROJECT.md Backlog CLI records {recorded!r} but verified command is {backlog_cli!r}"
                )
    return findings


def installed_version(root: Path) -> str | None:
    path = root / ".agent-workflow/VERSION"
    if not path.exists():
        return None
    return read_text(path).strip()


def preflight_conflicts(root: Path) -> list[str]:
    conflicts: list[str] = []
    for relative in MANAGED_FILES:
        if not is_owned_managed_file(root, relative):
            conflicts.append(f"unmanaged file occupies managed path: {relative.as_posix()}")

    root_claude = root / "CLAUDE.md"
    nested_claude = root / ".claude/CLAUDE.md"
    if has_managed_block(root_claude) and has_managed_block(nested_claude):
        conflicts.append("managed block exists in both CLAUDE.md and .claude/CLAUDE.md")

    for entry in entry_files(root):
        block_state, _ = inspect_managed_block(entry)
        if block_state == "malformed-block":
            conflicts.append(f"malformed or duplicate managed block: {entry.relative_to(root).as_posix()}")
    return conflicts


def migrate_deprecated_task_template(root: Path) -> str | None:
    """Remove the obsolete managed `.agent-workflow/TASK-TEMPLATE.md`.

    Removed only when the file is provably the backlog-workflow 1.0.x managed
    copy (exact content hash match). An unmanaged or user-owned file, or one the
    user edited after install, never matches and is left untouched.
    """
    path = root / ".agent-workflow/TASK-TEMPLATE.md"
    if not path.exists():
        return None
    text = read_text(path)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest == LEGACY_TASK_TEMPLATE_HASH:
        path.unlink()
        return "removed deprecated managed file: .agent-workflow/TASK-TEMPLATE.md"
    return None


def apply(root: Path, action: str) -> tuple[list[str], list[str]]:
    current = installed_version(root)
    current_tuple = semver_tuple(current) if current else None
    target_tuple = semver_tuple(VERSION)
    if current_tuple and target_tuple and current_tuple > target_tuple:
        raise InstallError(f"Project workflow {current} is newer than installer {VERSION}; refusing downgrade")

    conflicts = preflight_conflicts(root)
    if conflicts:
        raise InstallError("; ".join(conflicts))

    # Resolve and verify the required Backlog.md CLI before any repository
    # mutation. If it cannot be verified, fail with the repository unchanged.
    # Prefer the CLI already recorded in PROJECT.md when it still verifies.
    project_md = root / ".agent-workflow/PROJECT.md"
    existing_project_md = read_text(project_md) if project_md.exists() else None
    backlog_cli = effective_backlog_cli(root, existing_project_md)
    if backlog_cli is None:
        raise InstallError(
            "Backlog.md CLI is the required interface but no candidate verified as "
            "Backlog.md (a `backlog` on PATH may be a different package). Install "
            "Backlog.md so `npx backlog.md instructions overview` succeeds, then re-run."
        )

    changed: list[str] = []
    preserved: list[str] = []

    if not backlog_workspace_exists(root):
        changed.append(init_backlog_workspace(root, backlog_cli))

    for relative in MANAGED_FILES:
        destination = root / relative
        expected = expected_managed_text(root, relative)
        if destination.exists() and read_text(destination) == expected:
            preserved.append(relative.as_posix())
            continue
        atomic_write(destination, expected)
        changed.append(relative.as_posix())

    migrated = migrate_deprecated_task_template(root)
    if migrated:
        changed.append(migrated)

    if not project_md.exists():
        atomic_write(project_md, render_project_md(root, backlog_cli))
        changed.append(".agent-workflow/PROJECT.md")
    else:
        preserved.append(".agent-workflow/PROJECT.md")

    for entry in entry_files(root):
        rendered = render_entry_file(entry)
        relative = entry.relative_to(root).as_posix()
        if not entry.exists() or read_text(entry) != rendered:
            atomic_write(entry, rendered)
            changed.append(relative)
        else:
            preserved.append(relative)

    return changed, preserved


def audit(root: Path) -> list[str]:
    drift: list[str] = []
    if not backlog_workspace_exists(root):
        drift.append("Backlog.md workspace not detected")

    project_md = root / ".agent-workflow/PROJECT.md"
    project_md_text = read_text(project_md) if project_md.exists() else None
    # Prefer the CLI already recorded in PROJECT.md when it still verifies, so
    # installing a second valid CLI later does not create false drift.
    backlog_cli = effective_backlog_cli(root, project_md_text)
    if backlog_cli is None:
        drift.append("Backlog.md CLI not verified (required interface unavailable)")

    for relative in MANAGED_FILES:
        destination = root / relative
        if not destination.exists():
            drift.append(f"missing: {relative.as_posix()}")
            continue
        if not is_owned_managed_file(root, relative):
            drift.append(f"unmanaged-path conflict: {relative.as_posix()}")
            continue
        expected = expected_managed_text(root, relative)
        if read_text(destination) != expected:
            drift.append(f"content drift: {relative.as_posix()}")

    if not project_md.exists():
        drift.append("missing: .agent-workflow/PROJECT.md")
    else:
        drift.extend(stale_project_facts(root, project_md_text, backlog_cli))

    root_claude = root / "CLAUDE.md"
    nested_claude = root / ".claude/CLAUDE.md"
    if has_managed_block(root_claude) and has_managed_block(nested_claude):
        drift.append("managed block exists in both CLAUDE.md and .claude/CLAUDE.md")
    for entry in entry_files(root):
        block_state, _ = inspect_managed_block(entry)
        if block_state != "clean":
            relative = entry.relative_to(root).as_posix()
            drift.append(f"managed block {block_state}: {relative}")

    config = root / ".agent-workflow/config.yml"
    if config.exists():
        text = read_text(config)
        if not re.search(r"(?m)^default_mode:\s*manual\s*$", text):
            drift.append("default mode is not manual")

    return drift


def print_report(action: str, status: str, root: Path, changes: list[str], validation: list[str]) -> None:
    version = installed_version(root) or "not installed"
    print("Backlog workflow")
    print(f"- Action: {action}")
    print(f"- Status: {status}")
    print(f"- Version: {version}")
    print(f"- Changes: {', '.join(changes) if changes else 'none'}")
    print(f"- Validation: {'; '.join(validation) if validation else 'clean'}")
    if status in ("Installed", "Upgraded") and any(c.startswith(".claude/skills/") for c in changes):
        print(
            "- Next step: run /reload-skills (or restart Claude Code / start a new "
            "session) so it reloads project skills before using /backlog-plan, "
            "/backlog-run, or /backlog-auto."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "audit", "upgrade"), nargs="?", default="apply")
    parser.add_argument("--project", help="Project path; defaults to current Git root or working directory")
    args = parser.parse_args()

    root = resolve_project_root(args.project)
    if not root.exists() or not root.is_dir():
        print_report(args.action, "Blocked", root, [], ["project root does not exist"])
        return 2

    try:
        if args.action == "audit":
            drift = audit(root)
            print_report("audit", "Clean" if not drift else "Drift detected", root, [], drift)
            return 0 if not drift else 2

        before = installed_version(root)
        changed, _preserved = apply(root, args.action)
        # PROJECT.md is intentionally preserved, so its advisory staleness warnings
        # must not fail an otherwise correct install.
        drift = [item for item in audit(root) if not item.startswith("PROJECT.md ")]
        if drift:
            print_report(args.action, "Drift detected", root, changed, drift)
            return 2
        # "Installed" means nothing was present before; any other file change to an
        # existing install is an upgrade, including same-version template fixes.
        status = "Installed" if not before else ("Upgraded" if changed else "Clean")
        print_report(args.action, status, root, changed, [])
        return 0
    except InstallError as exc:
        print_report(args.action, "Blocked", root, [], [str(exc)])
        return 2
    except OSError as exc:
        print_report(args.action, "Blocked", root, [], [f"filesystem error: {exc}"])
        return 2


if __name__ == "__main__":
    sys.exit(main())
