# audit-claude-md

An agent-instruction audit skill that retains its historical
`audit-claude-md` name for backward compatibility.

`AGENTS.md`, `CLAUDE.md`, and scoped rules rot. They accumulate directory trees that went stale, progress
notes from three months ago, rules that only apply to one subdirectory, and
vague requests like "write good code" that change no behavior. All of it loads
into context on every single task.

This skill reviews every rule individually and acts on it — it does not just
report suggestions.

## What it does

Each rule gets exactly one disposition:

| Disposition | Meaning |
|---|---|
| `KEEP_ROOT` | Applies to nearly all work, stable, project-specific — stays in canonical `AGENTS.md` (or `CLAUDE.md` only when Claude-specific). |
| `MOVE_PATH` | Only applies to one directory or file type — moves to a nested instruction file or path-scoped rule. |
| `MOVE_SKILL` | A multi-step procedure or checklist — moves to canonical `.agents/skills/<name>/SKILL.md`, with a thin tool adapter when needed. |
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

Invoke the skill deliberately because it edits agent-facing files.

Before making changes it checks `git status` and warns if the target files
already have uncommitted edits, since its own diff would otherwise be
indistinguishable from yours.

## Scope

Modifies agent instruction files, scoped rules, and canonical
`.agents/skills/*/SKILL.md` when a procedure needs extracting. It may repair a
thin `.claude/skills` compatibility adapter, but does not create a second full
skill definition there.

Never modifies product code, or `CLAUDE.local.md` unless you ask.

Shared rules belong in `AGENTS.md`; `CLAUDE.md` remains available for
Claude-specific compatibility. Existing user-owned content is reviewed
conservatively rather than overwritten wholesale.

## Note

The skill's own instructions are written in Traditional Chinese.
