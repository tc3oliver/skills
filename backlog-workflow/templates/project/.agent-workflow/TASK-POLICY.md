<!-- Managed by backlog-workflow 1.5.0 -->

# Backlog Task Policy

What this project puts in a task beyond what Backlog.md already models.

Backlog.md owns these native fields. Set them through the CLI, never by editing
`backlog/tasks/*.md`, and do not restate them in the description:

| Content | CLI flag | JSON key |
|---|---|---|
| Authoritative requirement source | `--doc` | `documentation` |
| Supporting material | `--ref` | `references` |
| Dependencies | `--dep` | `dependencies` |
| Acceptance Criteria | `--ac` | `acceptanceCriteria` |
| Definition of Done | `--dod` | `definitionOfDone` |
| Implementation Plan | `--plan` | `implementationPlan` |
| Implementation Notes | `--notes` | `implementationNotes` |
| Final Summary | `--final-summary` | `finalSummary` |

## Description

The description carries what Backlog.md has no field for. Omit a heading that is
genuinely not applicable; do not invent content to fill it.

### Goal

One observable outcome.

### Scope / Out of scope

What this task changes, and the adjacent work it explicitly does not. Out of
scope is what keeps a task from growing during execution — state it even when it
looks obvious.

### Constraints

Repository-supported constraints any implementation must respect: supported
runtimes, public API contracts, performance budgets, and project conventions that
are not discoverable from the code being changed.

### Validation

How this task will be objectively validated: the verified commands from
`.agent-workflow/PROJECT.md`, plus the automated or manual test coverage this
task requires. A command recorded as `not detected` must not be invented. When
the task needs no new tests, say so with the reason.

### Impacts

List only the ones that apply: security, data/schema, API/compatibility,
documentation, migration/rollback.

## Completion

The Canonical Completion Gate in `.agent-workflow/WORKFLOW.md` defines when a
task is `Done`, and is bound to every task as Definition of Done items. Record
task-specific completion requirements as further `--dod` items rather than as
description prose.
