---
name: backlog-workflow
description: Install, audit, or upgrade the versioned Backlog.md workflow in the current project. Installs the requirement-planning, decomposition-review, single-task-execution, and explicit autonomous-execution skills as a policy/orchestration layer over Backlog.md.
argument-hint: "[apply|audit|upgrade]"
arguments: action
disable-model-invocation: true
allowed-tools: Read Glob Grep Bash Edit Write Skill
---

# Backlog Workflow Manager

Action: `$action`

Use `apply` when the action is empty. Accept only `apply`, `audit`, or `upgrade`.

## Architecture

This package is a **policy + orchestration layer** over Backlog.md:

- **Backlog.md** = the task/workflow engine (task schema, lifecycle, Acceptance
  Criteria, Definition of Done, Implementation Plan, Implementation Notes, Final
  Summary, dependencies, CLI, JSON interface, canonical instructions).
- **backlog-workflow** = development policy and orchestration on top of Backlog.md
  (modes, requirement authority, task decomposition policy, decomposition review,
  approval boundaries, grilling/decision policy, blocker policy, the Canonical
  Completion Gate, and autonomous execution).
- **PROJECT.md** = repository-specific configuration.
- **PRD/spec** = product truth.

Backlog.md canonical instructions are the single source of truth for Backlog
mechanics. This workflow does not duplicate them.

## Required reading

Read these before acting:

- [references/OPERATIONS.md](references/OPERATIONS.md)
- [references/PROJECT-DISCOVERY.md](references/PROJECT-DISCOVERY.md) when applying or upgrading

## Operation

1. Resolve the project root with `git rev-parse --show-toplevel`; otherwise use the current directory.
2. Inspect `git status --short` and treat existing changes as user-owned.
3. Do not initialize Backlog.md manually. The installer creates the workspace
   non-interactively when none exists, and blocks if initialization fails.
   Initialization passes `--agent-instructions none` because this workflow owns
   its managed CLAUDE.md/AGENTS.md blocks. Do not create speculative product
   tasks.
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
- `upgrade` updates only files marked as managed by this workflow, and migrates the deprecated managed `TASK-TEMPLATE.md` to `TASK-POLICY.md` (managed copy removed; unmanaged copy preserved).
- Do not install or configure MCP. The Backlog.md CLI is the required interface; MCP is optional and user-managed.
