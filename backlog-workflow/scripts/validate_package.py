#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = ROOT / "templates" / "project"
SKILLS = [
    ROOT / "SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/backlog-plan/SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/backlog-review/SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/backlog-run/SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/backlog-auto/SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/grilling/SKILL.md",
]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()

# Tokens that must no longer appear anywhere in the installed workflow. Each is
# a 1.0 behavior removed in 1.1.0, retained only as intentional migration logic.
FORBIDDEN_TOKENS = (
    "TASK-TEMPLATE.md",
    "Background board",
    "Board:",
    "claude mcp add",
    "codex mcp add",
)


def scalar(value: str) -> object:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    return value


def frontmatter(path: Path) -> dict:
    """Parse the flat `key: value` skill frontmatter without a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"missing frontmatter: {path}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError(f"unterminated frontmatter: {path}")

    data: dict[str, object] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t" or ":" not in line:
            raise AssertionError(f"unsupported non-scalar frontmatter line in {path}: {line!r}")
        key, _, raw = line.partition(":")
        data[key.strip()] = scalar(raw)
    if not data:
        raise AssertionError(f"invalid frontmatter mapping: {path}")
    return data


def assert_no_forbidden(text: str, where: str) -> None:
    for token in FORBIDDEN_TOKENS:
        if token in text:
            raise AssertionError(f"forbidden 1.0 token {token!r} present in {where}")


def iter_template_files() -> list[Path]:
    return [p for p in TEMPLATE_ROOT.rglob("*") if p.is_file()]


def main() -> int:
    if not re.fullmatch(r"\d+\.\d+\.\d+", VERSION):
        raise AssertionError(f"VERSION file is not semver: {VERSION!r}")

    seen: set[str] = set()
    for path in SKILLS:
        data = frontmatter(path)
        name = data.get("name")
        if not isinstance(name, str) or not name:
            raise AssertionError(f"missing name: {path}")
        if name in seen:
            raise AssertionError(f"duplicate skill name: {name}")
        seen.add(name)
        if name == "backlog":
            raise AssertionError("a '/backlog' skill must never be generated")
        if len(path.read_text(encoding="utf-8").splitlines()) > 500:
            raise AssertionError(f"SKILL.md exceeds 500 lines: {path}")

    for name in ("backlog-workflow", "backlog-plan", "backlog-review", "backlog-run", "backlog-auto"):
        path = next(path for path in SKILLS if frontmatter(path).get("name") == name)
        if frontmatter(path).get("disable-model-invocation") is not True:
            raise AssertionError(f"{name} must be user-triggered only")

    grilling = next(path for path in SKILLS if frontmatter(path).get("name") == "grilling")
    if frontmatter(grilling).get("user-invocable") is not False:
        raise AssertionError("grilling must be model-invoked only")
    if frontmatter(grilling).get("disable-model-invocation") is True:
        raise AssertionError("grilling cannot disable model invocation")

    config = (TEMPLATE_ROOT / ".agent-workflow/config.yml").read_text(encoding="utf-8")
    if "default_mode: manual" not in config:
        raise AssertionError("default mode must be manual")
    if f"workflow_version: {VERSION}" not in config:
        raise AssertionError(f"config.yml workflow_version must be {VERSION}")

    # Managed-by markers must carry the current version, not a stale one.
    managed_marker = f"Managed by backlog-workflow {VERSION}"
    for marker_path in (
        TEMPLATE_ROOT / ".agent-workflow/WORKFLOW.md",
        TEMPLATE_ROOT / ".agent-workflow/PLAN.md",
        TEMPLATE_ROOT / ".agent-workflow/EXECUTION.md",
        TEMPLATE_ROOT / ".agent-workflow/AUTO.md",
        TEMPLATE_ROOT / ".agent-workflow/config.yml",
        TEMPLATE_ROOT / ".agent-workflow/TASK-POLICY.md",
        TEMPLATE_ROOT / ".claude/skills/backlog-plan/SKILL.md",
        TEMPLATE_ROOT / ".claude/skills/backlog-review/SKILL.md",
        TEMPLATE_ROOT / ".claude/skills/backlog-run/SKILL.md",
        TEMPLATE_ROOT / ".claude/skills/backlog-auto/SKILL.md",
    ):
        text = marker_path.read_text(encoding="utf-8")
        if managed_marker not in text:
            raise AssertionError(f"missing/updated managed marker: {marker_path.name}")

    # TASK-POLICY replaces TASK-TEMPLATE; TASK-TEMPLATE must not exist.
    if not (TEMPLATE_ROOT / ".agent-workflow/TASK-POLICY.md").exists():
        raise AssertionError("TASK-POLICY.md template is missing")
    if (TEMPLATE_ROOT / ".agent-workflow/TASK-TEMPLATE.md").exists():
        raise AssertionError("TASK-TEMPLATE.md template must be removed")

    workflow = (TEMPLATE_ROOT / ".agent-workflow/WORKFLOW.md").read_text(encoding="utf-8")
    required = [
        "Acceptance Criteria all pass.",
        "Required tests, lint, typecheck, and build pass.",
        "Documentation and Requirement Matrix are synchronized.",
        "The task record contains validation evidence.",
    ]
    for item in required:
        if item not in workflow:
            raise AssertionError(f"missing completion condition: {item}")
    if "backlog instructions" not in workflow:
        raise AssertionError("WORKFLOW.md must reference Backlog.md canonical instructions")

    # The Canonical Completion Gate is defined once. Every other workflow file
    # references it by name; restating a condition is the duplication this
    # structure exists to prevent.
    for path in iter_template_files():
        if path.suffix != ".md" or path.name == "WORKFLOW.md":
            continue
        text = path.read_text(encoding="utf-8")
        for item in required:
            if item in text:
                raise AssertionError(
                    f"completion condition restated outside WORKFLOW.md: "
                    f"{path.relative_to(TEMPLATE_ROOT)} — reference the Canonical "
                    f"Completion Gate instead"
                )

    # Progressive disclosure: each mode reference is loaded only by the skills
    # whose phase needs it. A skill pointing at another phase's reference would
    # put that phase's context back into every run.
    phase_references = {
        "PLAN.md": {"backlog-plan", "backlog-review"},
        "EXECUTION.md": {"backlog-run", "backlog-auto"},
        "AUTO.md": {"backlog-auto"},
    }
    for skill_name in ("backlog-plan", "backlog-review", "backlog-run", "backlog-auto"):
        text = (TEMPLATE_ROOT / f".claude/skills/{skill_name}/SKILL.md").read_text(encoding="utf-8")
        if ".agent-workflow/WORKFLOW.md" not in text:
            raise AssertionError(f"{skill_name} must read the shared WORKFLOW.md")
        for reference, allowed in phase_references.items():
            mentioned = f".agent-workflow/{reference}" in text
            if skill_name in allowed and not mentioned:
                raise AssertionError(f"{skill_name} must read .agent-workflow/{reference}")
            if skill_name not in allowed and mentioned:
                raise AssertionError(
                    f"{skill_name} must not load .agent-workflow/{reference} "
                    f"(out-of-phase context)"
                )

    # No installed template may carry removed 1.0 behavior.
    for path in iter_template_files():
        assert_no_forbidden(path.read_text(encoding="utf-8"), f"template {path.relative_to(TEMPLATE_ROOT)}")

    if (TEMPLATE_ROOT / "README.md").exists():
        raise AssertionError("target template must not include README.md")

    # The workflow's blocked state is a real Backlog.md status, recorded as a role
    # so a project can rename it. Selection filters on `not_started`, which is
    # what keeps a blocked task out of the next /backlog-auto round.
    config = (TEMPLATE_ROOT / ".agent-workflow/config.yml").read_text(encoding="utf-8")
    roles = dict(re.findall(r"(?m)^  (not_started|active|blocked|done):\s*(.+?)\s*$", config))
    if len(roles) != 4:
        raise AssertionError(f"config.yml must define all four status roles, got {sorted(roles)}")
    if len(set(roles.values())) != 4:
        raise AssertionError(f"status roles must be distinct statuses: {roles}")
    auto = (TEMPLATE_ROOT / ".agent-workflow/AUTO.md").read_text(encoding="utf-8")
    if "not-started status" not in auto:
        raise AssertionError("AUTO.md selection must filter on the not-started status")
    if "blocked" not in workflow.lower() or "<blocked status>" not in workflow:
        raise AssertionError("WORKFLOW.md must define how a true blocker is written to a status")

    # Backlog.md `autoCommit` defaults to off, so an uncommitted claim sits on the
    # same task files the workers change and aborts the whole batch merge. The
    # commit must come before any worktree exists.
    checkpoint = "Commit the claims before creating any worktree"
    if checkpoint not in auto:
        raise AssertionError(f"AUTO.md must instruct: {checkpoint!r}")
    if auto.index(checkpoint) > auto.index("git worktree add"):
        raise AssertionError("AUTO.md must commit the batch claims before creating worktrees")
    if "git add backlog && git commit" not in auto:
        raise AssertionError("AUTO.md must show the claim commit, not just describe it")
    if "autoCommit" not in auto:
        raise AssertionError("AUTO.md must explain the autoCommit default the checkpoint exists for")

    # Workers branch from a commit, so uncommitted source work in the base tree is
    # invisible to them — silently, when the changed files do not overlap. A
    # parallel batch must refuse to start against a dirty tracked source tree.
    flat_auto = re.sub(r"\s+", " ", auto)
    precondition = "no staged, modified, deleted, renamed, or untracked non-ignored files"
    if precondition not in flat_auto:
        raise AssertionError(f"AUTO.md must state the parallel precondition: {precondition!r}")
    check = "git status --porcelain --untracked-files=normal -- . ':(exclude)backlog'"
    if check not in auto:
        raise AssertionError(f"AUTO.md must show the precondition check verbatim: {check!r}")
    if flat_auto.index(precondition) > flat_auto.index('backlog task edit <TASK-ID> -s "<active'):
        raise AssertionError("AUTO.md must check the clean-source precondition before claiming")
    if "Do not stash, commit, discard, or otherwise modify the user's working changes" not in flat_auto:
        raise AssertionError("AUTO.md must leave the user's in-progress work alone")
    # Ignored paths are not project state a worker needs; blocking on them would
    # trip on build output and make the precondition unusable.
    if "Ignored files do not block parallel execution" not in flat_auto:
        raise AssertionError("AUTO.md must exempt ignored paths from the precondition")
    if "--ignored" not in auto or "Do not add `--ignored`" not in flat_auto:
        raise AssertionError("AUTO.md must warn against adding --ignored to the check")

    # The Ready Gate is an execution invariant: /backlog-run never reads PLAN.md,
    # so a gate that only lived there could not stop an unready task.
    if "## Task Ready Gate" not in workflow:
        raise AssertionError("WORKFLOW.md must carry the Task Ready Gate as a shared invariant")
    execution = (TEMPLATE_ROOT / ".agent-workflow/EXECUTION.md").read_text(encoding="utf-8")
    if "Task Ready Gate" not in execution:
        raise AssertionError("EXECUTION.md must check the Task Ready Gate")
    if execution.index("Task Ready Gate") > execution.index('-s "<active status>"'):
        raise AssertionError("EXECUTION.md must check the Ready Gate before claiming the task")

    # `--ready` alone still returns claimed and blocked tasks, so every documented
    # selection query must carry the status filter that makes the loop terminate.
    for path in [*iter_template_files(), ROOT / "README.md", ROOT.parent / "README.md"]:
        if path.suffix != ".md" or not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "task list --ready" in line and "--status" not in line:
                raise AssertionError(
                    f"selection query without --status in {path.name}: {line.strip()!r}"
                )

    # Installation must go through a manifest, never a recursive copy of the
    # working tree: that is how untracked runtime state gets installed.
    install_md = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
    for banned in ("cp -R backlog-workflow", "cp -r backlog-workflow", "Copy-Item -Recurse"):
        if banned in install_md:
            raise AssertionError(f"INSTALL.md must not teach a recursive working-tree copy: {banned!r}")
    if "git archive" not in install_md or "npx skills add" not in install_md:
        raise AssertionError("INSTALL.md must install through the packaged installers or git archive")

    tracked = subprocess.run(
        ["git", "ls-files", "--", str(ROOT.name)],
        cwd=ROOT.parent, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
    )
    if tracked.returncode == 0 and tracked.stdout.strip():
        for line in tracked.stdout.splitlines():
            if re.search(r"(^|/)(\.omc|__pycache__|node_modules)(/|$)|\.pyc$", line):
                raise AssertionError(f"runtime state is tracked in the package: {line}")

    # install.py must agree on the version and define the legacy migration proof.
    install_py = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
    if f'VERSION = "{VERSION}"' not in install_py:
        raise AssertionError("install.py VERSION constant must match VERSION file")
    if "LEGACY_TASK_TEMPLATE_HASH" not in install_py or "migrate_deprecated_task_template" not in install_py:
        raise AssertionError("install.py must implement the deprecated TASK-TEMPLATE migration")
    if "verify_backlog_cli" not in install_py or "resolve_backlog_cli" not in install_py:
        raise AssertionError("install.py must verify the Backlog.md CLI before accepting it")
    if "effective_backlog_cli" not in install_py or "backlog_init_command" not in install_py:
        raise AssertionError(
            "install.py must prefer the recorded CLI and initialize via the verified command"
        )

    print("Package validation passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"Package validation failed: {exc}", file=sys.stderr)
        sys.exit(2)
