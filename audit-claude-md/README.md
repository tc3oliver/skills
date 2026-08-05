# audit-claude-md

A Claude Code skill that audits and restructures a project's Claude instructions.

`CLAUDE.md` files rot. They accumulate directory trees that went stale, progress
notes from three months ago, rules that only apply to one subdirectory, and
vague requests like "write good code" that change no behavior. All of it loads
into context on every single task.

This skill reviews every rule individually and acts on it — it does not just
report suggestions.

## What it does

Each rule gets exactly one disposition:

| Disposition | Meaning |
|---|---|
| `KEEP_ROOT` | Applies to nearly all work, stable, project-specific — stays in the root `CLAUDE.md`. |
| `MOVE_PATH` | Only applies to one directory or file type — moves to a nested `CLAUDE.md` or a path-scoped `.claude/rules/*.md`. |
| `MOVE_SKILL` | A multi-step procedure or checklist — moves to `.claude/skills/<name>/SKILL.md`. |
| `MOVE_DOC` | Long-form background or history — moves to real documentation. |
| `REWRITE` | Worth keeping, but vague, unverifiable, or mixing several requirements. |
| `DELETE` | Stale, duplicated, generic, or trivially rediscoverable. |
| `ENFORCEMENT_GAP` | A hard prohibition that only exists as prose — flags where a hook, CI check, or linter belongs. |

Deletion is deliberately conservative: "findable in the code" is not sufficient
grounds on its own, and anything that looks like important tacit knowledge but
cannot be verified from the repository is kept and listed for human review.

## Usage

```text
/audit-claude-md                 # audit the whole repository
/audit-claude-md packages/web    # audit a subtree
```

The skill is user-invoked only (`disable-model-invocation: true`) — it edits
files, so it never triggers on its own.

Before making changes it checks `git status` and warns if the target files
already have uncommitted edits, since its own diff would otherwise be
indistinguishable from yours.

## Scope

Modifies only: `CLAUDE.md` (root and nested), `.claude/rules/**/*.md`, and
`.claude/skills/*/SKILL.md` when a procedure needs extracting.

Never modifies product code, or `CLAUDE.local.md` unless you ask.

`AGENTS.md` and other agents' instruction files are read but never written —
they are only used to detect rules that conflict with `CLAUDE.md`, which get
reported for you to resolve.

## Note

The skill's own instructions are written in Traditional Chinese.
