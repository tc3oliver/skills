#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = [
    ROOT / "SKILL.md",
    ROOT / "templates/project/.claude/skills/backlog-plan/SKILL.md",
    ROOT / "templates/project/.claude/skills/backlog-run/SKILL.md",
    ROOT / "templates/project/.claude/skills/backlog-auto/SKILL.md",
    ROOT / "templates/project/.claude/skills/grilling/SKILL.md",
]


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


def main() -> int:
    seen: set[str] = set()
    for path in SKILLS:
        data = frontmatter(path)
        name = data.get("name")
        if not isinstance(name, str) or not name:
            raise AssertionError(f"missing name: {path}")
        if name in seen:
            raise AssertionError(f"duplicate skill name: {name}")
        seen.add(name)
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

    config = (ROOT / "templates/project/.agent-workflow/config.yml").read_text(encoding="utf-8")
    if "default_mode: manual" not in config:
        raise AssertionError("default mode must be manual")

    workflow = (ROOT / "templates/project/.agent-workflow/WORKFLOW.md").read_text(encoding="utf-8")
    required = [
        "Acceptance Criteria all pass.",
        "Required tests, lint, typecheck, and build pass.",
        "Documentation and Requirement Matrix are synchronized.",
        "The task record contains validation evidence.",
    ]
    for item in required:
        if item not in workflow:
            raise AssertionError(f"missing completion condition: {item}")

    if (ROOT / "templates/project/README.md").exists():
        raise AssertionError("target template must not include README.md")

    print("Package validation passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AssertionError as exc:
        print(f"Package validation failed: {exc}", file=sys.stderr)
        sys.exit(2)
