---
name: backlog-workflow
description: Install, audit, or upgrade the versioned Backlog.md workflow in the current project. Supports new and existing projects and installs manual planning/execution plus explicit automatic execution skills.
argument-hint: "[apply|audit|upgrade]"
arguments: action
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

# Backlog Workflow Manager

Action: `$action`

Use `apply` when the action is empty. Accept only `apply`, `audit`, or `upgrade`.

## Required reading

Read these before acting:

- [references/OPERATIONS.md](references/OPERATIONS.md)
- [references/PROJECT-DISCOVERY.md](references/PROJECT-DISCOVERY.md) when applying or upgrading

## Operation

1. Resolve the project root with `git rev-parse --show-toplevel`; otherwise use the current directory.
2. Inspect `git status --short` and treat existing changes as user-owned.
3. Do not initialize Backlog.md manually. The installer creates the workspace
   non-interactively when none exists, and blocks if initialization fails.
   Do not create speculative product tasks.
4. Run the bundled installer:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/install.py" "$action" --project "<project-root>"
```

Use `python` instead of `python3` only when that is the available interpreter.

5. For `apply` or `upgrade`, review the generated `.agent-workflow/PROJECT.md` against repository evidence and correct only inaccurate detected facts. Preserve valid project-specific additions.
6. Validate with:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/install.py" audit --project "<project-root>"
```

7. Report the operation using the exact compact format from `references/OPERATIONS.md`.

## Safety

- Do not modify `README.md`.
- Do not delete, recreate, archive, renumber, or change existing Backlog.md tasks.
- Do not rewrite PRDs, requirement matrices, ADRs, architecture files, or user-owned instructions.
- Do not begin product implementation.
- Do not silently overwrite unmanaged files at paths owned by this workflow. Report the conflict and stop.
- `upgrade` updates only files marked as managed by this workflow.
