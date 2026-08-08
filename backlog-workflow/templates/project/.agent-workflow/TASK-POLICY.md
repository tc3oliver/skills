<!-- Managed by backlog-workflow 1.2.0 -->

# Backlog Task Policy

This file defines the **additional project task semantics** layered on top of
Backlog.md. It is policy, not a task schema.

Backlog.md owns the task schema and these native fields — use them, do not
duplicate them:

- Acceptance Criteria
- Definition of Done
- Dependencies
- Implementation Plan
- Implementation Notes
- Final Summary

Create and edit tasks through the Backlog.md CLI (`backlog task create`,
`backlog task edit`). Do not hand-author these native fields by editing
`backlog/tasks/*.md`.

## Additional task policy fields

Capture the following in the task description or body. Omit sections that are
genuinely not applicable; do not invent content merely to fill the policy.

### Requirement Source

- `<PRD/spec/requirement-matrix path, or decision-<id> (<decision title>)>`

The authoritative source for this task's product intent. A task must not
silently introduce, remove, or reinterpret a requirement.

### Goal

- <One observable outcome.>

### Scope

- <Included work.>

### Out of Scope

- <Explicit exclusions.>

### Stable implementation constraints

- <Repository-supported constraints that any implementation must respect, e.g.
  supported runtimes, public API contracts, performance budgets.>

### Validation

- <How this task will be objectively validated: verified commands from
  `.agent-workflow/PROJECT.md`, or a concrete manual validation method. Commands
  marked `not detected` must not be invented.>

### Test Requirements

- <Required automated or manual test coverage, or "Not applicable" with reason.>

### Impacts

- Security: <impact or None>
- Data / Schema: <impact or None>
- API / Compatibility: <impact or None>
- Documentation: <files or None>
- Migration / Rollback: <requirements or None>

## Completion policy

A task may be marked `Done` only when all four conditions hold (see
`.agent-workflow/WORKFLOW.md`):

1. Acceptance Criteria all pass.
2. Required applicable tests, lint, typecheck, and build pass.
3. Documentation and Requirement Matrix are synchronized.
4. The task record contains validation evidence.

Record checks that do not exist or do not apply as unavailable or not
applicable rather than inventing them. PR/MR, CI, review, and merge are the
standard delivery flow when available; they are not a fifth completion
condition.
