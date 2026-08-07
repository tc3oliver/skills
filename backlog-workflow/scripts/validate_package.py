#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = ROOT / "templates" / "project"
SKILLS = [
    ROOT / "SKILL.md",
    TEMPLATE_ROOT / ".claude/skills/backlog-plan/SKILL.md",
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

    for name in ("backlog-workflow", "backlog-plan", "backlog-run", "backlog-auto"):
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
        TEMPLATE_ROOT / ".agent-workflow/config.yml",
        TEMPLATE_ROOT / ".agent-workflow/TASK-POLICY.md",
        TEMPLATE_ROOT / ".claude/skills/backlog-plan/SKILL.md",
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

    # No installed template may carry removed 1.0 behavior.
    for path in iter_template_files():
        assert_no_forbidden(path.read_text(encoding="utf-8"), f"template {path.relative_to(TEMPLATE_ROOT)}")

    if (TEMPLATE_ROOT / "README.md").exists():
        raise AssertionError("target template must not include README.md")

    # install.py must agree on the version and define the legacy migration proof.
    install_py = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
    if f'VERSION = "{VERSION}"' not in install_py:
        raise AssertionError("install.py VERSION constant must match VERSION file")
    if "LEGACY_TASK_TEMPLATE_HASH" not in install_py or "migrate_deprecated_task_template" not in install_py:
        raise AssertionError("install.py must implement the deprecated TASK-TEMPLATE migration")

    print("Package validation passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"Package validation failed: {exc}", file=sys.stderr)
        sys.exit(2)
