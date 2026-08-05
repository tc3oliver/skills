#!/usr/bin/env python3
"""Deterministic installer and auditor for the backlog-workflow Claude skill."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

VERSION = "1.0.0"
MANAGED_BEGIN = f"<!-- backlog-workflow:begin version={VERSION} -->"
MANAGED_END = "<!-- backlog-workflow:end -->"
MANAGED_BLOCK = f"""{MANAGED_BEGIN}
## Backlog Task Execution

- The default workflow mode is manual.
- Plan: align requirements and create Backlog.md tasks without implementation.
  In Claude Code use `/backlog-plan`; otherwise follow the manual-planning
  section of `.agent-workflow/WORKFLOW.md`.
- Execute: run exactly one task, then stop. In Claude Code use
  `/backlog-run <TASK-ID>`; otherwise follow the manual-execution section.
- Automatic execution runs only on explicit request (`/backlog-auto [TASK-ID]`
  in Claude Code). Requests such as "continue development" do not enable it.
- Product requirements remain authoritative in the files listed in `.agent-workflow/PROJECT.md`.
- Backlog.md is authoritative for task decomposition, dependencies, priority, status, plans, and validation evidence.
- Follow `.agent-workflow/WORKFLOW.md` and `.agent-workflow/PROJECT.md`.
- Do not expose internal autonomous-development mechanics in public README or product documentation.
{MANAGED_END}"""

REQUIREMENT_LIST_LIMIT = 30

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_DIR / "templates" / "project"

MANAGED_FILES = (
    Path(".agent-workflow/VERSION"),
    Path(".agent-workflow/config.yml"),
    Path(".agent-workflow/WORKFLOW.md"),
    Path(".agent-workflow/TASK-TEMPLATE.md"),
    Path(".claude/skills/backlog-plan/SKILL.md"),
    Path(".claude/skills/backlog-run/SKILL.md"),
    Path(".claude/skills/backlog-auto/SKILL.md"),
    Path(".claude/skills/grilling/SKILL.md"),
    Path(".claude/skills/grilling/LICENSE"),
)

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

    `AGENTS.md` is the cross-agent convention (Codex, Cursor, and others read it),
    so it is kept in sync whenever it exists. It is never created from nothing:
    only projects that already opted into it get the block.
    """
    targets = [choose_claude_file(root)]
    agents_file = root / "AGENTS.md"
    if agents_file.exists() or has_managed_block(agents_file):
        targets.append(agents_file)
    return targets


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


def render_claude_file(path: Path) -> str:
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


def init_backlog_workspace(root: Path) -> str:
    """Create a Backlog.md workspace non-interactively. Returns a status note."""
    if not shutil.which("npx"):
        raise InstallError("Backlog.md workspace missing and npx is unavailable to initialize it")

    cmd = [
        "npx",
        "--yes",
        "backlog.md",
        "init",
        detect_project_name(root),
        "--defaults",
        # This workflow owns its own CLAUDE.md block, so skip generated agent files.
        "--agent-instructions",
        "none",
    ]
    if not inside_git_repo(root):
        cmd.append("--no-git")

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


def detect_backlog_cli(root: Path) -> str:
    # Verified executables first; a documented command is only trusted when it
    # appears as a real command, not as prose that merely mentions "backlog".
    local_candidates = [
        root / "node_modules/.bin/backlog",
        root / "node_modules/.bin/backlog.cmd",
    ]
    if any(path.exists() for path in local_candidates):
        return "npx backlog"
    if shutil.which("backlog"):
        return "backlog"

    documented_files = [root / "CLAUDE.md", root / ".claude/CLAUDE.md", root / "AGENTS.md"]
    for path in documented_files:
        if not path.exists():
            continue
        text = read_text(path)
        for candidate in ("npx backlog.md", "npx backlog"):
            if re.search(rf"(?m)(?:^|[`$\s]){re.escape(candidate)}\s", text):
                return candidate

    package_json = root / "package.json"
    if package_json.exists():
        data = parse_json(package_json)
        deps = {}
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            value = data.get(key)
            if isinstance(value, dict):
                deps.update(value)
        if "backlog.md" in deps:
            return "npx backlog"

    if shutil.which("npx"):
        return "npx backlog.md"
    return "not detected"


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


def render_project_md(root: Path) -> str:
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
- Backlog CLI: `{detect_backlog_cli(root)}`

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


def stale_project_facts(root: Path, text: str) -> list[str]:
    """Report recorded PROJECT.md facts that no longer match repository evidence.

    PROJECT.md stays user-owned, so this only warns; it never rewrites the file.
    A recorded value is compared only when the generated line is still present and
    the project has not deliberately replaced it with something else.
    """
    findings: list[str] = []
    checks = (
        ("Default branch", detect_default_branch(root)),
        ("Backlog CLI", detect_backlog_cli(root)),
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


def apply(root: Path, action: str) -> tuple[list[str], list[str]]:
    current = installed_version(root)
    current_tuple = semver_tuple(current) if current else None
    target_tuple = semver_tuple(VERSION)
    if current_tuple and target_tuple and current_tuple > target_tuple:
        raise InstallError(f"Project workflow {current} is newer than installer {VERSION}; refusing downgrade")

    conflicts = preflight_conflicts(root)
    if conflicts:
        raise InstallError("; ".join(conflicts))

    changed: list[str] = []
    preserved: list[str] = []

    if not backlog_workspace_exists(root):
        changed.append(init_backlog_workspace(root))

    for relative in MANAGED_FILES:
        destination = root / relative
        expected = template_text(relative)
        if destination.exists() and read_text(destination) == expected:
            preserved.append(relative.as_posix())
            continue
        atomic_write(destination, expected)
        changed.append(relative.as_posix())

    project_md = root / ".agent-workflow/PROJECT.md"
    if not project_md.exists():
        atomic_write(project_md, render_project_md(root))
        changed.append(".agent-workflow/PROJECT.md")
    else:
        preserved.append(".agent-workflow/PROJECT.md")

    for entry in entry_files(root):
        rendered = render_claude_file(entry)
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

    for relative in MANAGED_FILES:
        destination = root / relative
        if not destination.exists():
            drift.append(f"missing: {relative.as_posix()}")
            continue
        if not is_owned_managed_file(root, relative):
            drift.append(f"unmanaged-path conflict: {relative.as_posix()}")
            continue
        expected = template_text(relative)
        if read_text(destination) != expected:
            drift.append(f"content drift: {relative.as_posix()}")

    project_md = root / ".agent-workflow/PROJECT.md"
    if not project_md.exists():
        drift.append("missing: .agent-workflow/PROJECT.md")
    else:
        drift.extend(stale_project_facts(root, read_text(project_md)))

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
