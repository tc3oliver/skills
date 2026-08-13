<!-- Managed by backlog-workflow 1.4.0 -->

# Backlog Development Workflow

Development policy on top of Backlog.md. Backlog.md owns task mechanics; this
file owns the invariants every mode shares.

Read this file, then the one reference for the mode you are actually running.

## Mode routing

| Mode | Entry point | Read next |
|---|---|---|
| Planning | `/backlog-plan <requirement, topic, or document path>` | `.agent-workflow/PLAN.md` |
| Decomposition review | `/backlog-review [requirement source or scope]` | `.agent-workflow/PLAN.md` |
| Single-task execution | `/backlog-run <TASK-ID>` | `.agent-workflow/EXECUTION.md` |
| Autonomous execution | `/backlog-auto [TASK-ID]` | `.agent-workflow/AUTO.md`, then `.agent-workflow/EXECUTION.md` |

Do not read a mode reference you are not running.

The default mode is manual: planning and execution are separate user-triggered
stages. That does not mean waiting for approval after every engineering step.
Autonomous execution starts only through `/backlog-auto`; "continue development"
does not start it.

The slash commands are Claude Code entry points. Any coding agent can follow the
same process by reading this file plus the mode reference it needs.

## Responsibility boundary

Backlog.md canonical instructions define how Backlog.md is operated: task schema,
lifecycle, fields, CLI, and JSON interface. Load them where each mode reference
says to:

```bash
backlog instructions overview
backlog instructions task-creation
backlog instructions task-execution
backlog instructions task-finalization
```

Do not duplicate upstream Backlog.md mechanics. This workflow adds policy and
explicit overrides, nothing else.

### Command convention

`backlog` in every example is a placeholder for the exact CLI command recorded in
`.agent-workflow/PROJECT.md` (for example `backlog`, `npx backlog`, or
`npx backlog.md`). Run the recorded command verbatim.

### Status roles

Backlog.md status names are per-project. `.agent-workflow/config.yml` records
which configured status plays each workflow role:

```yaml
statuses:
  not_started: To Do
  active: In Progress
  blocked: Blocked
  done: Done
```

Read those values instead of assuming names, and pass them verbatim to
`-s`/`--status`. Where this workflow writes `<blocked status>`, it means the
`blocked` value here.

### Backlog interface policy

The Backlog.md CLI is the required interface. Mutate tasks through
`backlog task ...`; do not parse or rewrite `backlog/tasks/*.md` for normal task
operations. Read task state through the structured JSON interface
(`backlog task list --json`, `backlog task <TASK-ID> --json`).

MCP is optional and user-managed. This workflow does not install or configure
MCP and never registers an MCP server; it must run with only the CLI available.

## Sources of truth

- Backlog.md canonical instructions — Backlog mechanics.
- PRDs, specifications, and requirement matrices — product intent, scope, and
  acceptance intent.
- Backlog.md decision records (`backlog decision create`) — a decision reached
  through `grilling`, authoritative from the moment it is written.
- `.agent-workflow/PROJECT.md` — repository-specific commands, paths, constraints.
- `CLAUDE.md` and `AGENTS.md` — workflow entry points and project rules.

A task must not silently introduce, remove, or reinterpret a product requirement.
Resolve conflicts in the authoritative source before implementation.

### Requirement traceability

A task records its authoritative source in the Backlog.md native `documentation`
field, so traceability is queryable instead of parsed out of Markdown:

```bash
backlog task create "<title>" --doc "docs/PRD.md#feature-x"
backlog task edit <TASK-ID> --doc "decision-3"
```

Use `--ref` for supporting material that is not the authority (issue links, prior
art, related code). Both come back from `backlog task <TASK-ID> --json` as
`documentation` and `references`.

A task with an empty `documentation` is unsourced work.

## Decision policy

A decision reached through `grilling` is not a requirement source until it is
written down.

- **Confined to one task's implementation** — record it in that task; no decision
  record needed.
- **Binds future tasks, or the task would otherwise have nothing authoritative to
  cite** — create a decision record (`backlog decision create "<title>"`) before
  creating or updating any task that depends on it. Fill its Context (the open
  question and why it was open), Decision (what was confirmed with the user), and
  Consequences (what it rules out or commits future work to). One record per
  distinct decision; several tasks may cite the same record.

A decision record fixes one choice at a point in time. A doc (`backlog doc
create`, typically `--type specification` or `guide`) is longer-form living
material meant to stay current. When a grilled decision changes an existing
specification, do both: record the decision, update the doc.

## Canonical Completion Gate

A task may be marked `Done` only when all four conditions hold:

1. Acceptance Criteria all pass.
2. Required tests, lint, typecheck, and build pass.
3. Documentation and Requirement Matrix are synchronized.
4. The task record contains validation evidence.

Only checks applicable to the task and supported by repository evidence are
required. Record an unavailable or non-applicable check explicitly rather than
inventing one — including "no Requirement Matrix exists" for condition 3.

PR/MR, CI, review fixes, and merge are the standard delivery flow when available.
They are not a fifth condition.

This gate is the only definition of completeness in this workflow. Every other
file references it and does not restate it.

### Native Definition of Done binding

The gate travels with each task as Backlog.md Definition of Done items:

- `Acceptance Criteria all pass`
- `Required applicable tests, lint, typecheck, and build pass`
- `Documentation and Requirement Matrix are synchronized when applicable`
- `Validation evidence is recorded in the task`

`/backlog-plan` adds them at creation with one repeatable `--dod` per item.
Before starting work, `/backlog-run` and `/backlog-auto` read `definitionOfDone`
from `backlog task <TASK-ID> --json` and append any missing item with `backlog
task edit <TASK-ID> --dod "<item>"`, so a task created before this binding, or
outside the workflow, cannot bypass the gate.

Task-specific completion requirements belong in the same native Definition of
Done, alongside these four.

## True blockers

Stop or block a task only for:

1. Contradictory product requirements or Acceptance Criteria
2. Missing required permission, credential, external service, or hardware
3. Existing uncommitted changes overlapping the task in a way that cannot be
   safely isolated
4. Incomplete task dependency
5. An irreversible product, data, or architecture decision not defined by an
   authoritative source
6. A newly discovered critical defect whose safe resolution materially exceeds
   the task scope

Implementation patterns, code navigation, task-scoped refactoring, test fixes,
and reversible engineering choices are not blockers.

On a true blocker, put the task in the blocked status and record why:

```bash
backlog task edit <TASK-ID> -s "<blocked status>" --append-notes "Blocked: <evidence>"
```

The status is what carries the blocked state forward — `/backlog-auto` selects on
the not-started status, so a task parked in the blocked status is out of the next
round by construction, with nothing to remember. Reporting `Status: Blocked`
without writing the status leaves the task selectable.

## Change discipline

- Do not mix unrelated cleanup into a task. Cleanup required for correctness is
  in scope; broad cleanup discovered during execution becomes a separate task.
- Remove obsolete code when the task's correctness requires it.
- Do not add placeholders or knowingly incomplete behavior and mark it complete.
- Keep internal autonomous-development mechanics out of public README and product
  documentation unless explicitly required.

## Language

Write Backlog.md free-text content — title, description, Acceptance Criteria,
Implementation Plan, Implementation Notes, Final Summary, and decision records —
in the language the user writes requirements in for this project. The board is a
working artifact for the user; it should not need translation to read.

- Code, identifiers, file paths, commands, and quoted command/log output stay
  as-is.
- CLI flags, native field names, and enumerated field values (status, priority)
  stay in canonical English.
- Quote an authoritative source in its original language where traceability needs
  the exact wording.
- Report field labels may be localized; report field values keep their defined
  English vocabulary — `Status` is `Done`, `Blocked`, or `In Progress`, and
  `Verdict` is `Satisfied`, `Gaps found`, or `Undetermined`.
